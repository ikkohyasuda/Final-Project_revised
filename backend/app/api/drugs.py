from typing import Optional
import re
import unicodedata

from fastapi import APIRouter, Form, HTTPException, status

from backend.app.db.database import db
from backend.app.models.extracted_medicine import ExtractedMedicine
from backend.app.models.matched_medicine import MatchedMedicine
from backend.app.models.medicine import Medicine
from backend.app.models.uploaded_image import UploadedImage

router = APIRouter()


def _normalize_text(value: str) -> str:
    """OCRテキストを正規化する。"""

    if not value:
        return ''
    normalized = unicodedata.normalize('NFKC', value).lower()
    # Remove spaces and common separators to handle OCR splits.
    normalized = re.sub(r'[\s\u3000\u00b7\u30fb\u2212\-\u2010\u2011\u2012\u2013_]+', '', normalized)
    return normalized.strip()


def _normalize_for_fuzzy(value: str) -> str:
    """曖昧一致用にノイズを取り除く。"""

    normalized = _normalize_text(value)
    if not normalized:
        return ''
    normalized = re.sub(r'[0-9a-z.%/]+', '', normalized)
    # Remove common non-name kanji and symbols (dosage, units).
    normalized = re.sub(r'[\u4e00-\u9fff]+', '', normalized)
    # Normalize small kana and prolonged sound mark.
    normalized = normalized.translate(str.maketrans({
        'ぁ': 'あ', 'ぃ': 'い', 'ぅ': 'う', 'ぇ': 'え', 'ぉ': 'お',
        'っ': 'つ', 'ゃ': 'や', 'ゅ': 'ゆ', 'ょ': 'よ', 'ゎ': 'わ',
        'ァ': 'ア', 'ィ': 'イ', 'ゥ': 'ウ', 'ェ': 'エ', 'ォ': 'オ',
        'ッ': 'ツ', 'ャ': 'ヤ', 'ュ': 'ユ', 'ョ': 'ヨ', 'ヮ': 'ワ',
        'ヵ': 'カ', 'ヶ': 'ケ', 'ー': '',
    }))
    return normalized


_DAKUTEN_MAP = str.maketrans({
    'ガ': 'カ', 'ギ': 'キ', 'グ': 'ク', 'ゲ': 'ケ', 'ゴ': 'コ',
    'ザ': 'サ', 'ジ': 'シ', 'ズ': 'ス', 'ゼ': 'セ', 'ゾ': 'ソ',
    'ダ': 'タ', 'ヂ': 'チ', 'ヅ': 'ツ', 'デ': 'テ', 'ド': 'ト',
    'バ': 'ハ', 'ビ': 'ヒ', 'ブ': 'フ', 'ベ': 'ヘ', 'ボ': 'ホ',
    'パ': 'ハ', 'ピ': 'ヒ', 'プ': 'フ', 'ペ': 'ヘ', 'ポ': 'ホ',
    'ヴ': 'ウ',
})


def _strip_dakuten(value: str) -> str:
    """濁点・半濁点を除去して形を寄せる。"""

    if not value:
        return ''
    return value.translate(_DAKUTEN_MAP)


_CONFUSION_MAP: dict[str, str] = {
    '二': 'エニ',
    '丁': 'エ',
    '工': 'エ',
    '六': 'チロ',
    '口': 'ロ',
    '日': 'ロ',
    '一': 'ー',
    '五': 'ラ',
    '三': 'ミ',
    '七': 'ナ',
    '八': 'ハ',
    '九': 'ク',
    '巡': 'ム',
    '〇': 'ロ',
    '○': 'ロ',
}


def _generate_variants(value: str, limit: int = 20) -> list[str]:
    """OCR誤認識の補正候補を生成する。"""

    if not value:
        return []
    variants = ['']
    for char in value:
        replacements = _CONFUSION_MAP.get(char)
        if not replacements:
            variants = [v + char for v in variants]
            continue
        new_variants = []
        for v in variants:
            for rep in replacements:
                new_variants.append(v + rep)
                if len(new_variants) >= limit:
                    break
            if len(new_variants) >= limit:
                break
        variants = new_variants
    return variants


def _levenshtein(a: str, b: str) -> int:
    """レーベンシュタイン距離を返す。"""

    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            insert = curr[j - 1] + 1
            delete = prev[j] + 1
            replace = prev[j - 1] + (0 if ca == cb else 1)
            curr.append(min(insert, delete, replace))
        prev = curr
    return prev[-1]


def _find_match(extracted_text: str, medicines: list[Medicine]) -> Optional[Medicine]:
    """抽出テキストに含まれる薬剤を探索する。"""

    normalized = _normalize_text(extracted_text)
    # 似た語との誤検出が起きやすい薬剤は、厳密一致のみ許可する。
    strict_exact_only = {
        _normalize_text('アレルギン'),
    }
    strict_blocklist = {
        _normalize_text('アレルギン'): [_normalize_text('アレルギー')],
    }
    for medicine in medicines:
        name = (medicine.medicine_name or '').strip().lower()
        normalized_name = _normalize_text(medicine.medicine_name or '')
        if normalized_name in strict_exact_only:
            if any(block in normalized for block in strict_blocklist.get(normalized_name, [])):
                continue
        if name and name in normalized:
            return medicine
        generic = (medicine.generic_name or '').strip().lower()
        if generic and generic in normalized:
            return medicine

    # ここまでで一致しない場合は、曖昧一致を試す（誤判定を避けるため厳しめに）
    text_fuzzy = _normalize_for_fuzzy(extracted_text)
    if not text_fuzzy:
        return None

    text_fuzzy = _strip_dakuten(text_fuzzy)
    text_variants = _generate_variants(text_fuzzy)
    if not text_variants:
        text_variants = [text_fuzzy]

    best: Optional[Medicine] = None
    best_score = 0.0
    best_distance = 999

    for medicine in medicines:
        normalized_name = _normalize_text(medicine.medicine_name or '')
        if normalized_name in strict_exact_only:
            continue
        name = _strip_dakuten(_normalize_for_fuzzy(medicine.medicine_name or ''))
        if len(name) < 4:
            continue
        best_for_name = 0.0
        best_distance_for_name = 999
        for variant in text_variants:
            distance = _levenshtein(variant, name)
            max_len = max(len(variant), len(name))
            if max_len == 0:
                continue
            score = 1 - (distance / max_len)
            if score > best_for_name or (score == best_for_name and distance < best_distance_for_name):
                best_for_name = score
                best_distance_for_name = distance
        score = best_for_name
        distance = best_distance_for_name
        if score > best_score or (score == best_score and distance < best_distance):
            best_score = score
            best_distance = distance
            best = medicine

    if best is None:
        return None

    if best_score >= 0.6 and best_distance <= 3:
        return best
    return None


@router.post('/api/drugs/check')
def check_medicines(image_id: int = Form(..., ge=1)) -> dict:
    """抽出薬剤を注意薬剤マスタと照合する。"""

    try:
        db.connect(reuse_if_open=True)
        image = UploadedImage.get_or_none(UploadedImage.image_id == image_id)
        if image is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='指定された画像が見つかりません。',
            )

        extracted = list(
            ExtractedMedicine.select().where(ExtractedMedicine.image == image)
        )
        if not extracted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='照合対象の抽出結果がありません。',
            )

        extracted_ids = [item.extracted_id for item in extracted]
        if extracted_ids:
            MatchedMedicine.delete().where(MatchedMedicine.extracted.in_(extracted_ids)).execute()

        medicines = list(Medicine.select())

        matched_items = []
        unmatched_items = []
        matched_medicine_ids: set[int] = set()
        for item in extracted:
            medicine = _find_match(item.extracted_text, medicines)
            if medicine is None:
                unmatched_items.append(
                    {
                        'extracted_id': item.extracted_id,
                        'text': item.extracted_text,
                    }
                )
                continue

            # 同一薬剤が複数行で抽出された場合は重複を避ける。
            if medicine.medicine_id in matched_medicine_ids:
                continue

            existing = MatchedMedicine.get_or_none(
                (MatchedMedicine.extracted == item) & (MatchedMedicine.medicine == medicine)
            )
            if existing is None:
                MatchedMedicine.create(
                    extracted=item,
                    medicine=medicine,
                    is_matched=True,
                )

            matched_medicine_ids.add(medicine.medicine_id)
            matched_items.append(
                {
                    'extracted_id': item.extracted_id,
                    'text': item.extracted_text,
                    'medicine_id': medicine.medicine_id,
                    'medicine_name': medicine.medicine_name,
                    'generic_name': medicine.generic_name,
                }
            )
    finally:
        if not db.is_closed():
            db.close()

    return {
        'image_id': image_id,
        'matched': matched_items,
        'unmatched': unmatched_items,
    }
