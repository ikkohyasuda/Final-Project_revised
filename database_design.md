# データベース設計書

**プロジェクト**: 患者参加型・薬の安全チェックアプリ  
**作成日**: 2026-01-24  
**バージョン**: 1.0  
**データベース**: SQLite3

---

## 📋 目次

1. [概要](#概要)
2. [テーブル一覧](#テーブル一覧)
3. [マスタデータ層](#マスタデータ層)
   - [Medicines（薬剤マスタ）](#1-medicines薬剤マスタ)
   - [SideEffects（副作用症状マスタ）](#2-sideeffects副作用症状マスタ)
   - [Medicine_SideEffect（薬剤-副作用関連マスタ）](#3-medicine_sideeffect薬剤-副作用関連マスタ)
4. [トランザクションデータ層](#トランザクションデータ層)
   - [UploadedImages（アップロード画像）](#4-uploadedimagesアップロード画像)
   - [ExtractedMedicines（抽出薬剤）](#5-extractedmedicines抽出薬剤)
   - [MatchedMedicines（該当薬剤照合結果）](#6-matchedmedicines該当薬剤照合結果)
   - [CheckedSymptoms（チェック症状）](#7-checkedsymptomsチェック症状)
   - [SummarySheets（症状まとめシート）](#8-summarysheetsシートまとめシート)
5. [インデックス設計](#インデックス設計)
6. [バリデーションルール](#バリデーションルール)
7. [シーダーデータ](#シーダーデータ)

---

## 概要

本データベースは、高齢者向け薬剤安全チェックアプリケーションのデータを管理します。

### 設計方針

- **正規化**: 第3正規形まで正規化
- **外部キー制約**: 全ての外部キーに制約を設定
- **インデックス**: 検索性能を考慮した最適なインデックス配置
- **バリデーション**: 3層バリデーション（DB層、アプリケーション層、UI層）
- **セキュリティ**: SQLインジェクション、XSS対策を実装

### データベース統計

| 分類 | テーブル数 | 想定レコード数（MVP版） |
|------|:----------:|:---------------------:|
| マスタデータ層 | 3 | 50-100件（薬剤） |
| トランザクションデータ層 | 5 | 利用状況に応じて増加 |
| **合計** | **8** | - |

---

## テーブル一覧

| # | テーブル名 | 分類 | 説明 | 主な用途 |
|---|-----------|------|------|---------|
| 1 | Medicines | マスタ | 薬剤マスタ | 高齢者注意薬剤リスト |
| 2 | SideEffects | マスタ | 副作用症状マスタ | 副作用症状の定義 |
| 3 | Medicine_SideEffect | マスタ | 薬剤-副作用関連 | 多対多の関連付け |
| 4 | UploadedImages | トランザクション | アップロード画像 | 処方箋画像の管理 |
| 5 | ExtractedMedicines | トランザクション | 抽出薬剤 | OCR抽出結果 |
| 6 | MatchedMedicines | トランザクション | 該当薬剤照合結果 | マスタとの照合結果 |
| 7 | CheckedSymptoms | トランザクション | チェック症状 | ユーザーの症状記録 |
| 8 | SummarySheets | トランザクション | 症状まとめシート | PDF出力用データ |

---

## マスタデータ層

### 1. Medicines（薬剤マスタ）

**概要**: 高齢者に特に注意が必要な薬剤の情報を管理

#### DDL（テーブル定義）

```sql
CREATE TABLE Medicines (
    medicine_id INTEGER PRIMARY KEY AUTOINCREMENT,
    medicine_name VARCHAR(200) NOT NULL,
    generic_name VARCHAR(200) NOT NULL,
    drug_category VARCHAR(100) NOT NULL,
    caution_reason TEXT DEFAULT NULL,
    reference_source VARCHAR(200) DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_medicines_name ON Medicines(medicine_name);
CREATE INDEX idx_medicines_generic ON Medicines(generic_name);
CREATE INDEX idx_medicines_category ON Medicines(drug_category);
CREATE INDEX idx_medicines_updated ON Medicines(updated_at DESC);

-- 更新トリガー
CREATE TRIGGER update_medicines_timestamp 
AFTER UPDATE ON Medicines
FOR EACH ROW
BEGIN
    UPDATE Medicines 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE medicine_id = NEW.medicine_id;
END;
```

#### カラム定義

| カラム名 | データ型 | NULL | デフォルト値 | 制約 | 説明 |
|---------|---------|:----:|------------|------|------|
| medicine_id | INTEGER | NOT NULL | 自動採番 | PRIMARY KEY, AUTOINCREMENT | 薬剤マスタの一意識別子 |
| medicine_name | VARCHAR(200) | NOT NULL | - | LENGTH >= 1 | 商品名（例：ロキソニン錠60mg） |
| generic_name | VARCHAR(200) | NOT NULL | - | LENGTH >= 1 | 一般名・成分名（例：ロキソプロフェンナトリウム水和物） |
| drug_category | VARCHAR(100) | NOT NULL | - | LENGTH >= 1 | 薬効分類（例：解熱鎮痛薬、抗生物質） |
| caution_reason | TEXT | NULL | NULL | - | 高齢者に対する注意理由を簡潔に記載 |
| reference_source | VARCHAR(200) | NULL | NULL | - | 参照元ガイドライン名 |
| created_at | DATETIME | NOT NULL | CURRENT_TIMESTAMP | - | レコード作成日時（自動設定） |
| updated_at | DATETIME | NOT NULL | CURRENT_TIMESTAMP | - | レコード更新日時（トリガーで自動更新） |

#### インデックス

| インデックス名 | 対象カラム | 種類 | 目的 |
|--------------|-----------|------|------|
| PRIMARY KEY | medicine_id | UNIQUE | 主キー検索 |
| idx_medicines_name | medicine_name | 非UNIQUE | 薬剤名での部分一致検索（照合処理） |
| idx_medicines_generic | generic_name | 非UNIQUE | 一般名での検索（照合処理） |
| idx_medicines_category | drug_category | 非UNIQUE | 薬効分類でのフィルタリング |
| idx_medicines_updated | updated_at | 非UNIQUE | 更新日時順ソート |

#### バリデーションルール

| 項目 | ルール | エラーメッセージ |
|------|-------|----------------|
| medicine_name | 必須、1-200文字、前後空白トリム | 「薬剤名を入力してください」 |
| medicine_name | 全角/半角英数字・カタカナ・漢字・記号 | 「薬剤名に使用できない文字が含まれています」 |
| generic_name | 必須、1-200文字、前後空白トリム | 「一般名を入力してください」 |
| drug_category | 必須、1-100文字 | 「薬効分類を選択してください」 |
| caution_reason | 最大2000文字、HTMLタグ除去 | 「注意理由は2000文字以内で入力してください」 |
| reference_source | 最大200文字 | 「参照元は200文字以内で入力してください」 |

---

### 2. SideEffects（副作用症状マスタ）

**概要**: 高齢者で注意すべき副作用症状の情報を管理

#### DDL（テーブル定義）

```sql
CREATE TABLE SideEffects (
    side_effect_id INTEGER PRIMARY KEY AUTOINCREMENT,
    symptom_name VARCHAR(100) NOT NULL UNIQUE,
    symptom_description TEXT DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_side_effects_name ON SideEffects(symptom_name);
CREATE INDEX idx_side_effects_updated ON SideEffects(updated_at DESC);

-- 更新トリガー
CREATE TRIGGER update_side_effects_timestamp 
AFTER UPDATE ON SideEffects
FOR EACH ROW
BEGIN
    UPDATE SideEffects 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE side_effect_id = NEW.side_effect_id;
END;
```

#### カラム定義

| カラム名 | データ型 | NULL | デフォルト値 | 制約 | 説明 |
|---------|---------|:----:|------------|------|------|
| side_effect_id | INTEGER | NOT NULL | 自動採番 | PRIMARY KEY, AUTOINCREMENT | 副作用症状の一意識別子 |
| symptom_name | VARCHAR(100) | NOT NULL | - | UNIQUE, LENGTH >= 1 | 副作用症状名（例：めまい、ふらつき） |
| symptom_description | TEXT | NULL | NULL | - | 症状の説明を平易な日本語で記載 |
| created_at | DATETIME | NOT NULL | CURRENT_TIMESTAMP | - | レコード作成日時 |
| updated_at | DATETIME | NOT NULL | CURRENT_TIMESTAMP | - | レコード更新日時 |

#### インデックス

| インデックス名 | 対象カラム | 種類 | 目的 |
|--------------|-----------|------|------|
| PRIMARY KEY | side_effect_id | UNIQUE | 主キー検索 |
| UNIQUE | symptom_name | UNIQUE | 症状名での検索・重複防止 |
| idx_side_effects_updated | updated_at | 非UNIQUE | 更新日時順ソート |

#### バリデーションルール

| 項目 | ルール | エラーメッセージ |
|------|-------|----------------|
| symptom_name | 必須、1-100文字、前後空白トリム | 「症状名を入力してください」 |
| symptom_name | 重複チェック（UNIQUE制約） | 「この症状名は既に登録されています」 |
| symptom_name | ひらがな・カタカナ・漢字のみ | 「症状名は日本語で入力してください」 |
| symptom_description | 最大1000文字、HTMLタグ除去 | 「症状説明は1000文字以内で入力してください」 |

---

### 3. Medicine_SideEffect（薬剤-副作用関連マスタ）

**概要**: 薬剤と副作用症状の多対多関係を管理する中間テーブル

#### DDL（テーブル定義）

```sql
CREATE TABLE Medicine_SideEffect (
    relation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    medicine_id INTEGER NOT NULL,
    side_effect_id INTEGER NOT NULL,
    frequency_note VARCHAR(50) DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (medicine_id) 
        REFERENCES Medicines(medicine_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    FOREIGN KEY (side_effect_id) 
        REFERENCES SideEffects(side_effect_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    UNIQUE(medicine_id, side_effect_id)
);

-- インデックス
CREATE INDEX idx_medicine_side_effect_medicine ON Medicine_SideEffect(medicine_id);
CREATE INDEX idx_medicine_side_effect_side_effect ON Medicine_SideEffect(side_effect_id);
```

#### カラム定義

| カラム名 | データ型 | NULL | デフォルト値 | 制約 | 説明 |
|---------|---------|:----:|------------|------|------|
| relation_id | INTEGER | NOT NULL | 自動採番 | PRIMARY KEY, AUTOINCREMENT | 関連の一意識別子 |
| medicine_id | INTEGER | NOT NULL | - | FK → Medicines | 薬剤マスタへの外部キー |
| side_effect_id | INTEGER | NOT NULL | - | FK → SideEffects | 副作用症状マスタへの外部キー |
| frequency_note | VARCHAR(50) | NULL | NULL | - | 頻度メモ（例：よくある、まれ） |
| created_at | DATETIME | NOT NULL | CURRENT_TIMESTAMP | - | 関連付け日時 |

**複合UNIQUE制約**: `UNIQUE(medicine_id, side_effect_id)`

#### インデックス

| インデックス名 | 対象カラム | 種類 | 目的 |
|--------------|-----------|------|------|
| PRIMARY KEY | relation_id | UNIQUE | 主キー検索 |
| UNIQUE | (medicine_id, side_effect_id) | 複合UNIQUE | 重複防止・複合検索 |
| idx_medicine_side_effect_medicine | medicine_id | 非UNIQUE | 薬剤からの副作用検索（最頻出） |
| idx_medicine_side_effect_side_effect | side_effect_id | 非UNIQUE | 副作用からの薬剤検索 |

#### バリデーションルール

| 項目 | ルール | エラーメッセージ |
|------|-------|----------------|
| medicine_id | 必須、正の整数、存在チェック | 「薬剤を選択してください」 |
| side_effect_id | 必須、正の整数、存在チェック | 「副作用を選択してください」 |
| 複合キー | 重複チェック | 「この薬剤と副作用の組み合わせは既に登録されています」 |
| frequency_note | 最大50文字 | 「頻度メモは50文字以内で入力してください」 |

---

## トランザクションデータ層

### 4. UploadedImages（アップロード画像）

**概要**: ユーザーがアップロードした処方箋画像を管理

#### DDL（テーブル定義）

```sql
CREATE TABLE UploadedImages (
    image_id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path VARCHAR(500) NOT NULL UNIQUE,
    file_format VARCHAR(10) NOT NULL CHECK(file_format IN ('JPEG', 'PNG', 'JPG')),
    file_size INTEGER NOT NULL CHECK(file_size > 0 AND file_size <= 10485760),
    uploaded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_uploaded_images_date ON UploadedImages(uploaded_at DESC);
CREATE INDEX idx_uploaded_images_format ON UploadedImages(file_format);
```

#### カラム定義

| カラム名 | データ型 | NULL | デフォルト値 | 制約 | 説明 |
|---------|---------|:----:|------------|------|------|
| image_id | INTEGER | NOT NULL | 自動採番 | PRIMARY KEY, AUTOINCREMENT | 画像の一意識別子 |
| file_path | VARCHAR(500) | NOT NULL | - | UNIQUE, LENGTH >= 1 | サーバー上のファイルパス |
| file_format | VARCHAR(10) | NOT NULL | - | CHECK IN ('JPEG', 'PNG', 'JPG') | ファイル形式 |
| file_size | INTEGER | NOT NULL | - | CHECK > 0 AND <= 10485760 | ファイルサイズ（バイト、最大10MB） |
| uploaded_at | DATETIME | NOT NULL | CURRENT_TIMESTAMP | - | アップロード日時 |

#### インデックス

| インデックス名 | 対象カラム | 種類 | 目的 |
|--------------|-----------|------|------|
| PRIMARY KEY | image_id | UNIQUE | 主キー検索 |
| UNIQUE | file_path | UNIQUE | ファイルパス検索・重複防止 |
| idx_uploaded_images_date | uploaded_at | 非UNIQUE | 日時降順ソート（最重要） |
| idx_uploaded_images_format | file_format | 非UNIQUE | ファイル形式フィルタ |

#### バリデーションルール

| 項目 | ルール | エラーメッセージ |
|------|-------|----------------|
| file_path | 必須、最大500文字、UNIQUE | 「ファイルパスが無効です」 |
| file_path | ディレクトリトラバーサル防止（`..`禁止） | 「不正なファイルパスです」 |
| file_format | 'JPEG', 'PNG', 'JPG'のみ | 「対応していないファイル形式です」 |
| file_format | MIME typeチェック | 「ファイル形式が一致しません」 |
| file_format | マジックバイトチェック | 「画像ファイルではありません」 |
| file_size | 1B〜10MB（10,485,760バイト） | 「ファイルサイズは10MB以内にしてください」 |
| file_size | 0バイトファイル拒否 | 「ファイルが空です」 |

---

### 5. ExtractedMedicines（抽出薬剤）

**概要**: 画像からOCRで抽出された薬剤名を管理

#### DDL（テーブル定義）

```sql
CREATE TABLE ExtractedMedicines (
    extracted_id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id INTEGER NOT NULL,
    extracted_text VARCHAR(200) NOT NULL,
    is_manually_edited BOOLEAN NOT NULL DEFAULT 0,
    extracted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    edited_at DATETIME DEFAULT NULL,
    FOREIGN KEY (image_id) 
        REFERENCES UploadedImages(image_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- インデックス
CREATE INDEX idx_extracted_medicines_image ON ExtractedMedicines(image_id);
CREATE INDEX idx_extracted_medicines_text ON ExtractedMedicines(extracted_text);
CREATE INDEX idx_extracted_medicines_edited ON ExtractedMedicines(is_manually_edited);
CREATE INDEX idx_extracted_medicines_date ON ExtractedMedicines(extracted_at DESC);
```

#### カラム定義

| カラム名 | データ型 | NULL | デフォルト値 | 制約 | 説明 |
|---------|---------|:----:|------------|------|------|
| extracted_id | INTEGER | NOT NULL | 自動採番 | PRIMARY KEY, AUTOINCREMENT | 抽出結果の一意識別子 |
| image_id | INTEGER | NOT NULL | - | FK → UploadedImages | 画像への外部キー |
| extracted_text | VARCHAR(200) | NOT NULL | - | LENGTH >= 1 | OCRで抽出された薬剤名テキスト |
| is_manually_edited | BOOLEAN | NOT NULL | 0 (false) | CHECK IN (0, 1) | 手動修正フラグ（0:未修正、1:修正済） |
| extracted_at | DATETIME | NOT NULL | CURRENT_TIMESTAMP | - | OCR抽出日時 |
| edited_at | DATETIME | NULL | NULL | - | 手動修正日時（修正時のみ記録） |

#### インデックス

| インデックス名 | 対象カラム | 種類 | 目的 |
|--------------|-----------|------|------|
| PRIMARY KEY | extracted_id | UNIQUE | 主キー検索 |
| idx_extracted_medicines_image | image_id | 非UNIQUE | 画像からの抽出結果検索（最重要） |
| idx_extracted_medicines_text | extracted_text | 非UNIQUE | 抽出テキスト検索 |
| idx_extracted_medicines_edited | is_manually_edited | 非UNIQUE | 手動修正済みフィルタ |
| idx_extracted_medicines_date | extracted_at | 非UNIQUE | 抽出日時ソート |

#### バリデーションルール

| 項目 | ルール | エラーメッセージ |
|------|-------|----------------|
| extracted_text | 必須、1-200文字、前後空白トリム | 「薬剤名を入力してください」 |
| extracted_text | 制御文字除去 | - |
| is_manually_edited | 0または1のみ | 「無効な値です」 |
| is_manually_edited | =1の場合、edited_atも必須 | 「手動編集日時が設定されていません」 |
| edited_at | 未来日時禁止 | 「未来の日時は設定できません」 |
| edited_at | extracted_at以降の日時 | 「抽出日時より前の日時は設定できません」 |

---

### 6. MatchedMedicines（該当薬剤照合結果）

**概要**: 抽出された薬剤名と薬剤マスタの照合結果を管理

#### DDL（テーブル定義）

```sql
CREATE TABLE MatchedMedicines (
    match_id INTEGER PRIMARY KEY AUTOINCREMENT,
    extracted_id INTEGER NOT NULL,
    medicine_id INTEGER DEFAULT NULL,
    is_matched BOOLEAN NOT NULL DEFAULT 0,
    matched_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (extracted_id) 
        REFERENCES ExtractedMedicines(extracted_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    FOREIGN KEY (medicine_id) 
        REFERENCES Medicines(medicine_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CHECK (
        (is_matched = 1 AND medicine_id IS NOT NULL) OR
        (is_matched = 0 AND medicine_id IS NULL)
    )
);

-- インデックス
CREATE INDEX idx_matched_medicines_extracted ON MatchedMedicines(extracted_id);
CREATE INDEX idx_matched_medicines_medicine ON MatchedMedicines(medicine_id);
CREATE INDEX idx_matched_medicines_matched ON MatchedMedicines(is_matched);
CREATE INDEX idx_matched_medicines_date ON MatchedMedicines(matched_at DESC);
CREATE INDEX idx_matched_medicines_extracted_matched ON MatchedMedicines(extracted_id, is_matched);
```

#### カラム定義

| カラム名 | データ型 | NULL | デフォルト値 | 制約 | 説明 |
|---------|---------|:----:|------------|------|------|
| match_id | INTEGER | NOT NULL | 自動採番 | PRIMARY KEY, AUTOINCREMENT | 照合結果の一意識別子 |
| extracted_id | INTEGER | NOT NULL | - | FK → ExtractedMedicines | 抽出薬剤への外部キー |
| medicine_id | INTEGER | NULL | NULL | FK → Medicines | 薬剤マスタへの外部キー（該当なしの場合NULL） |
| is_matched | BOOLEAN | NOT NULL | 0 (false) | CHECK IN (0, 1) | 該当フラグ（0:非該当、1:該当） |
| matched_at | DATETIME | NOT NULL | CURRENT_TIMESTAMP | - | 照合処理日時 |

**重要**: `is_matched=false` かつ `medicine_id=NULL` のレコードは「照合処理は完了したが、注意薬剤リストに該当しなかった」ことを表します。

**CHECK制約**: 
```sql
CHECK (
    (is_matched = 1 AND medicine_id IS NOT NULL) OR
    (is_matched = 0 AND medicine_id IS NULL)
)
```

#### インデックス

| インデックス名 | 対象カラム | 種類 | 目的 |
|--------------|-----------|------|------|
| PRIMARY KEY | match_id | UNIQUE | 主キー検索 |
| idx_matched_medicines_extracted | extracted_id | 非UNIQUE | 抽出結果からの照合検索 |
| idx_matched_medicines_medicine | medicine_id | 非UNIQUE | 薬剤マスタからの逆引き |
| idx_matched_medicines_matched | is_matched | 非UNIQUE | 該当/非該当フィルタ |
| idx_matched_medicines_date | matched_at | 非UNIQUE | 照合日時ソート |
| idx_matched_medicines_extracted_matched | (extracted_id, is_matched) | 複合 | 該当薬剤のみ抽出（最適化） |

#### バリデーションルール

| 項目 | ルール | エラーメッセージ |
|------|-------|----------------|
| medicine_id | is_matched=1の場合は必須 | 「該当薬剤を選択してください」 |
| medicine_id | is_matched=0の場合はNULL | 「非該当の場合、薬剤IDは設定できません」 |
| medicine_id | 存在チェック（FK検証） | 「選択された薬剤が見つかりません」 |
| is_matched | 0または1のみ | 「無効な値です」 |
| is_matched | medicine_idとの整合性チェック | 「該当フラグと薬剤IDが矛盾しています」 |

---

### 7. CheckedSymptoms（チェック症状）

**概要**: ユーザーがチェックした症状を記録

#### DDL（テーブル定義）

```sql
CREATE TABLE CheckedSymptoms (
    check_id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL,
    side_effect_id INTEGER NOT NULL,
    checked_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (match_id) 
        REFERENCES MatchedMedicines(match_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    FOREIGN KEY (side_effect_id) 
        REFERENCES SideEffects(side_effect_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    UNIQUE(match_id, side_effect_id)
);

-- インデックス
CREATE INDEX idx_checked_symptoms_match ON CheckedSymptoms(match_id);
CREATE INDEX idx_checked_symptoms_side_effect ON CheckedSymptoms(side_effect_id);
CREATE INDEX idx_checked_symptoms_date ON CheckedSymptoms(checked_at DESC);
```

#### カラム定義

| カラム名 | データ型 | NULL | デフォルト値 | 制約 | 説明 |
|---------|---------|:----:|------------|------|------|
| check_id | INTEGER | NOT NULL | 自動採番 | PRIMARY KEY, AUTOINCREMENT | チェック記録の一意識別子 |
| match_id | INTEGER | NOT NULL | - | FK → MatchedMedicines | 照合結果への外部キー |
| side_effect_id | INTEGER | NOT NULL | - | FK → SideEffects | 副作用症状への外部キー |
| checked_at | DATETIME | NOT NULL | CURRENT_TIMESTAMP | - | チェック日時 |

**複合UNIQUE制約**: `UNIQUE(match_id, side_effect_id)`

#### インデックス

| インデックス名 | 対象カラム | 種類 | 目的 |
|--------------|-----------|------|------|
| PRIMARY KEY | check_id | UNIQUE | 主キー検索 |
| UNIQUE | (match_id, side_effect_id) | 複合UNIQUE | 重複防止・複合検索 |
| idx_checked_symptoms_match | match_id | 非UNIQUE | 照合結果からのチェック症状検索（最頻出） |
| idx_checked_symptoms_side_effect | side_effect_id | 非UNIQUE | 副作用からの逆引き |
| idx_checked_symptoms_date | checked_at | 非UNIQUE | チェック日時ソート |

#### バリデーションルール

| 項目 | ルール | エラーメッセージ |
|------|-------|----------------|
| match_id | 必須、正の整数、存在チェック | 「照合結果を選択してください」 |
| match_id | is_matched=1の照合結果のみ | 「該当していない薬剤には症状をチェックできません」 |
| side_effect_id | 必須、正の整数、存在チェック | 「症状を選択してください」 |
| 複合キー | 重複チェック | 「この症状は既にチェック済みです」 |

---

### 8. SummarySheets（症状まとめシート）

**概要**: ユーザーが作成した症状まとめシートを管理

#### DDL（テーブル定義）

```sql
CREATE TABLE SummarySheets (
    sheet_id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id INTEGER NOT NULL UNIQUE,
    generated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    pdf_exported_at DATETIME DEFAULT NULL,
    printed_at DATETIME DEFAULT NULL,
    FOREIGN KEY (image_id) 
        REFERENCES UploadedImages(image_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- インデックス
CREATE INDEX idx_summary_sheets_image ON SummarySheets(image_id);
CREATE INDEX idx_summary_sheets_generated ON SummarySheets(generated_at DESC);
CREATE INDEX idx_summary_sheets_pdf ON SummarySheets(pdf_exported_at);
CREATE INDEX idx_summary_sheets_printed ON SummarySheets(printed_at);
```

#### カラム定義

| カラム名 | データ型 | NULL | デフォルト値 | 制約 | 説明 |
|---------|---------|:----:|------------|------|------|
| sheet_id | INTEGER | NOT NULL | 自動採番 | PRIMARY KEY, AUTOINCREMENT | シートの一意識別子 |
| image_id | INTEGER | NOT NULL | - | FK → UploadedImages, UNIQUE | 画像への外部キー（1画像につき1シート） |
| generated_at | DATETIME | NOT NULL | CURRENT_TIMESTAMP | - | シート生成日時 |
| pdf_exported_at | DATETIME | NULL | NULL | - | PDF出力日時（未出力の場合NULL） |
| printed_at | DATETIME | NULL | NULL | - | 印刷実行日時（未印刷の場合NULL） |

**UNIQUE制約**: `UNIQUE(image_id)` でMVP版では1画像につき1シートを強制

#### インデックス

| インデックス名 | 対象カラム | 種類 | 目的 |
|--------------|-----------|------|------|
| PRIMARY KEY | sheet_id | UNIQUE | 主キー検索 |
| UNIQUE | image_id | UNIQUE | 画像からのシート検索（1対1） |
| idx_summary_sheets_generated | generated_at | 非UNIQUE | 生成日時降順ソート |
| idx_summary_sheets_pdf | pdf_exported_at | 非UNIQUE | PDF出力済みフィルタ |
| idx_summary_sheets_printed | printed_at | 非UNIQUE | 印刷済みフィルタ |

#### バリデーションルール

| 項目 | ルール | エラーメッセージ |
|------|-------|----------------|
| image_id | 必須、正の整数、UNIQUE | 「画像を選択してください」 |
| image_id | 存在チェック | 「選択された画像が見つかりません」 |
| image_id | 重複チェック | 「この画像のシートは既に存在します」 |
| image_id | 抽出結果の存在チェック | 「この画像には抽出結果がありません」 |
| pdf_exported_at | 未来日時禁止 | 「未来の日時は設定できません」 |
| pdf_exported_at | generated_at以降の日時 | 「シート生成日時より前の日時は設定できません」 |
| printed_at | pdf_exported_at >= generated_at | 「印刷日時はPDF出力日時より前にできません」 |
| printed_at | pdf_exported_atがNULLの場合、printed_atも必須NULL | 「PDF出力前に印刷することはできません」 |

---

## インデックス設計

### インデックス統計サマリー

| テーブル | 主キー | UNIQUE | 外部キー用 | 検索用 | ソート用 | 複合 | 合計 |
|---------|:------:|:------:|:--------:|:------:|:-------:|:----:|:----:|
| Medicines | 1 | 0 | 0 | 3 | 1 | 0 | **5** |
| SideEffects | 1 | 1 | 0 | 0 | 1 | 0 | **3** |
| Medicine_SideEffect | 1 | 1 | 2 | 0 | 0 | 0 | **4** |
| UploadedImages | 1 | 1 | 0 | 1 | 1 | 0 | **4** |
| ExtractedMedicines | 1 | 0 | 1 | 2 | 1 | 0 | **5** |
| MatchedMedicines | 1 | 0 | 2 | 1 | 1 | 1 | **6** |
| CheckedSymptoms | 1 | 1 | 2 | 0 | 1 | 0 | **5** |
| SummarySheets | 1 | 1 | 0 | 2 | 1 | 0 | **5** |
| **合計** | **8** | **5** | **9** | **9** | **8** | **1** | **37** |

### 重要度別インデックス分類

#### ⭐⭐⭐ 超重要（必須実装）

これらのインデックスは性能に直結し、必ず作成すべきです。

```sql
-- 外部キー（JOIN性能向上）
CREATE INDEX idx_medicine_side_effect_medicine ON Medicine_SideEffect(medicine_id);
CREATE INDEX idx_extracted_medicines_image ON ExtractedMedicines(image_id);
CREATE INDEX idx_matched_medicines_extracted ON MatchedMedicines(extracted_id);
CREATE INDEX idx_checked_symptoms_match ON CheckedSymptoms(match_id);

-- 最頻出検索
CREATE INDEX idx_medicines_name ON Medicines(medicine_name);
CREATE INDEX idx_uploaded_images_date ON UploadedImages(uploaded_at DESC);
CREATE INDEX idx_matched_medicines_extracted_matched ON MatchedMedicines(extracted_id, is_matched);
```

#### ⭐⭐ 重要（推奨実装）

アプリの快適性向上に貢献します。

```sql
-- 検索・フィルタ用
CREATE INDEX idx_medicines_generic ON Medicines(generic_name);
CREATE INDEX idx_matched_medicines_medicine ON MatchedMedicines(medicine_id);
CREATE INDEX idx_checked_symptoms_side_effect ON CheckedSymptoms(side_effect_id);
CREATE INDEX idx_summary_sheets_generated ON SummarySheets(generated_at DESC);
```

#### ⭐ 通常（必要に応じて実装）

データ量が増えた時に追加を検討します。

```sql
-- 管理機能・レポート用
CREATE INDEX idx_medicines_category ON Medicines(drug_category);
CREATE INDEX idx_extracted_medicines_edited ON ExtractedMedicines(is_manually_edited);
CREATE INDEX idx_summary_sheets_pdf ON SummarySheets(pdf_exported_at);
```

### パフォーマンス影響分析

| 対象テーブル | インデックスなし | インデックスあり | 改善率 |
|------------|:---------------:|:---------------:|:-----:|
| Medicines照合（10,000件） | ~500ms | ~5ms | **100倍** |
| 画像の抽出結果取得 | ~100ms | ~1ms | **100倍** |
| 該当薬剤の症状取得 | ~50ms | ~1ms | **50倍** |
| シート一覧ソート | ~200ms | ~5ms | **40倍** |

---

## バリデーションルール

### バリデーション設計の方針

**3層バリデーション戦略**：
1. **データベース層**: 最終防衛線（制約、トリガー）
2. **アプリケーション層**: ビジネスロジック（バックエンド）
3. **UI層**: ユーザー体験（フロントエンド、即時フィードバック）

### セキュリティバリデーション

#### SQLインジェクション対策

```python
def sanitize_input(value: str) -> str:
    """入力値のサニタイゼーション"""
    # パラメータ化クエリ使用が基本だが、念のため
    dangerous_chars = ["'", '"', ';', '--', '/*', '*/', 'xp_', 'sp_']
    
    for char in dangerous_chars:
        if char in value:
            raise ValueError(f"不正な文字が含まれています: {char}")
    
    return value
```

#### XSS対策

```python
import html

def sanitize_html(value: str) -> str:
    """HTMLタグのエスケープ"""
    return html.escape(value)
```

#### ファイルアップロード対策

```python
import magic

def validate_file_upload(file_path: str, file_size: int) -> tuple[bool, str]:
    """アップロードファイルのセキュリティ検証"""
    # 1. ファイル名チェック
    if any(char in file_path for char in ['..', '/', '\\']):
        return False, "不正なファイル名です"
    
    # 2. ファイルサイズチェック（Zip爆弾対策）
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    if file_size > MAX_FILE_SIZE:
        return False, "ファイルサイズが大きすぎます"
    
    # 3. MIME typeチェック
    mime = magic.from_file(file_path, mime=True)
    if mime not in ['image/jpeg', 'image/png']:
        return False, "画像ファイルではありません"
    
    return True, ""
```

### クロスフィールドバリデーション

#### 時系列整合性チェック

```python
from datetime import datetime

def validate_timestamp_order(timestamps: dict) -> tuple[bool, str]:
    """時系列の整合性を検証"""
    now = datetime.now()
    
    for key, value in timestamps.items():
        if value and value > now:
            return False, f"{key}に未来の日時が設定されています"
    
    # ExtractedMedicines
    if 'extracted_at' in timestamps and 'edited_at' in timestamps:
        if timestamps['edited_at'] and timestamps['edited_at'] < timestamps['extracted_at']:
            return False, "手動編集日時は抽出日時より後でなければなりません"
    
    # SummarySheets
    if all(k in timestamps for k in ['generated_at', 'pdf_exported_at', 'printed_at']):
        if timestamps['pdf_exported_at'] and timestamps['pdf_exported_at'] < timestamps['generated_at']:
            return False, "PDF出力日時はシート生成日時より後でなければなりません"
        
        if timestamps['printed_at']:
            if not timestamps['pdf_exported_at']:
                return False, "PDF出力前に印刷することはできません"
            if timestamps['printed_at'] < timestamps['pdf_exported_at']:
                return False, "印刷日時はPDF出力日時より後でなければなりません"
    
    return True, ""
```

### バリデーション実装例

#### Medicines（薬剤マスタ）のバリデーション

```python
import re

def validate_medicine_name(name: str) -> tuple[bool, str]:
    """薬剤名のバリデーション"""
    if not name or not name.strip():
        return False, "薬剤名を入力してください"
    
    # トリム・正規化
    name = name.strip()
    name = re.sub(r'\s+', ' ', name)  # 連続空白を単一に
    
    if len(name) > 200:
        return False, f"薬剤名は200文字以内で入力してください（現在: {len(name)}文字）"
    
    # 使用可能文字チェック（日本語薬剤名対応）
    if not re.match(r'^[ぁ-んァ-ヶー一-龠a-zA-Z0-9０-９\s\-・（）()]+$', name):
        return False, "薬剤名に使用できない文字が含まれています"
    
    return True, ""
```

#### SideEffects（副作用症状マスタ）のバリデーション

```python
def validate_symptom_name(name: str, existing_id: int = None) -> tuple[bool, str]:
    """症状名のバリデーション"""
    if not name or not name.strip():
        return False, "症状名を入力してください"
    
    name = name.strip()
    
    if len(name) > 100:
        return False, f"症状名は100文字以内で入力してください（現在: {len(name)}文字）"
    
    # 日本語のみ
    if not re.match(r'^[ぁ-んァ-ヶー一-龠\s]+$', name):
        return False, "症状名は日本語（ひらがな・カタカナ・漢字）で入力してください"
    
    # 重複チェック（更新時は自分自身を除外）
    query = "SELECT COUNT(*) FROM SideEffects WHERE symptom_name = ?"
    if existing_id:
        query += f" AND side_effect_id != {existing_id}"
    
    # 重複があればエラー
    if check_duplicate(query, name):
        return False, "この症状名は既に登録されています"
    
    return True, ""
```

#### MatchedMedicines（照合結果）のバリデーション

```python
def validate_matched_medicine(is_matched: bool, medicine_id: int = None) -> tuple[bool, str]:
    """照合結果のバリデーション"""
    if is_matched:
        if medicine_id is None:
            return False, "該当薬剤を選択してください"
        if medicine_id <= 0:
            return False, "無効な薬剤IDです"
    else:
        if medicine_id is not None:
            return False, "非該当の場合、薬剤IDは設定できません"
    
    return True, ""
```

### バリデーション優先度

| 重要度 | 対象 | 理由 |
|-------|------|------|
| **🔴 Critical** | 外部キー整合性、UNIQUE制約、該当フラグとIDの整合性 | データ破損防止 |
| **🟠 High** | 必須項目、文字数制限、ファイル形式・サイズ | アプリ動作保証 |
| **🟡 Medium** | 時系列整合性、重複警告、データ正規化 | データ品質向上 |
| **🟢 Low** | プレースホルダー、サジェスト、リアルタイム表示 | UX向上 |

---

## シーダーデータ

### マスタデータ（本番環境で必要）

#### Medicines（薬剤マスタ）: 30件

高齢者の安全な薬物療法ガイドライン2015に基づく注意薬剤リスト

- 睡眠薬・抗不安薬: ハルシオン、デパス、レンドルミン、マイスリー
- 抗精神病薬: セロクエル、リスパダール、セレネース
- 抗うつ薬: トリプタノール、アナフラニール
- 抗コリン薬: アーテン、バップフォー
- 解熱鎮痛薬: ロキソニン、ボルタレン、インドメタシン
- 降圧薬: アルドメット、カルデナリン
- 糖尿病治療薬: オイグルコン、グリミクロン
- 抗ヒスタミン薬: ポララミン、レスタミンコーワ
- その他: ラシックス、ガスター、ワーファリン、プラザキサ、テルネリン、ブスコパン、ヨウ化カリウム、プレドニン、フェロミア、ジゴシン

#### SideEffects（副作用症状マスタ）: 20件

高齢者で特に注意すべき副作用症状

- 転倒関連: めまい、ふらつき、立ちくらみ
- 認知機能関連: 物忘れ、混乱、せん妄
- 消化器症状: 吐き気、食欲不振、便秘、下痢、胃痛
- 循環器症状: 動悸、息切れ、むくみ
- 排尿関連: 尿が出にくい、頻尿
- その他: 眠気、口の渇き、手足のふるえ、発疹

#### Medicine_SideEffect（薬剤-副作用関連）: 約90件

主要な薬剤と副作用の関連付け（頻度情報含む）

### テストデータ（開発環境のみ）

#### UploadedImages: 5件
- 多様なテストシナリオをカバー
- 正常系・準正常系・エッジケースを含む

#### ExtractedMedicines: 11件
- OCR抽出結果
- 手動修正ありのケースを含む

#### MatchedMedicines: 11件
- 該当/非該当の両パターン
- 複数薬剤の照合結果

#### CheckedSymptoms: 12件
- 複数症状のチェック例
- 異なる薬剤での症状記録

#### SummarySheets: 5件
- PDF出力前後の状態
- 印刷済み/未印刷の両パターン

---

## 関連ドキュメント

- [requirements.md](./requirements.md) - 要件定義書
- [entities.md](./entities.md) - エンティティ詳細仕様
- [relationships.md](./relationships.md) - リレーションシップ設計書
- [er_diagram.md](./er_diagram.md) - ER図
- [features.md](./features.md) - 機能仕様書

---

## 改訂履歴

| バージョン | 日付 | 変更内容 | 変更者 |
|-----------|------|----------|--------|
| 1.0 | 2026-01-24 | 初版作成（テーブル定義、インデックス、バリデーション） | |

---

**文書ステータス**: 承認済  
**最終更新日**: 2026-01-24  
**次回レビュー予定**: Phase 2設計時
