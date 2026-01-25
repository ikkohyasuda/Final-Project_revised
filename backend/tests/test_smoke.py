from pathlib import Path

import sys

sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.app.api.drugs import check_medicines
from backend.app.api.symptoms import check_symptoms, list_symptoms
from backend.app.db.database import db
from backend.app.db.db_manager import get_models
from backend.app.models.extracted_medicine import ExtractedMedicine
from backend.app.models.medicine import Medicine
from backend.app.models.medicine_side_effect import MedicineSideEffect
from backend.app.models.side_effect import SideEffect
from backend.app.models.uploaded_image import UploadedImage


def _init_test_db(tmp_path) -> None:
    db.init(str(tmp_path / 'test.db'))
    db.connect(reuse_if_open=True)
    db.create_tables(get_models())
    if not db.is_closed():
        db.close()


def test_basic_flow(tmp_path) -> None:
    _init_test_db(tmp_path)

    medicine = Medicine.create(
        medicine_name='Loxonin',
        generic_name='Loxoprofen',
        drug_category='Analgesic',
        caution_reason='GI risk',
        reference_source='guideline',
    )
    effect = SideEffect.create(
        symptom_name='dizziness',
        symptom_description='lightheadedness',
    )
    MedicineSideEffect.create(
        medicine=medicine,
        side_effect=effect,
        frequency_note='rare',
    )
    image = UploadedImage.create(
        file_path='static/uploads/sample.jpg',
        file_format='jpg',
        file_size=1234,
    )
    ExtractedMedicine.create(
        image=image,
        extracted_text='Loxonin 60mg',
    )

    result = check_medicines(image_id=image.image_id)
    assert result['matched']

    symptom_result = list_symptoms(image_id=image.image_id)
    assert symptom_result['items']

    match_id = symptom_result['items'][0]['match_id']
    checked = check_symptoms(match_id=match_id, side_effect_ids=str(effect.side_effect_id))
    assert checked['checked']
