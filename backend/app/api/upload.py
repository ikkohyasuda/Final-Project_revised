import io
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

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'heic', 'heif'}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
TARGET_IMAGE_BYTES = 300 * 1024


def _validate_extension(filename: str) -> str:
    """拡張子を検証して返す。"""

    ext = Path(filename).suffix.lower().lstrip('.')
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='対応形式はJPEG/PNG/HEICのみです。',
        )
    return ext


def _process_image(contents: bytes, ext: str) -> tuple[bytes, str]:
    """画像をPNGに変換し、必要ならサイズを圧縮する。"""

    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - import guard
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='画像変換に必要なライブラリがインストールされていません。',
        ) from exc

    try:
        if ext in {'heic', 'heif'}:
            try:
                import pillow_heif  # type: ignore
            except ImportError as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail='HEICの読み込みに必要なライブラリがインストールされていません。',
                ) from exc
            pillow_heif.register_heif_opener()
        image = Image.open(io.BytesIO(contents))
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='画像ファイルを読み込めません。',
        ) from exc

    # PNGへ統一（透過があれば保持する）
    if image.mode not in ('RGB', 'RGBA'):
        image = image.convert('RGBA' if 'A' in image.mode else 'RGB')

    def save_png(img: Image.Image) -> bytes:
        buffer = io.BytesIO()
        img.save(buffer, format='PNG', optimize=True)
        return buffer.getvalue()

    def save_jpeg(img: Image.Image, quality: int) -> bytes:
        buffer = io.BytesIO()
        img.convert('RGB').save(buffer, format='JPEG', quality=quality, optimize=True)
        return buffer.getvalue()

    processed = save_png(image)
    if len(processed) <= TARGET_IMAGE_BYTES:
        return processed, 'png'

    # サイズが大きい場合は段階的に縮小する
    scale = 0.9
    for _ in range(8):
        new_width = max(1, int(image.width * scale))
        new_height = max(1, int(image.height * scale))
        resized = image.resize((new_width, new_height), Image.LANCZOS)
        processed = save_png(resized)
        if len(processed) <= TARGET_IMAGE_BYTES:
            return processed, 'png'
        scale *= 0.85

    # PNGで収まらない場合はJPEGに変換して圧縮する
    jpeg_quality = 85
    processed_jpeg = save_jpeg(image, jpeg_quality)
    if len(processed_jpeg) <= TARGET_IMAGE_BYTES:
        return processed_jpeg, 'jpg'

    resized = image
    for _ in range(8):
        new_width = max(1, int(resized.width * 0.9))
        new_height = max(1, int(resized.height * 0.9))
        resized = resized.resize((new_width, new_height), Image.LANCZOS)
        for quality in (80, 70, 60, 50):
            processed_jpeg = save_jpeg(resized, quality)
            if len(processed_jpeg) <= TARGET_IMAGE_BYTES:
                return processed_jpeg, 'jpg'

    return processed_jpeg, 'jpg'


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
    processed, stored_ext = _process_image(contents, ext)
    filename = f'{uuid4().hex}.{stored_ext}'
    relative_path = Path('static') / 'uploads' / filename
    full_path = BASE_DIR / relative_path

    try:
        full_path.write_bytes(processed)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='ファイルの保存に失敗しました。',
        ) from exc

    try:
        db.connect(reuse_if_open=True)
        image = UploadedImage.create(
            file_path=str(relative_path),
            file_format=stored_ext,
            file_size=len(processed),
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
