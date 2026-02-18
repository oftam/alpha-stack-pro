@echo off
chcp 65001 >nul
echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║   🧬 ELITE v20 MEDALLION - Single Dashboard Launcher  ║
echo ╚════════════════════════════════════════════════════════╝
echo.
echo Starting MEDALLION Dashboard with Claude AI...
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
echo  🧬 MEDALLION Dashboard Features:
echo ════════════════════════════════════════════════════════
echo  ✓ Claude AI Chat Integration
echo  ✓ DUDU Overlay (Dynamic Calibration)
echo  ✓ Divergence Chart (Liquidity X-Ray)
echo  ✓ Defense Protocol (Fail-Safe Checks)
echo  ✓ Full Elite v20 (DCA + Tactical)
echo ════════════════════════════════════════════════════════
echo.

REM Launch MEDALLION Dashboard
echo 🚀 Launching on http://localhost:8501
echo.

streamlit run elite_v20_dashboard_MEDALLION.py --server.port 8501 --server.headless false

echo.
echo 💰 Dashboard closed. תודה!
pause
