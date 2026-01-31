import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Form, HTTPException, status

from backend.app.db.database import db
from backend.app.models.extracted_medicine import ExtractedMedicine
from backend.app.models.uploaded_image import UploadedImage

router = APIRouter()

BASE_DIR = Path(os.environ.get('PROJECT_ROOT', Path(__file__).resolve().parents[3]))
TESSERACT_LANG = os.environ.get('TESSERACT_LANG', 'jpn')

_TASKS: dict[str, dict[str, object]] = {}


def _split_lines(raw_text: str) -> list[str]:
    """OCR結果を行単位で整形する。"""

    return [line.strip() for line in raw_text.splitlines() if line.strip()]


def _run_ocr(image_path: Path) -> str:
    """画像からOCRテキストを取得する。"""

    try:
        from PIL import Image, ImageFilter, ImageOps, ImageEnhance
        import pytesseract
    except ImportError as exc:  # pragma: no cover - import guard
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='OCRに必要なライブラリがインストールされていません。',
        ) from exc

    try:
        image = Image.open(image_path)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='画像ファイルを読み込めません。',
        ) from exc

    # 複数の前処理パターンでOCRし、結果を統合する。
    base = image.convert('L')
    base = ImageOps.autocontrast(base)
    base = base.filter(ImageFilter.MedianFilter(size=3))

    # 速度優先: 2倍のみ + 二値化2パターン。
    base2x = base.resize((base.width * 2, base.height * 2))

    variants: list[Image.Image] = []
    sharpened = base2x.filter(ImageFilter.UnsharpMask(radius=1.5, percent=150, threshold=3))
    contrast = ImageEnhance.Contrast(sharpened).enhance(1.4)
    variants.append(contrast)
    for threshold in (160, 190):
        bw = contrast.point(lambda x, t=threshold: 0 if x < t else 255, mode='1').convert('L')
        variants.append(bw)

    psm_list = [6]

    def run_ocr_with_variants(target_variants: list[Image.Image], target_psm: list[int]) -> list[str]:
        results: list[str] = []
        for variant in target_variants:
            for psm in target_psm:
                try:
                    text = pytesseract.image_to_string(
                        variant,
                        lang=TESSERACT_LANG,
                        config=f'--oem 1 --psm {psm} -c preserve_interword_spaces=1 -c user_defined_dpi=300',
                    )
                    if text:
                        results.append(text)
                except pytesseract.TesseractError:
                    continue
        return results

    def katakana_ratio(text: str) -> float:
        if not text:
            return 0.0
        total = len(text)
        if total == 0:
            return 0.0
        katakana = sum(1 for ch in text if 'ァ' <= ch <= 'ン')
        return katakana / total

    # 1st pass: 軽量版
    results = run_ocr_with_variants(variants, psm_list)
    if results:
        combined = '\n'.join(results)
        # カタカナ比率が低い場合は重い再試行を実施
        if katakana_ratio(combined) >= 0.02:
            return combined

    # 2nd pass: 重めの再試行（3倍 + 追加PSM + 強めの二値化）
    heavy_variants: list[Image.Image] = []
    base3x = base.resize((base.width * 3, base.height * 3))
    sharpened3x = base3x.filter(ImageFilter.UnsharpMask(radius=1.5, percent=150, threshold=3))
    contrast3x = ImageEnhance.Contrast(sharpened3x).enhance(1.6)
    heavy_variants.append(contrast3x)
    for threshold in (140, 200):
        bw = contrast3x.point(lambda x, t=threshold: 0 if x < t else 255, mode='1').convert('L')
        heavy_variants.append(bw)
    heavy_psm = [3, 4, 6]
    results = run_ocr_with_variants(heavy_variants, heavy_psm)
    if not results:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='OCR処理に失敗しました。',
        )
    return '\n'.join(results)


@router.post('/api/ocr')
def start_ocr(image_id: int = Form(..., ge=1)) -> dict:
    """OCR処理を開始してタスクIDを返す。"""

    task_id = uuid4().hex
    _TASKS[task_id] = {'status': 'processing'}

    try:
        db.connect(reuse_if_open=True)
        image = UploadedImage.get_or_none(UploadedImage.image_id == image_id)
    finally:
        if not db.is_closed():
            db.close()

    if image is None:
        _TASKS[task_id] = {'status': 'failed', 'error': '指定された画像が見つかりません。'}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='指定された画像が見つかりません。',
        )

    image_path = BASE_DIR / image.file_path
    if not image_path.exists():
        _TASKS[task_id] = {'status': 'failed', 'error': '画像ファイルが見つかりません。'}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='画像ファイルが見つかりません。',
        )

    raw_text = _run_ocr(image_path)
    lines = _split_lines(raw_text)

    try:
        db.connect(reuse_if_open=True)
        extracted = [
            ExtractedMedicine.create(image=image, extracted_text=line)
            for line in lines
        ]
    finally:
        if not db.is_closed():
            db.close()

    result = {
        'image_id': image.image_id,
        'raw_text': raw_text,
        'items': [
            {
                'extracted_id': item.extracted_id,
                'text': item.extracted_text,
            }
            for item in extracted
        ],
    }
    _TASKS[task_id] = {'status': 'completed', 'result': result}
    return {'task_id': task_id}


@router.get('/api/ocr/status/{task_id}')
def get_ocr_status(task_id: str) -> dict:
    """OCRのステータスと結果を返す。"""

    task = _TASKS.get(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='指定されたタスクが見つかりません。',
        )

    response = {'task_id': task_id, 'status': task['status']}
    if task['status'] == 'failed':
        response['error'] = task.get('error', '処理に失敗しました。')
    if task['status'] == 'completed':
        response['result'] = task.get('result')
    return response
