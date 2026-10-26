@echo off
REM Activates the repo's venv and drops you into a shell at the repo root.
setlocal
set "REPO_ROOT=%~dp0.."
cd /d "%REPO_ROOT%"
call venv\Scripts\activate.bat
echo Virtual environment activated! (repo root: %REPO_ROOT%)
echo.
cmd /k
