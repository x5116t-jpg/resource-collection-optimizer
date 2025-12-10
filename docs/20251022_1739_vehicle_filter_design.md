# 資源適合車種フィルタ機能 設計

## 1. 目的
- 回収対象の資源種別を基に、適合する車種のみから最小コストの車両を選定する。
- 利用者がマスタに基づいた正しい車両選択を自動で行えるようにし、不適合車両の誤選択を防ぐ。

## 2. 入出力仕様
- 入力: Streamlit UI 上で選択された回収資源 (`pickup_inputs` 内 `kind`)。
- 出力: `VehicleCatalog` に登録される車種リストが、当該資源に適合するものに限定される。
- 付帯: 選択資源×車種の条件付き要件を UI に提示。

## 3. データソース
- `processed_master.compatibility`: `supports[資源名]` (True/False/None) と `requirements[資源名]` (要件文字列) を保持。
- `processed_master.vehicles`: `VehicleCatalog` 生成の元データ。
- `pickup_inputs`: `_collect_pickup_inputs` 結果に資源名 `kind` を含む。

## 4. 処理フロー
1. `pickup_inputs` から `selected_resources = {item["kind"] for item in pickup_inputs}` を生成。
2. `processed_master.compatibility` の各 `vehicle_name` について:
   - 全ての `resource` に対して `supports[resource]` が `True` または `None` の場合に適合と判定 (`False` が1つでもあれば除外)。
   - 適合判定時に、`requirements[resource]` が存在すれば注意リストに追加。
3. `VehicleCatalog` を構築する `_build_vehicle_catalog` の手前で、上記フィルタ結果を反映。
   - マスタ由来の車両レコードを走査し、適合車種のみを `VehicleCatalog.add_vehicle` へ追加。
   - 非適合の場合は UI にメッセージ表示し、`.add_vehicle` を呼ばない。
4. 適合車種がゼロの場合は `st.error` でユーザーに通知し、`solve_routing` 実行前にリターン。
5. 条件付き要件のまとめを UI（資源選択パネルまたは車種一覧）に表示。

## 5. UI 表示変更
- `_collect_pickup_inputs` で資源選択時、該当車種の状態を表示している `st.caption` / `st.warning` を拡張:
  - 適合車種リスト + 条件付き要件（例: 「軽トラック: 密閉容器を装備」）。
- 車種編集テーブルの下部に、現在選択されている資源に対して適合しない車種が除外されている旨を注記。

## 6. エラーハンドリング
- 適合車種が 0 件: `st.error("選択した資源に対応する車種がありません")` を表示し、`solve_routing` 前で return。
- 資源名がマスタに存在しない場合: `st.warning` を表示し、当該資源は適合判断から除外。

## 7. 変更箇所
- `src/app.py`
  - `_collect_pickup_inputs`: 資源名集合の抽出/保持と条件表示の強化。
  - `_build_vehicle_catalog`: `processed_master` と `selected_resources` を受け取り、適合判定でフィルタ。
  - 最適化ボタン押下処理：適合車種ゼロ時のガード追加。
- 必要に応じて `VehicleCatalog` に適合フラグを保持する拡張検討（現段階では不要）。

## 8. テスト観点
- 複数資源選択時に全てに対応する車種だけが残るか。
- 適合車種が 0 件の場合に最適化が中断されるか。
- 条件付き要件が UI に表示されるか。
- 資源名の typo（マスタにない）でログが出るがシステムが停止しないか。

END
