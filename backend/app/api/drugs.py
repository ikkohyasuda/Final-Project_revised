from typing import Optional

from fastapi import APIRouter, Form, HTTPException, status

from backend.app.db.database import db
from backend.app.models.extracted_medicine import ExtractedMedicine
from backend.app.models.matched_medicine import MatchedMedicine
from backend.app.models.medicine import Medicine
from backend.app.models.uploaded_image import UploadedImage

router = APIRouter()


def _normalize_text(value: str) -> str:
    """OCRテキストを正規化する。"""

    return value.strip().lower()


def _find_match(extracted_text: str, medicines: list[Medicine]) -> Optional[Medicine]:
    """抽出テキストに含まれる薬剤を探索する。"""

    normalized = _normalize_text(extracted_text)
    for medicine in medicines:
        name = (medicine.medicine_name or '').strip().lower()
        if name and name in normalized:
            return medicine
        generic = (medicine.generic_name or '').strip().lower()
        if generic and generic in normalized:
            return medicine
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

            existing = MatchedMedicine.get_or_none(
                (MatchedMedicine.extracted == item) & (MatchedMedicine.medicine == medicine)
            )
            if existing is None:
                MatchedMedicine.create(
                    extracted=item,
                    medicine=medicine,
                    is_matched=True,
                )

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
