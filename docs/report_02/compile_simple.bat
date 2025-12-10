@echo off
echo ========================================
echo Simple LaTeX Compilation (ignoring warnings)
echo ========================================
echo.

REM First compilation
echo [1/3] First compilation...
platex -kanji=utf8 -interaction=nonstopmode main.tex

REM Second compilation (for TOC and references)
echo [2/3] Second compilation...
platex -kanji=utf8 -interaction=nonstopmode main.tex

REM Third compilation (ensure all references are resolved)
echo [2.5/3] Third compilation...
platex -kanji=utf8 -interaction=nonstopmode main.tex

REM Convert to PDF
echo [3/3] Converting DVI to PDF...
dvipdfmx main.dvi

if exist main.pdf (
    echo.
    echo ========================================
    echo SUCCESS! PDF generated: main.pdf
    echo ========================================
    echo.
    echo Opening PDF file...
    start main.pdf
) else (
    echo.
    echo ========================================
    echo ERROR: PDF file was not generated
    echo ========================================
    echo Please check the log file: main.log
)

echo.
pause
