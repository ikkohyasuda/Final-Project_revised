import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, status
from fastapi.responses import FileResponse

from backend.app.db.database import db
from backend.app.models.checked_symptom import CheckedSymptom
from backend.app.models.extracted_medicine import ExtractedMedicine
from backend.app.models.matched_medicine import MatchedMedicine
from backend.app.models.summary_sheet import SummarySheet
from backend.app.models.uploaded_image import UploadedImage

router = APIRouter()

BASE_DIR = Path(os.environ.get('PROJECT_ROOT', Path(__file__).resolve().parents[3]))
REPORT_ROOT = Path(os.environ.get('REPORT_DIR', BASE_DIR / 'static' / 'reports'))
REPORT_FONT_PATH = os.environ.get('REPORT_FONT_PATH')
REPORT_FONT_INDEX = int(os.environ.get('REPORT_FONT_INDEX', '0'))


def _register_japanese_font() -> str | None:
    """日本語フォントを登録してフォント名を返す。"""

    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        return None

    try:
        pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
        return 'HeiseiKakuGo-W5'
    except Exception:
        pass

    font_candidates = []
    if REPORT_FONT_PATH:
        font_candidates.append((REPORT_FONT_PATH, REPORT_FONT_INDEX))
    else:
        font_candidates.extend(
            [
                ('/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc', 0),
                ('/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc', 0),
                ('/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc', 0),
                ('/System/Library/Fonts/AppleSDGothicNeo.ttc', 0),
                ('/Library/Fonts/Osaka.ttf', 0),
            ]
        )

    for path, index in font_candidates:
        font_path = Path(path)
        if not font_path.exists():
            continue
        try:
            pdfmetrics.registerFont(TTFont('JPFont', str(font_path), subfontIndex=index))
            return 'JPFont'
        except Exception:
            continue

    return None


def _build_report_data(image_id: int) -> dict:
    """症状まとめシートに必要な情報を構築する。"""

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
            detail='照合結果がありません。',
        )

    match_ids = [item.match_id for item in matched]
    checked = list(
        CheckedSymptom
        .select()
        .where(CheckedSymptom.match.in_(match_ids))
    )
    checked_map: dict[int, list[CheckedSymptom]] = {}
    for item in checked:
        checked_map.setdefault(item.match.match_id, []).append(item)

    return {
        'image': image,
        'matched': matched,
        'checked_map': checked_map,
    }


def _render_pdf(sheet: SummarySheet, report_data: dict) -> Path:
    """症状まとめシートのPDFを生成する。"""

    try:
        from reportlab.pdfgen import canvas
    except ImportError as exc:  # pragma: no cover - import guard
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='PDF生成に必要なライブラリがインストールされていません。',
        ) from exc

    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    filename = f'summary_{sheet.sheet_id}.pdf'
    output_path = REPORT_ROOT / filename

    japanese_font = _register_japanese_font()
    c = canvas.Canvas(str(output_path))
    y = 800
    c.setFont(japanese_font or 'Helvetica-Bold', 14)
    c.drawString(40, y, '症状まとめシート')
    y -= 30
    c.setFont(japanese_font or 'Helvetica', 10)
    c.drawString(40, y, f'画像ID: {report_data["image"].image_id}')
    y -= 20

    for match in report_data['matched']:
        c.setFont(japanese_font or 'Helvetica-Bold', 11)
        c.drawString(40, y, f'薬剤: {match.medicine.medicine_name} ({match.medicine.generic_name})')
        y -= 16
        c.setFont(japanese_font or 'Helvetica', 10)
        checked = report_data['checked_map'].get(match.match_id, [])
        if not checked:
            c.drawString(60, y, '症状チェック: なし')
            y -= 14
        else:
            for item in checked:
                c.drawString(60, y, f'- {item.side_effect.symptom_name}')
                y -= 14
        y -= 6
        if y < 100:
            c.showPage()
            y = 800

    c.save()
    return output_path


@router.post('/api/report/generate')
def generate_report(image_id: int = Form(..., ge=1)) -> dict:
    """症状まとめシートを生成する。"""

    try:
        db.connect(reuse_if_open=True)
        report_data = _build_report_data(image_id)
        sheet, created = SummarySheet.get_or_create(image=report_data['image'])
        if not created:
            sheet.save()
    finally:
        if not db.is_closed():
            db.close()

    return {
        'report_id': sheet.sheet_id,
        'image_id': image_id,
        'matched': [
            {
                'match_id': item.match_id,
                'medicine_id': item.medicine.medicine_id,
                'medicine_name': item.medicine.medicine_name,
                'generic_name': item.medicine.generic_name,
                'checked_symptoms': [
                    {
                        'side_effect_id': checked.side_effect.side_effect_id,
                        'symptom_name': checked.side_effect.symptom_name,
                    }
                    for checked in report_data['checked_map'].get(item.match_id, [])
                ],
            }
            for item in report_data['matched']
        ],
    }


@router.get('/api/report/{report_id}/pdf')
def export_report_pdf(report_id: int) -> FileResponse:
    """まとめシートのPDFを返す。"""

    try:
        db.connect(reuse_if_open=True)
        sheet = SummarySheet.get_or_none(SummarySheet.sheet_id == report_id)
        if sheet is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='指定されたまとめシートが見つかりません。',
            )
        report_data = _build_report_data(sheet.image.image_id)
    finally:
        if not db.is_closed():
            db.close()

    output_path = _render_pdf(sheet, report_data)

    try:
        db.connect(reuse_if_open=True)
        sheet.pdf_exported_at = sheet.pdf_exported_at or datetime.now()
        sheet.save()
    finally:
        if not db.is_closed():
            db.close()

    return FileResponse(path=output_path, filename=output_path.name)
