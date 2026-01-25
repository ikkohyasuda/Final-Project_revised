from datetime import datetime

from peewee import AutoField, DateTimeField, ForeignKeyField

from backend.app.db.database import BaseModel
from backend.app.models.uploaded_image import UploadedImage


class SummarySheet(BaseModel):
    """症状まとめシートモデル。"""

    sheet_id = AutoField(primary_key=True)
    image = ForeignKeyField(UploadedImage, backref='summary_sheet', unique=True, on_delete='CASCADE')
    generated_at = DateTimeField(default=datetime.now)
    pdf_exported_at = DateTimeField(null=True)
    printed_at = DateTimeField(null=True)

    class Meta:
        table_name = 'summary_sheets'
