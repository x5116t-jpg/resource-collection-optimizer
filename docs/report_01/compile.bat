@echo off
chcp 65001 > nul
echo ========================================
echo LaTeX報告書コンパイルスクリプト
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 1回目のplatexコンパイル実行中...
platex main.tex
if errorlevel 1 (
    echo エラー: 1回目のplatexコンパイルに失敗しました
    pause
    exit /b 1
)

echo.
echo [2/3] 2回目のplatexコンパイル実行中（目次・相互参照更新）...
platex main.tex
if errorlevel 1 (
    echo エラー: 2回目のplatexコンパイルに失敗しました
    pause
    exit /b 1
)

echo.
echo [3/3] PDFファイル生成中...
dvipdfmx main.dvi
if errorlevel 1 (
    echo エラー: PDF生成に失敗しました
    pause
    exit /b 1
)

echo.
echo ========================================
echo コンパイル完了！
echo 出力ファイル: main.pdf
echo ========================================
echo.

if exist main.pdf (
    echo PDFファイルを開きますか？ (Y/N)
    choice /c YN /n /m "[Y] はい / [N] いいえ: "
    if errorlevel 2 goto end
    if errorlevel 1 start main.pdf
)

:end
pause
