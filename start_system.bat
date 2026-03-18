@echo off
echo ===================================================
echo   Starting AIGC Club Planner System
echo ===================================================
echo.

echo [1/3] Checking dependencies...
python -c "import fastapi, uvicorn, openai" >nul 2>&1
if %errorlevel% neq 0 (
    echo Dependencies missing. Installing...
    pip install -r AIGC_Club_Planner/requirements.txt
) else (
    echo Dependencies ready.
)

echo.
echo [2/3] Starting Backend Server...
echo The server will run in a new window. Please do not close it.
start "AIGC Club Planner Backend" cmd /k "python -m uvicorn AIGC_Club_Planner.app.main:app --reload --port 8000"

echo.
echo [3/3] Opening Frontend Interface...
timeout /t 3 >nul
start http://localhost:8000/static/index.html

echo.
echo ===================================================
echo   System Started Successfully!
echo ===================================================
echo.
pause
