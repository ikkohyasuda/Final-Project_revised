import os
from typing import Iterable

from peewee import Model, SqliteDatabase

DATABASE_PATH = os.environ.get('DATABASE_PATH', 'medication_checker.db')

db = SqliteDatabase(DATABASE_PATH)


class BaseModel(Model):
    """Peeweeモデルの共通設定。"""

    class Meta:
        database = db


def initialize_database(models: Iterable[type[Model]]) -> None:
    """データベースを初期化する。

    Args:
        models: 作成対象のモデル一覧。
    """

    db.connect(reuse_if_open=True)
    db.create_tables(list(models))


def close_database() -> None:
    """データベース接続を閉じる。"""

    if not db.is_closed():
        db.close()
