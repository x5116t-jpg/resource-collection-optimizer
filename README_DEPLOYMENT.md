# 📦 資源回収最適化ツール - デプロイガイド

**バージョン:** 1.0
**最終更新:** 2025-12-03

---

## 🎯 配布方法の選択

このアプリケーションを第三者に配布する方法は以下の通りです：

### ✅ 推奨: Streamlit Cloud（無料・簡単）

| 項目 | 詳細 |
|------|------|
| **難易度** | ⭐⭐☆☆☆（初心者向け） |
| **所要時間** | 10〜30分 |
| **コスト** | 完全無料 |
| **メリット** | URLで即共有、メンテナンス不要、自動更新 |
| **デメリット** | インターネット接続必須 |
| **適用条件** | ✅ あなたの環境に適合 |

**クイックスタート:**
1. `prepare_deploy.bat` を実行
2. `QUICK_START_DEPLOY.md` の手順に従う
3. 10分でデプロイ完了

**詳細ガイド:**
- 📘 `STREAMLIT_CLOUD_DEPLOY.md` - ステップバイステップの完全ガイド
- 🚀 `QUICK_START_DEPLOY.md` - 10分クイックスタート

---

## ❌ exe化が推奨されない理由

以前試した `build_standalone.bat` による exe 化には以下の問題があります：

### 技術的制約
- **地図表示の問題:** Foliumは外部サーバー（OpenStreetMap）から地図タイルを取得するため、完全なオフライン化は困難
- **Streamlitのアーキテクチャ:** 本質的にウェブサーバー+ブラウザの仕組みで、真のスタンドアロンexeには不向き
- **パッケージングの不安定性:** PyInstallerで動的リソースを完全にバンドルすることが技術的に困難

### 実用上の問題
- **ファイルサイズ:** 200MB以上の巨大ファイル
- **成功率:** 30-50%（環境依存の問題が多発）
- **メンテナンス:** Streamlit/Folium更新で破損リスク

**詳細分析:** `claudedocs/distribution_strategy_analysis.md` を参照

---

## 📁 プロジェクト構成

デプロイに必要なファイル：

```
ResouceCollection_05/
├── src/
│   ├── __init__.py
│   ├── app.py                    ⚠️ メインファイル
│   ├── ui/                       (UIコンポーネント)
│   ├── services/                 (ビジネスロジック)
│   └── infra/                    (インフラストラクチャ)
│
├── data/
│   ├── road_network_*.json       ⚠️ 道路ネットワークデータ
│   └── processed/                (処理済みマスタデータ)
│
├── .streamlit/
│   └── config.toml               (Streamlit設定)
│
├── requirements.txt              ⚠️ 依存関係定義
├── .gitignore                    ✅ 作成済み
│
├── STREAMLIT_CLOUD_DEPLOY.md     📘 詳細デプロイガイド
├── QUICK_START_DEPLOY.md         🚀 クイックスタート
├── prepare_deploy.bat            🔧 デプロイ準備スクリプト
└── README_DEPLOYMENT.md          📖 このファイル
```

---

## 🚀 デプロイ手順（概要）

### 方法A: 自動準備スクリプト使用（推奨）

```bash
# 1. 準備スクリプト実行
prepare_deploy.bat

# 2. GitHubリポジトリ作成
https://github.com/new

# 3. リモートリポジトリ追加とプッシュ
git remote add origin https://github.com/[ユーザー名]/resource-collection-optimizer.git
git branch -M main
git push -u origin main

# 4. Streamlit Cloudデプロイ
https://streamlit.io/cloud → "New app" → デプロイ設定
```

### 方法B: 手動セットアップ

詳細は `STREAMLIT_CLOUD_DEPLOY.md` を参照してください。

---

## ⚙️ デプロイ設定

### Streamlit Cloud設定

| 設定項目 | 値 |
|---------|---|
| **Repository** | `[あなたのユーザー名]/resource-collection-optimizer` |
| **Branch** | `main` |
| **Main file path** | `src/app.py` ⚠️重要 |
| **Python version** | 3.8+ |

### 環境変数（必要に応じて）

機密情報がある場合は Streamlit Secrets を使用:
1. Streamlit Cloud → アプリ設定 → Secrets
2. TOML形式で記述

---

## 🔄 更新とメンテナンス

### コードを更新する

```bash
# 変更を加えた後
git add .
git commit -m "機能追加: XXX"
git push
```

→ **自動的にStreamlit Cloudで再デプロイされます！**

### データを更新する

1. `data/` フォルダのファイルを更新
2. 上記のコミット・プッシュ手順を実行
3. 自動再デプロイ完了

---

## 📊 管理とモニタリング

### Streamlit Cloud管理画面

アクセス: https://share.streamlit.io/

**できること:**
- アプリの起動/停止
- ログの確認
- 再起動
- アクセス統計
- 設定変更

### ログの確認

Streamlit Cloud → アプリ選択 → "Manage app" → "Logs"

---

## 🔒 セキュリティ考慮事項

### 公開データの確認

⚠️ **重要:** GitHubの公開リポジトリにアップロードされるファイルは誰でも閲覧可能です。

**確認項目:**
- [ ] `data/` フォルダに機密情報は含まれていないか
- [ ] 個人情報や企業秘密はないか
- [ ] パスワードや認証情報は含まれていないか

**機密データの扱い:**
- ダミーデータに置き換える
- または、Streamlit Secrets を使用
- または、有料プランでプライベートリポジトリを使用

---

## 💰 料金プラン

### 無料プラン（Community Cloud）

- ✅ 無制限の公開アプリ
- ✅ 1GBメモリ
- ✅ 自動スケーリング
- ⚠️ Publicリポジトリのみ
- ⚠️ 月間稼働時間の制限あり

**このプロジェクトは無料プランで十分対応可能です。**

### 有料プラン

プライベートリポジトリや高性能が必要な場合のみ検討：
- Starter: $20/月
- Professional: カスタム料金

---

## 🆘 トラブルシューティング

### よくある問題と解決方法

#### ❌ "ModuleNotFoundError: No module named 'XXX'"

**原因:** 依存関係が不足

**解決:**
```bash
# requirements.txtを更新
pip freeze > requirements.txt

# コミット・プッシュ
git add requirements.txt
git commit -m "Update dependencies"
git push
```

#### ❌ "File not found: src/app.py"

**原因:** Main file path の設定ミス

**解決:**
1. Streamlit Cloud → アプリ設定
2. Main file path を `src/app.py` に変更
3. 保存

#### ❌ "Git push: Permission denied"

**原因:** GitHub認証エラー

**解決:**
1. Personal Access Token (PAT) を作成
2. パスワードの代わりにPATを使用

[PAT作成ガイド](https://docs.github.com/ja/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)

#### ❌ 地図が表示されない

**原因:** インターネット接続またはFoliumの問題

**解決:**
1. ブラウザのコンソールでエラー確認
2. インターネット接続確認
3. Streamlit Cloudのログを確認

---

## 📞 サポートリソース

### 公式ドキュメント

- **Streamlit Cloud:** https://docs.streamlit.io/streamlit-community-cloud
- **Streamlit API:** https://docs.streamlit.io/
- **GitHub Docs:** https://docs.github.com/ja
- **Git 入門:** https://git-scm.com/book/ja/v2

### コミュニティ

- **Streamlit Forum:** https://discuss.streamlit.io/
- **Stack Overflow:** `[streamlit]` タグ

---

## 🎯 次のステップ

デプロイ完了後、以下を検討できます：

1. **カスタムドメイン設定**（有料プラン）
2. **Google Analytics 連携**
3. **パスワード保護**（有料プラン）
4. **CI/CDパイプライン構築**（GitHub Actions）
5. **パフォーマンス最適化**

---

## 📝 チェックリスト

デプロイ前の最終確認：

- [ ] Gitがインストールされている
- [ ] GitHubアカウントを作成した
- [ ] `prepare_deploy.bat` を実行した
- [ ] requirements.txtが正しい
- [ ] データファイル（data/）が含まれている
- [ ] 機密情報が含まれていないことを確認した

デプロイ後の確認：

- [ ] アプリが正常に起動した
- [ ] 地図が表示される
- [ ] 最適化が実行できる
- [ ] URLを共有できた
- [ ] ユーザーが問題なくアクセスできることを確認した

---

## 📄 ライセンスと配布

このプロジェクトを公開リポジトリで配布する場合、適切なライセンスファイル（LICENSE）の追加を検討してください。

推奨ライセンス:
- MIT License（最も自由度が高い）
- Apache License 2.0
- GPL v3（コピーレフト）

---

**作成者:** プロジェクト管理者
**最終更新:** 2025-12-03
**バージョン:** 1.0
