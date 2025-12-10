@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0"

echo PyInstallerをインストールしています...
echo.

REM 仮想環境のPythonパスを設定
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

echo 仮想環境が見つかりました
echo パス: %VENV_PYTHON%
echo.

REM PyInstallerをインストール
echo PyInstallerをインストール中...
"%VENV_PYTHON%" -m pip install pyinstaller

if errorlevel 1 (
    echo.
    echo エラー: PyInstallerのインストールに失敗しました。
    pause
    exit /b 1
)

echo.
echo ========================================
echo インストール完了！
echo ========================================
echo.

REM バージョン確認
echo PyInstallerのバージョン:
"%VENV_PYTHON%" -m PyInstaller --version

echo.
pause
endlocal
