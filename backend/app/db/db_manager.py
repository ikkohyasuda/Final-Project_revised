from typing import Sequence, Type
from pathlib import Path

from peewee import Model

try:
    from backend.app.db.database import close_database, initialize_database
    from backend.app.models import (
        CheckedSymptom,
        ExtractedMedicine,
        MatchedMedicine,
        Medicine,
        MedicineSideEffect,
        SideEffect,
        SummarySheet,
        UploadedImage,
    )
except ModuleNotFoundError:  # Running as a script without package context.
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[3]))
    from backend.app.db.database import close_database, initialize_database
    from backend.app.models import (
        CheckedSymptom,
        ExtractedMedicine,
        MatchedMedicine,
        Medicine,
        MedicineSideEffect,
        SideEffect,
        SummarySheet,
        UploadedImage,
    )


def get_models() -> Sequence[Type[Model]]:
    """初期化対象のモデル一覧を返す。"""

    return (
        Medicine,
        SideEffect,
        MedicineSideEffect,
        UploadedImage,
        ExtractedMedicine,
        MatchedMedicine,
        CheckedSymptom,
        SummarySheet,
    )


def init_db() -> None:
    """データベースを初期化する。"""

    initialize_database(get_models())
    close_database()


if __name__ == '__main__':
    init_db()
