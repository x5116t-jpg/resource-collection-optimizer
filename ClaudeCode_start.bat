@echo off

rem PowerShellを起動し、その中でコマンドを実行します。
rem -NoExit: コマンド実行後もPowerShellウィンドウを開いたままにするオプションです。
rem Set-Location -Path '%~dp0': バッチファイルがあるディレクトリに移動します。
rem claude code: 移動後に指定のコマンドを実行します。

powershell.exe -NoExit -Command "Set-Location -Path '%~dp0'; claude code"