@echo off
REM Setup script for Plickers Python project (Windows Command Prompt)
echo ========================================
echo   Plickers Python Setup
echo ========================================
echo.

REM Step 1: Create virtual environment if not exists
if not exist .venv (
    echo [1/4] Creating virtual environment...
    python -m venv .venv
    echo Virtual environment created at .venv
) else (
    echo [1/4] Virtual environment already exists
)

REM Step 2: Activate virtual environment
echo [2/4] Activating virtual environment...
call .venv\Scripts\activate.bat

REM Step 3: Upgrade pip
echo [3/4] Upgrading pip...
python -m pip install --upgrade pip

REM Step 4: Install dependencies
echo [4/4] Installing main dependencies...
pip install -r requirements.txt

echo.
echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo To install development dependencies ^(optional^):
echo   pip install -r requirements-dev.txt
echo.
echo To run tests:
echo   python test_all.py
echo.
echo To start web app:
echo   python run_web.py
echo.
echo To start standalone scanner:
echo   python run_scanner.py
echo.
