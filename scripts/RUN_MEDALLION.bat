@echo off
chcp 65001 >nul

REM ===========================================================
REM  🧬 ELITE v20 MEDALLION - Quick Launch
REM ===========================================================

echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║        🧬 ELITE v20 MEDALLION Dashboard               ║
echo ╚════════════════════════════════════════════════════════╝
echo.

REM Navigate to script directory
cd /d "%~dp0"

REM Set Python path
set PYTHONPATH=%PYTHONPATH%;%CD%

echo 🚀 Launching MEDALLION Dashboard...
echo 📍 URL: http://localhost:8501
echo.
echo Features:
echo   ✓ Genotype Model (Manifold DNA)
echo   ✓ Bayesian Model (Confidence)
echo   ✓ DUDU Overlay (Dynamic Calibration)
echo   ✓ Divergence Chart (Liquidity X-Ray)
echo   ✓ Claude AI Chat
echo   ✓ Defense Protocol
echo.

REM Launch Streamlit (dashboard is in ../dashboards/)
cd ..
streamlit run dashboards/elite_v20_dashboard_MEDALLION.py --server.port 8501 --server.headless false

echo.
echo Dashboard closed.
pause
