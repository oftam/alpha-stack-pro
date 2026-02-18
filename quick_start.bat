@echo off
REM ============================================================
REM ALPHA STACK PRO - Quick Start (All-in-One)
REM ============================================================
REM One click to do everything:
REM 1. Install/upgrade pip
REM 2. Install all dependencies
REM 3. Run backtest
REM ============================================================

setlocal enabledelayedexpansion

cls
echo.
echo ============================================================
echo ALPHA STACK PRO - QUICK START
echo ============================================================
echo.
echo This will:
echo  1. Install/upgrade pip
echo  2. Install all dependencies
echo  3. Run the backtest
echo.
echo (This may take 1-5 hours total)
echo.
echo Press ANY KEY to start...
pause >nul

cls
echo.
echo [STEP 1/3] Checking files...
if not exist "alpha_stack_backtest.py" (
    echo ERROR: alpha_stack_backtest.py not found!
    echo Make sure you're in the Desktop folder with all files.
    pause
    exit /b 1
)
if not exist "requirements.txt" (
    echo ERROR: requirements.txt not found!
    echo Make sure you're in the Desktop folder with all files.
    pause
    exit /b 1
)
echo ✓ Files found!

echo.
echo [STEP 2/3] Installing dependencies...
echo (This may take 2-5 minutes, please wait...)
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo ERROR: Installation failed!
    echo Please check your internet connection.
    pause
    exit /b 1
)
echo ✓ Dependencies installed!

echo.
echo [STEP 3/3] Running backtest...
echo (This may take 1-4 hours, please DON'T close this window)
echo.
python alpha_stack_backtest.py

if !errorlevel! neq 0 (
    echo.
    echo ERROR: Backtest failed!
    pause
    exit /b 1
)

echo.
echo ============================================================
echo ✓ SUCCESS! Backtest completed!
echo ============================================================
echo.
echo Results saved:
echo   - backtest_trades.csv
echo   - artifacts_meta.json
echo   - Models: lstm_model.h5, xgb_model.pkl, lr_model.pkl
echo.
echo Next steps:
echo   1. Check backtest_trades.csv for trade results
echo   2. Review the statistics above
echo   3. Consider paper trading before real money
echo.
pause
