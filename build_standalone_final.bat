@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ========================================
echo Build executable file...
echo ========================================
echo.

REM Set virtual environment path
set VENV_PYTHON=%~dp0.venv\Scripts\python.exe
set VENV_PIP=%~dp0.venv\Scripts\pip.exe

REM Check virtual environment
if not exist "%VENV_PYTHON%" (
    echo ERROR: Virtual environment not found.
    echo Path: %VENV_PYTHON%
    echo.
    echo Please run recreate_venv_windows.bat first.
    pause
    exit /b 1
)

echo Virtual environment found
echo Path: %VENV_PYTHON%

REM Check PyInstaller
"%VENV_PYTHON%" -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo.
    echo PyInstaller not installed.
    echo Install now? [Y/N]
    set /p INSTALL_PYINSTALLER=
    if /i "!INSTALL_PYINSTALLER!"=="Y" (
        echo Installing PyInstaller...
        "%VENV_PYTHON%" -m pip install pyinstaller
        if errorlevel 1 (
            echo ERROR: Failed to install PyInstaller.
            pause
            exit /b 1
        )
    ) else (
        echo Build cancelled.
        pause
        exit /b 1
    )
)

REM Get streamlit_folium path using pip show
echo.
echo Detecting streamlit_folium...
for /f "tokens=2" %%i in ('"%VENV_PIP%" show streamlit-folium ^| findstr "Location"') do set SITE_PACKAGES=%%i

if defined SITE_PACKAGES (
    set FOLIUM_PATH=!SITE_PACKAGES!\streamlit_folium
    if exist "!FOLIUM_PATH!" (
        echo streamlit_folium found: !FOLIUM_PATH!
        set FOLIUM_DATA_ARG=--add-data "!FOLIUM_PATH!;streamlit_folium"
        set BUILD_WITH_FOLIUM=1
    ) else (
        echo WARNING: streamlit_folium directory not found
        set BUILD_WITH_FOLIUM=0
    )
) else (
    echo WARNING: streamlit-folium not installed
    set BUILD_WITH_FOLIUM=0
)

echo.
echo Cleaning old build artifacts...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist "資源回収最適化ツール.spec" del "資源回収最適化ツール.spec"

echo.
echo ========================================
echo Starting PyInstaller build...
echo (This may take several minutes)
echo ========================================
echo.

REM Build with PyInstaller
if "!BUILD_WITH_FOLIUM!"=="1" (
    echo Building WITH folium map support
    "%VENV_PYTHON%" -m PyInstaller ^
        --name "資源回収最適化ツール" ^
        --onefile ^
        --console ^
        --add-data "src;src" ^
        --add-data "data;data" ^
        --add-data ".streamlit;.streamlit" ^
        !FOLIUM_DATA_ARG! ^
        --additional-hooks-dir=. ^
        --hidden-import=streamlit ^
        --hidden-import=streamlit.web.cli ^
        --hidden-import=networkx ^
        --hidden-import=pandas ^
        --hidden-import=folium ^
        --hidden-import=streamlit_folium ^
        --hidden-import=branca ^
        --hidden-import=jinja2 ^
        --collect-all streamlit ^
        --collect-submodules streamlit ^
        --copy-metadata streamlit ^
        --copy-metadata streamlit-folium ^
        run_app_standalone.py
) else (
    echo Building WITHOUT folium map support
    "%VENV_PYTHON%" -m PyInstaller ^
        --name "資源回収最適化ツール" ^
        --onefile ^
        --console ^
        --add-data "src;src" ^
        --add-data "data;data" ^
        --add-data ".streamlit;.streamlit" ^
        --additional-hooks-dir=. ^
        --hidden-import=streamlit ^
        --hidden-import=streamlit.web.cli ^
        --hidden-import=networkx ^
        --hidden-import=pandas ^
        --collect-all streamlit ^
        --collect-submodules streamlit ^
        --copy-metadata streamlit ^
        run_app_standalone.py
)

if errorlevel 1 (
    echo.
    echo ========================================
    echo ERROR: Build failed
    echo ========================================
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo Executable: dist\資源回収最適化ツール.exe
echo.
echo Next steps:
echo 1. Test run: dist\資源回収最適化ツール.exe
echo 2. If successful, create distribution package
echo.

pause
endlocal
