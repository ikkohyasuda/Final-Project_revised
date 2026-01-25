import csv
from pathlib import Path
from typing import Iterable

try:
    from backend.app.db.database import db
    from backend.app.db.db_manager import get_models
    from backend.app.models.medicine import Medicine
    from backend.app.models.medicine_side_effect import MedicineSideEffect
    from backend.app.models.side_effect import SideEffect
    from config import settings
except ModuleNotFoundError:  # Running as a script without package context.
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[3]))
    from backend.app.db.database import db
    from backend.app.db.db_manager import get_models
    from backend.app.models.medicine import Medicine
    from backend.app.models.medicine_side_effect import MedicineSideEffect
    from backend.app.models.side_effect import SideEffect
    from config import settings


def _read_csv(path: Path) -> Iterable[dict[str, str]]:
    """CSVを読み込んで行データを返す。"""

    if not path.exists():
        raise FileNotFoundError(f'CSVが見つかりません: {path}')

    with path.open('r', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if not any(value.strip() for value in row.values() if value):
                continue
            yield {key: (value or '').strip() for key, value in row.items()}


def seed_medicines(path: Path) -> dict[str, Medicine]:
    """薬剤マスタを投入する。"""

    medicines: dict[str, Medicine] = {}
    for row in _read_csv(path):
        name = row.get('medicine_name', '')
        if not name:
            continue
        medicine, created = Medicine.get_or_create(
            medicine_name=name,
            defaults={
                'generic_name': row.get('generic_name', ''),
                'drug_category': row.get('drug_category', ''),
                'caution_reason': row.get('caution_reason') or None,
                'reference_source': row.get('reference_source') or None,
            },
        )
        if not created:
            if row.get('generic_name'):
                medicine.generic_name = row['generic_name']
            if row.get('drug_category'):
                medicine.drug_category = row['drug_category']
            if row.get('caution_reason'):
                medicine.caution_reason = row['caution_reason']
            if row.get('reference_source'):
                medicine.reference_source = row['reference_source']
            medicine.save()
        medicines[name] = medicine
    return medicines


def seed_side_effects(path: Path) -> dict[str, SideEffect]:
    """副作用症状マスタを投入する。"""

    side_effects: dict[str, SideEffect] = {}
    for row in _read_csv(path):
        name = row.get('symptom_name', '')
        if not name:
            continue
        effect, created = SideEffect.get_or_create(
            symptom_name=name,
            defaults={'symptom_description': row.get('symptom_description') or None},
        )
        if not created and row.get('symptom_description'):
            effect.symptom_description = row['symptom_description']
            effect.save()
        side_effects[name] = effect
    return side_effects


def seed_relations(
    path: Path,
    medicines: dict[str, Medicine],
    side_effects: dict[str, SideEffect],
) -> int:
    """薬剤と副作用の関連を投入する。"""

    count = 0
    for row in _read_csv(path):
        medicine_name = row.get('medicine_name', '')
        symptom_name = row.get('symptom_name', '')
        if not medicine_name or not symptom_name:
            continue
        medicine = medicines.get(medicine_name) or Medicine.get_or_none(Medicine.medicine_name == medicine_name)
        if medicine is None:
            raise ValueError(f'薬剤が見つかりません: {medicine_name}')
        effect = side_effects.get(symptom_name) or SideEffect.get_or_none(SideEffect.symptom_name == symptom_name)
        if effect is None:
            raise ValueError(f'副作用が見つかりません: {symptom_name}')
        relation, created = MedicineSideEffect.get_or_create(
            medicine=medicine,
            side_effect=effect,
            defaults={'frequency_note': row.get('frequency_note') or None},
        )
        if not created and row.get('frequency_note'):
            relation.frequency_note = row['frequency_note']
            relation.save()
        count += 1
    return count


def _split_items(value: str) -> list[str]:
    """パイプ区切りの値をリストにする。"""

    return [item.strip() for item in value.split('|') if item.strip()]


def seed_from_rules(path: Path) -> None:
    """rules.csvからマスタデータを投入する。"""

    for row in _read_csv(path):
        category = row.get('category', '')
        effect_name = row.get('effect_name', '')
        keywords = _split_items(row.get('keywords', ''))
        symptoms = _split_items(row.get('symptoms', ''))

        for name in keywords:
            medicine, created = Medicine.get_or_create(
                medicine_name=name,
                defaults={
                    'generic_name': '',
                    'drug_category': category,
                    'caution_reason': effect_name or None,
                    'reference_source': 'rules.csv',
                },
            )
            if not created:
                if not medicine.drug_category and category:
                    medicine.drug_category = category
                if not medicine.caution_reason and effect_name:
                    medicine.caution_reason = effect_name
                if not medicine.reference_source:
                    medicine.reference_source = 'rules.csv'
                medicine.save()

            for symptom in symptoms:
                side_effect, effect_created = SideEffect.get_or_create(
                    symptom_name=symptom,
                    defaults={'symptom_description': None},
                )
                if not effect_created and side_effect.symptom_description is None and effect_name:
                    side_effect.symptom_description = effect_name
                    side_effect.save()

                MedicineSideEffect.get_or_create(
                    medicine=medicine,
                    side_effect=side_effect,
                    defaults={'frequency_note': effect_name or None},
                )


def seed_database() -> None:
    """CSVからマスタデータを投入する。"""

    medicines_path = settings.caution_medicines_csv
    side_effects_path = settings.side_effects_csv
    relations_path = settings.data_dir / 'medicine_side_effects.csv'
    rules_path = settings.rules_csv

    db.connect(reuse_if_open=True)
    db.create_tables(get_models(), safe=True)
    if rules_path.exists():
        seed_from_rules(rules_path)
    else:
        medicines = seed_medicines(medicines_path)
        side_effects = seed_side_effects(side_effects_path)
        seed_relations(relations_path, medicines, side_effects)
    if not db.is_closed():
        db.close()


if __name__ == '__main__':
    seed_database()
