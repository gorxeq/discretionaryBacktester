@echo off
echo Starting Nifty Options Replay Backend...

:: Check if python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not found! Please install Python.
    pause
    exit /b
)

:: Activate venv if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo No venv found, using system Python...
)

:: Install dependencies if needed (brief check)
echo Checking dependencies...
pip install -r requirements.txt >nul 2>&1
pip install uvicorn >nul 2>&1

:: Start Backend in background
start "Nifty Backend" cmd /k "venv\Scripts\activate.bat && uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000"

:: Start Frontend Server
echo Starting Frontend Server...
start "Nifty Frontend" cmd /k "cd frontend-html && python -m http.server 3000 --bind 127.0.0.1"

:: Wait a few seconds for services to start
timeout /t 3 /nobreak >nul

:: Open Frontend
echo Opening Frontend...
start "" "http://127.0.0.1:3000"

echo.
echo ===================================================
echo App started! 
echo 1. Backend running in new window (do not close)
echo 2. Frontend opened in your browser
echo ===================================================
pause
