@echo off
REM ========================================
REM 配布パッケージ作成スクリプト
REM ========================================

setlocal
cd /d "%~dp0"

echo.
echo ========================================
echo 配布パッケージを作成しています...
echo ========================================
echo.

REM 実行ファイルの存在確認
if not exist "dist\資源回収最適化ツール.exe" (
    echo エラー: 実行ファイルが見つかりません。
    echo 先に build_standalone.bat を実行してください。
    pause
    exit /b 1
)

REM バージョン番号の入力
set /p VERSION=バージョン番号を入力してください [例: 1.0]:
if "%VERSION%"=="" set VERSION=1.0

REM 配布ディレクトリの作成
set DIST_DIR=ResourceOptimizer_v%VERSION%
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
mkdir "%DIST_DIR%"

echo.
echo ファイルをコピーしています...

REM 実行ファイルのコピー
copy "dist\資源回収最適化ツール.exe" "%DIST_DIR%\" >nul
if errorlevel 1 (
    echo エラー: 実行ファイルのコピーに失敗しました。
    pause
    exit /b 1
)

REM dataディレクトリのコピー
echo dataディレクトリをコピー中...
xcopy /E /I /Y data "%DIST_DIR%\data" >nul
if errorlevel 1 (
    echo 警告: dataディレクトリのコピーに失敗しました。
)

REM READMEの作成
echo READMEを作成中...
(
echo ============================================================
echo 資源回収ルート最適化ツール - 使い方ガイド v%VERSION%
echo ============================================================
echo.
echo 【起動方法】
echo 1. 「資源回収最適化ツール.exe」をダブルクリック
echo 2. 数秒〜10秒程度でブラウザが自動的に開きます
echo 3. ブラウザが開かない場合は、手動で以下にアクセス:
echo    http://localhost:8501
echo.
echo 【終了方法】
echo 1. ブラウザを閉じる
echo 2. コマンドプロンプトウィンドウで Ctrl+C を押す
echo    または、ウィンドウを閉じる
echo.
echo 【基本的な使い方】
echo 1. 地図上で車庫を選択（緑色の点）
echo 2. 回収地点を選択（青色の点）
echo    - クリック後、資源種別と回収量を入力
echo 3. 集積場所を選択（赤色の点）
echo 4. 車種情報を確認・編集
echo 5. 「最適化を実行」ボタンをクリック
echo 6. 結果を確認（ルート・コスト・距離など）
echo.
echo 【トラブルシューティング】
echo.
echo Q: 「Windowsによって保護されました」と表示される
echo A: 「詳細情報」をクリック → 「実行」をクリックしてください。
echo    （初回のみ表示されます）
echo.
echo Q: ブラウザが開かない
echo A: 以下を確認してください:
echo    - ファイアウォール設定でポート8501がブロックされていないか
echo    - 既に別のアプリケーションがポート8501を使用していないか
echo    - 手動で http://localhost:8501 にアクセスしてみてください
echo.
echo Q: 動作が遅い
echo A: 以下を確認してください:
echo    - 回収地点の数を減らす（10箇所以下を推奨）
echo    - PCのメモリやCPU使用率を確認
echo    - データファイルのサイズを確認
echo.
echo Q: エラーが表示される
echo A: 以下を確認してください:
echo    - dataフォルダが実行ファイルと同じ場所にあるか
echo    - data/processedフォルダに必要なJSONファイルがあるか
echo    - data/road_network_*.json ファイルが存在するか
echo.
echo 【必須ファイル】
echo 以下のファイルが必要です:
echo - 資源回収最適化ツール.exe
echo - data/road_network_*.json
echo - data/processed/compatibility.json
echo - data/processed/resources.json
echo - data/processed/vehicles.json
echo - data/processed/supplement.json
echo.
echo 【システム要件】
echo - OS: Windows 10 以降（64bit）
echo - メモリ: 4GB以上推奨
echo - ディスク空き容量: 500MB以上
echo - インターネット接続: 不要（地図表示のみオンライン推奨）
echo.
echo 【データの更新】
echo - data/processedフォルダ内のJSONファイルを編集することで、
echo   車両情報や資源種別をカスタマイズできます。
echo - 道路ネットワークを追加する場合は、data/フォルダに
echo   新しいroad_network_*.jsonファイルを配置してください。
echo.
echo 【バージョン情報】
echo バージョン: %VERSION%
echo ビルド日: %DATE% %TIME%
echo.
echo ============================================================
) > "%DIST_DIR%\README.txt"

echo.
echo 配布パッケージの作成が完了しました！
echo.
echo 作成されたパッケージ: %DIST_DIR%
echo.
echo 次のステップ:
echo 1. %DIST_DIR% フォルダの内容を確認
echo 2. 「資源回収最適化ツール.exe」を実行してテスト
echo 3. 問題なければ、フォルダをZIP圧縮して配布
echo.

REM ZIP作成の提案
echo ZIP圧縮しますか？ [Y/N]
set /p CREATE_ZIP=
if /i "%CREATE_ZIP%"=="Y" (
    echo.
    echo ZIP圧縮を実行しています...

    REM PowerShellでZIP作成
    powershell -Command "Compress-Archive -Path '%DIST_DIR%' -DestinationPath '%DIST_DIR%.zip' -Force"

    if errorlevel 1 (
        echo 警告: ZIP圧縮に失敗しました。
        echo 手動でフォルダを圧縮してください。
    ) else (
        echo.
        echo ZIP圧縮完了: %DIST_DIR%.zip
    )
)

echo.
echo ========================================
echo 完了！
echo ========================================
pause
endlocal
