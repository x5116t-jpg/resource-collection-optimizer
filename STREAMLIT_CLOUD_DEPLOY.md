# 📘 Streamlit Cloud デプロイ完全ガイド

**所要時間:** 約30分〜1時間
**難易度:** ⭐⭐☆☆☆ (初心者向け)
**前提条件:** GitHubアカウント（無料）

---

## 🎯 このガイドのゴール

このアプリケーションをインターネット上に公開し、URLで誰でもアクセスできるようにします。

**デプロイ後のイメージ:**
```
あなた: https://your-app.streamlit.app というURLを共有
ユーザー: ブラウザでアクセスするだけで即利用可能
        → インストール不要
        → セットアップ不要
        → 常に最新版
```

---

## 📋 事前準備チェックリスト

デプロイ前に以下を確認してください：

- [ ] GitHubアカウントを持っている（[作成はこちら](https://github.com/signup)）
- [ ] Gitがインストールされている（[ダウンロード](https://git-scm.com/downloads)）
- [ ] インターネット接続が安定している
- [ ] プロジェクトフォルダが `D:\py\Resource Collection\ResouceCollection_05\` にある

---

## 🚀 デプロイ手順（7ステップ）

### ステップ1: Gitのインストール確認

コマンドプロンプトを開いて、以下を実行：

```bash
git --version
```

**結果例:**
```
git version 2.42.0.windows.1
```

**もしエラーが出たら:**
1. [Git公式サイト](https://git-scm.com/downloads)からダウンロード
2. インストール（全てデフォルト設定でOK）
3. 再度 `git --version` で確認

---

### ステップ2: Gitの初期設定（初回のみ）

```bash
git config --global user.name "あなたの名前"
git config --global user.email "your-email@example.com"
```

**例:**
```bash
git config --global user.name "Taro Yamada"
git config --global user.email "taro@example.com"
```

> 💡 この情報はコミット履歴に記録されますが、公開されても問題ない情報を使用してください。

---

### ステップ3: ローカルGitリポジトリの作成

コマンドプロンプトで以下を実行：

```bash
cd "D:\py\Resource Collection\ResouceCollection_05"
git init
git add .
git commit -m "Initial commit for Streamlit Cloud deployment"
```

**各コマンドの説明:**
- `git init`: このフォルダをGitで管理開始
- `git add .`: 全ファイルをステージング（登録準備）
- `git commit -m "..."`: 変更を記録（スナップショット作成）

**成功すると:**
```
[main (root-commit) abc1234] Initial commit for Streamlit Cloud deployment
 XX files changed, XXXX insertions(+)
 create mode 100644 src/app.py
 ...
```

---

### ステップ4: GitHubリポジトリの作成

#### 4-1. GitHubにログイン

ブラウザで [GitHub](https://github.com) にアクセスしてログイン

#### 4-2. 新しいリポジトリを作成

1. 右上の **「+」** → **「New repository」** をクリック
2. 以下を入力：

   | 項目 | 入力内容 |
   |------|---------|
   | **Repository name** | `resource-collection-optimizer` |
   | **Description** | 資源回収ルート最適化ツール |
   | **Public / Private** | **Public** を選択 ⚠️ |
   | **Add README** | チェック**しない** |
   | **Add .gitignore** | 選択**しない** |
   | **Choose a license** | 選択**しない** |

   > ⚠️ **重要:** Streamlit Cloudの無料プランは**Publicリポジトリのみ**対応です

3. **「Create repository」** をクリック

#### 4-3. リモートリポジトリのURLをコピー

作成直後の画面に表示される `https://github.com/[あなたのユーザー名]/resource-collection-optimizer.git` をコピー

---

### ステップ5: GitHubへプッシュ

コマンドプロンプトで以下を実行：

```bash
git remote add origin https://github.com/[あなたのユーザー名]/resource-collection-optimizer.git
git branch -M main
git push -u origin main
```

**⚠️ 注意:** `[あなたのユーザー名]` は実際のGitHubユーザー名に置き換えてください

**例:**
```bash
git remote add origin https://github.com/taro-yamada/resource-collection-optimizer.git
git branch -M main
git push -u origin main
```

**初回プッシュ時の認証:**
- **ユーザー名:** GitHubのユーザー名
- **パスワード:** GitHubパスワード（または Personal Access Token）

> 💡 **Personal Access Token (PAT) の作成方法:**
> 1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
> 2. Generate new token → 「repo」にチェック → Generate token
> 3. 表示されたトークンをコピー（⚠️ 一度しか表示されません）
> 4. パスワードの代わりにこのトークンを使用

**成功すると:**
```
Enumerating objects: XX, done.
Counting objects: 100% (XX/XX), done.
...
To https://github.com/[ユーザー名]/resource-collection-optimizer.git
 * [new branch]      main -> main
```

---

### ステップ6: Streamlit Cloudにデプロイ

#### 6-1. Streamlit Cloudにアクセス

ブラウザで [https://streamlit.io/cloud](https://streamlit.io/cloud) にアクセス

#### 6-2. サインアップ

1. **「Sign up」** をクリック
2. **「Continue with GitHub」** を選択
3. GitHubアカウントで認証
4. Streamlit Cloudがリポジトリにアクセスする権限を承認

#### 6-3. 新しいアプリをデプロイ

1. **「New app」** または **「Deploy an app」** をクリック
2. 以下を入力：

   | 項目 | 入力内容 |
   |------|---------|
   | **Repository** | `[あなたのユーザー名]/resource-collection-optimizer` を選択 |
   | **Branch** | `main` |
   | **Main file path** | `src/app.py` ⚠️ 重要 |
   | **App URL** | 好きな名前（例: `resource-optimizer`） |

   > ⚠️ **重要:** Main file pathは必ず `src/app.py` にしてください

3. **「Deploy!」** をクリック

#### 6-4. デプロイ完了を待つ

- 初回デプロイは **3〜5分** かかります
- 画面に進行状況が表示されます

**デプロイ中の表示例:**
```
Installing dependencies...
✓ networkx>=3.0
✓ streamlit>=1.20.0
✓ pandas>=1.3.0
✓ folium>=0.12.0
✓ streamlit-folium>=0.11.0
✓ branca>=0.6.0

Starting Streamlit app...
✓ App is live!
```

#### 6-5. デプロイ完了！

**成功すると:**
- アプリが自動的に起動します
- URLが表示されます（例: `https://resource-optimizer.streamlit.app`）
- このURLを共有すれば、誰でもアクセスできます！

---

## 🎉 デプロイ成功後の確認

### 動作確認

1. 表示されたURLにアクセス
2. 地図が正しく表示されるか確認
3. 車庫・回収地点・集積場所を選択できるか確認
4. 最適化が実行できるか確認

### URLの共有

**デプロイ完了後のURL例:**
```
https://resource-optimizer.streamlit.app
```

このURLを共有するだけで、誰でも以下が可能：
- ✅ ブラウザでアクセス
- ✅ 地図を使った地点選択
- ✅ ルート最適化の実行
- ✅ 結果の地図表示

**インストール・セットアップ一切不要！**

---

## 🔧 よくあるトラブルシューティング

### ❌ エラー1: "ModuleNotFoundError"

**原因:** requirements.txtに依存関係が足りない

**解決方法:**
1. ローカルで `pip freeze > requirements.txt` を実行
2. 変更をコミット・プッシュ
   ```bash
   git add requirements.txt
   git commit -m "Update requirements.txt"
   git push
   ```
3. Streamlit Cloudで自動的に再デプロイされます

---

### ❌ エラー2: "File not found: src/app.py"

**原因:** Main file pathの設定ミス

**解決方法:**
1. Streamlit Cloudのダッシュボード → アプリ設定（⚙️アイコン）
2. **Main file path** を `src/app.py` に修正
3. **「Save」** → 自動的に再デプロイ

---

### ❌ エラー3: "Git push failed - Permission denied"

**原因:** GitHub認証エラー

**解決方法:**
1. Personal Access Token (PAT) を作成（ステップ5参照）
2. パスワードの代わりにPATを使用
3. または、SSH鍵を設定（[公式ガイド](https://docs.github.com/ja/authentication/connecting-to-github-with-ssh)）

---

### ❌ エラー4: データファイルが見つからない

**原因:** `data/` フォルダがGitにコミットされていない

**解決方法:**
1. `.gitignore` で `data/` が除外されていないか確認
2. データファイルを追加：
   ```bash
   git add data/
   git commit -m "Add data files for deployment"
   git push
   ```

---

## 🔄 アプリの更新方法

コードを修正したら、以下の3コマンドで更新完了：

```bash
git add .
git commit -m "アップデート内容の説明"
git push
```

**自動的にStreamlit Cloudで再デプロイされます！**

---

## 📊 Streamlit Cloudの管理画面

### アクセス方法

[https://share.streamlit.io/](https://share.streamlit.io/)

### できること

- ✅ アプリの起動/停止
- ✅ ログの確認
- ✅ 再起動
- ✅ 削除
- ✅ URLの変更
- ✅ アクセス統計の確認

---

## 💰 料金プラン

### Community Cloud（無料）

- ✅ 無制限の公開アプリ
- ✅ 1GBメモリ
- ✅ 1コア
- ✅ 自動スケーリング
- ⚠️ Publicリポジトリのみ
- ⚠️ 月間稼働時間の制限あり

### 有料プラン

プライベートリポジトリや高性能が必要な場合：
- **Starter:** $20/月
- **Professional:** カスタム料金

**このプロジェクトは無料プランで十分です！**

---

## 🔐 セキュリティとプライバシー

### データの扱い

- ✅ `data/` フォルダのファイルはGitHub上で公開されます
- ⚠️ **機密データは含めないでください**
- ⚠️ 個人情報や企業秘密を含む場合は、ダミーデータに置き換えてください

### プライベートデータを扱う場合

1. **Streamlit Secrets** を使用（環境変数的な機能）
2. データベース接続情報などを安全に保管
3. [公式ガイド](https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app/secrets-management)

---

## 📞 サポート・参考リンク

- **Streamlit Cloud公式ドキュメント:**
  https://docs.streamlit.io/streamlit-community-cloud

- **Streamlit Community Forum:**
  https://discuss.streamlit.io/

- **GitHub Docs:**
  https://docs.github.com/ja

- **Git入門:**
  https://git-scm.com/book/ja/v2

---

## ✅ デプロイ完了チェックリスト

最終確認：

- [ ] GitHubリポジトリが作成された
- [ ] コードがプッシュされた
- [ ] Streamlit Cloudでアプリが起動した
- [ ] URLにアクセスして動作確認できた
- [ ] 地図が正しく表示される
- [ ] 最適化が実行できる
- [ ] URLを共有できた

**全てチェックできたら完了です！🎉**

---

## 🎯 次のステップ

デプロイ完了後、以下を検討できます：

1. **カスタムドメイン設定**（有料プラン）
2. **アクセス解析の導入**
3. **パスワード保護**（有料プラン）
4. **定期的な自動更新**（GitHub Actions）

---

**作成日:** 2025-12-03
**最終更新:** 2025-12-03
**問い合わせ:** プロジェクト管理者
