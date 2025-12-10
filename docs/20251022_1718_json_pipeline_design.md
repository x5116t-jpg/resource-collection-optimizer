# マスタデータJSON変換・読込設計

## 1. 背景
- CSV マスタを都度クレンジングする方式から、バッチで整形済み JSON を生成しアプリ側は読み取るだけの構成へ切り替える。
- 対象ファイル:
  - `data/車両資源適合性マトリックス.csv`
  - `data/車両諸元表.csv`
  - `data/補足データ集.csv`
  - `data/未利用資源特性表.csv`
- 既存の `MasterData` ローダーを整形に利用し、JSON 出力のスキーマを固定する。

## 2. 変換スクリプト設計
- 追加ファイル: `scripts/build_master_data.py`
  - 実行例: `python scripts/build_master_data.py --input data --output data/processed`
  - 処理手順:
    1. `MasterData.load(Path(input_dir))` で CSV を読み込みクレンジング。
    2. 変換ロジックで JSON 形式へ整形。
    3. 出力ディレクトリを作成（既存ファイルはバックアップ or 上書き）。
    4. 4 種類の JSON を保存。
  - オプション
    - `--pretty` でインデント付き出力。
    - `--overwrite` で上書き確認を抑止。
    - `--summary` で要約を標準出力。

### 2.1 JSON 出力ファイル
| ファイル名 | 内容 | スキーマ概要 |
| --- | --- | --- |
| `vehicles.json` | 車両諸元から集計した車種一覧 | `{"vehicles": [{"name": str, "capacity_kg": int, "volume_m3": float, "fuel_type": str, "fixed_cost_per_km": float, "variable_cost_per_km": float, "raw": {...}}]}` |
| `compatibility.json` | 車両×資源の適合性 | `{"compatibility": {vehicle_name: {"supports": {resource: bool|null}, "requirements": {resource: str|null}}}}` |
| `resources.json` | 資源特性 | `{"resources": [{"name": str, "bulk_density": {"min": float, "max": float, "avg": float}, "constraint_type": str, "treatment": str, "gate_fee": {...}, "notes": str}...]}` |
| `supplement.json` | 補足データ（カテゴリ別） | `{"categories": {category: [{"item": str, "values": [str|null x4], "description": str}]}, "notes": [...]}` |

- `raw` フィールドには変換前のデータを格納（任意）して検証性を確保。
- 数値レンジは `{ "min": number, "max": number, "avg": number }` で統一。
- `None` は JSON `null` として保存。

### 2.2 コスト計算の方針
- `MasterData` の `VehicleSpec.metrics` を利用し、代表値を以下のように算出:
  - `capacity_kg = max_payload_t.range.average * 1000`（欠損時は 0）。
  - 可変費 (`variable_cost_per_km`) は対象数値カラムの平均を合算（燃料費・高速料金・タイヤ交換等）。
  - 固定費 (`fixed_cost_per_km`) は年間費用項目 (減価償却・税・保険等) を合算し、`年間走行距離_km` (平均値) で割戻し。
  - 補足データ (`燃費補正係数`, `燃料単価`, `NEXCO料金区分`) を適用する計算式はスクリプト側で定数化。
- これらの計算式を関数化し、追加の係数や今後の拡張に備える。

## 3. アプリ側の読込ロジック
- 新モジュール案: `src/services/master_repository.py`
  - `load_processed_master(base_dir: Path) -> ProcessedMasterData`
  - JSON 読み込みとバリデーションを担当。
- `ProcessedMasterData` 構造
  ```python
  @dataclass
  class ProcessedMasterData:
      vehicles: List[VehicleCandidate]
      compatibility: Dict[str, CompatibilityInfo]
      resources: Dict[str, ResourceInfo]
      supplement: SupplementInfo
  ```
- Streamlit から利用する箇所
  1. 車両カタログ初期化 (`_init_session_state` の代替) → `vehicles.json` をベースに `VehicleCatalog` へ詰め替え。
  2. 資源セレクター → `resources.json` の `name` を候補とする。
  3. 適合性チェック → `compatibility.json` を参照して UI 上でフィードバック。
  4. 補足情報表示 → `supplement.json` から利用シーンごとに提示。

### 3.1 Streamlit 側の流れ
1. 起動時、`load_processed_master(Path("data/processed"))` を `@st.cache_resource` 付で読込。
2. 車両リストが session state に無い場合、`vehicles` をもとに初期化。
3. 資源選択 UI で `resources` を使って選択肢生成。
4. 車両×資源の整合性チェック機能を `compatibility` で実装。

## 4. バリデーションとテスト
- 変換スクリプト実行時に以下を検証:
  - 各 JSON の主キー重複がない。
  - 必須フィールド欠損時は警告/エラーを出す。
  - 変換件数をログ表示して人手で確認できる。
- Streamlit 起動時、JSON 読込に失敗した場合は警告とともにグレースフルにデフォルトデータへフォールバック。
- 単体テスト
  - `tests/test_data_loader.py` (追加) で `scripts/build_master_data` をサブプロセス起動せずに直接関数呼び出しし、サンプルデータで JSON の生成内容を確認。

## 5. 今後の運用
- マスタ更新手順
  1. CSV を `data/` に上書き。
  2. `python scripts/build_master_data.py --input data --output data/processed --pretty --summary` を実行。
  3. 生成された JSON を格納（バージョン管理推奨）。
  4. Streamlit アプリを再実行。
- JSON は Git 管理対象とし、変更レビューがしやすいよう整形（`--pretty`）をデフォルトにする案も検討。

