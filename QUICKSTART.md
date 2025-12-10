# クイックスタートガイド

## 🚀 3ステップで実行ファイルを作成

### ステップ1: PyInstallerのインストール

```
install_pyinstaller.bat をダブルクリック
```

**期待される出力**:
```
PyInstallerをインストールしています...
仮想環境が見つかりました: D:\py\Resource Collection\ResouceCollection_05\.venv\Scripts\python.exe
PyInstallerをインストール中...
Successfully installed pyinstaller-6.x.x
========================================
インストール完了！
========================================
PyInstallerのバージョン:
6.x.x
```

---

### ステップ2: ビルド実行

```
build_standalone.bat をダブルクリック
```

**期待される出力**:
```
========================================
実行ファイルをビルドしています...
========================================

仮想環境を確認しました: D:\py\Resource Collection\ResouceCollection_05\.venv\Scripts\python.exe

古いビルド成果物を削除しています...

========================================
PyInstallerでビルドを開始します...
（この処理には数分かかります）
========================================

Building...
...
Building EXE from EXE-00.toc completed successfully.

========================================
ビルド完了！
========================================

実行ファイル: dist\資源回収最適化ツール.exe
```

**所要時間**: 5-10分

---

### ステップ3: テスト実行

```
dist\資源回収最適化ツール.exe をダブルクリック
```

- ブラウザが自動的に開きます（初回10-20秒）
- アプリケーションが起動します

---

## 🎁 配布パッケージの作成（オプション）

```
create_distribution_package.bat をダブルクリック
```

1. バージョン番号を入力（例: `1.0`）
2. ZIP圧縮するか確認 → `Y` を入力
3. `ResourceOptimizer_v1.0.zip` が作成されます

---

## 🔧 トラブルシューティング

### エラーが発生した場合

まず環境チェックを実行:
```
quick_test.bat をダブルクリック
```

これで以下が確認できます:
- ✅ 仮想環境の存在
- ✅ Python/Streamlit/NetworkXのインストール
- ✅ PyInstallerのインストール状況

---

### よくあるエラー

#### 「仮想環境が見つかりません」

**解決策**:
```cmd
# コマンドプロンプトで実行
cd "D:\py\Resource Collection\ResouceCollection_05"
python -m venv .venv
.venv\Scripts\pip.exe install -r requirements.txt
```

#### 「PyInstallerのインストールに失敗しました」

**解決策**:
```cmd
# コマンドプロンプトで実行
cd "D:\py\Resource Collection\ResouceCollection_05"
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install pyinstaller
```

#### ビルド中に「ModuleNotFoundError」

**解決策**:
```cmd
# 必要なパッケージをインストール
.venv\Scripts\python.exe -m pip install streamlit networkx pandas folium streamlit-folium
```

---

## 📝 修正履歴

### 2024年修正内容

**問題**: パスにスペースが含まれているため、バッチファイルが正しく動作しない

**解決策**:
1. `%~dp0` を使用して絶対パスを取得
2. 環境変数にパスを格納
3. `python -m pip` および `python -m PyInstaller` を使用

**変更点**:
- ✅ `activate.bat` を呼び出さない方式に変更
- ✅ 絶対パスを環境変数に格納
- ✅ `python -m` 経由でモジュールを実行

---

## 🎯 次のステップ

1. **今すぐ実行**: `install_pyinstaller.bat`
2. **続いて実行**: `build_standalone.bat`
3. **テスト**: `dist\資源回収最適化ツール.exe`
4. **配布準備**: `create_distribution_package.bat`

準備完了です！ 🚀
