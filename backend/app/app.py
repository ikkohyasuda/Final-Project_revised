from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

try:
    from backend.app.api import drugs_router, ocr_router, report_router, symptoms_router, upload_router
except ModuleNotFoundError:  # Running as a script without package context.
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from backend.app.api import drugs_router, ocr_router, report_router, symptoms_router, upload_router

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / 'templates'))

app = FastAPI()

app.include_router(upload_router)
app.include_router(ocr_router)
app.include_router(drugs_router)
app.include_router(symptoms_router)
app.include_router(report_router)


@app.get('/', response_class=HTMLResponse)
def read_index(request: Request) -> HTMLResponse:
    """トップページを表示する。"""
    return templates.TemplateResponse('index.html', {'request': request, 'message': 'Hello World'})


@app.get('/upload', response_class=HTMLResponse)
def read_upload(request: Request) -> HTMLResponse:
    """画像アップロードフォームを表示する。"""
    return templates.TemplateResponse('upload.html', {'request': request})


@app.get('/ocr', response_class=HTMLResponse)
def read_ocr(request: Request) -> HTMLResponse:
    """OCR開始フォームを表示する。"""
    return templates.TemplateResponse('ocr.html', {'request': request})


@app.get('/check', response_class=HTMLResponse)
def read_check(request: Request) -> HTMLResponse:
    """薬剤照合フォームを表示する。"""
    return templates.TemplateResponse('check.html', {'request': request})


@app.get('/symptoms', response_class=HTMLResponse)
def read_symptoms(request: Request) -> HTMLResponse:
    """症状チェックフォームを表示する。"""
    return templates.TemplateResponse('symptoms.html', {'request': request})


@app.get('/result', response_class=HTMLResponse)
def read_result(request: Request) -> HTMLResponse:
    """まとめシート生成フォームを表示する。"""
    return templates.TemplateResponse('result.html', {'request': request})


@app.get('/flow', response_class=HTMLResponse)
def read_flow(request: Request) -> HTMLResponse:
    """一連のフローを実行する画面を表示する。"""
    return templates.TemplateResponse('flow.html', {'request': request})


if __name__ == '__main__':
    import uvicorn

    uvicorn.run('backend.app.app:app', host='0.0.0.0', port=8000)
