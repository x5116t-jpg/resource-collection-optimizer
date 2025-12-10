# 受託報告書 - LaTeX版

## ファイル構成

- `main.tex` - メインLaTeX文書
- `ntsel-report.sty` - カスタムスタイルファイル
- `section_*.tex` - 各セクションのコンテンツ
- `references.tex` - 参考文献
- `appendix.tex` - 付録

## コンパイル方法

### Windows（日本語対応）

```bash
platex main.tex
platex main.tex  # 目次更新のため2回実行
dvipdfmx main.dvi
```

### または pLaTeX + dvipdfmx

```bash
platex -kanji=utf8 main.tex
platex -kanji=utf8 main.tex
dvipdfmx main.dvi
```

### LuaLaTeX（推奨）

```bash
lualatex main.tex
lualatex main.tex
```

## 必要なLaTeXパッケージ

- jsarticle（日本語文書クラス）
- geometry（ページレイアウト）
- amsmath, amssymb（数式）
- graphicx（図）
- booktabs, multirow, array, longtable（表）
- listings, xcolor（コードリスト）
- fancyhdr（ヘッダー・フッター）
- titlesec（見出しスタイル）
- hyperref（ハイパーリンク）
- rotating（表の回転）

## 注意事項

1. 日本語を含むため、必ずpLaTeXまたはLuaLaTeXを使用してください
2. 目次を正しく生成するため、最低2回コンパイルしてください
3. 図表の参照を正しく解決するため、必要に応じて3回コンパイルしてください

## 出力ファイル

- `main.pdf` - 最終的なPDF報告書
- `main.aux`, `main.log`, `main.toc` - 中間ファイル（削除可）

## トラブルシューティング

### 文字化けする場合
- UTF-8エンコーディングで保存されていることを確認
- `platex -kanji=utf8` オプションを使用

### 目次が表示されない場合
- 2回以上コンパイルを実行

### 図表が表示されない場合
- ファイルパスが正しいか確認
- 必要な画像ファイルが存在するか確認
