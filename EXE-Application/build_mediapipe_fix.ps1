# =============================================================================
# ObserveProctor Build Script - Fix for MediaPipe PyInstaller Bundle
# =============================================================================
# Usage: powershell -ExecutionPolicy Bypass -File build_mediapipe_fix.ps1
# This script rebuilds the executable with proper MediaPipe support
# =============================================================================

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"

Write-Host "`n" -ForegroundColor White
Write-Host "[*] ObserveProctor Build System v2" -ForegroundColor Cyan
Write-Host "[*] MediaPipe PyInstaller Fix v2" -ForegroundColor Cyan
Write-Host "`n" -ForegroundColor White

# Change to script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Check if we're in the right directory
if (-not (Test-Path "main.py")) {
    Write-Host "[ERROR] main.py not found! Are you in the new_version directory?" -ForegroundColor Red
    exit 1
}

# Check if venv exists
$venvPath = "..\venv\Scripts\activate.ps1"
if (-not (Test-Path $venvPath)) {
    Write-Host "[ERROR] Virtual environment not found at ..\venv" -ForegroundColor Red
    Write-Host "[*] Please create it first: python -m venv ..\venv" -ForegroundColor Yellow
    exit 1
}

# Step 1: Activate virtual environment
Write-Host "[*] Step 1: Activating virtual environment..." -ForegroundColor Yellow
try {
    & $venvPath
    Write-Host "[SUCCESS] Virtual environment activated" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Failed to activate virtual environment: $_" -ForegroundColor Red
    exit 1
}

# Step 2: Verify dependencies
Write-Host "`n[*] Step 2: Verifying dependencies..." -ForegroundColor Yellow
$missingDeps = @()

$deps = @("PyQt6", "cv2", "mediapipe", "numpy", "scipy", "sounddevice", "psutil", "wmi")
foreach ($dep in $deps) {
    python -c "import $dep" 2>$null
    if ($LASTEXITCODE -ne 0) {
        $missingDeps += $dep
    }
}

if ($missingDeps.Count -eq 0) {
    Write-Host "[SUCCESS] All core dependencies found" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Missing dependencies: $($missingDeps -join ', ')" -ForegroundColor Yellow
    Write-Host "[*] Installing missing dependencies..." -ForegroundColor Yellow
    pip install $missingDeps --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[SUCCESS] Dependencies installed" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Failed to install dependencies" -ForegroundColor Red
        exit 1
    }
}

# Step 3: Verify face_landmarker.task
Write-Host "`n[*] Step 3: Checking for face_landmarker.task..." -ForegroundColor Yellow
if (-not (Test-Path "face_landmarker.task")) {
    Write-Host "[ERROR] face_landmarker.task not found!" -ForegroundColor Red
    Write-Host "[*] Expected location: $(Get-Location)\face_landmarker.task" -ForegroundColor Cyan
    Write-Host "[*] Expected size: ~60 MB" -ForegroundColor Cyan
    exit 1
}

$modelFile = Get-Item "face_landmarker.task"
$modelSize = $modelFile.Length
$modelSizeMB = [math]::Round($modelSize / 1MB, 2)

if ($modelSize -gt 50MB) {
    Write-Host "[SUCCESS] face_landmarker.task found ($modelSizeMB MB)" -ForegroundColor Green
} else {
    Write-Host "[ERROR] face_landmarker.task seems incomplete ($modelSizeMB MB)" -ForegroundColor Red
    exit 1
}

# Step 4: Clean previous builds
Write-Host "`n[*] Step 4: Cleaning previous builds..." -ForegroundColor Yellow
$dirsToRemove = @("build", "dist")
foreach ($dir in $dirsToRemove) {
    if (Test-Path $dir) {
        Remove-Item -Path $dir -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "[SUCCESS] Removed old $dir directory" -ForegroundColor Green
    }
}

# Step 5: Build with PyInstaller
Write-Host "`n[*] Step 5: Building executable with PyInstaller..." -ForegroundColor Yellow
Write-Host "[*] This may take 2-3 minutes..." -ForegroundColor Cyan
Write-Host ""

# Ensure ObserveProctor.spec exists
if (-not (Test-Path "ObserveProctor.spec")) {
    Write-Host "[ERROR] ObserveProctor.spec not found! Cannot proceed." -ForegroundColor Red
    exit 1
}

pyinstaller ObserveProctor.spec 2>&1 | Tee-Object -Variable buildOutput | ForEach-Object {
    Write-Host $_
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] PyInstaller build failed!" -ForegroundColor Red
    Write-Host "[*] Check the output above for details" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "[SUCCESS] Build completed!" -ForegroundColor Green

# Step 6: Verify bundle
Write-Host "`n[*] Step 6: Verifying bundle..." -ForegroundColor Yellow

if (-not (Test-Path "dist\ObserveProctor.exe")) {
    Write-Host "[ERROR] ObserveProctor.exe not found in dist directory" -ForegroundColor Red
    exit 1
}
Write-Host "[SUCCESS] ObserveProctor.exe created" -ForegroundColor Green

# Ensure face_landmarker.task is in dist
if (-not (Test-Path "dist\face_landmarker.task")) {
    Write-Host "[WARNING] face_landmarker.task not in dist directory" -ForegroundColor Yellow
    Write-Host "[*] Copying it manually..." -ForegroundColor Cyan
    Copy-Item "face_landmarker.task" "dist\face_landmarker.task" -ErrorAction SilentlyContinue
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[SUCCESS] face_landmarker.task copied to dist" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Failed to copy face_landmarker.task" -ForegroundColor Red
        exit 1
    }
}

# Success summary
Write-Host "`n" -ForegroundColor White
Write-Host "=" * 80 -ForegroundColor Green
Write-Host "[SUCCESS] Build completed successfully!" -ForegroundColor Green
Write-Host "=" * 80 -ForegroundColor Green

$exePath = Join-Path (Get-Location) "dist\ObserveProctor.exe"
$modelPath = Join-Path (Get-Location) "dist\face_landmarker.task"

Write-Host ""
Write-Host "[*] Executable location: $exePath" -ForegroundColor Cyan
Write-Host "[*] Model file included: $modelPath" -ForegroundColor Cyan
Write-Host "[*] Build directory size: $('{0:N0}' -f (Get-ChildItem -Path dist -Recurse | Measure-Object -Property Length -Sum).Sum) bytes" -ForegroundColor Cyan

Write-Host ""
Write-Host "[*] To test the build:" -ForegroundColor Yellow
Write-Host "   1. cd dist" -ForegroundColor Cyan
Write-Host "   2. .\ObserveProctor.exe" -ForegroundColor Cyan

Write-Host ""
Write-Host "[*] Expected behavior:" -ForegroundColor Yellow
Write-Host "   - Application should start normally" -ForegroundColor Cyan
Write-Host "   - No 'MediaPipe resource loading' errors in console" -ForegroundColor Cyan
Write-Host "   - Face detection works on Step 4 (Biometric Verification)" -ForegroundColor Cyan
Write-Host "   - Gaze detection displays real-time metrics" -ForegroundColor Cyan

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Green
Write-Host ""
