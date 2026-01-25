from datetime import datetime

from peewee import AutoField, CharField, DateTimeField, TextField

from backend.app.db.database import BaseModel


class Medicine(BaseModel):
    """薬剤マスタモデル。"""

    medicine_id = AutoField(primary_key=True)
    medicine_name = CharField(max_length=200, null=False, index=True)
    generic_name = CharField(max_length=200, null=False, index=True)
    drug_category = CharField(max_length=100, null=False, index=True)
    caution_reason = TextField(null=True)
    reference_source = CharField(max_length=200, null=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'medicines'
        indexes = ((('medicine_name',), False), (('generic_name',), False), (('drug_category',), False))

    def save(self, *args: object, **kwargs: object) -> int:
        """保存時にupdated_atを自動更新する。"""

        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)
