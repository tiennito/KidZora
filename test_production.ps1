# Test production configuration locally

Write-Host ""
Write-Host "========================================"
Write-Host "KidZora Production Configuration Test"
Write-Host "========================================"
Write-Host ""

# Set production environment
$env:FLASK_CONFIG = "production"
$env:FLASK_ENV = "production"

# Check for SECRET_KEY
if (-not $env:SECRET_KEY) {
    Write-Host ""
    Write-Host "[INFO] SECRET_KEY not set. Generate one with:" -ForegroundColor Yellow
    Write-Host "python -c `"import secrets; print(secrets.token_hex(32))`"" -ForegroundColor Cyan
    Write-Host ""
}

Write-Host ""
Write-Host "[INFO] Testing with production config..." -ForegroundColor Green
Write-Host "[INFO] Make sure these env vars are set:" -ForegroundColor Yellow
Write-Host "  - SUPABASE_URL"
Write-Host "  - SUPABASE_ANON_KEY"
Write-Host "  - SUPABASE_SERVICE_ROLE_KEY"
Write-Host "  - SECRET_KEY"
Write-Host "  - MAIL_PASSWORD (new Resend key)"
Write-Host ""
Write-Host "[INFO] Start test with:" -ForegroundColor Cyan
Write-Host "  python kidzora/run.py"
Write-Host ""
Write-Host "[INFO] Then visit http://localhost:5000" -ForegroundColor Cyan
Write-Host ""
Write-Host "========================================"
Write-Host ""
