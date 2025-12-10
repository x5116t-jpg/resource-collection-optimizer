# ntsel-report.sty 修正設計書

**作成日**: 2025年12月2日
**目的**: 報告書の階層構造スタイルを統一し、以下の要求仕様を満たす汎用的なスタイルファイルを実現する

## 📋 要求仕様

### 階層構造の定義
```
1 章タイトル
  1.1 節タイトル
    1.1.1 項タイトル
      a) 細目
      b) 細目
        • 細目以下："• "、"："を使用し「ぶら下げインデント」形式で記述する
```

---

## 🔍 問題分析と要件定義

### 【問題1】paragraph番号（a), b) など）が表示されない

#### 現状の問題
- **TeX入力**: `\paragraph{ユーザー入力}`
- **期待出力**: `a) ユーザー入力`
- **実際出力**: `ユーザー入力`（太字のみ、番号なし）

#### 詳細分析
```latex
% 現在のntsel-report.sty 102-111行目
\renewcommand{\theparagraph}{\alph{paragraph})}
\titleformat{\paragraph}[hang]
  {\normalfont\normalsize\bfseries}
  {\theparagraph}    % ← ラベル設定は存在
  {1em}
  {}
\titlespacing*{\paragraph}
  {0pt}              % 左インデント
  {1.0em}            % 上のスペース
  {0.5em}            % 下のスペース
```

#### 根本原因
1. **カウンターリセット設定の欠如**:
   - LaTeXのデフォルトでは`paragraph`カウンターは`subsubsection`が変わってもリセットされない
   - 明示的な`\counterwithin`または`\@addtoreset`が必要

2. **カウンターインクリメントの問題**:
   - `\titleformat`はカウンターを表示するが、自動インクリメントは`\paragraph`コマンド自体が行う
   - しかし、リセット設定がないため、カウンターが0のまま、または前の値を保持している可能性

3. **検証方法**:
   - main.logを確認: paragraphカウンターの値が記録されているか
   - 実際のTeX処理: `\paragraph`が呼ばれたときにカウンターがインクリメントされているか

#### 要件定義
- **R1.1**: `\paragraph`が呼ばれるたびに自動的に番号がインクリメントされること
- **R1.2**: `\subsubsection`が変わるたびに`paragraph`カウンターが1にリセットされること
- **R1.3**: 番号形式は`a), b), c), ...`であること
- **R1.4**: 番号と見出しテキストの間隔は全角1文字分（1em）であること
- **R1.5**: 見出しは太字（`\bfseries`）であること

---

### 【問題2】detaillist環境のぶら下げインデントが機能不全

#### 現状の問題
- **TeX入力**:
  ```latex
  \begin{detaillist}
      \detailitem{システムデフォルトのデータ} システムに予め組み込まれており、ユーザーの入力作業を軽減する基本データである。
  \end{detaillist}
  ```
- **期待出力**:
  ```
  • システムデフォルトのデータ：システムに予め組み込まれており、ユーザーの入力作業を軽減する基本デー
                               タである。
  ```
- **実際出力**:
  ```
  • システムデフォルトのデータ：システムに予め組み込まれており、ユーザーの入力作業を軽減する基本データである。
  ```
  （2行目が正しい位置に揃っていない）

#### 詳細分析
```latex
% 現在のntsel-report.sty 215-233行目
\newlist{detaillist}{itemize}{3}
\setlist[detaillist,1]{
    label=,                      % ラベルは手動で設定
    leftmargin=0pt,              % 左マージンなし
    itemindent=0pt,              % 項目インデントなし
    labelsep=0pt,                % ラベル間隔なし
    itemsep=0.3em,
    parsep=0em,
    topsep=0.5em,
    listparindent=0pt,
    before={\raggedright}
}

\newcommand{\detailitem}[1]{%
    \item\textbullet~\textbf{#1}：%
    \hangindent=3zw\hangafter=1%      % ← 問題箇所
}
```

#### 根本原因
1. **`\hangindent`の適用タイミング**:
   - `\item\textbullet~\textbf{#1}：`を出力した**後**に`\hangindent`を設定
   - LaTeXでは段落開始時に`\hangindent`が確定している必要がある
   - 出力後の設定では次の段落にしか適用されない

2. **`\hangafter=1`の意味**:
   - 「1行目の後から」ぶら下げを開始
   - しかし、段落の2行目から適用されるのが期待される動作
   - 実際には1行目自体が既に出力されているため、効果がない

3. **`3zw`の不正確性**:
   - `zw` = 全角文字幅
   - 「• 」（bullet + 半角スペース）+ 項目名 + 「：」の実際の幅と一致しない
   - 項目名の長さは可変なので、固定値では対応できない

4. **enumitemパッケージとの非互換**:
   - `leftmargin=0pt`と`\hangindent`の併用は予期しない動作を引き起こす可能性

#### 要件定義
- **R2.1**: 箇条書き記号は「• 」（`\textbullet` + 半角スペース）であること
- **R2.2**: 項目名は太字で表示され、直後に全角コロン「：」が付くこと
- **R2.3**: 2行目以降は「項目名：」の直後（説明文開始位置）に揃うこと
- **R2.4**: ぶら下げインデント幅は項目名の長さに応じて動的に計算されること
- **R2.5**: 複数段落にまたがる場合でも、各段落で同じインデントが維持されること

---

### 【問題3】通常のitemize環境でぶら下げインデントが設定されていない

#### 現状の問題
- **TeX入力**:
  ```latex
  \begin{itemize}
      \item \textbf{名称}：地域交通計画立案ツールを改良した群馬県内の未利用資源運搬等に関する基礎的研究
  \end{itemize}
  ```
- **期待出力**:
  ```
  • 名称：地域交通計画立案ツールを改良した群馬県内の未利用資源運搬等に関する基礎的研究
  ```
  （項目名が短い場合、ぶら下げは不要）

  または:
  ```
  • 目的：交通安全環境研究所で開発中の「地域交通計画立案ツール」を改良し、群馬県内の未利用資源運搬時
        の最短経路と運搬費用を推計する
  ```
  （2行目は「交」の位置に揃う）

- **実際出力**: 2行目が左端または「•」の直後に揃っている

#### 詳細分析
```latex
% 現在のntsel-report.sty 177-184行目
\setlist[itemize]{
    leftmargin=*,           % 左マージン自動調整
    labelsep=0.5em,         % ラベルと本文の間隔
    itemsep=0.3em,
    parsep=0em,
    topsep=0.5em
}
```

#### 根本原因
1. **`leftmargin=*`の動作**:
   - ラベル幅に基づいて左マージンを自動計算
   - しかし、これはラベル（`\textbullet`）の幅のみを考慮
   - 「\textbf{項目名}：」の幅は考慮されない

2. **ぶら下げインデント設定の欠如**:
   - 標準のitemize設定にはぶら下げインデントのメカニズムがない
   - `\item \textbf{項目名}：説明文`という使い方を想定した設定がない

3. **2つの使用パターンの存在**:
   - パターンA: `\item 説明文のみ`（ぶら下げ不要）
   - パターンB: `\item \textbf{項目名}：説明文`（ぶら下げ必要）
   - 現在の設定はパターンAのみに対応

#### 要件定義
- **R3.1**: 通常のitemizeは従来通り動作すること（後方互換性）
- **R3.2**: `\item \textbf{項目名}：説明文`パターンでぶら下げインデントが機能すること
- **R3.3**: 2つの使用パターンが混在しても問題なく動作すること
- **R3.4**: ユーザーが明示的に環境を使い分けられるようにすること（例: `itemize` vs `detaillist`）

---

## 🎯 解決策の検討

### 【解決策1】paragraph番号の修正

#### 方針A: カウンターリセットの自動化（推奨）

**実装方法**:
```latex
% chngcntrパッケージを使用
\RequirePackage{chngcntr}
\counterwithin{paragraph}{subsubsection}
```

**メリット**:
- ✅ 自動的にリセットされるため、ユーザーの手間がない
- ✅ LaTeX標準の動作に沿った実装
- ✅ 他の報告書でも再利用可能

**デメリット**:
- ⚠️ パッケージの追加が必要

**代替実装（パッケージ不使用）**:
```latex
\makeatletter
\@addtoreset{paragraph}{subsubsection}
\makeatother
```

---

#### 方針B: 手動リセットをドキュメント化

**実装方法**:
- スタイルファイルは変更せず、ユーザーガイドに記載
- 各`\subsubsection`の後に`\setcounter{paragraph}{0}`を挿入

**メリット**:
- ✅ スタイルファイルの変更が最小限

**デメリット**:
- ❌ ユーザーの負担が大きい
- ❌ 忘れた場合に番号がおかしくなる
- ❌ 汎用性がない

---

#### 方針C: 番号形式の変更

**実装方法**:
```latex
\renewcommand{\theparagraph}{\thesubsubsection.\alph{paragraph})}
```

**出力例**: `2.1.1.a)` 形式

**メリット**:
- ✅ リセット不要でもユニークな番号

**デメリット**:
- ❌ 要求仕様（`a), b), c)`）と異なる

---

#### **選定結果**: 方針A（カウンターリセットの自動化）

**理由**:
- 要求仕様を満たす
- 汎用性が高く、他の報告書でも使用可能
- ユーザーの負担がない

---

### 【解決策2】detaillistのぶら下げインデント修正

#### 方針A: `\item`のオーバーライドとボックス測定（推奨）

**実装方法**:
```latex
\newlist{detaillist}{itemize}{3}
\setlist[detaillist,1]{
    leftmargin=0pt,
    itemindent=0pt,
    labelwidth=0pt,
    labelsep=0pt,
    itemsep=0.3em,
    parsep=0em,
    topsep=0.5em,
    listparindent=0pt,
    before={\raggedright}
}

\newcommand{\detailitem}[1]{%
    \item%
    \begingroup%
    \setbox0=\hbox{\textbullet~\textbf{#1}：}% ← ボックスに測定
    \hangindent=\wd0% ← ボックスの幅を使用
    \hangafter=1%
    \box0% ← ボックスを出力
    \endgroup%
    \ignorespaces%
}
```

**動作説明**:
1. `\setbox0=\hbox{...}`: 「• 項目名：」をボックス0に格納して幅を測定
2. `\hangindent=\wd0`: 測定した幅をぶら下げインデント幅として設定
3. `\box0`: ボックスを出力
4. 以降のテキストは自動的にぶら下げインデントが適用される

**メリット**:
- ✅ 項目名の長さに応じて動的に計算
- ✅ 正確なインデント位置
- ✅ 複数段落にも対応

**デメリット**:
- ⚠️ やや複雑な実装

---

#### 方針B: enumitemの`leftmargin`と`itemindent`の組み合わせ

**実装方法**:
```latex
\setlist[detaillist,1]{
    leftmargin=3em,      % 固定値
    itemindent=-3em,
    labelwidth=0pt,
    labelsep=0pt,
    itemsep=0.3em,
    parsep=0em,
    topsep=0.5em
}
```

**メリット**:
- ✅ シンプルな実装

**デメリット**:
- ❌ 固定値のため、項目名の長さが変わると位置がずれる
- ❌ 要件R2.4（動的計算）を満たさない

---

#### 方針C: `\parshape`の使用

**実装方法**:
```latex
\newcommand{\detailitem}[1]{%
    \item%
    \setbox0=\hbox{\textbullet~\textbf{#1}：}%
    \parshape 2 0pt \linewidth \wd0 \dimexpr\linewidth-\wd0\relax%
    \box0%
}
```

**メリット**:
- ✅ 正確な制御

**デメリット**:
- ❌ `\parshape`は2段落までしか指定できない（3段落目以降は通常の形状に戻る）
- ❌ 要件R2.5（複数段落対応）を満たさない

---

#### **選定結果**: 方針A（`\item`のオーバーライドとボックス測定）

**理由**:
- 要件R2.1～R2.5を全て満たす
- 動的な幅計算により、項目名の長さに対応
- 複数段落にも対応

---

### 【解決策3】通常itemizeのぶら下げインデント

#### 方針A: 新しいカスタム環境を追加（推奨）

**実装方法**:
```latex
% 既存のitemizeは変更しない
% 新しい環境を追加
\newlist{hangitemize}{itemize}{3}
\setlist[hangitemize,1]{
    leftmargin=*,
    labelsep=0.5em,
    itemsep=0.3em,
    parsep=0em,
    topsep=0.5em
}

% ぶら下げインデント用のitemコマンド
\newcommand{\hangitem}[1]{%
    \item%
    \setbox0=\hbox{\textbf{#1}：}%
    \hangindent=\dimexpr\labelwidth+\labelsep+\wd0\relax%
    \hangafter=1%
    \box0%
    \ignorespaces%
}
```

**使用例**:
```latex
\begin{hangitemize}
    \hangitem{名称} 地域交通計画立案ツールを...
    \hangitem{目的} 交通安全環境研究所で...
\end{hangitemize}
```

**メリット**:
- ✅ 既存のitemizeに影響しない（後方互換性）
- ✅ 明示的な使い分けが可能
- ✅ 要件R3.1～R3.4を満たす

**デメリット**:
- ⚠️ 新しい環境を覚える必要がある

---

#### 方針B: itemizeを上書き（非推奨）

**実装方法**:
- 既存のitemize環境を再定義してぶら下げインデントを強制

**メリット**:
- ✅ ユーザーは既存のコードを変更不要

**デメリット**:
- ❌ 既存の動作が変わる（後方互換性なし）
- ❌ 通常の箇条書きでも意図しないぶら下げが発生する可能性
- ❌ 汎用性が低い

---

#### 方針C: detaillist環境を推奨（現状維持）

**実装方法**:
- スタイルファイルは変更せず、ドキュメントで`detaillist`環境の使用を推奨

**メリット**:
- ✅ 変更が最小限

**デメリット**:
- ❌ 既存のitemizeを使っている箇所を全て修正する必要がある
- ❌ 要件R3.2を満たさない

---

#### **選定結果**: 方針A（新しいカスタム環境を追加）

**理由**:
- 後方互換性を保ちながら、ぶら下げインデント機能を提供
- 明示的な使い分けにより、意図しない動作を防止
- detaillistとは異なる用途（「•」と「項目名：」の組み合わせ）に対応

---

## 📐 詳細設計

### 1. paragraph番号の修正

#### 実装箇所
- `ntsel-report.sty` 77-78行目の直後に追加

#### 実装コード
```latex
% セクション番号の深さを設定（paragraphまで番号を表示）
\setcounter{secnumdepth}{4}

% paragraphカウンターをsubsubsectionでリセット
\RequirePackage{chngcntr}
\counterwithin{paragraph}{subsubsection}

% sectionの設定
\titleformat{\section}
```

#### 代替実装（chngcntrパッケージを使わない場合）
```latex
% セクション番号の深さを設定（paragraphまで番号を表示）
\setcounter{secnumdepth}{4}

% paragraphカウンターをsubsubsectionでリセット（パッケージ不使用版）
\makeatletter
\@addtoreset{paragraph}{subsubsection}
\makeatother
```

#### 検証方法
1. TeXファイルに以下を記述:
   ```latex
   \subsubsection{テスト1}
   \paragraph{項目A} 内容A
   \paragraph{項目B} 内容B

   \subsubsection{テスト2}
   \paragraph{項目C} 内容C
   ```
2. 期待される出力:
   ```
   テスト1
   a) 項目A 内容A
   b) 項目B 内容B

   テスト2
   a) 項目C 内容C  ← aにリセットされる
   ```

---

### 2. detaillist環境の修正

#### 実装箇所
- `ntsel-report.sty` 228-233行目を全面的に書き換え

#### 実装コード
```latex
% カスタムリスト環境を新規作成（itemize環境ベース）
% \hangindentを使用した真のぶら下げインデントを実現
\newlist{detaillist}{itemize}{3}
\setlist[detaillist,1]{
    label=,                      % ラベルは手動で設定
    leftmargin=0pt,              % 左マージンなし
    itemindent=0pt,              % 項目インデントなし
    labelwidth=0pt,              % ラベル幅なし
    labelsep=0pt,                % ラベル間隔なし
    itemsep=0.3em,               % 項目間の間隔
    parsep=0em,                  % 段落間の間隔
    topsep=0.5em,                % リスト前後の間隔
    listparindent=0pt,           % リスト内段落のインデント
    before={\raggedright}        % 右端を揃えない
}

% detaillist環境用のitem再定義コマンド（改良版）
% 使用方法: \detailitem{項目名} 説明文
%
% 動作説明:
% 1. \setbox0で「• 項目名：」の幅を測定
% 2. 測定した幅をぶら下げインデント幅として設定
% 3. ボックスを出力後、以降のテキストは自動的にぶら下げ
\newcommand{\detailitem}[1]{%
    \item%
    \begingroup%
    % 「• 項目名：」の幅を測定
    \setbox0=\hbox{\textbullet~\textbf{#1}：}%
    % 測定した幅をぶら下げインデント幅として設定
    % \hangafter=1 は「1行目の後から」ぶら下げ開始を意味
    \hangindent=\wd0%
    \hangafter=1%
    % ボックスを出力
    \unhbox0%
    \endgroup%
    % 直後の空白を無視
    \ignorespaces%
}
```

#### 改良点の詳細

1. **`\box0` → `\unhbox0`に変更**:
   - `\box0`: ボックスをそのまま出力（内部構造を保持）
   - `\unhbox0`: ボックスの内容を展開して出力
   - `\unhbox`を使うことで、後続のテキストとの結合がスムーズになる

2. **`\ignorespaces`の追加**:
   - コマンド直後の空白を無視
   - `\detailitem{項目名} 説明文`のように、スペースを入れて記述できる

3. **`labelwidth=0pt`の追加**:
   - ラベル幅を明示的に0に設定
   - enumitemパッケージとの互換性向上

#### 検証方法
1. TeXファイルに以下を記述:
   ```latex
   \begin{detaillist}
       \detailitem{短い} これは短い項目名のテストです。
       \detailitem{非常に長い項目名} これは非常に長い項目名のテストです。2行目がどこに揃うか確認します。さらに長いテキストを追加して、3行目も確認します。
   \end{detaillist}
   ```
2. 期待される出力:
   ```
   • 短い：これは短い項目名のテストです。
   • 非常に長い項目名：これは非常に長い項目名のテストです。2行目がどこに揃うか確認します。さらに長い
                       テキストを追加して、3行目も確認します。
   ```

---

### 3. hangitemize環境の追加

#### 実装箇所
- `ntsel-report.sty` の箇条書き設定セクション（detaillistの後）に追加

#### 実装コード
```latex
% ============================================================
% ぶら下げインデント付きitemize環境
% ============================================================
%
% 使用方法:
% \begin{hangitemize}
%     \hangitem{項目名} 説明文
% \end{hangitemize}
%
% 出力例：
% • 項目名：説明文が長くなった場合、2行目以降は
%          「説」の位置に揃います。

\newlist{hangitemize}{itemize}{3}
\setlist[hangitemize,1]{
    leftmargin=*,           % 左マージン自動調整
    labelsep=0.5em,         % ラベルと本文の間隔
    itemsep=0.3em,          % 項目間の間隔
    parsep=0em,             % 段落間の間隔
    topsep=0.5em            % リスト前後の間隔
}

% hangitemize環境用のitemコマンド
%
% 動作説明:
% 1. \labelwidthと\labelsepを取得（enumitemが設定した値）
% 2. 「項目名：」の幅を測定
% 3. 合計幅をぶら下げインデント幅として設定
\newcommand{\hangitem}[1]{%
    \item%
    \begingroup%
    % 「項目名：」の幅を測定
    \setbox0=\hbox{\textbf{#1}：}%
    % ぶら下げインデント幅 = ラベル幅 + ラベル間隔 + 項目名幅
    % \labelwidthはenumitemが自動設定した「•」の幅
    % \labelsepは「•」と本文の間隔（0.5em）
    \hangindent=\dimexpr\labelwidth+\labelsep+\wd0\relax%
    \hangafter=1%
    % ボックスを出力
    \unhbox0%
    \endgroup%
    \ignorespaces%
}

% 第2レベル、第3レベルも同様に設定
\setlist[hangitemize,2]{
    leftmargin=*,
    labelsep=0.5em,
    itemsep=0.3em,
    parsep=0em,
    topsep=0.5em
}

\setlist[hangitemize,3]{
    leftmargin=*,
    labelsep=0.5em,
    itemsep=0.3em,
    parsep=0em,
    topsep=0.5em
}
```

#### 使用ガイドライン

**従来のitemize（変更なし）**:
```latex
\begin{itemize}
    \item 項目1
    \item 項目2
\end{itemize}
```

**項目名付きの箇条書き（新規）**:
```latex
\begin{hangitemize}
    \hangitem{名称} 地域交通計画立案ツールを改良した...
    \hangitem{目的} 交通安全環境研究所で開発中の...
\end{hangitemize}
```

**detaillist環境（改良）**:
```latex
\begin{detaillist}
    \detailitem{システムデフォルトのデータ} システムに予め...
    \detailitem{道路ネットワークデータ} OpenStreetMapまたは...
\end{detaillist}
```

#### 検証方法
1. TeXファイルに以下を記述:
   ```latex
   \begin{hangitemize}
       \hangitem{名称} 地域交通計画立案ツールを改良した群馬県内の未利用資源運搬等に関する基礎的研究
       \hangitem{目的} 交通安全環境研究所で開発中の「地域交通計画立案ツール」を改良し、群馬県内の未利用資源運搬時の最短経路と運搬費用を推計する
   \end{hangitemize}
   ```
2. 期待される出力:
   ```
   • 名称：地域交通計画立案ツールを改良した群馬県内の未利用資源運搬等に関する基礎的研究
   • 目的：交通安全環境研究所で開発中の「地域交通計画立案ツール」を改良し、群馬県内の未利用資源運搬
         時の最短経路と運搬費用を推計する
   ```

---

## 🧪 実装前の検証ポイント

### 検証項目リスト

#### 1. paragraph番号の検証
- [ ] **V1.1**: 連続する`\paragraph`で番号が a), b), c) とインクリメントされるか
- [ ] **V1.2**: `\subsubsection`が変わると番号が a) にリセットされるか
- [ ] **V1.3**: `\section`や`\subsection`が変わっても影響がないか
- [ ] **V1.4**: 番号と見出しテキストの間隔が適切か
- [ ] **V1.5**: 太字が適用されているか

#### 2. detaillistのぶら下げインデント検証
- [ ] **V2.1**: 「•」が正しく表示されるか
- [ ] **V2.2**: 項目名が太字で、直後に「：」が付くか
- [ ] **V2.3**: 2行目が「：」の直後の位置に揃うか
- [ ] **V2.4**: 項目名の長さが異なる場合でも正しく揃うか
- [ ] **V2.5**: 複数段落にまたがる場合でもインデントが維持されるか
- [ ] **V2.6**: ネストした場合（detaillist内のdetaillist）の動作は適切か

#### 3. hangitemizeのぶら下げインデント検証
- [ ] **V3.1**: 「•」が正しく表示されるか
- [ ] **V3.2**: 項目名が太字で、直後に「：」が付くか
- [ ] **V3.3**: 2行目が「：」の直後の位置に揃うか
- [ ] **V3.4**: 既存のitemizeに影響がないか（後方互換性）
- [ ] **V3.5**: 第2レベル、第3レベルのネストが正しく動作するか

#### 4. 統合テスト
- [ ] **V4.1**: 全ての階層が混在した文書で正しく動作するか
- [ ] **V4.2**: main.texを含む既存の報告書がエラーなくコンパイルできるか
- [ ] **V4.3**: 出力PDFが要求仕様を満たしているか
- [ ] **V4.4**: ログファイルにWarningやErrorがないか

---

## 📦 パッケージ依存関係

### 追加が必要なパッケージ

#### chngcntrパッケージ
- **目的**: `\counterwithin`コマンドを提供
- **使用箇所**: paragraph番号のリセット設定
- **代替案**: `\@addtoreset`を使用（パッケージ不要、ただし内部コマンド）

#### 実装の選択肢

**オプションA（推奨）**: chngcntrパッケージを使用
```latex
\RequirePackage{chngcntr}
\counterwithin{paragraph}{subsubsection}
```

**オプションB**: 内部コマンドを使用（パッケージ不要）
```latex
\makeatletter
\@addtoreset{paragraph}{subsubsection}
\makeatother
```

**推奨**: オプションBを採用
- 理由: 追加パッケージを最小限に抑える
- LaTeX 2eの標準機能のみを使用

---

## 📝 ドキュメント更新

### スタイルファイルのコメント更新

各セクションに以下のコメントを追加:

```latex
% ============================================================
% セクションタイトルの設定
% ============================================================
%
% 階層構造:
%   1 章タイトル (section)
%     1.1 節タイトル (subsection)
%       1.1.1 項タイトル (subsubsection)
%         a) 細目 (paragraph)
%         b) 細目
%           • 細目以下 (itemize/detaillist/hangitemize)
%
% paragraph番号は subsubsection ごとに自動的にリセットされます
```

### README.md の更新内容

```markdown
## 箇条書き環境の使い分け

### 1. 通常の箇条書き（itemize）
シンプルな箇条書きに使用します。

\begin{itemize}
    \item 項目1
    \item 項目2
\end{itemize}

### 2. 項目名付き箇条書き（hangitemize）
項目名と説明文の組み合わせで、ぶら下げインデントが必要な場合に使用します。

\begin{hangitemize}
    \hangitem{名称} 説明文...
    \hangitem{目的} 説明文...
\end{hangitemize}

### 3. 詳細説明リスト（detaillist）
「•」記号 + 太字項目名 + コロン + 説明文の形式で使用します。

\begin{detaillist}
    \detailitem{システムデフォルトのデータ} 説明文...
    \detailitem{道路ネットワークデータ} 説明文...
\end{detaillist}
```

---

## 🔄 移行ガイド

### 既存コードの修正が必要な箇所

#### main.tex での変更

**変更前**:
```latex
\begin{itemize}
    \item \textbf{名称}：地域交通計画立案ツールを...
    \item \textbf{目的}：交通安全環境研究所で...
\end{itemize}
```

**変更後（オプション1: hangitemize環境を使用）**:
```latex
\begin{hangitemize}
    \hangitem{名称} 地域交通計画立案ツールを...
    \hangitem{目的} 交通安全環境研究所で...
\end{hangitemize}
```

**変更後（オプション2: detaillist環境を使用）**:
```latex
\begin{detaillist}
    \detailitem{名称} 地域交通計画立案ツールを...
    \detailitem{目的} 交通安全環境研究所で...
\end{detaillist}
```

**推奨**: オプション1（hangitemize）
- 理由: detaillistは「•」が含まれる特殊な形式
- hangitemizeは標準的なitemizeの拡張として理解しやすい

---

## 🎨 出力サンプル

### 期待される最終出力

```
2 システムの説明

  2.1 システムの全体構成

    2.1.1 システム構成要素

      a) ユーザー入力
      ユーザーがStreamlitの対話的インターフェースを通じて入力・選択する情報である：

      • 車庫地点：車両の出発地点・帰着地点の座標
      • 資源回収地点：資源を回収する地点の座標

      b) 入力層
      入力層では、システムが最適化計算を実行するために必要なデータを管理する。

      • システムデフォルトのデータ：システムに予め組み込まれており、ユーザーの入力作業を軽減する基本デー
                                   タである。

        道路ネットワークデータ：OpenStreetMap（OSM）またはカスタムJSON形式で提供される道路ネット
                               ワーク情報である。
```

---

## ⚠️ 注意事項とリスク

### リスク分析

#### リスク1: 後方互換性の問題
- **内容**: 既存の文書でレイアウトが変わる可能性
- **影響度**: 低
- **対策**: itemize環境は変更しないため、影響は最小限

#### リスク2: ボックス測定の精度
- **内容**: `\setbox`と`\wd`による幅測定の誤差
- **影響度**: 低
- **対策**: TeXの標準機能のため、高精度が保証される

#### リスク3: フォント変更時の動作
- **内容**: フォントサイズや種類を変更した場合の幅計算
- **影響度**: 低
- **対策**: 実行時に動的に計算するため、自動的に対応

#### リスク4: 複雑なネスト構造
- **内容**: detaillist内のhangitemizeなど、深いネスト
- **影響度**: 中
- **対策**: enumitemのネストレベル制限（最大3レベル）内で使用を推奨

---

## 📊 実装工数見積もり

| 作業項目 | 見積もり時間 | 難易度 |
|---------|-------------|--------|
| paragraph番号修正 | 15分 | 低 |
| detaillist修正 | 30分 | 中 |
| hangitemize追加 | 45分 | 中 |
| コメント・ドキュメント更新 | 30分 | 低 |
| 統合テスト | 60分 | 中 |
| 既存文書の修正 | 30分 | 低 |
| **合計** | **3.5時間** | - |

---

## ✅ 実装チェックリスト

### 実装前
- [ ] 現在のntsel-report.styのバックアップを作成
- [ ] 設計書の内容を再確認
- [ ] テスト環境の準備

### 実装中
- [ ] paragraph番号のリセット設定を追加
- [ ] detaillist環境の`\detailitem`コマンドを修正
- [ ] hangitemize環境と`\hangitem`コマンドを追加
- [ ] コメントを適切に追加
- [ ] インデント・スペーシングを統一

### 実装後
- [ ] 全ての検証項目（V1.1～V4.4）をクリア
- [ ] main.texが正常にコンパイルできることを確認
- [ ] 出力PDFが要求仕様を満たすことを確認
- [ ] ログファイルにエラーがないことを確認
- [ ] README.mdを更新

---

**END OF DESIGN DOCUMENT**
