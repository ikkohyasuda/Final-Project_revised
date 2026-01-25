from datetime import datetime

from peewee import AutoField, CharField, DateTimeField, IntegerField

from backend.app.db.database import BaseModel


class UploadedImage(BaseModel):
    """アップロード画像モデル。"""

    image_id = AutoField(primary_key=True)
    file_path = CharField(max_length=500, null=False)
    file_format = CharField(max_length=20, null=False)
    file_size = IntegerField(null=False)
    uploaded_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'uploaded_images'
