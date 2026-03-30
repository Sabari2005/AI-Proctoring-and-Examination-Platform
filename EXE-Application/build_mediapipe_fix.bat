@echo off
REM =============================================================================
REM ObserveProctor Build Script - Fix for MediaPipe PyInstaller Bundle
REM =============================================================================
REM Usage: build.bat
REM This script rebuilds the executable with proper MediaPipe support
REM =============================================================================

echo.
echo [*] ObserveProctor Build System v2
echo [*] MediaPipe PyInstaller Fix
echo.

cd /d "%~dp0"

REM Check if we're in the right directory
if not exist "main.py" (
    echo [ERROR] main.py not found! Are you in the new_version directory?
    exit /b 1
)

REM Check if venv exists
if not exist "..\venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found at ..\venv
    echo [*] Please create it first: python -m venv ..\venv
    exit /b 1
)

echo [*] Step 1: Activating virtual environment...
call ..\venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment
    exit /b 1
)
echo [SUCCESS] Virtual environment activated

echo.
echo [*] Step 2: Verifying dependencies...
python -c "import PyQt6, cv2, mediapipe; print('[SUCCESS] All core dependencies found')" 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] Some dependencies may be missing
    echo [*] Installing dependencies...
    pip install PyQt6 opencv-python mediapipe numpy scipy sounddevice psutil wmi -q
)

echo.
echo [*] Step 3: Checking for face_landmarker.task...
if not exist "face_landmarker.task" (
    echo [ERROR] face_landmarker.task not found in current directory
    echo [*] Please download or copy it to: %cd%\face_landmarker.task
    echo [*] Expected size: ~60 MB
    exit /b 1
)
for /F "tokens=*" %%i in ('dir /b face_landmarker.task') do set "FILESIZE=%%~zi"
if %FILESIZE% gtr 50000000 (
    echo [SUCCESS] face_landmarker.task found (size: %FILESIZE% bytes)
) else (
    echo [ERROR] face_landmarker.task seems incomplete (size: %FILESIZE% bytes)
    exit /b 1
)

echo.
echo [*] Step 4: Cleaning previous builds...
if exist "build\" (
    rmdir /s /q "build" 2>nul
    echo [SUCCESS] Removed old build directory
)
if exist "dist\" (
    rmdir /s /q "dist" 2>nul
    echo [SUCCESS] Removed old dist directory
)

echo.
echo [*] Step 5: Building executable with PyInstaller...
echo [*] This may take 2-3 minutes...
echo.

pyinstaller ObserveProctor.spec

if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller build failed!
    exit /b 1
)

echo.
echo [SUCCESS] Build completed!
echo.
echo [*] Step 6: Verifying bundle...

REM Check if EXE was created
if not exist "dist\ObserveProctor.exe" (
    echo [ERROR] ObserveProctor.exe not found in dist directory
    exit /b 1
)
echo [SUCCESS] ObserveProctor.exe created

REM Check if face_landmarker.task was bundled
if not exist "dist\face_landmarker.task" (
    echo [WARNING] face_landmarker.task not in dist directory
    echo [*] Copying it manually...
    copy "face_landmarker.task" "dist\face_landmarker.task" >nul
    if %errorlevel% equ 0 (
        echo [SUCCESS] face_landmarker.task copied to dist
    ) else (
        echo [ERROR] Failed to copy face_landmarker.task
        exit /b 1
    )
)

echo.
echo ================================================================================
echo [SUCCESS] Build completed successfully!
echo ================================================================================
echo.
echo [*] Executable location: %cd%\dist\ObserveProctor.exe
echo [*] Model file included: dist\face_landmarker.task
echo.
echo [*] To test the build:
echo    1. cd "%cd%\dist"
echo    2. ObserveProctor.exe
echo.
echo [*] Expected behavior:
echo    - Application should start normally
echo    - No "MediaPipe resource loading" errors
echo    - Face detection works on Step 4 (Biometric Verification)
echo.
echo ================================================================================

pause
