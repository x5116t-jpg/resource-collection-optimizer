@echo off

rem バッチファイルが置かれているディレクトリに移動します。
cd /d %~dp0

rem wslを起動し、その中で codex を実行後、ターミナルを開いたままにします。
rem codex; exec bash -i : codex 実行後、対話型シェルを開き直します。
wsl bash -c "codex; exec bash -i"