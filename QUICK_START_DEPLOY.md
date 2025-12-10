# 🚀 Streamlit Cloud クイックスタート（10分版）

**超簡単版のデプロイ手順です。詳細は `STREAMLIT_CLOUD_DEPLOY.md` を参照してください。**

---

## ステップ1: Git初期設定（初回のみ・2分）

```bash
# Gitバージョン確認
git --version

# 初回のみ実行
git config --global user.name "あなたの名前"
git config --global user.email "your-email@example.com"
```

---

## ステップ2: GitHubアカウント作成（5分）

1. https://github.com/signup にアクセス
2. アカウント作成（無料）
3. メール認証を完了

---

## ステップ3: ローカルリポジトリ作成（1分）

```bash
cd "D:\py\Resource Collection\ResouceCollection_05"
git init
git add .
git commit -m "Initial commit for Streamlit Cloud"
```

---

## ステップ4: GitHubにリポジトリ作成（2分）

1. GitHub → 右上の「+」→「New repository」
2. **Repository name:** `resource-collection-optimizer`
3. **Public** を選択 ⚠️重要
4. **Create repository** をクリック

---

## ステップ5: GitHubへプッシュ（2分）

```bash
# 表示されたURLをコピーして実行
git remote add origin https://github.com/[あなたのユーザー名]/resource-collection-optimizer.git
git branch -M main
git push -u origin main
```

**認証が求められたら:**
- ユーザー名とパスワードを入力
- またはPersonal Access Token（[作成方法](https://docs.github.com/ja/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)）

---

## ステップ6: Streamlit Cloudデプロイ（3分）

1. https://streamlit.io/cloud にアクセス
2. **「Sign up with GitHub」** をクリック
3. GitHub認証を許可
4. **「New app」** をクリック
5. 以下を入力：
   - **Repository:** `[あなたのユーザー名]/resource-collection-optimizer`
   - **Branch:** `main`
   - **Main file path:** `src/app.py` ⚠️重要
6. **「Deploy!」** をクリック

---

## ステップ7: 完了！（3〜5分待機）

初回デプロイ中...

```
Installing dependencies...
✓ networkx>=3.0
✓ streamlit>=1.20.0
...
✓ App is live!
```

**完了すると URL が表示されます:**
```
https://resource-optimizer.streamlit.app
```

**このURLを共有すれば誰でもアクセス可能！**

---

## 🔄 更新方法（3コマンドだけ）

```bash
git add .
git commit -m "アップデート内容"
git push
```

→ 自動的にStreamlit Cloudで再デプロイ！

---

## ⚠️ よくあるエラーと解決

### エラー: "File not found: src/app.py"
**解決:** Streamlit Cloud設定 → Main file path を `src/app.py` に変更

### エラー: "Git push failed"
**解決:** Personal Access Tokenを使用（パスワードの代わり）

### エラー: "ModuleNotFoundError"
**解決:** requirements.txtを確認して再プッシュ

---

## 📞 詳細ガイド

困ったら `STREAMLIT_CLOUD_DEPLOY.md` を参照してください。
スクリーンショット付きの詳細手順があります。

---

**所要時間:** 合計 10〜15分
**難易度:** ⭐⭐☆☆☆
**コスト:** 完全無料
