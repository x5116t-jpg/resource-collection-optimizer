@echo off
REM ========================================
REM クイックテスト - 環境チェック
REM ========================================

setlocal
cd /d "%~dp0"

echo.
echo ========================================
echo 環境チェックを実行しています...
echo ========================================
echo.

REM 仮想環境のパスを設定
set VENV_PYTHON=%~dp0.venv\Scripts\python.exe

REM 仮想環境の確認
echo [1/5] 仮想環境の確認...
if not exist "%VENV_PYTHON%" (
    echo エラー: 仮想環境が見つかりません
    echo 確認してください: %VENV_PYTHON%
    goto :error
)
echo 仮想環境が見つかりました
echo パス: %VENV_PYTHON%

REM Pythonバージョンの確認
echo.
echo [2/5] Pythonバージョンの確認...
"%VENV_PYTHON%" --version
if errorlevel 1 goto :error

REM Streamlitの確認
echo.
echo [3/5] Streamlitの確認...
"%VENV_PYTHON%" -c "import streamlit; print('Streamlit:', streamlit.__version__)"
if errorlevel 1 (
    echo エラー: Streamlitが見つかりません
    goto :error
)

REM NetworkXの確認
echo.
echo [4/5] NetworkXの確認...
"%VENV_PYTHON%" -c "import networkx; print('NetworkX:', networkx.__version__)"
if errorlevel 1 (
    echo エラー: NetworkXが見つかりません
    goto :error
)

REM PyInstallerの確認
echo.
echo [5/5] PyInstallerの確認...
"%VENV_PYTHON%" -c "import PyInstaller; print('PyInstaller:', PyInstaller.__version__)" 2>nul
if errorlevel 1 (
    echo PyInstallerがインストールされていません
    echo install_pyinstaller.bat を実行してください
) else (
    echo PyInstallerがインストールされています
)

echo.
echo ========================================
echo 環境チェック完了！
echo ========================================
echo.
echo 次のステップ:
echo 1. PyInstallerをインストール: install_pyinstaller.bat
echo 2. ビルドを実行: build_standalone.bat
echo.
goto :end

:error
echo.
echo ========================================
echo エラーが発生しました
echo ========================================
pause
exit /b 1

:end
pause
endlocal
