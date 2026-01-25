# スモークチェック手順（MVP）

## 前提
- venvが有効化されていること
- 依存関係をインストール済みであること
- DB初期化とマスタ投入が完了していること

## 事前準備
1. 依存関係のインストール
   - `pip install -r requirements.txt`
2. DB初期化（未実施の場合のみ）
   - `python backend/app/db/db_manager.py`
3. マスタ投入
   - `python backend/app/db/seed_db.py`
4. アプリ起動
   - `python backend/app/app.py`

## チェックシナリオ

### 1. 画像アップロード
1. ブラウザで `http://localhost:8000/upload` にアクセス
2. JPEG/PNGファイルを選択しアップロード
3. レスポンスの `image_id` を控える

### 2. OCR開始
1. `http://localhost:8000/ocr` にアクセス
2. `image_id` を入力してOCR開始
3. レスポンスの `task_id` を控える
4. `http://localhost:8000/api/ocr/status/{task_id}` にアクセスし結果を確認
5. `result.items` に薬剤名が返っていることを確認

### 3. 照合
1. `http://localhost:8000/check` にアクセス
2. `image_id` を入力して照合開始
3. `matched` に該当薬剤が含まれることを確認

### 4. 症状チェック
1. `http://localhost:8000/symptoms` にアクセス
2. 上段フォームに `image_id` を入力して症状一覧を取得
3. `items[0].match_id` と `side_effect_id` を控える
4. 下段フォームで `match_id` と `side_effect_ids` を入力して保存
5. `checked` に症状が含まれることを確認

### 5. まとめシート生成/PDF
1. `http://localhost:8000/result` にアクセス
2. `image_id` を入力してまとめシート生成
3. レスポンスの `report_id` を控える
4. `report_id` を入力してPDFを取得
5. PDFに薬剤名と症状が表示されることを確認

## 期待結果
- 各エンドポイントが200で応答する
- OCR結果から照合までのデータがつながる
- PDFに日本語が文字化けせず出力される
