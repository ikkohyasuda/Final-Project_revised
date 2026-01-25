from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

try:
    from backend.app.api import upload_router
except ModuleNotFoundError:  # Running as a script without package context.
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from backend.app.api import upload_router

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / 'templates'))

app = FastAPI()

app.include_router(upload_router)


@app.get('/', response_class=HTMLResponse)
def read_index(request: Request) -> HTMLResponse:
    """トップページを表示する。"""
    return templates.TemplateResponse('index.html', {'request': request, 'message': 'Hello World'})


if __name__ == '__main__':
    import uvicorn

    uvicorn.run('backend.app.app:app', host='0.0.0.0', port=8000)
