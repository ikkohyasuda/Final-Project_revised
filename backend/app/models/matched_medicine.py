from datetime import datetime

from peewee import AutoField, BooleanField, DateTimeField, ForeignKeyField

from backend.app.db.database import BaseModel
from backend.app.models.extracted_medicine import ExtractedMedicine
from backend.app.models.medicine import Medicine


class MatchedMedicine(BaseModel):
    """該当薬剤照合結果モデル。"""

    match_id = AutoField(primary_key=True)
    extracted = ForeignKeyField(ExtractedMedicine, backref='matched_medicines', on_delete='CASCADE')
    medicine = ForeignKeyField(Medicine, backref='matched_medicines', on_delete='CASCADE')
    is_matched = BooleanField(default=True)
    matched_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'matched_medicines'
