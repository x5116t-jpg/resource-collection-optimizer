@echo off
chcp 65001 > nul
REM ========================================
REM Streamlit Cloud デプロイ準備スクリプト
REM ========================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ========================================
echo Streamlit Cloud デプロイ準備
echo ========================================
echo.

REM ステップ1: Gitインストール確認
echo [1/5] Gitインストール確認中...
git --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ❌ Gitがインストールされていません。
    echo.
    echo 以下からダウンロードしてインストールしてください：
    echo https://git-scm.com/downloads
    echo.
    pause
    exit /b 1
)
echo ✅ Git確認完了

REM ステップ2: Git設定確認
echo.
echo [2/5] Git設定確認中...
git config --global user.name >nul 2>&1
if errorlevel 1 (
    echo.
    echo ⚠️ Gitユーザー名が未設定です。
    echo.
    set /p GIT_NAME="あなたの名前を入力してください: "
    git config --global user.name "!GIT_NAME!"
    echo.
    set /p GIT_EMAIL="メールアドレスを入力してください: "
    git config --global user.email "!GIT_EMAIL!"
    echo.
    echo ✅ Git設定完了
) else (
    for /f "delims=" %%i in ('git config --global user.name') do set CURRENT_NAME=%%i
    for /f "delims=" %%i in ('git config --global user.email') do set CURRENT_EMAIL=%%i
    echo ✅ Git設定済み（名前: !CURRENT_NAME!）
)

REM ステップ3: Gitリポジトリ初期化
echo.
echo [3/5] Gitリポジトリ初期化中...
if exist ".git" (
    echo ℹ️ Gitリポジトリは既に存在します。
) else (
    git init
    if errorlevel 1 (
        echo ❌ Gitリポジトリの初期化に失敗しました。
        pause
        exit /b 1
    )
    echo ✅ Gitリポジトリ初期化完了
)

REM ステップ4: ファイルをステージング
echo.
echo [4/5] ファイルをステージング中...
git add .
if errorlevel 1 (
    echo ❌ ファイルのステージングに失敗しました。
    pause
    exit /b 1
)
echo ✅ ファイルステージング完了

REM ステップ5: コミット
echo.
echo [5/5] コミット作成中...
git commit -m "Initial commit for Streamlit Cloud deployment" >nul 2>&1
if errorlevel 1 (
    echo ℹ️ コミット済み、または変更がありません。
) else (
    echo ✅ コミット作成完了
)

echo.
echo ========================================
echo ✅ デプロイ準備が完了しました！
echo ========================================
echo.
echo 次のステップ:
echo.
echo 1. GitHubにアクセス: https://github.com/new
echo 2. リポジトリ名: resource-collection-optimizer
echo 3. Publicを選択（⚠️重要）
echo 4. Create repositoryをクリック
echo.
echo 5. 表示されたコマンドの中から以下を実行:
echo.
echo    git remote add origin https://github.com/[あなたのユーザー名]/resource-collection-optimizer.git
echo    git branch -M main
echo    git push -u origin main
echo.
echo 6. Streamlit Cloudにデプロイ: https://streamlit.io/cloud
echo.
echo 詳細は STREAMLIT_CLOUD_DEPLOY.md を参照してください。
echo.

pause
endlocal
