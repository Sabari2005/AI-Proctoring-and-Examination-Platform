@echo off
REM Build Observe Proctoring EXE (production pipeline)

setlocal enabledelayedexpansion

echo.
echo ================================================================================
echo Observe Proctoring - Production Build
echo ================================================================================
echo.

REM Activate local venv
call .\venv\Scripts\activate.bat
if errorlevel 1 (
    echo Error: Failed to activate virtual environment
    pause
    exit /b 1
)

echo [1/2] Virtual environment activated
echo.

REM Build using hardened Python pipeline
echo [2/2] Running production builder...
python build.py --clean
if errorlevel 1 (
    echo Error: production build failed
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo ✓ Build Complete!
echo ================================================================================
echo.
echo Output File:
echo   - Main Application: dist\ObserveProctor.exe
echo.
echo To run the application:
echo   1. Start server: python server\mock_server.py
echo   2. Run application:   dist\ObserveProctor.exe
echo.
pause
