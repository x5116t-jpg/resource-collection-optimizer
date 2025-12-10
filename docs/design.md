# 1. 目的／スコープ
- **目的**: 車庫（発着）・回収地点（複数）・集積場所を地図上で指定し、実道路ネットワークに基づく最短経路長で、
  「車庫→回収…→集積→車庫」の単一車両ルートを最適化する。車種（容量・固定費・距離単価）の候補から総コスト最小の車両タイプとルートを自動選択し、ブラウザ地図に出力する。
- **スコープ**: 市町村レベル、回収地点≤10、単一車両、時間窓なし、速度・渋滞は考慮しない（距離最短）。
- **想定ユーザー**: 運行計画担当、政策・試算担当、研究者。

---

# 2. 要求仕様
## 2.1 機能要件（FR）
1. **地図入力**: クリックで「車庫」「回収地点」「集積場所」を登録・編集できる。
2. **回収属性入力**: 各回収地点に「量（kg）」「資源種別（選択肢＋自由入力）」を付与できる。
3. **車種入力**: サイドバーから候補となる複数の車両タイプ（容量[kg]・固定費[円/台]・距離単価[円/km]）を登録できる。
4. **最適化**: OR-Tools を用い、
   - start=end=車庫、集積場所は**必ず回収点の後**に訪問
   - 容量制約を満たし
   - 総コスト=固定費 + 距離単価×総距離 を最小化する
   - 車種は候補を総当たりし、最小総コストのものを採用
5. **可視化**: 最適ルートを OSM 実道路上のポリラインで描画。総距離・総コスト・車種・コスト内訳を表示。
6. **永続化（任意）**: 入力・結果をCSV/JSONへエクスポートできる（拡張）。

## 2.2 非機能要件（NFR）
- **性能**: 10地点・市町村範囲で応答<数十秒。OSM 取得キャッシュで体感<数秒。
- **可用性**: ローカル PC（Windows/WSL/Ubuntu/Mac）で実行可。
- **再現性**: OSMnx/NetworkX/OR-Tools のバージョンを `requirements.txt` 固定。
- **操作性**: ブラウザUI（Streamlit）で導線を単純化。クリック3種モードを明示。

---

# 3. 前提・制約
- 実道路距離は OSMnx グラフ（`network_type=drive`）のエッジ長 `length` を使用。
- 渋滞・一方通行は OSM データ準拠（一方通行は方向性エッジで表現）。
- 距離単価は車格ごとに一定。運転手コストは距離単価に内包（速度一定近似）。
- 時間窓/休憩/通行規制（車格制限）は現時点では未実装（拡張で対応）。

---

# 4. ドメイン定義／データモデル
- **地点**: `Point(id, lat, lon, type)` — type∈{depot(車庫), pickup(回収), sink(集積)}
- **回収属性**: `PickupAttr(point_id, qty_kg:int, kind:str)`
- **車種**: `VehicleType(name:str, capacity_kg:int, fixed_cost:float, per_km_cost:float)`
- **距離行列**: `D[i][j]`（m）。ノード集合は `[depot] + pickups + [sink]` の順で索引。
- **ソリューション**: `Solution(vehicle:VehicleType, route:List[idx], total_m:int, cost:float)`

---

# 5. アーキテクチャ
```
[Streamlit UI] ──入力──▶ [OSMnx Loader]
     │                          │
     │                          └──▶ [NetworkX Shortest Path] ──▶ D[i][j]
     │
     └─最適化要求──▶ [OR-Tools RoutingModel]
                         │ (容量, 順序制約: 回収 ≤ 集積)
                         └──▶ best(vehicle, route)

[Folium] ◀─ルート/座標── [OSM経路再構成（ノード列→ポリライン）]
```
- UI：Streamlit + streamlit-folium（双方向クリック捕捉）。
- 計算：OSMnx（グラフ）→NetworkX（最短距離）→OR-Tools（ルート順）→OSM最短路で線形再構成。

---

# 6. 最適化モデル（単一車両, Depot→Pickups→Sink→Depot）
- ノード集合: `V={0..n+1}` で `0=depot`, `1..n=pickups`, `n+1=sink`
- 距離: `c_ij = D[i][j]`（m）
- 需要: `d_i (i∈1..n)`, `d_0=d_{n+1}=0`
- 車種候補 `K`（容量 `Q_k`, 固定費 `F_k`, 距離単価 `α_k` [円/km]）

**決定**: 各 `k∈K` についてルート `r_k` を求め、
\[
\min_k \big\{ F_k + α_k\cdot (\sum_{(i,j)∈r_k} c_{ij}/1000) \big\}
\]

**OR-Tools 実装要点**
- `RoutingIndexManager(n_nodes, 1, depot, depot)` で start=end=車庫。
- 容量: `AddDimensionWithVehicleCapacity(demand_cb, 0, [Q_k], True, "Capacity")`
- **順序制約**: ダミー次元 `Order` を追加し、各回収 `i` に対し `Order(i) ≤ Order(sink)` を付与 ⇒ sink が必ず最後。
- 検索: `PATH_CHEAPEST_ARC` 初期解 + `GUIDED_LOCAL_SEARCH` で近傍探索、`time_limit=5s`。
- 車種は候補を総当たりし、最小コスト解を採用。

---

# 7. 距離行列・経路再構成
1. **距離行列**: OSMnx グラフ `G` に各地点を最近傍ノードにスナップし、NetworkX の `shortest_path_length(G, u, v, weight='length')` を用いて `D[i][j]` をm単位で算出。到達不能は `1e9` で代替。
2. **地図ポリライン**: OR-Tools の巡回順 `…→i→j→…` の各区間について、`nx.shortest_path(G, u, v, weight='length')` で**ノード列**を求め、(lat,lon) 列へ変換し `folium.PolyLine` として描画。

---

# 8. コストモデル
- **総コスト** `C = F_k + α_k × (dist_m/1000)` を採用。
- α_k は燃料・人件費・車両走行コストを含む距離単価。必要に応じて
  - 時間単価を追加（`t_ij` 推定や平均速度で距離→時間換算）
  - 固定費の**日割/便あたり**調整
 へ拡張可能。

---

# 9. UI 仕様
- クリックモード: {回収地点追加, 車庫設定, 集積場所設定}
- 回収テーブル: qty(kg) 数値、資源種別は {紙,プラ,缶,瓶,混合,その他}+自由入力。
- 車種テーブル: name/capacity/fixed_cost/per_km を行追加。削除ボタンあり。
- 実行: エラーハンドリング（車庫/集積/回収/車種の未設定、容量不足、到達不能）。
- 出力: 総距離[km], 推定総コスト[円], 採用車種, コスト内訳テーブル, 地図上のポリライン。

---

# 10. エラーハンドリングと検証
- **到達不能**: `NoPath` を捕捉し距離を `1e9` に。最終的に解が不可なら UI で警告。
- **容量不足**: OR-Tools 解なし→車種容量不足の可能性を明示。
- **未入力**: 必須項目は実行時バリデーション。
- **検証**: 出力ルートが `0(車庫)` から始まり `n+1(集積)` を経由し、最後に `0(車庫)` に戻ることをプログラムで確認。

---

# 11. 性能・キャッシュ
- `@st.cache_data` で OSM グラフ取得・距離行列計算をキャッシュ。
- バッファ半径は 5–10km を目安に。広域は計算が重い。市町村レベルで 7.5km を初期値とする。

---

# 12. ロギング／可観測性
- 実行時ログ（INFO/ERROR）を標準出力。必要に応じて `logging` を挿入。
- メトリクス: ノード数、最短路計算回数、OR-Tools 探索統計（配列長、反復回数、ベストコスト）。

---

# 13. セキュリティ／プライバシ
- ローカル実行前提。地点データは端末内で完結。
- 共有時は `map.html` のみ配布可（住所・座標の匿名化に留意）。

---

# 14. テスト計画
- **ユニット**: 距離行列生成（同一点→0, 対称性, NoPath 代替値）。
- **統合**: サンプル地点（3回収+車庫+集積）で期待どおり「車庫→…→集積→車庫」になるか。
- **回帰**: バージョン更新時に同インスタンスで総距離・巡回順の安定性を確認。

---

# 15. 拡張計画（ロードマップ）
1. **複数台**: 車種ごとに台数入力→RoutingModel(vehicles>1) で容量配分。
2. **時間窓**: Pickup/Sink/Depot に開庁時間→Time dimension 導入。
3. **資源別容量**: 重量/容積の二次元容量（multi-capacity）。
4. **車格制限**: OSM エッジ属性に基づくタイプ別通行可否マスク。
5. **Google Distance/Direction API連携**: 実時間ベースの距離/時間推定。
6. **費用モデル強化**: 走行時間単価、CO₂原単位コスト、積載率ペナルティ等。
7. **保存/読込**: GeoJSON/CSV エクスポート・インポート、案件テンプレ。
8. **ダッシュボード**: Streamlit tabs で比較・感度分析。

---

# 16. 依存関係・環境
- Python 3.10+
- パッケージ: `streamlit`, `folium`, `streamlit-folium`, `osmnx`, `networkx`, `ortools`, `numpy`, `pandas`
- OSMnx は `geopandas` 系の依存を内部解決。OS 環境により `libspatialindex` 等が必要な場合あり。

---

# 17. デプロイ／運用
- ローカル: `streamlit run app.py`
- 社内共有: Streamlit Community Cloud / 社内サーバでのコンテナ実行（`Dockerfile` 整備推奨）。
- キャッシュ: 市町村ごとにグラフキャッシュを保存して初期応答を高速化。

---

# 18. 既存キャンバスコードとの対応
- キャンバスの `app.py` は本設計に準拠：
  - 単一車両・車庫=発着、集積場所が回収後に来る順序制約
  - 車種を総当たりして最小コストを選択
  - OSM 実道路での距離行列＋ポリライン描画
- 差分が出た場合は、当ドキュメントの仕様を優先して微修正を加える。

---

# 19. 既知の制限・リスク
- OSM の欠落・誤属性により到達不能が出る場合がある。
- 広域・ノード高密度時に距離行列計算が遅い（n≤12では実用、n²最短路呼び出し）。
- 集積場所の必訪・最終訪問は順序次元で担保しているが、将来的に複数集積や中継を扱う場合はセットパーティショニング等への切替を検討。

---

# 20. 変更管理
- 仕様変更は本ドキュメントに追記し、キャンバスの `app.py` に反映。
- バージョンタグ: `vX.Y.Z`（機能追加/改善/修正）。


# 21. 詳細モジュール設計
## 21.1 要求とモジュールの対応
| 要件 | 主担当モジュール | 補助モジュール | 主な責務 |
| --- | --- | --- | --- |
| 地図入力 (FR1) | `ui.map_panel` | `services.point_registry` | 座標クリック捕捉・ポイント種別登録、重複検証 |
| 回収属性入力 (FR2) | `ui.pickup_table` | `services.point_registry` | 回収地点に属性を紐付け、入力検証 |
| 車種入力 (FR3) | `ui.vehicle_table` | `services.vehicle_catalog` | 車種候補の追加・編集、容量・コスト検証 |
| 最適化 (FR4) | `services.optimizer` | `services.distance_matrix`, `services.vehicle_catalog` | 車種総当たり最適化、制約設定、結果整形 |
| 可視化 (FR5) | `ui.result_map` | `services.route_reconstruction` | 巡回順からポリライン生成、結果指標表示 |
| 永続化(任意) (FR6) | `services.persistence` | `ui.export_controls` | 入力・結果のCSV/JSON出力 |
| キャッシュ (NFR) | `infra.cache_manager` | `services.osm_loader`, `services.distance_matrix` | OSMデータと距離行列のキャッシュ制御 |

## 21.2 データアクセスとキャッシュ方針
- **OSMロード (`services.osm_loader`)**: エリア境界と`network_type='drive'`でグラフを取得し、`osmnx`の`graph_from_bbox`を使用。`metadata.area_bounds`から初期バウンディングボックスを推定し、UIで指定されたバッファを適用。
- **ノード辞書 (`services.point_registry`)**: JSONノードを`Point`データクラスに変換し、UI選択済みポイントを保持する。`type`未設定ポイントはUIで種別指定まで仮保管。
- **キャッシュ層 (`infra.cache_manager`)**:
  - `@st.cache_data`を用い、キー: `(bbox_hash, graph_hash)`でOSMグラフをキャッシュ。
  - 距離行列は`frozenset(point_ids)`とグラフバージョンをキーに多段キャッシュ。ポイントが追加されるたびに必要ペアのみ再計算する差分ロジックを持つ。
  - エラーハンドリング: `NetworkXNoPath`捕捉時は`1e9`で埋め、最終的に最適化で検知した場合はUI警告。
- **入力検証**: 重複座標の検出、車種容量>0、固定費・距離単価>=0、不完全行に対するUIエラー提示。
- **永続化**: 任意機能として`services.persistence`が、選択ポイント・車種・最適化結果をJSON/CSVエクスポート。ファイル名はタイムスタンプ+シナリオ名で自動生成。

## 21.3 最適化パイプライン
1. **距離行列生成 (`services.distance_matrix`)**
   - ポイントをOSMノードへスナップし、`nx.shortest_path_length`で`D[i][j]`を計算。
   - 結果は`numpy.ndarray`として保持し、メートル単位。未達は`1e9`。
2. **車種総当たり (`services.vehicle_catalog`)**
   - 登録順に`VehicleType`リストを提供し、容量不足が明確な車種は事前フィルタ（合計需要>容量の場合はskip）。
3. **OR-Tools呼び出し (`services.optimizer`)**
   - `RoutingIndexManager`にノード数・車庫インデックスを渡し、単一車両設定。
   - `Distance`コールバックは距離行列参照、`Capacity`ディメンションは回収需要を設定。
   - 集積地点の後訪問制約は`Order`ディメンションで`pickup_order <= sink_order`を追加。
   - 探索パラメータ: `first_solution_strategy=PATH_CHEAPEST_ARC`, `local_search_metaheuristic=GUIDED_LOCAL_SEARCH`, `time_limit=5s`。
   - 各車種から最小コストルートを算出し、最小値を更新。不可解な場合は`NoSolution`状態を返却してUIがメッセージ表示。
4. **結果整形 (`services.result_formatter`)**
   - 最適車種・ルートインデックス列・総距離(メートル)・コスト内訳(固定費/距離費用)を`Solution`データクラスに格納。
   - ルート指数をOSMノード番号に変換して`services.route_reconstruction`へ引き渡す。

## 21.4 UIフローと状態管理
- **画面構成**
  1. サイドバー: キャッシュ設定、車種テーブル、エクスポート操作。
  2. メイン: 地図パネル（クリックモード切替）、回収属性テーブル、最適化ボタン、結果タブ（サマリー／詳細表／マップ）。
- **状態管理**
  - `st.session_state`で選択ポイント、車種リスト、計算結果を管理。各フォームは`key`で分離。
  - 地図クリック時は`callback`で座標を登録し、`point_registry`に同期。
  - 最適化実行で`services.optimizer`を呼び出し、結果は`session_state['solution']`に格納。
- **メッセージング**
  - 必須設定不足（車庫/集積/車種未入力など）は実行前チェックで`st.warning`。
  - エラー（到達不能、容量不足）は`optimizer`からのステータスを解釈し`st.error`表示。
- **可視化**
  - `streamlit-folium`で地図を埋め込み、ポイント表示とポリライン描画。
  - 結果タブで総距離[km]、総コスト[円]、車種名、コスト内訳テーブルを表示し、ダウンロードボタンと連携。

## 21.5 レイヤリングとテスト観点
- **レイヤ構成**
  - UI層: `ui.*`モジュール群（Streamlitコンポーネント、メッセージ表示）。
  - サービス層: `services.*`（最適化・距離計算・ルート再構成・永続化）。
  - インフラ層: `infra.*`（キャッシュ、OSM取得、設定管理）。
- **依存方向**: UI→サービス→インフラの一方向依存を徹底。サービスはUI依存なし、インフラは外部ライブラリへの薄いラッパー。
- **テスト観点**
  - ユニット: 距離行列生成、容量制約、集積順序制約、コスト計算。
  - サービス統合: ダミーグラフを用いた最適化一連の再現（小規模ケースで車庫→回収→集積→車庫の経路検証）。
  - UI回帰: SessionStateをモック化しクリック操作→最適化→結果表示までのフローが期待どおりに更新されるかをpytest+Streamlitの`script_runner`で確認。

## 21.6 モジュール構成とインターフェース
- **ディレクトリ構成（案）**
  - `src/ui/`
    - `__init__.py`
    - `map_panel.py`: `render_map(points, mode, on_click)`
    - `pickup_table.py`: `render_pickup_table(registry)`
    - `vehicle_table.py`: `render_vehicle_table(catalog)`
    - `result_panel.py`: `render_results(solution, download_handler)`
    - `export_controls.py`: `render_export_controls(persistence_service)`
  - `src/services/`
    - `__init__.py`
    - `point_registry.py`: クラス`PointRegistry`
      - `add_point(lat, lon, point_type)` → `Point`
      - `set_pickup_attr(point_id, qty, kind)`
      - `list_points(point_type=None)`
    - `vehicle_catalog.py`: クラス`VehicleCatalog`
      - `add_vehicle(name, capacity, fixed_cost, per_km_cost)`
      - `valid_vehicles(total_demand)` → `List[VehicleType]`
    - `distance_matrix.py`
      - `build_distance_matrix(graph, points)` → `DistanceMatrix`
      - `snap_to_graph(graph, point)` → `SnappedPoint`
    - `optimizer.py`
      - `solve_routing(distance_matrix, pickups, depot, sink, vehicles)` → `Solution | NoSolution`
    - `route_reconstruction.py`
      - `reconstruct_paths(graph, snapped_route)` → `List[List[LatLon]]`
    - `result_formatter.py`
      - `format_solution(raw_route, vehicle, distance_m)` → `Solution`
    - `persistence.py`
      - `export_to_json(state, solution, path)`
      - `export_to_csv(state, solution, path)`
  - `src/infra/`
    - `__init__.py`
    - `osm_loader.py`: `load_graph(bbox, network_type='drive')`
    - `cache_manager.py`: `cached_graph(bbox)`, `cached_distance_matrix(key, build_fn)`
    - `settings.py`: 共通定数・パラメータ管理
- **インターフェース方針**
  - すべての`services`関数/クラスは型ヒントとDocstringを付与し、UI層から利用するパブリックAPIを明確化。
  - `DistanceMatrix`は`@dataclass`で`matrix: np.ndarray`、`index_map: Dict[int, int]`を保持し、距離参照メソッド`distance(i, j)`を提供。
  - `Solution`は`vehicle: VehicleType`、`order: List[str]`（ノードID）、`total_distance_m: float`、`cost_breakdown: Dict[str, float]`で定義。
  - `NoSolution`は`Enum`または`NamedTuple`で原因コード（`CAPACITY`, `INFEASIBLE`, `DISCONNECTED`）を持ちUIメッセージに変換可能とする。
  - `ui.*`はStateless関数を基本とし、状態更新は`session_state`またはサービス層へ委譲。
  - `infra.cache_manager`はStreamlitキャッシュとファイルベースキャッシュ（将来拡張）を抽象化し、サービスがキャッシュ機構に依存しないAPIを提供。

## 21.7 ユニットテストケースとpytest雛形
- **距離行列テストケース**
  - 同一地点組の距離が0になる。
  - 直線的に接続された小グラフで、期待する最短距離（エッジ長合計）が返る。
  - 逆向きエッジが存在しない場合に`1e9`が返る。
  - スナップ処理で最寄りノードが正しく割り当てられる。
- **最適化テストケース**
  - 単一回収・容量充分な車種で、ルートが`depot→pickup→sink→depot`になる。
  - 容量不足の車種がスキップされ、別車種が選択される。
  - 到達不能エッジを含む距離行列で`NoSolution(DISCONNECTED)`を返す。
  - 集積地点が回収前に来ないよう順序制約が守られる。
- **pytest雛形（`tests/services/test_distance_matrix.py`）**
```python
import numpy as np
import networkx as nx
from services.distance_matrix import build_distance_matrix

def test_distance_matrix_simple_path():
    G = nx.DiGraph()
    G.add_edge('A', 'B', length=100)
    G.add_edge('B', 'C', length=200)
    points = [
        {'id': 'depot', 'osmid': 'A'},
        {'id': 'pickup1', 'osmid': 'B'},
        {'id': 'sink', 'osmid': 'C'},
    ]
    dm = build_distance_matrix(G, points)
    assert dm.distance('A', 'C') == 300
```
- **pytest雛形（`tests/services/test_optimizer.py`）**
```python
from services.optimizer import solve_routing
from services.distance_matrix import DistanceMatrix
from services.vehicle_catalog import VehicleType

def test_optimizer_single_route(simple_graph_dm):
    vehicle = VehicleType(name='small', capacity_kg=500, fixed_cost=1000, per_km_cost=50)
    solution = solve_routing(
        distance_matrix=simple_graph_dm,
        pickups=[{'id': 'pickup1', 'demand': 100}],
        depot='depot',
        sink='sink',
        vehicles=[vehicle],
    )
    assert solution.is_feasible
    assert solution.order == ['depot', 'pickup1', 'sink', 'depot']
```
- **フィクスチャ案 (`tests/conftest.py`)**
  - `simple_graph_dm`: ノード`depot`, `pickup1`, `sink`を持つ小規模グラフから距離行列を生成する共通フィクスチャ。
  - `vehicle_small`, `vehicle_large`: 容量差による車種フィクスチャ。
