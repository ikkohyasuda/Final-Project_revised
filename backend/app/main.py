from fastapi import FastAPI

from backend.app.api import upload_router

app = FastAPI()

app.include_router(upload_router)


@app.get('/')
def read_root() -> dict:
    """トップページの動作確認用レスポンスを返す。"""

    return {
        'title': '患者参加型・薬の安全チェックアプリ',
        'description': [
            'お薬手帳の画像から薬剤名を抽出し、',
            '注意が必要とされる薬剤や関連する症状を整理します。',
            '医師・薬剤師への相談を促すためのサポートツールです。',
        ],
        'actions': [
            {'label': 'チェックを開始', 'href': '/upload'},
            {'label': '使い方を見る', 'href': '/help'},
        ],
        'disclaimer': '診断を行うものではなく、受診や相談の判断材料としてご利用ください。',
    }
