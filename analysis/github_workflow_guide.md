# GitHubを軸にした修正作業フロー

このガイドでは、GitHubリポジトリを中心とした開発ワークフローを習得します。

---

## 前提知識

### リポジトリ構成
- **GitHubリポジトリ**: https://github.com/x5116t-jpg/resource-collection-optimizer
- **ローカルリポジトリ**: `D:\py\Resource Collection\ResouceCollection_05`
- **リモート名**: `origin` (GitHub)

### ブランチ戦略
- **main**: 本番環境（安定版）
- **feature/***: 機能開発用ブランチ
- **hotfix/***: 緊急修正用ブランチ

---

## GitHubベース修正フロー（全体像）

```
┌─────────────────────────────────────────────────────┐
│ GitHub Issue作成 → フィーチャーブランチ作成       │
│    ↓                                                │
│ ローカルで開発 → コミット → GitHubにプッシュ      │
│    ↓                                                │
│ Pull Request作成 → レビュー → マージ → デプロイ   │
└─────────────────────────────────────────────────────┘
```

---

## ステップバイステップガイド

### Step 1: 現在の状態確認

```bash
# ブランチとリモートの確認
git status
git branch -a
git remote -v

# 最新の変更を取得（作業開始前に必ず実行）
git fetch origin
git pull origin main
```

**ポイント**:
- 作業開始前に必ず`git pull`で最新状態に更新
- `git status`で未コミットの変更がないか確認

---

### Step 2: GitHub Issue作成（推奨）

GitHub上でIssueを作成し、作業内容を記録します。

**Issueテンプレート例**:
```markdown
### 問題の概要
複数の資源種別（下水汚泥、林業残材など）を選択した際、1台で運べない場合でもエラーが表示され、2台での最適解が提示されない。

### 期待される動作
- 下水汚泥専用車両1台 + 林業残材専用車両1台の2台での最適解を提示

### 根本原因
src/app.pyの_filter_by_resource_compatibility関数が、全資源種別を同時にサポートする車両のみをフィルタリングしている。

### 解決策
資源種別ごとにピックアップをグループ化し、各資源に最適な車両を割り当てる複数車両最適化を実装。

### 参考資料
- 分析レポート: claudedocs/multi_vehicle_issue_analysis.md
```

**作成方法**:
1. GitHubリポジトリのIssuesタブを開く
2. "New issue"ボタンをクリック
3. 上記テンプレートを参考に内容を記入
4. ラベル（例: `bug`, `enhancement`）を追加
5. "Submit new issue"をクリック

**メリット**:
- 作業履歴の記録
- チーム共有（将来的に）
- Issue番号をコミットメッセージで参照可能

---

### Step 3: フィーチャーブランチ作成

```bash
# 新しいブランチを作成して切り替え
git checkout -b feature/multi-vehicle-allocation

# ブランチ作成確認
git branch
# * feature/multi-vehicle-allocation  ← アスタリスクが現在のブランチ
#   main
```

**ブランチ命名規則**:
- `feature/説明的な名前`: 新機能追加
- `fix/説明的な名前`: バグ修正
- `refactor/説明的な名前`: リファクタリング
- `docs/説明的な名前`: ドキュメント更新

**ポイント**:
- ブランチ名は英語でケバブケース（ハイフン区切り）
- 内容が分かりやすい名前にする

---

### Step 4: ローカルで開発

#### 4.1 コード編集
```bash
# エディタで編集（例: VSCode）
code src/app.py

# または Claude Code で編集
# （現在のセッション）
```

#### 4.2 変更内容の確認
```bash
# 変更されたファイルの一覧
git status

# 変更内容の詳細確認
git diff

# 特定ファイルの変更確認
git diff src/app.py
```

**ポイント**:
- `git diff`で意図しない変更が含まれていないか確認
- 不要なファイル（一時ファイル、ログなど）が含まれていないか注意

---

### Step 5: 変更のコミット

#### 5.1 変更をステージング
```bash
# 特定ファイルを追加
git add src/app.py

# 複数ファイルを追加
git add src/app.py claudedocs/multi_vehicle_issue_analysis.md

# 全ての変更を追加（注意して使用）
git add .
```

#### 5.2 コミット実行
```bash
# コミットメッセージ付きでコミット
git commit -m "Implement multi-vehicle allocation for different resource types

- Add _group_pickups_by_resource() to group pickups by resource type
- Add _select_vehicle_for_resource() to select optimal vehicle per resource
- Refactor _plan_vehicle_allocations() to support multiple vehicles
- Fix issue where incompatible resource combinations showed error
- Now supports allocation like: sewage sludge truck + forestry residue truck

Closes #1"
```

**コミットメッセージのベストプラクティス**:
```
1行目: 変更の概要（50文字以内）

3行目以降: 詳細説明
- 何を変更したか
- なぜ変更したか
- どのように動作するか

最終行: Issue番号参照（例: Closes #1, Fixes #2, Refs #3）
```

**ポイント**:
- 1行目は簡潔に（英語推奨）
- 本文で詳細を説明
- `Closes #番号`でIssueを自動クローズ

---

### Step 6: GitHubにプッシュ

#### 6.1 初回プッシュ（ブランチをGitHubに作成）
```bash
# リモートに新しいブランチを作成してプッシュ
git push -u origin feature/multi-vehicle-allocation

# 出力例:
# To https://github.com/x5116t-jpg/resource-collection-optimizer.git
#  * [new branch]      feature/multi-vehicle-allocation -> feature/multi-vehicle-allocation
# Branch 'feature/multi-vehicle-allocation' set up to track remote branch 'feature/multi-vehicle-allocation' from 'origin'.
```

**`-u`オプションの意味**:
- `--set-upstream`の短縮形
- ローカルブランチとリモートブランチを紐付け
- 次回以降は`git push`だけでOK

#### 6.2 追加のコミットをプッシュ
```bash
# 2回目以降は-uオプション不要
git push

# または明示的に
git push origin feature/multi-vehicle-allocation
```

---

### Step 7: Pull Request (PR) 作成

#### 7.1 GitHub上でPR作成
1. GitHubリポジトリを開く
2. "Pull requests"タブをクリック
3. "New pull request"ボタンをクリック
4. base: `main` ← compare: `feature/multi-vehicle-allocation` を選択
5. "Create pull request"をクリック

#### 7.2 PR説明テンプレート
```markdown
## 変更内容
複数の資源種別に対応した車両割り当て機能を実装

## 解決するIssue
Closes #1

## 主な変更点
- `_group_pickups_by_resource()`: ピックアップを資源種別でグループ化
- `_select_vehicle_for_resource()`: 資源種別ごとに最適車両を選択
- `_plan_vehicle_allocations()`: 複数車両での割り当てに対応

## テスト結果
- ✅ 下水汚泥 + 林業残材の組み合わせで2台割り当て成功
- ✅ 既存の単一資源種別ケースも正常動作
- ✅ エラーメッセージが適切に表示されることを確認

## スクリーンショット（任意）
（動作確認のスクリーンショットを添付）

## チェックリスト
- [x] コードが正しく動作することを確認
- [x] コミットメッセージが明確
- [x] ドキュメントを更新
- [ ] レビュアーを指定（チーム開発の場合）
```

#### 7.3 PR作成のコマンドライン方法（GitHub CLI使用）
```bash
# GitHub CLIがインストールされている場合
gh pr create --title "Implement multi-vehicle allocation for different resource types" \
  --body "$(cat <<'EOF'
## 変更内容
複数の資源種別に対応した車両割り当て機能を実装

## 解決するIssue
Closes #1
...
EOF
)"
```

---

### Step 8: コードレビュー（チーム開発の場合）

#### セルフレビューのポイント
```bash
# PRの差分をローカルで確認
git diff main..feature/multi-vehicle-allocation

# 特定ファイルの差分
git diff main..feature/multi-vehicle-allocation src/app.py
```

**チェック項目**:
- [ ] 意図しない変更が含まれていないか
- [ ] コメントやデバッグコードが残っていないか
- [ ] 命名規則が統一されているか
- [ ] エラーハンドリングが適切か

---

### Step 9: PRのマージ

#### 9.1 GitHub上でマージ
1. PRページを開く
2. "Merge pull request"ボタンをクリック
3. マージコミットメッセージを確認
4. "Confirm merge"をクリック
5. （オプション）"Delete branch"でフィーチャーブランチを削除

#### 9.2 ローカルの更新
```bash
# mainブランチに切り替え
git checkout main

# 最新の変更を取得
git pull origin main

# マージ済みのブランチを削除（任意）
git branch -d feature/multi-vehicle-allocation

# リモートで削除されたブランチをローカルから削除
git fetch --prune
```

---

## トラブルシューティング

### コンフリクトが発生した場合

```bash
# mainブランチの最新状態を取得
git checkout main
git pull origin main

# フィーチャーブランチに戻る
git checkout feature/multi-vehicle-allocation

# mainの変更をマージ
git merge main

# コンフリクトが発生した場合、手動で解決
# エディタで<<<<<<< HEAD, =======, >>>>>>>の箇所を編集

# 解決後、変更をコミット
git add .
git commit -m "Resolve merge conflicts with main"

# プッシュ
git push
```

### 間違ったブランチで作業してしまった場合

```bash
# 現在の変更を一時保存
git stash

# 正しいブランチに切り替え
git checkout feature/multi-vehicle-allocation

# 変更を復元
git stash pop
```

### コミットを取り消したい場合

```bash
# 最新のコミットを取り消し（変更は保持）
git reset --soft HEAD~1

# 最新のコミットを完全に取り消し（変更も削除）
git reset --hard HEAD~1
```

**注意**: プッシュ後の取り消しは避ける（チーム開発時は特に）

---

## GitHubフロー vs ローカルフロー比較

| 作業 | ローカル中心 | GitHub中心 |
|------|------------|----------|
| 問題追跡 | ローカルメモ | GitHub Issues |
| ブランチ管理 | ローカルのみ | リモートと同期 |
| コードレビュー | なし | Pull Request |
| 履歴管理 | git log | GitHub Insights |
| コラボレーション | 困難 | 容易 |
| バックアップ | ローカルのみ | 自動（GitHub） |

**GitHubを軸にするメリット**:
- ✅ 作業履歴が明確
- ✅ 変更の理由が追跡可能
- ✅ ロールバックが容易
- ✅ チーム開発への移行が容易

---

## 便利なGitコマンド集

### 状態確認
```bash
# 現在のブランチと変更状態
git status

# コミット履歴
git log --oneline -10

# グラフ表示
git log --graph --oneline --all

# 特定ファイルの履歴
git log --follow src/app.py
```

### ブランチ操作
```bash
# ブランチ一覧（ローカル）
git branch

# ブランチ一覧（リモート含む）
git branch -a

# ブランチ切り替え
git checkout feature/multi-vehicle-allocation

# 新規ブランチ作成＋切り替え
git checkout -b feature/new-feature

# ブランチ削除
git branch -d feature/old-feature
```

### リモート同期
```bash
# リモートの最新状態を取得
git fetch origin

# mainブランチの最新を取得してマージ
git pull origin main

# 現在のブランチをプッシュ
git push

# 強制プッシュ（注意）
git push --force
```

### 変更の確認
```bash
# ステージング前の変更
git diff

# ステージング後の変更
git diff --staged

# ブランチ間の差分
git diff main..feature/multi-vehicle-allocation
```

---

## ベストプラクティス

### 1. 小さく頻繁にコミット
```bash
# 悪い例: 1日の作業を1コミット
git add .
git commit -m "Fixed everything"

# 良い例: 機能ごとにコミット
git add src/app.py
git commit -m "Add _group_pickups_by_resource function"

git add tests/test_app.py
git commit -m "Add tests for resource grouping"
```

### 2. 意味のあるコミットメッセージ
```bash
# 悪い例
git commit -m "fix"
git commit -m "update"
git commit -m "changes"

# 良い例
git commit -m "Fix vehicle allocation for multiple resource types"
git commit -m "Add validation for empty pickup inputs"
git commit -m "Improve error message clarity for capacity shortage"
```

### 3. mainブランチで直接作業しない
```bash
# 悪い例
git checkout main
# mainで直接編集...

# 良い例
git checkout -b feature/my-feature
# フィーチャーブランチで作業
```

### 4. 定期的にリモートと同期
```bash
# 1日の作業開始時
git checkout main
git pull origin main
git checkout feature/my-feature
git merge main

# 1日の作業終了時
git push origin feature/my-feature
```

---

## 次のステップ

### このフローで実際に修正作業を行う

1. ✅ この分析レポートをGitHubにコミット
2. ✅ GitHub Issueを作成
3. ✅ フィーチャーブランチで実装
4. ✅ Pull Requestを作成
5. ✅ レビュー＆マージ

### 実践コマンド例
```bash
# 1. 分析レポートをコミット
git checkout main
git pull origin main
git checkout -b docs/add-multi-vehicle-analysis
git add claudedocs/multi_vehicle_issue_analysis.md
git add claudedocs/github_workflow_guide.md
git commit -m "Add analysis report for multi-vehicle allocation issue

- Document root cause of single-vehicle constraint
- Propose solution with resource-based grouping approach
- Add GitHub-based development workflow guide
"
git push -u origin docs/add-multi-vehicle-analysis

# 2. GitHub上でPR作成
# （GitHub UI または gh pr create）

# 3. マージ後、実装ブランチ作成
git checkout main
git pull origin main
git checkout -b feature/multi-vehicle-allocation

# 4. 実装...
# （コード編集）

# 5. コミット＆プッシュ
git add src/app.py
git commit -m "Implement multi-vehicle allocation logic"
git push -u origin feature/multi-vehicle-allocation

# 6. GitHub上でPR作成＆マージ
```

---

## 参考リンク

- **GitHub公式ドキュメント**: https://docs.github.com/
- **Git公式ドキュメント**: https://git-scm.com/doc
- **GitHub Flow**: https://docs.github.com/en/get-started/quickstart/github-flow
- **Conventional Commits**: https://www.conventionalcommits.org/
