# ====================================================================
# 🗄️ Archive Legacy Files - Part 2
# ====================================================================
# This moves remaining legacy files to archive/
# Run AFTER the main cleanup script
# ====================================================================

$ErrorActionPreference = "Stop"
$BaseDir = "C:\Users\ofirt\Documents\alpha-stack-pro"
$ArchiveDir = Join-Path $BaseDir "archive"

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "Archive Legacy Files - Part 2" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

# Ensure archive exists
if (-not (Test-Path $ArchiveDir)) {
    New-Item -ItemType Directory -Path $ArchiveDir -Force | Out-Null
}

$moved = 0
$errors = 0

# Files to KEEP in root (don't archive these)
$keepFiles = @(
    ".env", ".env.txt", "requirements.txt", "__init__.py",
    "config.toml", "secrets.toml", "Dockerfile", "docker-compose.yml",
    "CLEANUP.ps1", "CLEANUP_README.md",
    "dudu_overlay.py",  # Core file - keep in root
    "divergence_chart.py",  # Core file
    "claude_chat_module_ELITE_v20.py"  # Core file (if not in modules)
)

# Directories to KEEP (don't archive)
$keepDirs = @(
    "dashboards", "scripts", "docs", "archive", "modules",
    ".venv", ".streamlit", "files", "files (50)",
    "core", "utils", "config", "strategies", "data", "logs"
)

Write-Host "Moving legacy  Python files..." -ForegroundColor Green

# Get all .py files in root
$pyFiles = Get-ChildItem -Path $BaseDir -Filter "*.py" -File | Where-Object {
    $_.Name -notin $keepFiles
}

foreach ($file in $pyFiles) {
    try {
        $dest = Join-Path $ArchiveDir $file.Name
        Move-Item -Path $file.FullName -Destination $dest -Force
        $moved++
    }
    catch {
        $errors++
    }
}

Write-Host "   Moved $moved Python files" -ForegroundColor White

Write-Host ""
Write-Host "Moving legacy BAT/PS1 files..." -ForegroundColor Green

# Get all .bat and .ps1 files (except CLEANUP.ps1)
$scriptFiles = Get-ChildItem -Path $BaseDir -Include "*.bat", "*.ps1" -File | Where-Object {
    $_.Name -notin $keepFiles -and $_.Name -ne "CLEANUP.ps1"
}

$scriptMoved = 0
foreach ($file in $scriptFiles) {
    try {
        $dest = Join-Path $ArchiveDir $file.Name
        Move-Item -Path $file.FullName -Destination $dest -Force
        $scriptMoved++
    }
    catch {
        $errors++
    }
}

Write-Host "   Moved $scriptMoved script files" -ForegroundColor White

Write-Host ""
Write-Host "Moving legacy MD files..." -ForegroundColor Green

# Get all .md files in root (keep only main ones)
$keepMd = @("README.md", "CLEANUP_README.md", "mathematical_foundation.md", "implementation_plan.md")
$mdFiles = Get-ChildItem -Path $BaseDir -Filter "*.md" -File | Where-Object {
    $_.Name -notin $keepMd
}

$mdMoved = 0
foreach ($file in $mdFiles) {
    try {
        $dest = Join-Path $ArchiveDir $file.Name
        Move-Item -Path $file.FullName -Destination $dest -Force
        $mdMoved++
    }
    catch {
        $errors++
    }
}

Write-Host "   Moved $mdMoved MD files" -ForegroundColor White

Write-Host ""
Write-Host "Moving other files..." -ForegroundColor Green

# Move HTML, JSON, CSV, PNG, ZIP files
$extensions = @("*.html", "*.json", "*.csv", "*.png", "*.zip", "*.txt", "*.sh", "*.joblib", "*.sqlite", "*.log", "*.jsonl")
$otherMoved = 0

foreach ($ext in $extensions) {
    $files = Get-ChildItem -Path $BaseDir -Filter $ext -File | Where-Object {
        $_.Name -notin $keepFiles
    }
    
    foreach ($file in $files) {
        try {
            $dest = Join-Path $ArchiveDir $file.Name
            if (-not (Test-Path $dest)) {
                Move-Item -Path $file.FullName -Destination $dest -Force
                $otherMoved++
            }
        }
        catch {
            $errors++
        }
    }
}

Write-Host "   Moved $otherMoved other files" -ForegroundColor White

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "Archive Complete!" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Total moved: $($moved + $scriptMoved + $mdMoved + $otherMoved) files" -ForegroundColor White
if ($errors -gt 0) {
    Write-Host "Errors: $errors (files in use or already moved)" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "Check your directory now - it should be much cleaner!" -ForegroundColor Green
