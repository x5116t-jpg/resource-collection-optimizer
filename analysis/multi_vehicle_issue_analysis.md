# 複数車両最適化問題の根本原因分析

## 問題の概要

**現象**: 複数の資源種別（例: 下水汚泥、林業残材）が選択された場合、1台で運べない場合でも「資源種別 [下水汚泥、林業残材] に対応できる車種が見つかりません。」とエラー表示される

**期待動作**: 下水汚泥専用車両1台 + 林業残材専用車両1台の2台での最適解を提示

---

## 根本原因の特定

### 1. 車両フィルタリングロジックの制約 (src/app.py:626-635)

```python
def _filter_by_resource_compatibility(
    record_map: Dict[str, Dict[str, object]],
    required_resources: Sequence[str],
    master: Optional[ProcessedMasterData],
) -> List[Dict[str, object]]:
    compatible: List[Dict[str, object]] = []
    for name, record in record_map.items():
        # 🔴 問題: すべての資源種別をサポートする車両のみフィルタ
        if all(_vehicle_supports_resource(name, res, master) for res in required_resources):
            compatible.append(record)
    return compatible
```

**問題点**: `all()`条件により、**全ての資源種別を同時にサポートする車両のみ**が候補になる

**影響**:
- 下水汚泥専用車両: ❌ (林業残材非対応のため除外)
- 林業残材専用車両: ❌ (下水汚泥非対応のため除外)
- 結果: `compatible_candidates = []` → エラー表示

---

### 2. 単一車両前提の割り当て設計 (src/app.py:694-737)

```python
def _plan_vehicle_allocations(...) -> Tuple[List[Dict[str, object]], List[str]]:
    # ...
    if capacity_ok_candidates:
        # 🔴 問題: 単一のbest_vehicleのみを返す設計
        best_vehicle = _select_best_vehicle(capacity_ok_candidates)
        plan = [
            {
                "vehicle": str(best_vehicle.get("name") or ""),
                "record": best_vehicle,
                "resources": sorted(required_resources),
                "pickups": list(pickup_inputs),  # 全ピックアップを1台に割り当て
            }
        ]
        return plan, []
```

**問題点**: 全ピックアップを1台の車両に割り当てる設計

**影響**: 複数車両での分割配送が考慮されない

---

### 3. solve_fleet_routingは存在するが活用されていない

`optimizer.py:403-445`に`solve_fleet_routing`関数は実装されているが、`app.py`での呼び出し時（line 1847）、`assignments`パラメータが単一車両前提で作られているため、複数車両の最適化が機能しない。

---

## 問題の構造図

```
ユーザー選択: [下水汚泥, 林業残材]
    ↓
_extract_required_resources()
    ↓
required_resources = ["下水汚泥", "林業残材"]
    ↓
_filter_by_resource_compatibility()  ← 🔴 all()条件で厳しすぎるフィルタ
    ↓
compatible_candidates = []  ← 両方サポートする車両がない
    ↓
_generate_error_messages()
    ↓
エラー表示: "資源種別 [下水汚泥, 林業残材] に対応できる車種が見つかりません。"
```

---

## 解決策の方向性

### オプション1: 資源種別ごとの車両グループ化 (推奨)

1. **ピックアップを資源種別でグループ化**
   ```python
   # 例:
   # グループA: 下水汚泥のピックアップ → 下水汚泥対応車両
   # グループB: 林業残材のピックアップ → 林業残材対応車両
   ```

2. **各グループに最適車両を割り当て**
   ```python
   assignments = [
       (下水汚泥車両, [下水汚泥ピックアップ]),
       (林業残材車両, [林業残材ピックアップ])
   ]
   ```

3. **solve_fleet_routingで最適化**
   - 既存関数を活用、新規実装不要

**メリット**:
- ✅ 既存のsolve_fleet_routing活用
- ✅ ロジックが明確で保守しやすい
- ✅ 資源種別の組み合わせに柔軟対応

**デメリット**:
- ⚠️ 同一資源種別のピックアップが複数車両に分散できない（容量オーバー時）

---

### オプション2: 組み合わせ最適化 (高度)

1. **全車両候補を資源ごとに収集**
2. **ピックアップの車両割り当て組み合わせ探索**
3. **総コスト最小の組み合わせを選択**

**メリット**:
- ✅ 最適解の探索範囲が広い
- ✅ 容量制約にも柔軟対応

**デメリット**:
- ❌ 実装複雑度が高い
- ❌ 計算時間増加の可能性
- ❌ OR-Toolsへの組み込みが必要

---

## 推奨アプローチ: オプション1

### 実装ステップ

#### Step 1: ピックアップの資源種別グループ化
```python
def _group_pickups_by_resource(
    pickup_inputs: Sequence[Dict[str, object]]
) -> Dict[str, List[Dict[str, object]]]:
    """ピックアップを資源種別ごとにグループ化"""
    groups: Dict[str, List[Dict[str, object]]] = {}
    for pickup in pickup_inputs:
        resource = str(pickup.get("kind", ""))
        if not resource:
            continue
        if resource not in groups:
            groups[resource] = []
        groups[resource].append(pickup)
    return groups
```

#### Step 2: 資源種別ごとの最適車両選択
```python
def _select_vehicle_for_resource(
    resource: str,
    pickups: List[Dict[str, object]],
    record_map: Dict[str, Dict[str, object]],
    master: Optional[ProcessedMasterData]
) -> Optional[Dict[str, object]]:
    """特定資源種別に対応する最適車両を選択"""
    total_demand = _calculate_total_demand(pickups)

    # この資源をサポートする車両のみフィルタ
    compatible = [
        record for name, record in record_map.items()
        if _vehicle_supports_resource(name, resource, master)
    ]

    # 容量チェック
    capacity_ok = _filter_by_capacity(compatible, total_demand)

    if not capacity_ok:
        return None

    return _select_best_vehicle(capacity_ok)
```

#### Step 3: 複数車両割り当て計画の作成
```python
def _plan_vehicle_allocations(
    records: List[Dict[str, object]],
    master: Optional[ProcessedMasterData],
    pickup_inputs: Sequence[Dict[str, object]],
) -> Tuple[List[Dict[str, object]], List[str]]:
    """複数車両での割り当て計画を作成"""

    if not pickup_inputs:
        return [], []

    # 資源種別でグループ化
    resource_groups = _group_pickups_by_resource(pickup_inputs)

    if not resource_groups:
        return [], ["資源種別が指定されていません。"]

    record_map = {str(r.get("name", "")): r for r in records if r.get("name")}

    plan = []
    warnings = []

    # 各資源種別に最適車両を割り当て
    for resource, pickups in resource_groups.items():
        vehicle = _select_vehicle_for_resource(resource, pickups, record_map, master)

        if vehicle is None:
            total_demand = _calculate_total_demand(pickups)
            warnings.append(
                f"資源種別 [{resource}] (総重量: {total_demand}kg) に対応できる車両が見つかりません。"
            )
            continue

        plan.append({
            "vehicle": str(vehicle.get("name", "")),
            "record": vehicle,
            "resources": [resource],
            "pickups": pickups,
        })

    if not plan:
        return [], warnings

    return plan, warnings
```

---

## 修正対象ファイル

### 主要修正
- **src/app.py**:
  - `_plan_vehicle_allocations()` 関数の改修 (line 694-737)
  - 新規関数追加: `_group_pickups_by_resource()`, `_select_vehicle_for_resource()`

### 影響範囲
- ✅ `src/services/optimizer.py`: 修正不要（既存のsolve_fleet_routingを活用）
- ✅ `src/services/vehicle_catalog.py`: 修正不要
- ⚠️ テストケース追加推奨: `tests/services/test_optimizer.py`

---

## テストシナリオ

### テストケース1: 異なる資源種別を2台で運搬
```python
pickups = [
    {"id": "P1", "qty": 1000, "kind": "下水汚泥"},
    {"id": "P2", "qty": 1500, "kind": "林業残材"},
]

期待結果:
- 車両1: 下水汚泥専用車両 → P1回収
- 車両2: 林業残材専用車両 → P2回収
- 総コスト最小化
```

### テストケース2: 同一資源種別で容量オーバー（将来対応）
```python
pickups = [
    {"id": "P1", "qty": 2000, "kind": "下水汚泥"},
    {"id": "P2", "qty": 2000, "kind": "下水汚泥"},
]
車両容量: 3000kg

期待結果 (将来):
- 車両1: 下水汚泥車両 → P1回収 (2000kg)
- 車両2: 下水汚泥車両 → P2回収 (2000kg)

現状 (オプション1):
- エラー: 容量不足
```

---

## リスク評価

### 低リスク
- ✅ 既存のsolve_fleet_routing関数を活用
- ✅ 車両選択ロジックの再利用
- ✅ 段階的な実装が可能

### 中リスク
- ⚠️ 同一資源種別の複数車両分割は未対応（将来拡張課題）
- ⚠️ UIでの複数車両結果表示の調整が必要（既存実装で対応済みか要確認）

### 高リスク
- ❌ 特になし

---

## 次のアクション

1. ✅ GitHubでissue作成（この分析を添付）
2. ✅ featureブランチ作成 (`feature/multi-vehicle-allocation`)
3. 📝 実装: `_plan_vehicle_allocations()` 改修
4. 🧪 テストケース追加
5. ✅ プルリクエスト作成
6. 🔍 コードレビュー
7. 🚀 マージ & デプロイ

---

## 参考情報

### 関連コード位置
- エラー表示: `src/app.py:666`
- 車両フィルタ: `src/app.py:626-635`
- 割り当て計画: `src/app.py:694-737`
- 最適化実行: `src/app.py:1847`
- FleetSolution: `src/services/optimizer.py:403-445`

### GitHubリポジトリ
- URL: https://github.com/x5116t-jpg/resource-collection-optimizer
- ブランチ: main
