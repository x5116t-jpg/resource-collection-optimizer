# ResouceCollection_05 配布パッケージ作成スクリプト

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "配布パッケージ作成スクリプト" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

$source = "D:\py\Resource Collection\ResouceCollection_05"
$destination = "D:\py\Resource Collection\ResouceCollection_05_Distribution"

# 除外するフォルダとファイル
$excludeFolders = @('.venv', '.pytest_cache', 'SuperClaude_Setup', '__pycache__')
$excludeFiles = @('*.pyc', '.DS_Store', 'Thumbs.db', 'create_distribution.ps1')

Write-Host "[1/4] 配布フォルダを準備中..." -ForegroundColor Yellow

# 既存の配布フォルダがある場合の確認
if (Test-Path $destination) {
    $response = Read-Host "既存の配布フォルダが見つかりました。削除して再作成しますか? (Y/N)"
    if ($response -eq 'Y' -or $response -eq 'y') {
        Remove-Item $destination -Recurse -Force
        Write-Host "✅ 既存フォルダを削除しました" -ForegroundColor Green
    } else {
        Write-Host "❌ 処理を中止しました" -ForegroundColor Red
        exit
    }
}

# フォルダ構造作成
New-Item -ItemType Directory -Path "$destination\project" -Force | Out-Null
New-Item -ItemType Directory -Path "$destination\superclaude" -Force | Out-Null
Write-Host "✅ フォルダ構造作成完了" -ForegroundColor Green

Write-Host ""
Write-Host "[2/4] プロジェクトファイルをコピー中..." -ForegroundColor Yellow

# プロジェクトファイルをコピー（除外ファイル以外）
Get-ChildItem $source -Directory | Where-Object {
    $_.Name -notin $excludeFolders
} | ForEach-Object {
    Write-Host "  コピー中: $($_.Name)" -ForegroundColor Gray
    Copy-Item $_.FullName -Destination "$destination\project\$($_.Name)" -Recurse -Force
}

# ルートディレクトリのファイルをコピー
Get-ChildItem $source -File | Where-Object {
    $excludeMatch = $false
    foreach ($pattern in $excludeFiles) {
        if ($_.Name -like $pattern) {
            $excludeMatch = $true
            break
        }
    }
    -not $excludeMatch
} | ForEach-Object {
    Write-Host "  コピー中: $($_.Name)" -ForegroundColor Gray
    Copy-Item $_.FullName -Destination "$destination\project\$($_.Name)" -Force
}

Write-Host "✅ プロジェクトファイルコピー完了" -ForegroundColor Green

Write-Host ""
Write-Host "[3/4] SuperClaude設定をコピー中..." -ForegroundColor Yellow

# SuperClaude_Setupの内容をsuperclaudeフォルダにコピー
if (Test-Path "$source\SuperClaude_Setup") {
    Copy-Item "$source\SuperClaude_Setup\*" -Destination "$destination\superclaude" -Recurse -Force

    # インストーラー名を変更
    if (Test-Path "$destination\superclaude\Windows用インストール.bat") {
        Rename-Item "$destination\superclaude\Windows用インストール.bat" "installer.bat"
    }
    if (Test-Path "$destination\superclaude\Mac用インストール.command") {
        Rename-Item "$destination\superclaude\Mac用インストール.command" "installer.command"
    }

    Write-Host "✅ SuperClaude設定コピー完了" -ForegroundColor Green
} else {
    Write-Host "⚠️  SuperClaude_Setupフォルダが見つかりません" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[4/4] 統合セットアップスクリプトを作成中..." -ForegroundColor Yellow

# setup.bat を作成（ルートディレクトリに配置）
$setupBatContent = @'
@echo off
chcp 65001 > nul
echo.
echo ====================================
echo ResouceCollection_05
echo 統合セットアップ
echo ====================================
echo.
echo このスクリプトは以下を自動的に行います:
echo 1. Python環境の確認
echo 2. 仮想環境の作成
echo 3. 依存関係のインストール
echo 4. SuperClaude設定の適用
echo.
pause

REM ステップ1: Python確認
echo.
echo [1/4] Python環境を確認中...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ エラー: Pythonがインストールされていません。
    echo.
    echo Python 3.8以上をインストールしてください:
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)
echo ✅ Python が見つかりました
python --version

REM ステップ2: 仮想環境作成
echo.
echo [2/4] 仮想環境を作成中...
cd project
if exist ".venv" (
    echo ⚠️  既存の仮想環境が見つかりました
    choice /C YN /M "削除して再作成しますか"
    if errorlevel 2 goto skip_venv
    rmdir /s /q .venv
)
python -m venv .venv
if %errorlevel% neq 0 (
    echo ❌ 仮想環境の作成に失敗しました
    pause
    exit /b 1
)
echo ✅ 仮想環境作成完了

:skip_venv

REM ステップ3: 依存関係インストール
echo.
echo [3/4] 依存関係をインストール中...
call .venv\Scripts\activate.bat
if exist "requirements.txt" (
    pip install -r requirements.txt
    echo ✅ 依存関係インストール完了
) else (
    echo ⚠️  requirements.txt が見つかりません
)

REM ステップ4: SuperClaude設定
echo.
echo [4/4] SuperClaude設定を適用中...
cd ..\superclaude
if exist "installer.bat" (
    call installer.bat
) else (
    echo ⚠️  SuperClaudeインストーラーが見つかりません
)
cd ..\project

echo.
echo ====================================
echo ✅✅✅ セットアップ完了！ ✅✅✅
echo ====================================
echo.
echo 次のステップ:
echo 1. Claude Code を起動
echo 2. この project フォルダを開く
echo 3. 開発を開始！
echo.
pause
'@

Set-Content -Path "$destination\setup.bat" -Value $setupBatContent -Encoding UTF8

Write-Host "✅ setup.bat 作成完了" -ForegroundColor Green

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "✅ 配布パッケージ作成完了！" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "配布パッケージの場所:" -ForegroundColor White
Write-Host "  $destination" -ForegroundColor Cyan
Write-Host ""
Write-Host "次のステップ:" -ForegroundColor White
Write-Host "  1. README.md などのドキュメントを追加" -ForegroundColor Gray
Write-Host "  2. テスト実行" -ForegroundColor Gray
Write-Host "  3. ZIP圧縮して配布" -ForegroundColor Gray
Write-Host ""

Read-Host "終了するには Enter キーを押してください"
