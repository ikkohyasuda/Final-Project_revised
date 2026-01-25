from datetime import datetime

from peewee import AutoField, BooleanField, DateTimeField, ForeignKeyField, TextField

from backend.app.db.database import BaseModel
from backend.app.models.uploaded_image import UploadedImage


class ExtractedMedicine(BaseModel):
    """抽出薬剤モデル。"""

    extracted_id = AutoField(primary_key=True)
    image = ForeignKeyField(UploadedImage, backref='extracted_medicines', on_delete='CASCADE')
    extracted_text = TextField(null=False)
    is_manually_edited = BooleanField(default=False)
    extracted_at = DateTimeField(default=datetime.now)
    edited_at = DateTimeField(null=True)

    class Meta:
        table_name = 'extracted_medicines'
