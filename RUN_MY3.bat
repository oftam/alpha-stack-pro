@echo off
chcp 65001 >nul 2>&1
REM ========================================
REM   ELITE v20 - Local 3 Dashboard Launcher
REM ========================================

cd /d C:\Users\ofirt\Documents\alpha-stack-pro

echo.
echo ========================================
echo   ELITE v20 - Local Dashboard Launcher
echo ========================================
echo.

REM Dashboard 1: ELITE v20 MEDALLION (Main)
start "ELITE v20 Main" cmd /k "cd /d C:\Users\ofirt\Documents\alpha-stack-pro && set PYTHONIOENCODING=utf-8 && py -3.11 -m streamlit run elite_v20_dashboard_MEDALLION.py --server.port=8510 --server.address=127.0.0.1 --server.headless=true"
timeout /t 3 /nobreak >nul

REM Dashboard 2: Multi-Timeframe
start "Multi-Timeframe" cmd /k "cd /d C:\Users\ofirt\Documents\alpha-stack-pro && set PYTHONIOENCODING=utf-8 && py -3.11 -m streamlit run multi_timeframe_dashboard.py --server.port=8511 --server.address=127.0.0.1 --server.headless=true"
timeout /t 3 /nobreak >nul

REM Dashboard 3: DUDU Overlay
start "DUDU Overlay" cmd /k "cd /d C:\Users\ofirt\Documents\alpha-stack-pro && set PYTHONIOENCODING=utf-8 && py -3.11 -m streamlit run dudu_overlay_dashboard.py --server.port=8512 --server.address=127.0.0.1 --server.headless=true"
timeout /t 3 /nobreak >nul

echo.
echo Waiting for dashboards to start...
timeout /t 8 /nobreak >nul

REM Open in browser
start "" "http://localhost:8510"
start "" "http://localhost:8511"
start "" "http://localhost:8512"

echo.
echo ======================================
echo   Dashboards running:
echo   - ELITE v20 Main:    http://localhost:8510
echo   - Multi-Timeframe:   http://localhost:8511
echo   - DUDU Overlay:      http://localhost:8512
echo ======================================
echo.
echo Leave the CMD windows open!
echo Close them to stop the dashboards.
echo.

pause
