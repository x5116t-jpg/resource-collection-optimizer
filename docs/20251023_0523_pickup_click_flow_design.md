# 資源回収地点クリック時フロー改修設計

## 背景
- 現状は地図上で回収地点をクリックすると即座にノードが `pickup_selection` に追加される。
- 資源種別と量の入力 UI はページ下部に独立して存在し、地点確定のワークフローと分離している。
- 利用者からは「クリック→資源種別と量の選択→地点確定」を一連の操作として行いたいという要望がある。

## 目的
- 地図クリック直後に資源種別と量を確定させるダイアログを表示し、入力完了後に地点を確定する。
- 1 箇所ごとの指定完了後に次の地点を指定できるよう制御し、入力漏れを防ぐ。
- 既存の手動調整 UI や結果表示への影響を最小限に留める。

## 想定 UI フロー
1. ユーザーがクリックモード「回収地点」を選択し、地図上をクリックする。
2. 最近傍ノードを特定し、一時的に `pending_pickup` として保持。
3. モーダル（`st.experimental_dialog` もしくは `st.form` で代替）を開き、以下を入力させる。
   - 資源種別（マスタのリストから選択）
   - 回収量（kg）
   - 任意: 追加項目（将来拡張を想定）
4. ユーザーが「追加」ボタンを押すと、`pickup_selection` にノードを追加し、`pickup_attrs` に入力値を保存。
5. モーダルを閉じ、トーストで追加完了を通知。
6. キャンセルが押された場合は `pending_pickup` を破棄し、ノードは追加しない。
7. 次の地点クリックまでに未処理の `pending_pickup` があれば、再度ダイアログを表示して入力完了を促す。

## 状態管理設計
- 追加する `session_state` キー
  - `pending_pickup`: `{ "node_id": str, "lat": float, "lon": float }`（仮決定ノード）
  - `pending_pickup_defaults`: `{ "qty": int, "resource": str }`（候補初期値）
  - `pickup_dialog_open`: `bool`（ダイアログ再描画制御）
- 既存 `pickup_attrs` は確定済みノードの入力内容を保持する役割を継続。
- `last_click_token` は pending 状態でも更新するが、未確定のまま次のクリックが来た場合は警告を表示し、先に処理させる。

## 処理シーケンス詳細
1. `_render_network_map` から戻った `map_state` を評価。
2. クリックモードが回収地点の場合:
   - 既に `pending_pickup` が存在する場合は `_toast` で通知し、新しいクリックは無視。
   - 存在しなければ、`spatial_index.nearest` でノード ID を取得し `pending_pickup` に保存。
   - `pending_pickup_defaults` は `pickup_attrs` の過去入力、または `master` の既定値から作成。
   - `pickup_dialog_open = True` に設定。
3. 表示フェーズで `_render_pickup_dialog()` を呼び出し、`pickup_dialog_open` が True かつ `pending_pickup` があるときのみダイアログを描画。
4. ダイアログ内部では `st.form` または `st.experimental_dialog` を使い、選択肢と数値入力を行う。
5. 「追加」ボタン押下時の処理:
   - 入力値のバリデーション（資源種別選択済み、量>0 等）
   - `pickup_selection` にノードを追記。
   - `pickup_attrs[node_id] = {"qty": qty, "kind": resource, "resource": resource}` を保存。
   - `pending_pickup*` と `pickup_dialog_open` をクリア。
6. 「キャンセル」ボタン押下時は `pending_pickup*` をクリアし、トーストで取消を通知。
7. `pickup_selection` に追加済みノードは従来通り `_collect_pickup_inputs` により下部のフォームで再編集可能。

## 例外・エラー処理
- ダイアログ表示中に地図が再描画されてもボタン状態を維持するため、`form_submit_button` の戻り値で処理する。
- クリックしたノードが `depot` / `sink` と重複する場合は、従来通り `_toast` で警告し、`pending_pickup` を作成しない。
- マスタから取得した資源種別リストが空の場合はダイアログ内で警告を表示し、追加ボタンを disable。

## 影響範囲
- `src/app.py`
  - クリック処理 `_render_network_map` 呼び出し後のロジック
  - 新規関数 `_render_pickup_dialog`
  - `session_state` 初期化 `_init_session_state`
  - `_collect_pickup_inputs`（既存 UI との整合確認）
- 追加で `ui` モジュール化を行う場合、`src/ui` 配下にダイアログ用モジュールを新設。

## 残課題・検討事項
- ダイアログ UI の実装は `st.experimental_dialog` が必要。古い Streamlit バージョンでは `st.form` + 条件付きレンダリングで代替する必要がある。
- 既存のマニュアル選択 UI との重複をどう扱うか（手動選択でも同様の入力を要求するか）は要検討。
- 大量の地点登録時の操作性（複数選択や一覧編集）を改善する追加施策は別途計画する。
- E2E テストは Streamlit UI のため難易度が高い。単体ではセッション状態遷移のテスト用ヘルパーを検討する。

