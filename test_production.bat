@echo off
REM Test production configuration locally
REM Copy this to a test_prod.bat or run manually

echo.
echo ========================================
echo KidZora Production Configuration Test
echo ========================================
echo.

REM Set production environment
set FLASK_CONFIG=production
set FLASK_ENV=production

REM Generate a test SECRET_KEY if not set
if not defined SECRET_KEY (
    echo.
    echo [INFO] SECRET_KEY not set. Generate one with:
    echo python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"
    echo.
)

echo.
echo [INFO] Testing with production config...
echo [INFO] Make sure these env vars are set:
echo   - SUPABASE_URL
echo   - SUPABASE_ANON_KEY
echo   - SUPABASE_SERVICE_ROLE_KEY
echo   - SECRET_KEY
echo   - MAIL_PASSWORD (new Resend key)
echo.
echo [INFO] Start test with:
echo   python kidzora/run.py
echo.
echo [INFO] Then visit http://localhost:5000
echo.
echo ========================================
