@echo off
REM ELITE v20 - One-Click Deployment (Windows)
REM This script will install dependencies and launch the dashboard

echo ========================================
echo  ELITE v20 - PRODUCTION DEPLOYMENT
echo ========================================
echo.

echo [1/3] Checking Python...
python --version
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

echo.
echo [2/3] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [3/3] Launching ELITE v20 Dashboard...
echo.
echo Dashboard will open at: http://localhost:8501
echo.
echo Press CTRL+C to stop the dashboard
echo.

streamlit run elite_v20_dashboard.py

pause
