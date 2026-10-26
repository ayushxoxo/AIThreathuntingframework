@echo off
REM Creates a virtual environment in the repo root and installs dependencies.
REM Safe to run from anywhere -- it resolves the repo root relative to this
REM script's own location (scripts\..), so it no longer assumes a specific
REM machine or username.

setlocal
set "REPO_ROOT=%~dp0.."
cd /d "%REPO_ROOT%"

echo ========================================
echo Creating Virtual Environment
echo ========================================
echo Repo root: %REPO_ROOT%

echo.
echo Creating venv...
python -m venv venv

echo.
echo Activating venv...
call venv\Scripts\activate.bat

echo.
echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ========================================
echo Virtual Environment Ready!
echo ========================================
echo.
echo To activate in future, run:
echo   scripts\activate_venv.bat
echo.
echo To run Stage 1 (clustering):
echo   python run_clustering.py
echo.
pause
