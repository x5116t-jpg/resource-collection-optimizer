@echo off

rem cursorの実行ファイルパス
set CURSOR_PATH="C:\Users\t\AppData\Local\Programs\cursor\Cursor.exe"

rem バッチファイルが置かれているディレクトリのフルパスを取得
set TARGET_DIR="%~dp0"

rem 指定されたパスのcursorを起動し、バッチファイルのあるディレクトリを引数として渡します。
start "" %CURSOR_PATH% %TARGET_DIR%

rem **このpause行を削除します**