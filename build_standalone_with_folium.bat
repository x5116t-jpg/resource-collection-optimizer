@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ========================================
echo 実行ファイルをビルドしています...
echo ========================================
echo.

REM 仮想環境のパスを設定
set VENV_PYTHON=%~dp0.venv\Scripts\python.exe

REM 仮想環境の確認
if not exist "%VENV_PYTHON%" (
    echo エラー: 仮想環境が見つかりません。
    echo 確認してください: %VENV_PYTHON%
    echo.
    echo recreate_venv_windows.bat を先に実行してください。
    pause
    exit /b 1
)

echo 仮想環境を確認しました
echo パス: %VENV_PYTHON%

REM PyInstallerがインストールされているか確認
"%VENV_PYTHON%" -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo.
    echo PyInstallerがインストールされていません。
    echo インストールしますか？ [Y/N]
    set /p INSTALL_PYINSTALLER=
    if /i "!INSTALL_PYINSTALLER!"=="Y" (
        echo PyInstallerをインストールしています...
        "%VENV_PYTHON%" -m pip install pyinstaller
        if errorlevel 1 (
            echo エラー: PyInstallerのインストールに失敗しました。
            pause
            exit /b 1
        )
    ) else (
        echo ビルドを中止しました。
        pause
        exit /b 1
    )
)

REM streamlit_foliumのパスを取得
echo.
echo streamlit_foliumのパスを取得しています...
for /f "delims=" %%i in ('"%VENV_PYTHON%" -c "import streamlit_folium; import os; print(os.path.dirname(streamlit_folium.__file__))" 2^>nul') do set FOLIUM_PATH=%%i

if not defined FOLIUM_PATH (
    echo 警告: streamlit_foliumが見つかりません。
    echo 地図機能が動作しない可能性があります。
    set FOLIUM_DATA_ARG=
) else (
    echo streamlit_foliumのパス: !FOLIUM_PATH!
    set FOLIUM_DATA_ARG=--add-data "!FOLIUM_PATH!;streamlit_folium"
)

echo.
echo 古いビルド成果物を削除しています...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist "資源回収最適化ツール.spec" del "資源回収最適化ツール.spec"

echo.
echo ========================================
echo PyInstallerでビルドを開始します...
echo （この処理には数分かかります）
echo ========================================
echo.

REM PyInstallerでビルド
if defined FOLIUM_DATA_ARG (
    echo folium サポート付きでビルドします
    "%VENV_PYTHON%" -m PyInstaller ^
        --name "資源回収最適化ツール" ^
        --onefile ^
        --console ^
        --add-data "src;src" ^
        --add-data "data;data" ^
        --add-data ".streamlit;.streamlit" ^
        !FOLIUM_DATA_ARG! ^
        --additional-hooks-dir=. ^
        --hidden-import=streamlit ^
        --hidden-import=streamlit.web.cli ^
        --hidden-import=networkx ^
        --hidden-import=pandas ^
        --hidden-import=folium ^
        --hidden-import=streamlit_folium ^
        --hidden-import=branca ^
        --hidden-import=jinja2 ^
        --collect-all streamlit ^
        --collect-submodules streamlit ^
        --copy-metadata streamlit ^
        --copy-metadata streamlit-folium ^
        run_app_standalone.py
) else (
    echo folium サポートなしでビルドします
    "%VENV_PYTHON%" -m PyInstaller ^
        --name "資源回収最適化ツール" ^
        --onefile ^
        --console ^
        --add-data "src;src" ^
        --add-data "data;data" ^
        --add-data ".streamlit;.streamlit" ^
        --additional-hooks-dir=. ^
        --hidden-import=streamlit ^
        --hidden-import=streamlit.web.cli ^
        --hidden-import=networkx ^
        --hidden-import=pandas ^
        --collect-all streamlit ^
        --collect-submodules streamlit ^
        --copy-metadata streamlit ^
        --copy-metadata streamlit-folium ^
        run_app_standalone.py
)

if errorlevel 1 (
    echo.
    echo ========================================
    echo エラー: ビルドに失敗しました。
    echo ========================================
    pause
    exit /b 1
)

echo.
echo ========================================
echo ビルド完了！
echo ========================================
echo.
echo 実行ファイル: dist\資源回収最適化ツール.exe
echo.
echo 次のステップ:
echo 1. dist\資源回収最適化ツール.exe をテスト実行
echo 2. 問題なければ配布パッケージを作成
echo.

pause
endlocal
