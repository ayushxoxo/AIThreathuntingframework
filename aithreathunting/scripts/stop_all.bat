@echo off
echo ======================================================================
echo Stopping BETH Cybersecurity Analytics Services
echo ======================================================================
echo.

echo Stopping Grafana...
taskkill /F /IM grafana-server.exe 2>nul
if %errorlevel% equ 0 (echo   [OK] Grafana stopped) else (echo   [INFO] Grafana not running)

echo Stopping Prometheus...
taskkill /F /IM prometheus.exe 2>nul
if %errorlevel% equ 0 (echo   [OK] Prometheus stopped) else (echo   [INFO] Prometheus not running)

echo Stopping Python Exporter...
echo   NOTE: this kills ALL python.exe processes, not just the exporter --
echo   close other Python work first if that matters to you.
taskkill /F /IM python.exe 2>nul
if %errorlevel% equ 0 (echo   [OK] Python processes stopped) else (echo   [INFO] No python.exe running)

echo.
echo ======================================================================
echo All services stopped
echo ======================================================================
pause
