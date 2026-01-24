# プロジェクト基本情報

## プロジェクト概要
- プロジェクト名: 患者参加型・薬の安全チェックアプリ
- 目的: お薬手帳画像から薬剤名を抽出し、注意薬剤や一般的な副作用症状を整理・可視化して医師・薬剤師への相談を促す支援アプリ
- バックエンド: FastAPI
- フロントエンド: Next.js（React）
- データベース: SQLite（ファイルベース、MVPはローカル動作）

## 技術スタック

### バックエンド
- Python: 3.9以上
- FastAPI
- Pillow（画像前処理）
- OCR: Tesseract OCR / Google Cloud Vision API
- SQLite

### フロントエンド
- Next.js（React）
- React Dropzone（画像アップロード）
- Canvas API / EXIF.js（プレビュー・回転補正）
- React Toastify（通知）

## 補足事項
- 認証はMVPでは未実装（全画面公開）
- SaMD非該当性を担保する文言（断定表現を避ける）

## ディレクトリ構造
```
med_safety_check/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPIエントリーポイント
│   │   ├── api/              # ルーティング
│   │   ├── models/           # DBモデル
│   │   ├── services/         # OCR/照合/レポート処理
│   │   └── core/             # 設定・共通処理
│   ├── data/                 # CSV（注意薬剤/副作用症状）
│   └── requirements.txt
├── frontend/
│   ├── app/                  # Next.js ルーティング
│   ├── components/
│   ├── styles/
│   ├── public/
│   └── package.json
├── docs/
└── README.md
```
