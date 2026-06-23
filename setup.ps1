# Setup script for Plickers Python project (Windows PowerShell)
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Plickers Python Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Create virtual environment if not exists
if (-Not (Test-Path ".venv")) {
    Write-Host "[1/4] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
    Write-Host "✓ Virtual environment created at .venv" -ForegroundColor Green
} else {
    Write-Host "[1/4] Virtual environment already exists" -ForegroundColor Green
}

# Step 2: Activate virtual environment
Write-Host "[2/4] Activating virtual environment..." -ForegroundColor Yellow
& .venv\Scripts\Activate.ps1

# Step 3: Upgrade pip
Write-Host "[3/4] Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Step 4: Install dependencies
Write-Host "[4/4] Installing main dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To install development dependencies (optional):" -ForegroundColor Yellow
Write-Host "  pip install -r requirements-dev.txt"
Write-Host ""
Write-Host "To run tests:" -ForegroundColor Yellow
Write-Host "  python test_all.py"
Write-Host ""
Write-Host "To start web app:" -ForegroundColor Yellow
Write-Host "  python run_web.py"
Write-Host ""
Write-Host "To start standalone scanner:" -ForegroundColor Yellow
Write-Host "  python run_scanner.py"
Write-Host ""
