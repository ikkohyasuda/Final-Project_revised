from datetime import datetime

from peewee import AutoField, DateTimeField, ForeignKeyField

from backend.app.db.database import BaseModel
from backend.app.models.matched_medicine import MatchedMedicine
from backend.app.models.side_effect import SideEffect


class CheckedSymptom(BaseModel):
    """チェック症状モデル。"""

    check_id = AutoField(primary_key=True)
    match = ForeignKeyField(MatchedMedicine, backref='checked_symptoms', on_delete='CASCADE')
    side_effect = ForeignKeyField(SideEffect, backref='checked_symptoms', on_delete='CASCADE')
    checked_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'checked_symptoms'
