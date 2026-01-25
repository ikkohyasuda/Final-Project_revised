from datetime import datetime

from peewee import AutoField, CharField, DateTimeField, ForeignKeyField

from backend.app.db.database import BaseModel
from backend.app.models.medicine import Medicine
from backend.app.models.side_effect import SideEffect


class MedicineSideEffect(BaseModel):
    """薬剤-副作用関連モデル。"""

    relation_id = AutoField(primary_key=True)
    medicine = ForeignKeyField(Medicine, backref='medicine_side_effects', on_delete='CASCADE')
    side_effect = ForeignKeyField(SideEffect, backref='medicine_side_effects', on_delete='CASCADE')
    frequency_note = CharField(max_length=200, null=True)
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'medicine_side_effect'
