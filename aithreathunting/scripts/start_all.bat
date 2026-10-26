@echo off
REM Starts the real XGBoost exporter + Prometheus + Grafana.
REM
REM EDIT THESE TWO LINES if your Prometheus / Grafana folders are named
REM differently or live somewhere else. The defaults assume the layout this
REM project was originally developed with: Prometheus and Grafana unzipped
REM as sibling folders next to the repo itself, e.g.
REM
REM   some-folder\
REM     aithreathunting\              <- this repo (REPO_ROOT)
REM     prometheus-3.9.1.windows-amd64\prometheus-3.9.1.windows-amd64\
REM     grafana-enterprise_12.3.3_.../grafana-12.3.3\bin\
REM
REM If you installed Prometheus/Grafana as Windows services instead, you
REM don't need this script at all -- just start the exporter below and
REM make sure your existing Prometheus config scrapes 127.0.0.1:8001.

setlocal
set "REPO_ROOT=%~dp0.."
set "PROMETHEUS_DIR=%REPO_ROOT%\..\prometheus-3.9.1.windows-amd64\prometheus-3.9.1.windows-amd64"
set "GRAFANA_DIR=%REPO_ROOT%\..\grafana-enterprise_12.3.3_21957728731_windows_amd64\grafana-12.3.3\bin"

echo ======================================================================
echo BETH Cybersecurity Analytics - HDBSCAN + XGBoost Pipeline
echo ======================================================================
echo Repo root:        %REPO_ROOT%
echo Prometheus dir:    %PROMETHEUS_DIR%
echo Grafana dir:       %GRAFANA_DIR%
echo.
echo Starting all services...
echo.

echo [1/3] Starting XGBoost Prometheus Exporter...
start "XGBoost Exporter" cmd /k "cd /d "%REPO_ROOT%" && (if exist venv\Scripts\activate.bat call venv\Scripts\activate) && python prometheus_exporter_xgboost.py"
timeout /t 5 /nobreak >nul

echo [2/3] Starting Prometheus Server...
if exist "%PROMETHEUS_DIR%\prometheus.exe" (
    start "Prometheus" cmd /k "cd /d "%PROMETHEUS_DIR%" && prometheus.exe --config.file=prometheus.yml"
) else (
    echo   [SKIP] Prometheus not found at %PROMETHEUS_DIR%
    echo          Edit PROMETHEUS_DIR at the top of this script, or start your own Prometheus
    echo          pointed at 127.0.0.1:8001.
)
timeout /t 5 /nobreak >nul

echo [3/3] Starting Grafana Server...
if exist "%GRAFANA_DIR%\grafana-server.exe" (
    start "Grafana" cmd /k "cd /d "%GRAFANA_DIR%" && grafana-server.exe"
) else (
    echo   [SKIP] Grafana not found at %GRAFANA_DIR%
    echo          Edit GRAFANA_DIR at the top of this script, or start your own Grafana instance.
)
timeout /t 10 /nobreak >nul

echo.
echo ======================================================================
echo Startup sequence complete (see above for anything skipped)
echo ======================================================================
echo.
start http://localhost:3000
echo.
echo Services:
echo   - Exporter:   http://localhost:8001/metrics
echo   - Prometheus: http://localhost:9090
echo   - Grafana:    http://localhost:3000
echo.
echo Press any key to close this window (started services keep running)
pause >nul
