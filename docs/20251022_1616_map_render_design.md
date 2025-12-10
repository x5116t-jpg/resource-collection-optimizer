# 地図描画ミニマム化設計

## 背景
- 現行 UI は道路ネットワーク内の全ノード（数千件想定）を folium のマーカーとして描画しており、Streamlit の再実行ごとに全てを再生成するため応答が重くなっている。
- 地図上で利用者が把握したい情報は「現在選択している車庫／回収地点／集積場所」とクリック直後のフィードバックが中心で、全ノードの常時表示は必須要件ではない。

## 目的
- 地図描画を「選択済みノード＋最小限のフィードバック」に絞り、再実行時の Python 側処理量とクライアント描画負荷を削減する。
- 既存の操作体験（クリックで最寄りノード選択、選択状況の確認）は維持する。

## 現状整理
- `src/app.py::_render_network_map` で `node_coords` の全要素に対し `folium.CircleMarker` を生成し地図へ追加している。
- クリック処理は `SpatialIndex.nearest` を利用し、`st.session_state` を更新している。
- 選択済みノードの座標情報は都度 `node_coords` から線形探索して取得している。

## 要件
1. 地図上には選択済みの車庫・回収地点・集積場所のみ表示する。
2. クリックモード（車庫／回収地点／集積場所）に応じた色分けを継続し、現在のモードを視覚的に把握できるようにする。
3. クリック直後に「どの地点が選ばれたか」を地図上で確認できるよう、選択変更直後のフィードバック（強調表示）を残す。
4. 全ノード描画を外しても、最寄りノード検索・手動選択 UI・最適化処理はこれまで通り動作する。
5. 既存の `st.session_state` キーは互換性を保ち、他画面・テストへの副作用を出さない。

## 方針概要
- `_render_network_map` の責務を「背景地図生成」と「選択済みポイントの描画」に特化させる。
- 選択済みノード向けに `SelectedPoint`（役割・座標・名称をまとめたデータ構造）を組み立て、描画処理をシンプルにする。
- クリックモードごとの色と強調状態（例えば `radius` や `fill_opacity`）をマッピングし、描画時に適用する。
- 直近クリック座標や直近選択ノード ID を `st.session_state` に保持し、モードに応じたハイライトを追加する。

## 詳細設計

### 1. 座標アクセスの高速化
- `_extract_node_coordinates` の戻り値（リスト）は維持しつつ、ID→座標の辞書を併せて構築する。
    - 例: `_build_node_lookup(node_coords: List[Dict[str, object]]) -> Dict[str, Dict[str, object]]`。
    - セッション状態 `node_coords_cache` に `{ "ファイル名": { "list": [...], "lookup": {...} } }` のように保持し、再実行時の再計算を避ける。

### 2. 選択済みポイントの抽出
- 新ユーティリティ `_collect_selected_points(depot_id, sink_id, pickup_ids, node_lookup)` を追加。
    - 返却値: `List[SelectedPoint]`。
    - `SelectedPoint` は `TypedDict` または `dataclass` で `role`（"depot"/"pickup"/"sink"）、`node_id`、`lat`、`lon`、`label` を持つ想定。
    - 存在しない ID の場合はスキップし、ログ or `st.warning` で気づけるようにする（想定外ケース）。

### 3. `_render_network_map` の再構成
- 引数を `selected_points: Sequence[SelectedPoint]`, `mode: str`, `last_feedback: Optional[SelectedPoint]` へ整理。
- 地図中心は以下の優先順位で決定:
    1. `last_feedback` があればその座標。
    2. `selected_points` があれば最初の座標。
    3. それも無い場合は従来通り `node_coords` の先頭。
- マーカー描画:
    - `color_map = {"depot": "green", "pickup": "blue", "sink": "red"}` をベースにする。
    - 現在の `mode` に該当するポイントは `radius` を +2 / `fill_opacity` を 1.0 などで強調。
    - `last_feedback` に一致する ID はアウトライン色を黄色にする等の追加指定で選択直後を明示。
- 既存の `st.write(f"クリックモード: **{mode}**")` は残しつつ、凡例を `st.caption` で提示。

### 4. クリックフィードバック管理
- 既存の `st.session_state["last_click_token"]` を拡張し、`last_selected_node` と `last_selected_role` を保持（なければ None）。
- クリック処理内でノード確定時に `last_selected_node` を更新し、`_collect_selected_points` の結果から `last_feedback` を導き `_render_network_map` に渡す。
- 手動で選択が変更された場合（selectbox/multiselect）、同様に `last_selected_node` を更新してハイライトを同期。

### 5. 凡例と補助テキスト
- 地図直下に `st.caption("凡例: 緑=車庫 / 青=回収 / 赤=集積 / 黄色枠=最新の更新")` を表示し、全ノード非表示でも利用者が迷わないようにする。

## 影響範囲
- 主要変更ファイル: `src/app.py`（地図描画、ノード抽出、クリック処理、セッション状態管理）。
- 補助モジュール: `src/ui/map_panel.py` を活かし続ける場合はシグネチャの変更検討。ただし現状 `app.py` が直接 `folium` を扱っているため、`map_panel.py` には即時影響なし。
- テスト: 既存の単体テストが少ないため、`SelectedPoint` のユニットテストや `_collect_selected_points` の挙動を追加する余地がある。

## 開発ステップ案
1. `SelectedPoint` 型・ユーティリティ関数を追加し、ノード辞書を構築する。
2. `_render_network_map` を新シグネチャへ書き換え、描画内容を選択済みノードに限定する。
3. クリック処理・手動選択処理で `last_selected_node` を更新し、描画へ渡す。
4. 凡例表示やクリックモード強調を追加。
5. 動作確認: ノード選択のレスポンス、選択解除、最適化実行、セッションリセットなど。

## テスト観点
- 車庫／集積を別ノードへ切り替えたとき、マーカー色とハイライトが切り替わるか。
- 回収地点を複数選択／削除したとき、表示中マーカーが同期しているか。
- クリック後すぐに別モードへ切り替えても、ハイライトが適切に更新されるか。
- ネットワーク JSON に座標欠損があった場合のフォールバック（警告表示など）。

## 補足
- 今後さらに軽量化する場合は、背景地図のベースを `folium.TileLayer` で最小限にしたり、`st.pydeck_chart` への置換も検討余地がある。
- 本設計でマーカー数は選択数（多くても数十件）に限定されるため、Streamlit 再実行の負荷は大幅に低減する見込み。
