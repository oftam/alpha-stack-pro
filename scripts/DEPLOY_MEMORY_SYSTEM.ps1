# 🚀 Elite v20 - Memory System Deployment Script
# ================================================
# Run this to deploy SQL schema to Supabase

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "Elite v20 - Memory System Deployment" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# Check if .env.memory exists
if (!(Test-Path ".env.memory")) {
    Write-Host "❌ .env.memory not found!" -ForegroundColor Red
    Write-Host "Please create it with SUPABASE_URL and SUPABASE_KEY" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Step 1: Installing dependencies..." -ForegroundColor Green
pip install supabase cohere python-dotenv --quiet

Write-Host ""
Write-Host "Step 2: Testing Supabase connection..." -ForegroundColor Green
python -c "from modules.supabase_client import get_client; client = get_client(); print('✅ Connection successful!')"

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "⚠️  MANUAL STEP REQUIRED" -ForegroundColor Yellow
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Please deploy the SQL schema manually:" -ForegroundColor White
Write-Host ""
Write-Host "1. Go to: https://supabase.com/dashboard" -ForegroundColor White
Write-Host "2. Select your project: alpha-stack-memory" -ForegroundColor White
Write-Host "3. Click: SQL Editor" -ForegroundColor White
Write-Host "4. Open file: docs/SUPABASE_SCHEMA.sql" -ForegroundColor White
Write-Host "5. Copy and paste the entire file" -ForegroundColor White
Write-Host "6. Click: Run" -ForegroundColor White
Write-Host ""
Write-Host "Then press any key to continue..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

Write-Host ""
Write-Host "Step 3: Testing database schema..." -ForegroundColor Green
python modules/supabase_client.py

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "✅ Deployment Complete!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "1. Get Cohere API key: https://dashboard.cohere.com" -ForegroundColor White
Write-Host "2. Add to .env.memory: COHERE_API_KEY=your-key" -ForegroundColor White
Write-Host "3. Run MEDALLION dashboard - it will auto-log signals!" -ForegroundColor White
Write-Host ""
