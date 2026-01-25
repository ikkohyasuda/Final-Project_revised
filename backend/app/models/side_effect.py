from datetime import datetime

from peewee import AutoField, CharField, DateTimeField, TextField

from backend.app.db.database import BaseModel


class SideEffect(BaseModel):
    """副作用症状マスタモデル。"""

    side_effect_id = AutoField(primary_key=True)
    symptom_name = CharField(max_length=200, null=False, index=True)
    symptom_description = TextField(null=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'side_effects'

    def save(self, *args: object, **kwargs: object) -> int:
        """保存時にupdated_atを自動更新する。"""

        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)
