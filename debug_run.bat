@echo off
chcp 65001 > nul
echo ========================================
echo Streamlit App Debug Launcher
echo ========================================
echo.

cd /d "%~dp0"

echo Step 1: Activating virtual environment...
IF EXIST ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
    echo Virtual environment activated
) ELSE (
    echo ERROR: Virtual environment not found at .venv\Scripts\activate.bat
    pause
    exit /b 1
)

echo.
echo Step 2: Checking Python version...
python --version
echo.

echo Step 3: Checking Streamlit installation...
python -c "import streamlit; print('Streamlit version:', streamlit.__version__)"
IF ERRORLEVEL 1 (
    echo ERROR: Streamlit import failed
    echo Installing streamlit...
    pip install streamlit
)
echo.

echo Step 4: Checking required packages...
python -c "import networkx, pandas, folium; print('Core packages OK')"
IF ERRORLEVEL 1 (
    echo ERROR: Some packages missing
    echo Installing from requirements.txt...
    pip install -r requirements.txt
)
echo.

echo Step 5: Testing app imports...
python -c "import sys; sys.path.insert(0, 'src'); from services.map_generator import MapGenerator; print('App modules OK')"
IF ERRORLEVEL 1 (
    echo ERROR: App module import failed - see error above
    pause
    exit /b 1
)
echo.

echo Step 6: Launching Streamlit...
echo.
set PYTHONPATH=%CD%;%PYTHONPATH%
streamlit run "src\app.py" %*

IF ERRORLEVEL 1 (
    echo.
    echo ERROR: Streamlit failed to start
    pause
)
