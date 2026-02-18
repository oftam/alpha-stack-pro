# Alpha-Stack-Pro Cleanup Script
$ErrorActionPreference = "Stop"
$Timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$BaseDir = "C:\Users\ofirt\Documents\alpha-stack-pro"
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "Alpha-Stack-Pro Cleanup" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
# Step 1: Backup
Write-Host ""
Write-Host "Step 1: Creating backup..." -ForegroundColor Green
$BackupZip = "C:\Users\ofirt\Documents\alpha-stack-pro_BACKUP_$Timestamp.zip"
Compress-Archive -Path $BaseDir -DestinationPath $BackupZip -Force
Write-Host "   Backup saved: $BackupZip" -ForegroundColor Green
# Step 2: Create directories
Write-Host ""
Write-Host "Step 2: Creating directories..." -ForegroundColor Green
$NewDirs = @("dashboards", "scripts", "docs", "archive")
foreach ($dir in $NewDirs) {
    $path = Join-Path $BaseDir $dir
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
        Write-Host "   Created: $dir/" -ForegroundColor Green
    } else {
        Write-Host "   Exists: $dir/" -ForegroundColor Gray
    }
}
# Step 3: Move dashboards
Write-Host ""
Write-Host "Step 3: Moving dashboards..." -ForegroundColor Green
$Dashboards = @(
    "elite_v20_dashboard_MEDALLION.py",
    "elite_v20_dashboard.py",
    "dudu_overlay_dashboard.py",
    "multi_timeframe_dashboard.py",
    "ultimate_dashboard_ULTRA_ML_v20_ONEFILE_SCOREBOARD_fixfetch_ELITE.py"
)
foreach ($file in $Dashboards) {
    $src = Join-Path $BaseDir $file
    $dst = Join-Path "$BaseDir\dashboards" $file
    if (Test-Path $src) {
        Move-Item -Path $src -Destination $dst -Force
        Write-Host "   Moved: $file" -ForegroundColor Green
    }
}
# Step 4: Move scripts
Write-Host ""
Write-Host "Step 4: Moving scripts..." -ForegroundColor Green
$Scripts = @("RUN_ALL_DASHBOARDS.bat", "RUN_MEDALLION.bat", "run_elite_v20.bat")
foreach ($file in $Scripts) {
    $src = Join-Path $BaseDir $file
    $dst = Join-Path "$BaseDir\scripts" $file
    if (Test-Path $src) {
        Move-Item -Path $src -Destination $dst -Force
        Write-Host "   Moved: $file" -ForegroundColor Green
    }
}
Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "Cleanup complete!" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backup: $BackupZip" -ForegroundColor White
Write-Host "Next: Manually move old files to archive/" -ForegroundColor Yellow