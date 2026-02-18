@echo off
cd C:\Users\ofirt\Documents\alpha-stack-pro

REM Start Agent in new window
start cmd /k python alpha_stack_binance_only.py --mode paper

REM Start Dashboard in new window
timeout /t 2 /nobreak
start cmd /k python dashboard.py

REM Start Alerts in new window
timeout /t 2 /nobreak
start cmd /k python alerts.py

echo.
echo =========================================
echo All systems started!
echo Agent: Terminal 1
echo Dashboard: Terminal 2 (GUI)
echo Alerts: Terminal 3
echo =========================================
pause
