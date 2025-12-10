# CursorでLaTeX報告書を編集・プレビューする方法

## 手順1: LaTeX Workshop拡張機能をインストール

### 方法A: Cursor内でインストール
1. Cursorを開く
2. 左側のサイドバーから拡張機能アイコン（四角4つ）をクリック
3. 検索ボックスに「LaTeX Workshop」と入力
4. **LaTeX Workshop** (by James Yu) をインストール

### 方法B: コマンドパレットから
1. `Ctrl+Shift+P` (Windows) または `Cmd+Shift+P` (Mac)
2. 「Extensions: Install Extensions」と入力
3. 「LaTeX Workshop」を検索してインストール

## 手順2: LaTeXファイルを開く

```powershell
# Cursorで報告書ディレクトリを開く
cursor "D:\py\Resource Collection\ResouceCollection_05\docs\report"
```

または、Cursor内で：
1. File → Open Folder
2. `D:\py\Resource Collection\ResouceCollection_05\docs\report` を選択

## 手順3: 編集とプレビュー

### ファイル構成の確認
```
docs/report/
├── main.tex                 # メインファイル（これを開く）
└── sections/
    ├── abstract.tex         # 要旨
    ├── introduction.tex     # 序論
    ├── system_overview.tex  # システム概要
    └── ...                  # その他のセクション
```

### 編集
1. `main.tex` を開く
2. シンタックスハイライトで読みやすく表示される
3. セクションファイル（`sections/*.tex`）も同様に編集可能

### プレビュー（要：LaTeX環境）
LaTeX Workshop拡張機能を使うと：
- **PDFプレビュー**: `Ctrl+Alt+V` (Windows) または `Cmd+Alt+V` (Mac)
- **自動コンパイル**: ファイル保存時に自動的にPDF生成
- **エラー表示**: 問題箇所をハイライト

**⚠️ 注意**: プレビューとコンパイルにはLaTeX環境（platex, pdflatexなど）が必要です

## 選択肢：LaTeX環境なしでCursorを活用

### オプション1: Cursorで編集 + Overleafでコンパイル

**ワークフロー**:
1. **Cursorで編集**（快適なエディタ環境）
   ```
   - シンタックスハイライト
   - 自動補完
   - Git連携
   - マルチカーソル編集
   ```

2. **Overleafで同期**
   - Cursorで編集したファイルをOverleafにアップロード
   - Overleafで自動コンパイル
   - PDFをダウンロード

**メリット**:
- LaTeXインストール不要
- Cursorの強力な編集機能を活用
- Overleafの自動コンパイル機能を利用

### オプション2: LaTeX環境をインストール

**軽量版（MiKTeX）のインストール手順**:

```powershell
# 1. Chocolateyがインストールされている場合
choco install miktex

# または公式サイトからダウンロード
# https://miktex.org/download
```

**インストール後のCursor設定**:

1. Cursor設定を開く（`Ctrl+,`）
2. 「latex-workshop」で検索
3. 以下を設定：

```json
{
  "latex-workshop.latex.tools": [
    {
      "name": "platex",
      "command": "platex",
      "args": [
        "-interaction=nonstopmode",
        "-file-line-error",
        "%DOC%"
      ]
    },
    {
      "name": "dvipdfmx",
      "command": "dvipdfmx",
      "args": ["%DOCFILE%"]
    }
  ],
  "latex-workshop.latex.recipes": [
    {
      "name": "platex -> dvipdfmx",
      "tools": ["platex", "platex", "dvipdfmx"]
    }
  ]
}
```

## 便利な機能（LaTeX Workshop）

### キーボードショートカット
| ショートカット | 機能 |
|---------------|------|
| `Ctrl+Alt+B` | ビルド（コンパイル） |
| `Ctrl+Alt+V` | PDFプレビュー |
| `Ctrl+Alt+J` | 現在行にジャンプ（PDF↔TeX） |
| `Ctrl+Alt+C` | 中間ファイル削除 |

### 自動補完
- `\begin{` と入力すると環境の候補が表示
- `\ref{` でラベルの候補が表示
- `\cite{` で引用の候補が表示

### エラーチェック
- リアルタイムでシンタックスエラーを検出
- 問題箇所に波線表示
- エラーメッセージをホバーで表示

## 推奨ワークフロー

### パターンA: LaTeX環境あり
```
1. Cursorで main.tex を開く
2. 編集
3. Ctrl+S で保存 → 自動コンパイル
4. Ctrl+Alt+V でPDFプレビュー
5. 問題なければ main.pdf を使用
```

### パターンB: LaTeX環境なし（推奨）
```
1. Cursorで編集
   - 優れたエディタ機能
   - Git統合
   - AIアシスタント機能

2. Overleafにアップロード
   - https://www.overleaf.com/
   - すべての .tex ファイルをアップロード
   - 自動的にPDF生成

3. 必要に応じてCursorで編集 → Overleafで再アップロード
```

## Cursorの利点

### 編集機能
- **マルチカーソル**: 複数箇所を同時編集
- **検索置換**: 正規表現対応
- **Git統合**: バージョン管理が簡単
- **AI補助**: Cursorのコード生成機能

### LaTeX特有の機能
- **セクション折りたたみ**: `\section{}` 単位で折りたたみ可能
- **アウトライン表示**: 文書構造を一覧表示
- **参照ジャンプ**: `\ref{}` から定義元へジャンプ

## 現在の報告書を開く

```powershell
# Cursorで開く
cursor "D:\py\Resource Collection\ResouceCollection_05\docs\report"
```

Cursorが開いたら：
1. `main.tex` をクリック
2. 左側のExplorerで `sections/` フォルダを展開
3. 各セクションファイルを確認・編集

## まとめ

| 方法 | メリット | デメリット |
|------|---------|----------|
| **Cursor編集 + Overleaf** | インストール不要、即使用可能 | ネット接続必要 |
| **Cursor + LaTeX環境** | オフライン可、高速 | インストール必要(大容量) |
| **Cursor閲覧のみ** | すぐ確認可能 | PDF生成不可 |

**推奨**: まずCursorで内容を確認し、PDF生成はOverleafを使用する
