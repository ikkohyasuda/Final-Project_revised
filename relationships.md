# リレーションシップ設計書

**プロジェクト**: 患者参加型・薬の安全チェックアプリ  
**作成日**: 2026-01-24  
**バージョン**: 1.0

---

## 📊 リレーションシップ概要

全8つのリレーションシップで構成されるデータベース設計

| 分類 | リレーション数 | 詳細 |
|------|:-------------:|------|
| 1対1 | 1件 | 画像 → まとめシート（MVP版） |
| 1対多 | 7件 | 階層的なデータ構造 |
| 多対多 | 1件 | 薬剤 ⇔ 副作用症状（中間テーブル経由） |
| **合計** | **8件** | - |

---

## 🔗 全リレーションシップ一覧表

| ID | 親エンティティ | 子エンティティ | 関係 | 外部キー | 削除制約 | 更新制約 | NULL許容 |
|:--:|------------|------------|:---:|---------|---------|---------|:-------:|
| R1 | Medicines | Medicine_SideEffect | 1:N | medicine_id | CASCADE | CASCADE | ❌ |
| R2 | SideEffects | Medicine_SideEffect | 1:N | side_effect_id | CASCADE | CASCADE | ❌ |
| R3 | UploadedImages | ExtractedMedicines | 1:N | image_id | CASCADE | CASCADE | ❌ |
| R4 | ExtractedMedicines | MatchedMedicines | 1:N | extracted_id | CASCADE | CASCADE | ❌ |
| R5 | Medicines | MatchedMedicines | 1:N | medicine_id | RESTRICT | CASCADE | ✅ |
| R6 | MatchedMedicines | CheckedSymptoms | 1:N | match_id | CASCADE | CASCADE | ❌ |
| R7 | SideEffects | CheckedSymptoms | 1:N | side_effect_id | RESTRICT | CASCADE | ❌ |
| R8 | UploadedImages | SummarySheets | 1:1 | image_id | CASCADE | CASCADE | ❌ |

---

## 📐 関係種類別の整理

### 🟢 1対1関係（1:1）

| 親テーブル | 子テーブル | 外部キー | 削除制約 | UNIQUE制約 | ビジネスルール |
|-----------|-----------|---------|---------|-----------|--------------|
| UploadedImages | SummarySheets | image_id | CASCADE | UNIQUE(image_id) | MVP版では1画像につき1シート |

**実装方法**:
```sql
CREATE TABLE SummarySheets (
  sheet_id INTEGER PRIMARY KEY AUTOINCREMENT,
  image_id INTEGER NOT NULL UNIQUE,  -- UNIQUE制約で1対1を強制
  generated_at DATETIME NOT NULL,
  FOREIGN KEY (image_id) REFERENCES UploadedImages(image_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);
```

**Phase 2での拡張**:
- UNIQUE制約を削除 → 1対多に変更
- 複数回のチェック履歴を管理可能に

---

### 🟡 1対多関係（1:N）

| ID | 親テーブル | 子テーブル | 外部キー | 削除制約 | 理由 |
|:--:|-----------|-----------|---------|---------|------|
| R1 | Medicines | Medicine_SideEffect | medicine_id | CASCADE | マスタ削除時、関連も削除 |
| R2 | SideEffects | Medicine_SideEffect | side_effect_id | CASCADE | マスタ削除時、関連も削除 |
| R3 | UploadedImages | ExtractedMedicines | image_id | CASCADE | 画像削除時、抽出結果も削除 |
| R4 | ExtractedMedicines | MatchedMedicines | extracted_id | CASCADE | 抽出削除時、照合結果も削除 |
| R5 | Medicines | MatchedMedicines | medicine_id | RESTRICT | 参照中のマスタは削除不可 |
| R6 | MatchedMedicines | CheckedSymptoms | match_id | CASCADE | 照合削除時、チェックも削除 |
| R7 | SideEffects | CheckedSymptoms | side_effect_id | RESTRICT | 参照中のマスタは削除不可 |

---

### 🔴 多対多関係（N:M）

| テーブルA | テーブルB | 中間テーブル | 理由 |
|----------|----------|------------|------|
| Medicines | SideEffects | Medicine_SideEffect | 1つの薬剤は複数の副作用を持ち、1つの副作用は複数の薬剤で共通 |

**実装方法**:
```sql
CREATE TABLE Medicine_SideEffect (
  relation_id INTEGER PRIMARY KEY AUTOINCREMENT,
  medicine_id INTEGER NOT NULL,
  side_effect_id INTEGER NOT NULL,
  frequency_note VARCHAR(50),
  created_at DATETIME NOT NULL,
  FOREIGN KEY (medicine_id) REFERENCES Medicines(medicine_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (side_effect_id) REFERENCES SideEffects(side_effect_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  UNIQUE(medicine_id, side_effect_id)  -- 同じ組み合わせの重複を防止
);
```

---

## 🎯 詳細リレーションシップ仕様

### R1: Medicines → Medicine_SideEffect（1対多）

**概要**: 薬剤マスタと副作用関連データ

```sql
FOREIGN KEY (medicine_id) 
  REFERENCES Medicines(medicine_id)
  ON DELETE CASCADE
  ON UPDATE CASCADE
```

**仕様**:
- **カーディナリティ**: 1薬剤あたり1〜20副作用（想定）
- **NULL許容**: 不可
- **削除制約**: CASCADE（薬剤削除時、関連も自動削除）
- **ビジネスルール**: 管理者のみマスタ削除可能

---

### R2: SideEffects → Medicine_SideEffect（1対多）

**概要**: 副作用症状マスタと薬剤関連データ

```sql
FOREIGN KEY (side_effect_id) 
  REFERENCES SideEffects(side_effect_id)
  ON DELETE CASCADE
  ON UPDATE CASCADE
```

**仕様**:
- **カーディナリティ**: 1副作用あたり1〜50薬剤（想定）
- **NULL許容**: 不可
- **削除制約**: CASCADE（副作用削除時、関連も自動削除）
- **ビジネスルール**: 管理者のみマスタ削除可能

---

### R3: UploadedImages → ExtractedMedicines（1対多）

**概要**: アップロード画像とOCR抽出結果

```sql
FOREIGN KEY (image_id) 
  REFERENCES UploadedImages(image_id)
  ON DELETE CASCADE
  ON UPDATE CASCADE
```

**仕様**:
- **カーディナリティ**: 1画像あたり0〜20抽出結果（想定）
- **NULL許容**: 不可
- **削除制約**: CASCADE（画像削除時、抽出結果も全削除）
- **ビジネスルール**: 
  - 削除時に確認ダイアログ表示
  - 「関連する全ての結果が削除されます」と警告

**カーディナリティ詳細**:
- 最小: 0件（OCR失敗時）
- 平均: 5〜10件
- 最大: 20件程度

---

### R4: ExtractedMedicines → MatchedMedicines（1対多）

**概要**: 抽出薬剤と注意薬剤マスタの照合結果

```sql
FOREIGN KEY (extracted_id) 
  REFERENCES ExtractedMedicines(extracted_id)
  ON DELETE CASCADE
  ON UPDATE CASCADE
```

**仕様**:
- **カーディナリティ**: 1抽出あたり1〜5照合結果
- **NULL許容**: 不可
- **削除制約**: CASCADE（抽出削除時、照合結果も全削除）
- **ビジネスルール**: 
  - 部分一致で複数マッチの可能性あり
  - 該当なしの場合もレコード作成（is_matched=false）

**照合例**:
```
抽出薬剤: "ロキソニン"
  → マッチ1: "ロキソニン錠60mg" (is_matched=true)
  → マッチ2: "ロキソニンテープ100mg" (is_matched=true)
  → マッチ3: "ロキソプロフェンNa" (is_matched=true)
```

---

### R5: Medicines → MatchedMedicines（1対多）

**概要**: 薬剤マスタの照合結果での参照

```sql
FOREIGN KEY (medicine_id) 
  REFERENCES Medicines(medicine_id)
  ON DELETE RESTRICT
  ON UPDATE CASCADE
```

**仕様**:
- **カーディナリティ**: 1薬剤マスタあたり0〜多数の照合結果
- **NULL許容**: 可（is_matched=falseの場合のみ）
- **削除制約**: RESTRICT（参照中は削除不可）
- **ビジネスルール**: 
  - 参照件数チェック後に削除
  - エラーメッセージ: 「この薬剤は○件の照合結果で使用されています」

**削除前チェックSQL**:
```sql
SELECT COUNT(*) FROM MatchedMedicines WHERE medicine_id = ?;
```

---

### R6: MatchedMedicines → CheckedSymptoms（1対多）

**概要**: 該当薬剤とユーザーがチェックした症状

```sql
FOREIGN KEY (match_id) 
  REFERENCES MatchedMedicines(match_id)
  ON DELETE CASCADE
  ON UPDATE CASCADE
```

**仕様**:
- **カーディナリティ**: 1照合結果あたり0〜10チェック症状（想定）
- **NULL許容**: 不可
- **削除制約**: CASCADE（照合結果削除時、チェックも全削除）
- **複合UNIQUE制約**: `UNIQUE(match_id, side_effect_id)`
- **ビジネスルール**: 
  - 同じ症状の重複チェック不可
  - チェックボックスで複数選択可能

---

### R7: SideEffects → CheckedSymptoms（1対多）

**概要**: 副作用症状マスタのチェック症状での参照

```sql
FOREIGN KEY (side_effect_id) 
  REFERENCES SideEffects(side_effect_id)
  ON DELETE RESTRICT
  ON UPDATE CASCADE
```

**仕様**:
- **カーディナリティ**: 1副作用マスタあたり0〜多数のチェック
- **NULL許容**: 不可
- **削除制約**: RESTRICT（チェック履歴がある場合は削除不可）
- **ビジネスルール**: 
  - 履歴保護のため参照中は削除不可
  - 論理削除（is_deleted フラグ）の検討も可

---

### R8: UploadedImages → SummarySheets（1対1）

**概要**: 画像と症状まとめシート（MVP版）

```sql
FOREIGN KEY (image_id) 
  REFERENCES UploadedImages(image_id)
  ON DELETE CASCADE
  ON UPDATE CASCADE
```

**仕様**:
- **カーディナリティ**: 1画像につき1シート（MVP版）
- **NULL許容**: 不可
- **削除制約**: CASCADE（画像削除時、シートも削除）
- **UNIQUE制約**: `UNIQUE(image_id)` で1対1を強制
- **ビジネスルール**: 
  - MVP版: 最新のチェック結果のみ保持
  - Phase 2: 1対多に変更し履歴管理

**Phase 2への移行**:
```sql
-- UNIQUE制約を削除
ALTER TABLE SummarySheets DROP CONSTRAINT IF EXISTS unique_image_id;
-- 生成回数カラム追加
ALTER TABLE SummarySheets ADD COLUMN generation_number INTEGER DEFAULT 1;
```

---

## 🔒 複合ユニーク制約一覧

| テーブル | カラム組み合わせ | 目的 | 制約名 |
|---------|----------------|------|--------|
| Medicine_SideEffect | (medicine_id, side_effect_id) | 同じ薬剤-副作用の組み合わせの重複防止 | uk_medicine_side_effect |
| CheckedSymptoms | (match_id, side_effect_id) | 同じ照合結果に対する症状の重複チェック防止 | uk_checked_symptoms |
| SummarySheets | (image_id) | 1画像につき1シート（MVP版） | uk_summary_sheets_image |

**実装例**:
```sql
-- 複合ユニーク制約の作成
CREATE UNIQUE INDEX uk_medicine_side_effect 
  ON Medicine_SideEffect(medicine_id, side_effect_id);

CREATE UNIQUE INDEX uk_checked_symptoms 
  ON CheckedSymptoms(match_id, side_effect_id);

CREATE UNIQUE INDEX uk_summary_sheets_image 
  ON SummarySheets(image_id);
```

---

## 📋 削除制約の選択基準

### CASCADE（連鎖削除）

**使用ケース**:

| 条件 | 理由 | 該当リレーション |
|------|------|----------------|
| トランザクションデータ | ユーザー操作データは親に従属 | R3, R4, R6, R8 |
| 中間テーブル | 多対多の中間テーブルは両親に従属 | R1, R2 |
| 密接な関連 | 親なしでは意味をなさないデータ | 全てのCASCADE |

**利点**:
- データ整合性の自動維持
- 孤立レコードの防止
- 実装の簡素化

**注意点**:
- 意図しない大量削除の可能性
- 削除前の確認ダイアログ必須

---

### RESTRICT（削除制限）

**使用ケース**:

| 条件 | 理由 | 該当リレーション |
|------|------|----------------|
| マスタデータ参照 | 参照整合性の厳密な保護 | R5, R7 |
| 履歴データ | 過去データの保護 | R5, R7 |
| 慎重な削除 | 誤削除の防止 | R5, R7 |

**利点**:
- マスタデータの保護
- 履歴の保全
- 意図しない削除の防止

**実装時の対応**:
```sql
-- 削除前チェック
BEGIN TRANSACTION;

-- 参照件数確認
SELECT COUNT(*) INTO ref_count 
FROM MatchedMedicines 
WHERE medicine_id = ?;

IF ref_count > 0 THEN
  ROLLBACK;
  RAISE ERROR('この薬剤は' || ref_count || '件の照合結果で使用されています');
ELSE
  DELETE FROM Medicines WHERE medicine_id = ?;
  COMMIT;
END IF;
```

---

### SET NULL（NULL設定）

**使用しない理由**:
- MVP版では親子関係が必須
- データの整合性維持のため
- 例外: `MatchedMedicines.medicine_id`（該当なし時のみNULL）

---

## 🎯 参照整合性チェックSQL

### 画像削除前の影響範囲確認

```sql
-- 削除される関連データ件数の確認
SELECT 
  ui.image_id,
  ui.file_path,
  COUNT(DISTINCT em.extracted_id) AS extracted_count,
  COUNT(DISTINCT mm.match_id) AS matched_count,
  COUNT(DISTINCT cs.check_id) AS checked_count,
  COUNT(DISTINCT ss.sheet_id) AS sheet_count
FROM UploadedImages ui
LEFT JOIN ExtractedMedicines em ON ui.image_id = em.image_id
LEFT JOIN MatchedMedicines mm ON em.extracted_id = mm.extracted_id
LEFT JOIN CheckedSymptoms cs ON mm.match_id = cs.match_id
LEFT JOIN SummarySheets ss ON ui.image_id = ss.image_id
WHERE ui.image_id = ?
GROUP BY ui.image_id;
```

---

### 薬剤マスタ削除前の参照確認

```sql
-- 薬剤マスタの参照件数確認
SELECT 
  m.medicine_id,
  m.medicine_name,
  COUNT(DISTINCT mse.relation_id) AS side_effect_relations,
  COUNT(DISTINCT mm.match_id) AS match_results
FROM Medicines m
LEFT JOIN Medicine_SideEffect mse ON m.medicine_id = mse.medicine_id
LEFT JOIN MatchedMedicines mm ON m.medicine_id = mm.medicine_id
WHERE m.medicine_id = ?
GROUP BY m.medicine_id;
```

---

### 副作用症状マスタ削除前の参照確認

```sql
-- 副作用症状マスタの参照件数確認
SELECT 
  se.side_effect_id,
  se.symptom_name,
  COUNT(DISTINCT mse.relation_id) AS medicine_relations,
  COUNT(DISTINCT cs.check_id) AS check_history
FROM SideEffects se
LEFT JOIN Medicine_SideEffect mse ON se.side_effect_id = mse.side_effect_id
LEFT JOIN CheckedSymptoms cs ON se.side_effect_id = cs.side_effect_id
WHERE se.side_effect_id = ?
GROUP BY se.side_effect_id;
```

---

## 🔧 実装時の重要設定

### SQLiteの外部キー制約有効化

**必須設定**:
```sql
-- 毎回のDB接続時に実行
PRAGMA foreign_keys = ON;
```

**確認方法**:
```sql
-- 設定確認
PRAGMA foreign_keys;  -- 結果: 1（有効）、0（無効）
```

**Python実装例**:
```python
import sqlite3

def get_db_connection():
    conn = sqlite3.connect('medication_checker.db')
    conn.execute('PRAGMA foreign_keys = ON;')  # 外部キー制約を有効化
    return conn
```

---

### インデックス作成推奨

**全ての外部キーにインデックスを作成**:

```sql
-- R3: ExtractedMedicines.image_id
CREATE INDEX idx_extracted_medicines_image_id 
  ON ExtractedMedicines(image_id);

-- R4: MatchedMedicines.extracted_id
CREATE INDEX idx_matched_medicines_extracted_id 
  ON MatchedMedicines(extracted_id);

-- R5: MatchedMedicines.medicine_id
CREATE INDEX idx_matched_medicines_medicine_id 
  ON MatchedMedicines(medicine_id);

-- R6: CheckedSymptoms.match_id
CREATE INDEX idx_checked_symptoms_match_id 
  ON CheckedSymptoms(match_id);

-- R7: CheckedSymptoms.side_effect_id
CREATE INDEX idx_checked_symptoms_side_effect_id 
  ON CheckedSymptoms(side_effect_id);

-- R8: SummarySheets.image_id
CREATE INDEX idx_summary_sheets_image_id 
  ON SummarySheets(image_id);
```

**パフォーマンス効果**:
- JOIN操作の高速化
- 外部キー制約チェックの高速化
- 削除時の参照チェックの高速化

---

## 📊 トランザクション管理

### 画像削除のトランザクション例

```sql
BEGIN TRANSACTION;

-- 1. 影響範囲の確認
SELECT COUNT(*) INTO total_records
FROM ExtractedMedicines
WHERE image_id = ?;

-- 2. 画像削除（CASCADE により関連データも自動削除）
DELETE FROM UploadedImages WHERE image_id = ?;

-- 3. エラーなければコミット
COMMIT;

-- エラー時はロールバック
-- ROLLBACK;
```

---

### マスタデータ更新のトランザクション例

```sql
BEGIN TRANSACTION;

-- 1. 既存データの削除チェック
SELECT COUNT(*) INTO ref_count
FROM MatchedMedicines
WHERE medicine_id = ?;

IF ref_count > 0 THEN
  ROLLBACK;
  RAISE ERROR('参照データが存在するため削除できません');
END IF;

-- 2. マスタデータの更新/削除
DELETE FROM Medicines WHERE medicine_id = ?;

-- 3. コミット
COMMIT;
```

---

## 🎨 ER図（Entity-Relationship Diagram）

```
[マスタデータ層]
┌─────────────┐        ┌──────────────────────┐        ┌──────────────┐
│  Medicines  │◄───N───│ Medicine_SideEffect  │───N───►│ SideEffects  │
│ (薬剤マスタ)  │        │   (中間テーブル)       │        │(副作用マスタ) │
└─────────────┘        └──────────────────────┘        └──────────────┘
       │                                                        │
       │ RESTRICT                                               │ RESTRICT
       │                                                        │
       ▼                                                        ▼

[トランザクションデータ層]
┌─────────────────┐
│ UploadedImages  │
│ (アップロード画像) │
└────────┬────────┘
         │ CASCADE (1:N)
         ├──────────────────────────────────────┐
         │                                      │ CASCADE (1:1)
         ▼                                      ▼
┌──────────────────┐                   ┌──────────────────┐
│ExtractedMedicines│                   │  SummarySheets   │
│  (抽出薬剤)       │                   │ (症状まとめシート) │
└────────┬─────────┘                   └──────────────────┘
         │ CASCADE (1:N)
         ▼
┌──────────────────┐
│ MatchedMedicines │◄──────────┐
│  (該当薬剤照合)   │            │ (マスタ参照)
└────────┬─────────┘            │
         │ CASCADE (1:N)        │
         ▼                      │
┌──────────────────┐            │
│ CheckedSymptoms  │────────────┘
│  (チェック症状)   │      (マスタ参照)
└──────────────────┘

凡例:
─── : リレーションシップ
◄─► : 多対多（中間テーブル経由）
CASCADE : 連鎖削除
RESTRICT : 削除制限
1:1 : 1対1関係
1:N : 1対多関係
N:M : 多対多関係
```

---

## 📈 データフロー図

```
[ユーザー操作フロー]

1. 画像アップロード
   UploadedImages (作成)

2. OCR抽出
   ExtractedMedicines (作成) ← image_id参照

3. 照合処理
   MatchedMedicines (作成) ← extracted_id参照
                           ← medicine_id参照（マスタ）

4. 症状チェック
   CheckedSymptoms (作成) ← match_id参照
                          ← side_effect_id参照（マスタ）

5. まとめシート生成
   SummarySheets (作成) ← image_id参照
```

---

## 🔍 リレーションシップ検証チェックリスト

### 設計検証

- [ ] 全ての外部キーに対応する主キーが存在する
- [ ] 削除制約が適切に設定されている
- [ ] 必要な複合ユニーク制約が定義されている
- [ ] NULL許容が適切に設定されている
- [ ] カーディナリティが現実的な範囲である

### 実装検証

- [ ] `PRAGMA foreign_keys = ON;` が設定されている
- [ ] 全ての外部キーにインデックスが作成されている
- [ ] CASCADE削除の影響範囲確認処理がある
- [ ] RESTRICT削除時のエラーハンドリングがある
- [ ] トランザクション管理が適切である

### テスト検証

- [ ] CASCADE削除が正常に動作する
- [ ] RESTRICT削除が適切にエラーを返す
- [ ] 複合ユニーク制約が重複を防止する
- [ ] 孤立レコードが発生しない
- [ ] ロールバックが正常に動作する

---

## 📚 関連ドキュメント

- [entities.md](./entities.md) - エンティティ詳細仕様
- [requirements.md](./requirements.md) - 要件定義書
- [features.md](./features.md) - 機能仕様書

---

## 🔄 改訂履歴

| バージョン | 日付 | 変更内容 | 変更者 |
|-----------|------|----------|--------|
| 1.0 | 2026-01-24 | 初版作成 | |

---

**文書ステータス**: 承認済  
**最終更新日**: 2026-01-24
