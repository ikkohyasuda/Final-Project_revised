import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from backend.app.db.database import db
from backend.app.models.uploaded_image import UploadedImage

router = APIRouter()

BASE_DIR = Path(os.environ.get('PROJECT_ROOT', Path(__file__).resolve().parents[3]))
UPLOAD_ROOT = Path(os.environ.get('UPLOAD_DIR', BASE_DIR / 'static' / 'uploads'))

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _validate_extension(filename: str) -> str:
    """拡張子を検証して返す。"""

    ext = Path(filename).suffix.lower().lstrip('.')
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='対応形式はJPEG/PNGのみです。',
        )
    return ext


@router.post('/api/upload')
async def upload_image(file: UploadFile = File(...)) -> dict:
    """画像をアップロードしてDBに保存する。"""

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='ファイル名が不正です。',
        )

    ext = _validate_extension(file.filename)
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail='ファイルサイズは10MB以下にしてください。',
        )

    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    filename = f'{uuid4().hex}.{ext}'
    relative_path = Path('static') / 'uploads' / filename
    full_path = BASE_DIR / relative_path

    try:
        full_path.write_bytes(contents)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='ファイルの保存に失敗しました。',
        ) from exc

    try:
        db.connect(reuse_if_open=True)
        image = UploadedImage.create(
            file_path=str(relative_path),
            file_format=ext,
            file_size=len(contents),
        )
    except Exception as exc:
        if full_path.exists():
            full_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='データベースの保存に失敗しました。',
        ) from exc
    finally:
        if not db.is_closed():
            db.close()

    return {
        'image_id': image.image_id,
        'file_path': image.file_path,
        'file_format': image.file_format,
        'file_size': image.file_size,
        'url': f'/api/images/{image.image_id}',
    }


@router.get('/api/images/{image_id}')
def get_image(image_id: int) -> FileResponse:
    """アップロード済みの画像を返す。"""

    try:
        db.connect(reuse_if_open=True)
        image = UploadedImage.get_or_none(UploadedImage.image_id == image_id)
    finally:
        if not db.is_closed():
            db.close()

    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='指定された画像が見つかりません。',
        )

    full_path = BASE_DIR / image.file_path
    if not full_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='画像ファイルが見つかりません。',
        )

    return FileResponse(path=full_path)
