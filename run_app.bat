@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

REM =============================================================
REM Resource Collection Optimizer launcher (double-click friendly)
REM - Always pause on error so the window does not close immediately
REM - Always write a startup log under .\logs\
REM =============================================================

cd /d "%~dp0"

set "LOG_DIR=%CD%\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1
set "LOG_FILE=%LOG_DIR%\run_app_startup_%RANDOM%.log"

echo ============================================================ > "%LOG_FILE%"
echo [%DATE% %TIME%] run_app.bat started >> "%LOG_FILE%"
echo WorkingDir=%CD% >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"

call :log "Detecting Python..."
set "PYTHON_CMD="
where python >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=python"

if not defined PYTHON_CMD (
  where py >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=py"
)

if not defined PYTHON_CMD (
  call :log "[ERROR] Python was not found. Install Python 3.9+ and rerun this script."
  echo [ERROR] Python was not found. Install Python 3.9+ and rerun this script.
  echo.
  echo Log: "%LOG_FILE%"
  echo.
  pause
  exit /b 1
)

call :log "PYTHON_CMD=%PYTHON_CMD%"

REM Detect venv
set "VENV_DIR="
if exist ".venv\Scripts\activate.bat" set "VENV_DIR=.venv"
if not defined VENV_DIR if exist "venv\Scripts\activate.bat" set "VENV_DIR=venv"

if defined VENV_DIR goto :venv_ready
call :log "Creating virtual environment (.venv)..."
echo [INFO] Creating virtual environment (.venv)...
"%PYTHON_CMD%" -m venv .venv >> "%LOG_FILE%" 2>&1
if errorlevel 1 goto :error
set "VENV_DIR=.venv"
:venv_ready

call :log "Activating venv: %VENV_DIR%"
call "%VENV_DIR%\Scripts\activate.bat" >> "%LOG_FILE%" 2>&1
if errorlevel 1 goto :error

REM Prefer UTF-8 output from Python (for readable logs)
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

REM Check dependencies (install if streamlit missing)
call :log "Checking dependencies (streamlit)..."
"%PYTHON_CMD%" -m pip show streamlit >nul 2>&1
if not errorlevel 1 goto :deps_ok
call :log "Streamlit not found. Installing requirements..."
echo [INFO] Installing required packages (first run may take a while)...
"%PYTHON_CMD%" -m pip install --upgrade pip >> "%LOG_FILE%" 2>&1
if errorlevel 1 goto :error
"%PYTHON_CMD%" -m pip install -r requirements.txt >> "%LOG_FILE%" 2>&1
if errorlevel 1 goto :error
:deps_ok

REM Local imports
set "PYTHONPATH=%CD%;%PYTHONPATH%"

call :log "Starting Streamlit: src\\app.py"
echo [INFO] Starting Streamlit. Press Ctrl+C to stop.
echo [INFO] Log: "%LOG_FILE%"
echo.

REM Run Streamlit (this should block while the server is running)
"%PYTHON_CMD%" -m streamlit run "src\app.py" %* >> "%LOG_FILE%" 2>&1
set "EXIT_CODE=!ERRORLEVEL!"

echo.
if not "!EXIT_CODE!"=="0" (
  echo [ERROR] Streamlit exited with error (exit code !EXIT_CODE!)
  echo [ERROR] Check the log: "%LOG_FILE%"
) else (
  echo [INFO] Streamlit shut down cleanly
)
echo.
pause
endlocal
exit /b !EXIT_CODE!

:log
REM Usage: call :log "message"
>> "%LOG_FILE%" echo [%DATE% %TIME%] %~1
exit /b 0

:error
call :log "[ERROR] Initialisation failed (errorlevel=%ERRORLEVEL%)."
echo.
echo [ERROR] Initialisation failed. Check the log:
echo   "%LOG_FILE%"
echo.
pause
endlocal
exit /b 1


