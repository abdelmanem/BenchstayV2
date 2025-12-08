@echo off
setlocal

REM Change to this script's directory (hotelkit folder)
cd /d "%~dp0"

REM Prefer a virtualenv Python if present; otherwise fall back to system Python
set PY_CMD=python
if exist "..\venv\Scripts\python.exe" set PY_CMD=..\venv\Scripts\python.exe
if exist "..\.venv\Scripts\python.exe" set PY_CMD=..\.venv\Scripts\python.exe
if exist ".venv\Scripts\python.exe" set PY_CMD=.venv\Scripts\python.exe

echo Running Hotelkit Excel template generator...
%PY_CMD% hotelkit_excel_template.py
if errorlevel 1 (
    echo.
    echo Generation failed. Ensure Python and the 'openpyxl' package are installed.
) else (
    echo.
    echo Done. File created: hotelkit_template.xlsx
)

echo.
pause


