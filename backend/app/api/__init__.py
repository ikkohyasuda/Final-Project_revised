from backend.app.api.drugs import router as drugs_router
from backend.app.api.ocr import router as ocr_router
from backend.app.api.report import router as report_router
from backend.app.api.symptoms import router as symptoms_router
from backend.app.api.upload import router as upload_router

__all__ = ['upload_router', 'ocr_router', 'drugs_router', 'symptoms_router', 'report_router']
