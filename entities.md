# エンティティ一覧表

**プロジェクト**: 患者参加型・薬の安全チェックアプリ  
**作成日**: 2026-01-24  
**バージョン**: 1.0

---

## 📚 マスタデータ（Master Data）

基準データ・参照データとして使用される静的なエンティティ

| No | エンティティ名 | 英名 | 主キー | 説明 |
|:--:|-------------|------|--------|------|
| 1 | 薬剤マスタ | Medicines | medicine_id | 高齢者注意薬剤の情報。薬剤名（商品名）、一般名（成分名）、薬効分類、注意理由、参照元を管理 |
| 2 | 副作用症状マスタ | SideEffects | side_effect_id | 一般に報告されやすい副作用症状の情報。症状名、症状の説明（平易な日本語）を管理 |
| 3 | 薬剤-副作用関連マスタ | Medicine_SideEffect | relation_id | 薬剤マスタと副作用症状マスタの多対多関係を解決する中間テーブル |

---

## 📊 トランザクションデータ（Transaction Data）

ユーザーの操作や処理結果として生成される動的なエンティティ

| No | エンティティ名 | 英名 | 主キー | 説明 |
|:--:|-------------|------|--------|------|
| 4 | アップロード画像 | UploadedImages | image_id | ユーザーがアップロードしたお薬手帳の画像情報。ファイルパス、形式（JPEG/PNG）、サイズ、アップロード日時を管理 |
| 5 | 抽出薬剤 | ExtractedMedicines | extracted_id | OCRで画像から抽出された薬剤名。手動修正フラグ、抽出日時を含む。1つの画像から複数抽出される |
| 6 | 該当薬剤照合結果 | MatchedMedicines | match_id | 抽出薬剤と注意薬剤マスタの照合結果。該当/非該当フラグ、照合日時を管理 |
| 7 | チェック症状 | CheckedSymptoms | check_id | ユーザーが気になる症状としてチェックした副作用症状。チェック日時を記録 |
| 8 | 症状まとめシート | SummarySheets | sheet_id | 医師・薬剤師への相談用まとめシート。生成日時、PDF/印刷出力日時を管理 |

---

## 🔮 将来拡張エンティティ（Phase 2）

将来的な機能拡張時に追加予定のエンティティ

| No | エンティティ名 | 英名 | 主キー | 説明 | Phase |
|:--:|-------------|------|--------|------|:-----:|
| 9 | ユーザー | Users | user_id | アプリ利用者の情報。名前、続柄（本人/家族）、登録日時を管理 | Phase 2 |
| 10 | 服薬履歴 | MedicationHistory | history_id | ユーザーの服薬履歴。服用開始日、終了日を時系列で管理 | Phase 2 |

---

## 📋 エンティティ詳細仕様

### 1. 薬剤マスタ（Medicines）

| 属性名 | 型 | 必須 | 説明 |
|--------|-----|:----:|------|
| medicine_id | INTEGER | ✅ | 主キー（自動採番） |
| medicine_name | VARCHAR(200) | ✅ | 薬剤名（商品名） |
| generic_name | VARCHAR(200) | ✅ | 一般名（成分名） |
| drug_category | VARCHAR(100) | ✅ | 薬効分類 |
| caution_reason | TEXT | ⬜ | 注意理由（簡潔に） |
| reference_source | VARCHAR(200) | ⬜ | 参照元（ガイドライン名など） |
| created_at | DATETIME | ✅ | 登録日時 |
| updated_at | DATETIME | ✅ | 更新日時 |

**データソース**: CSV（`medicines.csv`）

---

### 2. 副作用症状マスタ（SideEffects）

| 属性名 | 型 | 必須 | 説明 |
|--------|-----|:----:|------|
| side_effect_id | INTEGER | ✅ | 主キー（自動採番） |
| symptom_name | VARCHAR(100) | ✅ | 副作用症状名（例: ふらつき、眠気） |
| symptom_description | TEXT | ⬜ | 症状の説明（平易な日本語） |
| created_at | DATETIME | ✅ | 登録日時 |
| updated_at | DATETIME | ✅ | 更新日時 |

**データソース**: CSV（`side_effects.csv`）

---

### 3. 薬剤-副作用関連マスタ（Medicine_SideEffect）

| 属性名 | 型 | 必須 | 説明 |
|--------|-----|:----:|------|
| relation_id | INTEGER | ✅ | 主キー（自動採番） |
| medicine_id | INTEGER | ✅ | 外部キー → Medicines(medicine_id) |
| side_effect_id | INTEGER | ✅ | 外部キー → SideEffects(side_effect_id) |
| frequency_note | VARCHAR(50) | ⬜ | 頻度メモ（例: よくある、まれ） |
| created_at | DATETIME | ✅ | 登録日時 |

**制約**:
- UNIQUE(medicine_id, side_effect_id): 同じ組み合わせの重複を防止
- ON DELETE CASCADE: 薬剤または副作用が削除されたら関連も削除

---

### 4. アップロード画像（UploadedImages）

| 属性名 | 型 | 必須 | 説明 |
|--------|-----|:----:|------|
| image_id | INTEGER | ✅ | 主キー（自動採番） |
| file_path | VARCHAR(500) | ✅ | 画像ファイルのパス |
| file_format | VARCHAR(10) | ✅ | ファイル形式（JPEG, PNG） |
| file_size | INTEGER | ✅ | ファイルサイズ（バイト） |
| uploaded_at | DATETIME | ✅ | アップロード日時 |

**制約**:
- file_format: ['JPEG', 'PNG']のみ
- file_size: 10MB（10,485,760バイト）以下

---

### 5. 抽出薬剤（ExtractedMedicines）

| 属性名 | 型 | 必須 | 説明 |
|--------|-----|:----:|------|
| extracted_id | INTEGER | ✅ | 主キー（自動採番） |
| image_id | INTEGER | ✅ | 外部キー → UploadedImages(image_id) |
| extracted_text | VARCHAR(200) | ✅ | OCRで抽出された薬剤名 |
| is_manually_edited | BOOLEAN | ✅ | 手動修正フラグ（デフォルト: false） |
| extracted_at | DATETIME | ✅ | 抽出日時 |

**制約**:
- ON DELETE CASCADE: 画像が削除されたら抽出薬剤も削除

---

### 6. 該当薬剤照合結果（MatchedMedicines）

| 属性名 | 型 | 必須 | 説明 |
|--------|-----|:----:|------|
| match_id | INTEGER | ✅ | 主キー（自動採番） |
| extracted_id | INTEGER | ✅ | 外部キー → ExtractedMedicines(extracted_id) |
| medicine_id | INTEGER | ⬜ | 外部キー → Medicines(medicine_id) |
| is_matched | BOOLEAN | ✅ | 該当フラグ（true: 該当, false: 非該当） |
| matched_at | DATETIME | ✅ | 照合日時 |

**制約**:
- ON DELETE CASCADE: 抽出薬剤が削除されたら照合結果も削除
- medicine_id: is_matched=trueの場合は必須

---

### 7. チェック症状（CheckedSymptoms）

| 属性名 | 型 | 必須 | 説明 |
|--------|-----|:----:|------|
| check_id | INTEGER | ✅ | 主キー（自動採番） |
| match_id | INTEGER | ✅ | 外部キー → MatchedMedicines(match_id) |
| side_effect_id | INTEGER | ✅ | 外部キー → SideEffects(side_effect_id) |
| checked_at | DATETIME | ✅ | チェック日時 |

**制約**:
- ON DELETE CASCADE: 該当薬剤照合結果が削除されたらチェック症状も削除
- UNIQUE(match_id, side_effect_id): 同じ症状の重複チェックを防止

---

### 8. 症状まとめシート（SummarySheets）

| 属性名 | 型 | 必須 | 説明 |
|--------|-----|:----:|------|
| sheet_id | INTEGER | ✅ | 主キー（自動採番） |
| image_id | INTEGER | ✅ | 外部キー → UploadedImages(image_id) |
| generated_at | DATETIME | ✅ | シート生成日時 |
| pdf_exported_at | DATETIME | ⬜ | PDF出力日時 |
| printed_at | DATETIME | ⬜ | 印刷実行日時 |

**制約**:
- ON DELETE CASCADE: 画像が削除されたらまとめシートも削除

---

## 🔗 エンティティ関連図（概念）

```
[マスタデータ]
Medicines (N) ←─── Medicine_SideEffect ───→ (N) SideEffects

[トランザクションデータ]
UploadedImages (1)
    ├──→ (N) ExtractedMedicines (1)
    │         └──→ (N) MatchedMedicines (1)
    │                   └──→ (N) CheckedSymptoms
    └──→ (1) SummarySheets
```

---

## 📊 統計情報

| 分類 | エンティティ数 |
|------|:-------------:|
| マスタデータ | 3 |
| トランザクションデータ | 5 |
| **MVP版 合計** | **8** |
| 将来拡張（Phase 2） | 2 |
| **総合計** | **10** |

---

## 🎯 命名規則

- **テーブル名**: パスカルケース、複数形（例: `Medicines`, `CheckedSymptoms`）
- **カラム名**: スネークケース（例: `medicine_id`, `extracted_at`）
- **主キー**: `{テーブル名の単数形}_id`（例: `medicine_id`, `check_id`）
- **外部キー**: 参照先テーブルの主キー名と同じ（例: `image_id` → `UploadedImages.image_id`）
- **フラグ**: `is_` プレフィックス（例: `is_matched`, `is_manually_edited`）
- **日時**: `_at` サフィックス（例: `created_at`, `uploaded_at`）

---

## 📝 データ更新容易性（NFR-009対応）

### CSVファイル管理

| マスタテーブル | CSVファイル名 | 更新方法 |
|-------------|-------------|---------|
| Medicines | `medicines.csv` | CSVインポート機能 |
| SideEffects | `side_effects.csv` | CSVインポート機能 |
| Medicine_SideEffect | `medicine_side_effects.csv` | CSVインポート機能 |

**更新フロー**:
1. CSVファイルを編集
2. アプリのインポート機能で読み込み
3. アプリ再起動不要で即座に反映

---

## 🔐 セキュリティ・プライバシー（NFR-005対応）

### 個人情報を含むエンティティ

| エンティティ | 個人情報レベル | 対応策 |
|------------|:-------------:|--------|
| UploadedImages | 🔴 高 | ローカル保存、暗号化（クラウド時） |
| ExtractedMedicines | 🟡 中 | 薬剤名のみ（氏名は含まない） |
| CheckedSymptoms | 🟡 中 | 症状データのみ |
| SummarySheets | 🔴 高 | 一時ファイル、使用後削除推奨 |

---

**文書ステータス**: 承認済  
**最終更新日**: 2026-01-24
