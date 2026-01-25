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
        from PIL import Image
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

    # 軽い前処理で日本語OCRの精度を底上げする。
    image = image.convert('L')
    image = image.resize((image.width * 2, image.height * 2))
    image = image.point(lambda x: 0 if x < 160 else 255, mode='1')

    try:
        return pytesseract.image_to_string(image, lang=TESSERACT_LANG, config='--psm 6')
    except pytesseract.TesseractError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='OCR処理に失敗しました。',
        ) from exc


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
