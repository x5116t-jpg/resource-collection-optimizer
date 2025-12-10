@echo off
echo ========================================
echo LaTeX Report Compilation Script
echo ========================================
echo.

REM Check if platex is available
where platex >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: platex not found!
    echo Please install TeX Live or W32TeX
    pause
    exit /b 1
)

echo Compiling main.tex with platex...
echo.

REM First compilation
echo [1/3] First compilation...
platex -kanji=utf8 -interaction=nonstopmode main.tex
if %ERRORLEVEL% GTR 1 (
    echo Fatal error during first compilation!
    pause
    exit /b 1
)
if %ERRORLEVEL% EQU 1 (
    echo Warning: Some warnings occurred, but continuing...
)

REM Second compilation (for TOC)
echo [2/3] Second compilation (updating TOC)...
platex -kanji=utf8 -interaction=nonstopmode main.tex
if %ERRORLEVEL% GTR 1 (
    echo Fatal error during second compilation!
    pause
    exit /b 1
)
if %ERRORLEVEL% EQU 1 (
    echo Warning: Some warnings occurred, but continuing...
)

REM Convert to PDF
echo [3/3] Converting DVI to PDF...
dvipdfmx main.dvi
if %ERRORLEVEL% NEQ 0 (
    echo Error during PDF conversion!
    echo Checking if DVI file exists...
    if exist main.dvi (
        echo DVI file exists, trying alternate conversion...
        dvipdfmx -f ptex-ipaex.map main.dvi
    )
    if %ERRORLEVEL% NEQ 0 (
        pause
        exit /b 1
    )
)

echo.
echo ========================================
echo Compilation successful!
echo Output: main.pdf
echo ========================================
echo.

REM Clean up auxiliary files (optional)
echo Cleaning up auxiliary files...
del main.aux main.log main.toc main.dvi 2>nul

echo.
echo Done!
pause
