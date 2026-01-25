from fastapi import APIRouter, Form, HTTPException, status

from backend.app.db.database import db
from backend.app.models.checked_symptom import CheckedSymptom
from backend.app.models.extracted_medicine import ExtractedMedicine
from backend.app.models.matched_medicine import MatchedMedicine
from backend.app.models.medicine_side_effect import MedicineSideEffect
from backend.app.models.side_effect import SideEffect
from backend.app.models.uploaded_image import UploadedImage

router = APIRouter()


def _parse_side_effect_ids(raw_ids: str) -> list[int]:
    """カンマ区切りのID文字列を整数配列に変換する。"""

    ids = []
    for item in raw_ids.split(','):
        value = item.strip()
        if not value:
            continue
        if not value.isdigit():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='副作用IDは数値で入力してください。',
            )
        ids.append(int(value))
    if not ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='副作用IDが入力されていません。',
        )
    return ids


@router.post('/api/drugs/symptoms')
def list_symptoms(image_id: int = Form(..., ge=1)) -> dict:
    """該当薬剤に紐づく副作用症状を返す。"""

    try:
        db.connect(reuse_if_open=True)
        image = UploadedImage.get_or_none(UploadedImage.image_id == image_id)
        if image is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='指定された画像が見つかりません。',
            )

        extracted = (
            ExtractedMedicine
            .select(ExtractedMedicine.extracted_id)
            .where(ExtractedMedicine.image == image)
        )
        matched = list(
            MatchedMedicine
            .select()
            .where(MatchedMedicine.extracted.in_(extracted))
        )
        if not matched:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='該当薬剤の照合結果がありません。',
            )

        matched_ids = [item.match_id for item in matched]
        relations = (
            MedicineSideEffect
            .select(MedicineSideEffect.medicine, MedicineSideEffect.side_effect, MedicineSideEffect.frequency_note)
            .where(MedicineSideEffect.medicine.in_([item.medicine for item in matched]))
        )
        side_effect_map = {}
        for relation in relations:
            side_effect_map.setdefault(relation.medicine.medicine_id, []).append(
                {
                    'side_effect_id': relation.side_effect.side_effect_id,
                    'symptom_name': relation.side_effect.symptom_name,
                    'symptom_description': relation.side_effect.symptom_description,
                    'frequency_note': relation.frequency_note,
                }
            )
    finally:
        if not db.is_closed():
            db.close()

    return {
        'image_id': image_id,
        'matched_ids': matched_ids,
        'items': [
            {
                'match_id': item.match_id,
                'medicine_id': item.medicine.medicine_id,
                'medicine_name': item.medicine.medicine_name,
                'side_effects': side_effect_map.get(item.medicine.medicine_id, []),
            }
            for item in matched
        ],
    }


@router.post('/api/drugs/symptoms/check')
def check_symptoms(match_id: int = Form(..., ge=1), side_effect_ids: str = Form(...)) -> dict:
    """症状チェック結果を保存する。"""

    ids = _parse_side_effect_ids(side_effect_ids)

    try:
        db.connect(reuse_if_open=True)
        matched = MatchedMedicine.get_or_none(MatchedMedicine.match_id == match_id)
        if matched is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='指定された照合結果が見つかりません。',
            )

        effects = list(SideEffect.select().where(SideEffect.side_effect_id.in_(ids)))
        if len(effects) != len(ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='存在しない副作用IDが含まれています。',
            )

        saved = []
        for effect in effects:
            existing = CheckedSymptom.get_or_none(
                (CheckedSymptom.match == matched) & (CheckedSymptom.side_effect == effect)
            )
            if existing is None:
                checked = CheckedSymptom.create(match=matched, side_effect=effect)
            else:
                checked = existing
            saved.append(
                {
                    'check_id': checked.check_id,
                    'match_id': match_id,
                    'side_effect_id': effect.side_effect_id,
                    'symptom_name': effect.symptom_name,
                }
            )
    finally:
        if not db.is_closed():
            db.close()

    return {'match_id': match_id, 'checked': saved}
