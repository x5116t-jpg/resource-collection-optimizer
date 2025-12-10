@echo off
chcp 65001 > nul
echo ========================================
echo LaTeX中間ファイルクリーンアップ
echo ========================================
echo.

cd /d "%~dp0"

echo 以下のファイルを削除します:
echo - *.aux (補助ファイル)
echo - *.log (ログファイル)
echo - *.toc (目次ファイル)
echo - *.dvi (DVIファイル)
echo - *.out (アウトラインファイル)
echo.

set /p confirm="実行しますか？ (Y/N): "
if /i not "%confirm%"=="Y" (
    echo キャンセルしました
    pause
    exit /b 0
)

echo.
echo クリーンアップ中...

del /q *.aux 2>nul
del /q *.log 2>nul
del /q *.toc 2>nul
del /q *.dvi 2>nul
del /q *.out 2>nul

echo.
echo クリーンアップ完了！
echo.
pause
