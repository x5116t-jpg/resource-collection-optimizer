# LaTeX報告書のコンパイルガイド

## 状況: LaTeX環境がインストールされていない

現在、お使いのシステムにLaTeX環境がインストールされていません。
以下の3つの選択肢から選んでください：

## 🌐 選択肢1: オンラインでコンパイル（最も簡単・推奨）

**Overleafを使用（無料・インストール不要）**

1. https://www.overleaf.com/ にアクセス
2. 「Register」で無料アカウントを作成
3. 「New Project」→「Blank Project」を選択
4. プロジェクト名を入力（例：資源回収システム報告書）
5. 左側のファイルリストで「Upload」をクリック
6. 以下のファイルをすべてアップロード：
   ```
   main.tex
   sections/abstract.tex
   sections/introduction.tex
   sections/system_overview.tex
   sections/system_architecture.tex
   sections/implementation.tex
   sections/functions.tex
   sections/usage.tex
   sections/results.tex
   sections/discussion.tex
   sections/conclusion.tex
   sections/references.tex
   sections/appendix.tex
   ```
7. 自動的にPDFが生成されます（右側のプレビュー）
8. 「Download PDF」でダウンロード

**所要時間**: 約5-10分

**メリット**:
- インストール不要
- すぐに使える
- エラーが出ても自動的に対処
- 複数人で共同編集可能

## 💻 選択肢2: ローカル環境にLaTeXをインストール

**TeX Live（フルインストール・推奨）**

```powershell
# 1. ダウンロード
# https://www.tug.org/texlive/acquire-netinstall.html
# install-tl-windows.exe をダウンロード

# 2. インストール実行（1-2時間かかります）
# ダウンロードしたファイルをダブルクリック

# 3. インストール後、コンパイル
cd "D:\py\Resource Collection\ResouceCollection_05\docs\report"
platex main.tex
platex main.tex
dvipdfmx main.dvi
```

**MiKTeX（軽量版）**

```powershell
# 1. ダウンロード
# https://miktex.org/download

# 2. インストール実行

# 3. 日本語パッケージをインストール
mpm --install=platex
mpm --install=jsclasses

# 4. コンパイル
cd "D:\py\Resource Collection\ResouceCollection_05\docs\report"
platex main.tex
platex main.tex
dvipdfmx main.dvi
```

**所要時間**: インストール1-2時間 + コンパイル数分

**メリット**:
- オフラインで作業可能
- 高速なコンパイル
- カスタマイズ可能

**デメリット**:
- 大容量（7GB程度）
- インストールに時間がかかる

## 📄 選択肢3: 代替フォーマットで出力

LaTeXを使わずに、以下の形式で報告書を出力できます：

### A. Markdownバージョン
- GitHub、VSCode等で読みやすい形式
- 軽量で編集が容易

### B. HTMLバージョン
- ブラウザで閲覧可能
- PDFへの変換も簡単（印刷機能でPDF出力）

### C. Word（.docx）バージョン
- Microsoft Wordで編集可能
- 一般的なビジネス文書形式

どの形式が必要か教えていただければ、すぐに作成いたします。

## 推奨フロー

### 急いでPDFが必要な場合
→ **選択肢1（Overleaf）** を使用

### 今後も継続的にLaTeX文書を作成する場合
→ **選択肢2（TeX Liveインストール）** を推奨

### LaTeX環境を構築したくない場合
→ **選択肢3（Markdown/HTML）** で代替

## 次のステップ

どの方法を選択されますか？
1. Overleafで開く（手順が必要な場合はお知らせください）
2. TeX Liveをインストールする（インストール後にサポート）
3. Markdown/HTML形式で出力する（すぐに作成可能）

お選びいただければ、次のステップをサポートいたします。
