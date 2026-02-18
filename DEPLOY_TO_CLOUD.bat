@echo off
REM ========================================
REM   ELITE v20 - Deploy to Google Cloud VM
REM ========================================

echo.
echo ========================================
echo   ELITE v20 - Cloud Deployment
echo ========================================
echo.

SET PROJECT=deep-arch-451722-n0
SET ZONE=us-central1-f
SET VM_NAME=whale-monitor
SET REMOTE_DIR=/home/ofirt/elite_v20_production

echo Deploying to: %VM_NAME% (%ZONE%)
echo.

REM Copy all dashboard files
echo [1/6] Copying main dashboard...
gcloud compute scp elite_v20_dashboard.py %VM_NAME%:%REMOTE_DIR%/elite_v20_dashboard.py --zone=%ZONE% --project=%PROJECT%

echo [2/6] Copying multi-timeframe dashboard...
gcloud compute scp multi_timeframe_dashboard.py %VM_NAME%:%REMOTE_DIR%/multi_timeframe_dashboard.py --zone=%ZONE% --project=%PROJECT%

echo [3/6] Copying multi-timeframe class...
gcloud compute scp multi_timeframe_dashboard_ORIGINAL.py %VM_NAME%:%REMOTE_DIR%/multi_timeframe_dashboard_ORIGINAL.py --zone=%ZONE% --project=%PROJECT%

echo [4/6] Copying DUDU overlay dashboard...
gcloud compute scp dudu_overlay_dashboard.py %VM_NAME%:%REMOTE_DIR%/dudu_overlay_dashboard.py --zone=%ZONE% --project=%PROJECT%

echo [5/6] Copying DUDU overlay module...
gcloud compute scp dudu_overlay.py %VM_NAME%:%REMOTE_DIR%/dudu_overlay.py --zone=%ZONE% --project=%PROJECT%

echo [6/6] Copying Claude chat module...
gcloud compute scp claude_chat_module_ELITE_v20.py %VM_NAME%:%REMOTE_DIR%/claude_chat_module_ELITE_v20.py --zone=%ZONE% --project=%PROJECT%

echo.
echo ========================================
echo Files copied successfully!
echo ========================================
echo.

REM Optional: Copy secrets.toml (if needed for Claude in cloud)
SET /P COPY_SECRETS="Copy secrets.toml for Claude? (Y/N): "
IF /I "%COPY_SECRETS%"=="Y" (
    echo Copying secrets.toml...
    gcloud compute scp .streamlit\secrets.toml %VM_NAME%:%REMOTE_DIR%/.streamlit/secrets.toml --zone=%ZONE% --project=%PROJECT%
    echo Secrets copied!
)

echo.
echo ========================================
echo Restarting dashboards on VM...
echo ========================================
echo.

REM SSH and restart dashboards
gcloud compute ssh %VM_NAME% --zone=%ZONE% --project=%PROJECT% --command="cd %REMOTE_DIR% && pkill -f streamlit && nohup streamlit run elite_v20_dashboard.py --server.port 8510 --server.address 0.0.0.0 > /dev/null 2>&1 & nohup streamlit run multi_timeframe_dashboard.py --server.port 8511 --server.address 0.0.0.0 > /dev/null 2>&1 & nohup streamlit run dudu_overlay_dashboard.py --server.port 8512 --server.address 0.0.0.0 > /dev/null 2>&1 &"

echo.
echo ========================================
echo Deployment complete!
echo ========================================
echo.
echo Dashboards accessible at:
echo - Main Dashboard:      http://34.31.23.107:8510
echo - Multi-Timeframe:     http://34.31.23.107:8511
echo - DUDU Overlay:        http://34.31.23.107:8512
echo.
echo NOTE: Wait 10-15 seconds for dashboards to start
echo.

pause
