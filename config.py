import os
from pathlib import Path
from typing import Optional, Set

from pydantic import BaseSettings, Field

BASE_DIR = Path(os.environ.get('PROJECT_ROOT', Path(__file__).resolve().parent))
DEFAULT_INSTANCE_DIR = BASE_DIR / 'instance'
DEFAULT_UPLOAD_DIR = BASE_DIR / 'static' / 'uploads'
DEFAULT_DATA_DIR = BASE_DIR / 'backend' / 'data'


class Settings(BaseSettings):
    """患者参加型・薬の安全チェックアプリの設定。"""

    app_name: str = Field('med_safety_check', env='APP_NAME')
    api_prefix: str = Field('/api', env='API_PREFIX')
    environment: str = Field('development', env='APP_ENV')
    debug: bool = Field(False, env='DEBUG')

    secret_key: str = Field('dev-secret-key-please-change-in-production', env='SECRET_KEY')

    database_name: str = Field('medication_checker.db', env='DATABASE_NAME')
    instance_dir: Path = Field(DEFAULT_INSTANCE_DIR, env='INSTANCE_DIR')

    upload_dir: Path = Field(DEFAULT_UPLOAD_DIR, env='UPLOAD_DIR')
    max_upload_bytes: int = Field(16 * 1024 * 1024, env='MAX_UPLOAD_BYTES')
    allowed_extensions: Set[str] = Field(default_factory=lambda: {'png', 'jpg', 'jpeg', 'gif'})

    ocr_provider: str = Field('tesseract', env='OCR_PROVIDER')
    tesseract_cmd: Optional[str] = Field(None, env='TESSERACT_CMD')
    gcv_project_id: Optional[str] = Field(None, env='GCV_PROJECT_ID')
    gcv_credentials_path: Optional[Path] = Field(None, env='GOOGLE_APPLICATION_CREDENTIALS')

    data_dir: Path = Field(DEFAULT_DATA_DIR, env='DATA_DIR')
    caution_medicines_csv: Path = Field(DEFAULT_DATA_DIR / 'caution_medicines.csv', env='CAUTION_MEDICINES_CSV')
    side_effects_csv: Path = Field(DEFAULT_DATA_DIR / 'side_effects.csv', env='SIDE_EFFECTS_CSV')

    class Config:
        """Pydantic設定."""

        env_file = '.env'
        case_sensitive = False

    @property
    def database_path(self) -> Path:
        """SQLiteデータベースのフルパスを返す。"""

        return self.instance_dir / self.database_name


settings = Settings()
