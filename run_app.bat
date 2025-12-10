@echo off
chcp 65001 > nul
setlocal
REM Launch the Streamlit application for the resource collection tool.

REM Move to script directory to ensure Python can resolve the ``src`` package.
cd /d "%~dp0"

REM Activate virtual environment if present.
IF EXIST "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) ELSE IF EXIST ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

set PYTHONPATH=%CD%;%PYTHONPATH%
streamlit run "src\app.py" %*
endlocal
