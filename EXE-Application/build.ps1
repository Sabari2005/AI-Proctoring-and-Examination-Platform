# Build Observe Proctoring EXE (production pipeline)

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "Observe Proctoring - Production Build" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Activate local venv
$venvPath = ".\venv\Scripts\Activate.ps1"
if (-Not (Test-Path $venvPath)) {
    Write-Host "[✗] Error: Virtual environment not found at $venvPath" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

try {
    & $venvPath
    Write-Host "[✓] Virtual environment activated" -ForegroundColor Green
} catch {
    Write-Host "[✗] Error: Failed to activate virtual environment" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""

# Step 1: Build using hardened Python pipeline
Write-Host "[1/2] Running production builder..." -ForegroundColor Yellow
python build.py --clean
if ($LASTEXITCODE -ne 0) {
    Write-Host "[✗] Error: production build failed" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "[✓] EXE built successfully" -ForegroundColor Green

Write-Host ""

# Success message
Write-Host "[2/2] Finalizing build..." -ForegroundColor Yellow
Write-Host ""
Write-Host "================================================================================" -ForegroundColor Green
Write-Host "✓ Build Complete!" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Output File:" -ForegroundColor Cyan
Write-Host "  - Main Application: dist\ObserveProctor.exe" -ForegroundColor White
Write-Host ""
Write-Host "To run the application:" -ForegroundColor Cyan
Write-Host "  1. Start server: python server\mock_server.py" -ForegroundColor White
Write-Host "  2. Run application:   .\dist\ObserveProctor.exe" -ForegroundColor White
Write-Host ""

Read-Host "Press Enter to exit"
