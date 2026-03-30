@echo off
REM Start server in production-aligned mode

echo.
echo ============================================================================
echo Observe Proctoring - Server
echo ============================================================================
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo [ERROR] Virtual environment not found. Run: python -m venv venv
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

echo [INFO] Starting Mock Server on port 8080...
echo [INFO] Using values from server\.env
echo.

set "ENV_FILE=%CD%\server\.env"

REM Start mock server
python server\mock_server.py

pause
