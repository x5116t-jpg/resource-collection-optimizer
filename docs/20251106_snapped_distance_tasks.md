# SnappedPoint / DistanceMatrix 再設計タスク整理 (2025-11-06)

## 1. データモデル拡張
- [ ] `src/services/distance_matrix.py`
  - `SnappedPoint` に `connector_distance_m: float` と `original_latlon: tuple[float, float] | None` を追加。
  - `snap_to_graph` を (lat, lon) 入力に対応し、既存の node_id 指定時は距離 0 として生成。
  - `build_distance_matrix` は `SnappedPoint` をそのまま受け取り、ノード距離行列自体は変えない。
- [ ] `src/services/point_registry.py`
  - `Point` に `node_id` と `connector_distance_m` を保持するフィールドを追加。
  - 既存の `add_point` 呼び出し箇所を調整し、`snap_to_graph` 結果を保存。

## 2. 距離行列オフセット適用
- [ ] `DistanceMatrix` に `connector_offsets: dict[str, float]` を保持し、`distance()` で前後の補正距離を加算。
- [ ] `build_distance_matrix` で `SnappedPoint` から `connector_offsets` を構築。
- [ ] `DistanceMatrix.as_numpy()` など既存 API の互換性が保たれるか確認。

## 3. キャッシュキー再設計 (`src/app.py:52-56`)
- [ ] `cached_distance_matrix(json_path, node_ids)` を `cached_distance_matrix(json_path, snapped_points)` 相当に改修。
- [ ] キャッシュキーに `(node_id, round(connector_distance_m, 2))` を含める。node_id 直接指定（0m）との区別を維持。
- [ ] `infra/cache_manager.cached_distance_matrix` に複合キーを渡すヘルパーを追加し、浮動小数丸めの統一を図る。

## 4. 既存 JSON シナリオ互換性検証
- [ ] 既存サンプルシナリオ（node_id のみ）で UI 操作／テストがそのまま成功することを確認。
- [ ] `tests/services/test_distance_matrix.py` にコネクタ距離があるケースを追加し、距離が `node距離 + 起点補正 + 終点補正` になることを検証。
- [ ] `tests/services/test_optimizer.py` にオフネットポイントを含むケースを追加。
- [ ] エクスポート機能（`src/services/persistence.py`）が新フィールドを保持するよう更新。

## 5. リスクとフォローアップ
- フォールバック: `snap_to_graph` が node_id 直接指定を受けた際は connector=0 で生成することで旧コードからの呼び出しも安全。
- テスト拡充前に `PointRegistry` のシリアライザ／`list_points` 返却値に対する後方互換性をレビュー。
- キャッシュキーの浮動小数丸めによる衝突リスクを QA 計画に含める（端末環境でベンチマーク予定）。
