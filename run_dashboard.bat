@echo off
REM Ultimate Dashboard v20 Elite - Quick Launch

echo.
echo ===================================
echo   Ultimate Dashboard v20 Elite
echo ===================================
echo.

REM Load environment variables from .env
if exist .env (
    echo Loading configuration...
    for /f "usebackq tokens=1,2 delims==" %%a in (".env") do (
        if not "%%a"=="" if not "%%b"=="" (
            set %%a=%%b
        )
    )
)

REM Check if streamlit is installed
python -c "import streamlit" 2>nul
if errorlevel 1 (
    echo ERROR: Streamlit not installed
    echo.
    echo Run setup.ps1 first:
    echo    powershell -ExecutionPolicy Bypass -File setup.ps1
    echo.
    pause
    exit /b 1
)

REM Launch dashboard
echo Starting dashboard...
echo.
streamlit run ultimate_v20_ELITE_COMPLETE.py

pause
