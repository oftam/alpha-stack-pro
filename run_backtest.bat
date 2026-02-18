@echo off
REM ============================================================
REM ALPHA STACK PRO - Backtest Runner (Anaconda)
REM ============================================================
REM This script:
REM 1. Activates Anaconda environment
REM 2. Installs requirements
REM 3. Runs the backtest
REM ============================================================

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo ALPHA STACK PRO - Backtest Launcher
echo ============================================================
echo.

REM Check if we're in the right directory
if not exist "alpha_stack_backtest.py" (
    echo ERROR: alpha_stack_backtest.py not found!
    echo Please run this script from the Desktop folder containing the files.
    pause
    exit /b 1
)

echo [STEP 1] Activating Anaconda...
call conda activate base >nul 2>&1
if !errorlevel! neq 0 (
    echo WARNING: Could not activate conda. Trying system Python...
)

echo [STEP 2] Installing dependencies (this may take 2-5 minutes)...
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo ERROR: pip install failed!
    echo Please check your internet connection and try again.
    pause
    exit /b 1
)

echo.
echo [STEP 3] Running backtest (this may take 1-4 hours)...
echo.
python alpha_stack_backtest.py

if !errorlevel! neq 0 (
    echo.
    echo ERROR: Backtest failed!
    echo Check the error messages above.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo SUCCESS! Backtest completed!
echo ============================================================
echo.
echo Check the following files:
echo   - backtest_trades.csv (trade history)
echo   - artifacts_meta.json (configuration)
echo   - lstm_model.h5 (LSTM model)
echo   - xgb_model.pkl (XGBoost model)
echo   - lr_model.pkl (LogisticRegression model)
echo.
pause
