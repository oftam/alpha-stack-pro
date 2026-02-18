@echo off
chcp 65001 >nul
echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║   🧬 ELITE v20 - Triple Dashboard Launcher 🚀        ║
echo ╚════════════════════════════════════════════════════════╝
echo.
echo Starting 3 dashboards simultaneously...
echo.

REM Check if virtual environment exists
if not exist ".venv" (
    if not exist "venv" (
        echo 📦 Creating virtual environment...
        python -m venv .venv
    )
)

REM Activate virtual environment
if exist ".venv" (
    echo ⚡ Activating virtual environment (.venv)...
    call .venv\Scripts\activate.bat
) else if exist "venv" (
    echo ⚡ Activating virtual environment (venv)...
    call venv\Scripts\activate.bat
)

REM Set environment
set PYTHONPATH=%PYTHONPATH%;%CD%

echo.
echo ════════════════════════════════════════════════════════
echo  📊 Launching Dashboards:
echo ════════════════════════════════════════════════════════
echo  [1] MEDALLION Dashboard  → http://localhost:8501
echo  [2] Standard Dashboard   → http://localhost:8502  
echo  [3] ULTRA ML Dashboard   → http://localhost:8503
echo ════════════════════════════════════════════════════════
echo.

REM Change to parent directory to access dashboards/
cd ..

REM Launch Dashboard 1: MEDALLION (Port 8501)
start "ELITE MEDALLION - Port 8501" cmd /k "title ELITE MEDALLION ^& streamlit run dashboards/elite_v20_dashboard_MEDALLION.py --server.port 8501 --server.headless false"

REM Wait 3 seconds
timeout /t 3 /nobreak >nul

REM Launch Dashboard 2: Standard (Port 8502)
start "ELITE Standard - Port 8502" cmd /k "title ELITE Standard ^& streamlit run dashboards/elite_v20_dashboard.py --server.port 8502 --server.headless false"

REM Wait 3 seconds
timeout /t 3 /nobreak >nul

REM Launch Dashboard 3: ULTRA ML (Port 8503)
if exist "dashboards\ultimate_dashboard_ULTRA_ML_v20_ONEFILE_SCOREBOARD_fixfetch_ELITE.py" (
    start "ELITE ULTRA ML - Port 8503" cmd /k "title ELITE ULTRA ML ^& streamlit run dashboards/ultimate_dashboard_ULTRA_ML_v20_ONEFILE_SCOREBOARD_fixfetch_ELITE.py --server.port 8503 --server.headless false"
) else (
    echo ⚠️  ULTRA ML dashboard file not found, skipping...
)

echo.
echo ✅ All dashboards launched!
echo.
echo 🌐 Open in browser:
echo    → MEDALLION: http://localhost:8501
echo    → Standard:  http://localhost:8502
echo    → ULTRA ML:  http://localhost:8503
echo.
echo 💡 To stop all dashboards: Close all CMD windows or press Ctrl+C in each
echo.
pause
