# LaTeX環境のインストール手順

## Windows環境でのインストール

### 方法1: TeX Live（推奨）

1. **TeX Liveのダウンロード**
   - https://www.tug.org/texlive/acquire-netinstall.html
   - `install-tl-windows.exe` をダウンロード

2. **インストール**
   - ダウンロードしたファイルを実行
   - インストールには約1-2時間かかります（約7GB）
   - デフォルト設定でOK

3. **確認**
   ```powershell
   platex --version
   pdflatex --version
   ```

### 方法2: MiKTeX（軽量版）

1. **MiKTeXのダウンロード**
   - https://miktex.org/download
   - Windows用インストーラーをダウンロード

2. **インストール**
   - インストーラーを実行
   - 「Install missing packages on-the-fly」を選択

3. **日本語対応パッケージのインストール**
   ```powershell
   mpm --install=platex
   mpm --install=jsclasses
   ```

## コンパイル方法

### 日本語LaTeX（platex）を使用する場合

```powershell
cd "D:\py\Resource Collection\ResouceCollection_05\docs\report"
platex main.tex
platex main.tex  # 目次生成のため2回
dvipdfmx main.dvi
```

生成されるファイル: `main.pdf`

### pdfLaTeXを使用する場合（日本語が文字化けする可能性あり）

```powershell
cd "D:\py\Resource Collection\ResouceCollection_05\docs\report"
pdflatex main.tex
pdflatex main.tex  # 目次生成のため2回
```

## トラブルシューティング

### エラー: `jsarticle.cls not found`
```powershell
# TeX Liveの場合
tlmgr install jsclasses

# MiKTeXの場合
mpm --install=jsclasses
```

### エラー: 日本語が表示されない
- `platex` + `dvipdfmx` を使用してください
- `pdflatex` は日本語に対応していません

### エラー: コンパイルが途中で止まる
- Enterキーを押してスキップ
- または `platex -interaction=nonstopmode main.tex` を使用

## オンライン環境（インストール不要）

### Overleaf
1. https://www.overleaf.com/ にアクセス
2. 無料アカウント作成
3. New Project → Upload Project
4. `main.tex` と `sections/` フォルダをアップロード
5. 自動的にPDFが生成されます

### Cloud LaTeX
1. https://cloudlatex.io/ にアクセス
2. 日本語対応のオンラインLaTeXエディタ
3. 無料プランあり

## エディタ推奨

- **VS Code** + LaTeX Workshop拡張機能
- **TeXworks**（TeX Liveに同梱）
- **TeXstudio**（無料）

## クリーンアップコマンド

コンパイル後の中間ファイルを削除：

```powershell
# PowerShellの場合
Remove-Item *.aux, *.log, *.dvi, *.toc -ErrorAction SilentlyContinue

# Bashの場合
rm -f *.aux *.log *.dvi *.toc
```
