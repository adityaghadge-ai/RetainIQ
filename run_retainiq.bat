@echo off
TITLE RetainIQ Platform Launcher
echo ===================================================
echo Starting RetainIQ - Employee Attrition Platform
echo ===================================================

cd /d "%~dp0"

echo [1/3] Starting Python FastAPI ML Service (Port 8001)...
start "RetainIQ - ML Service (:8001)" cmd /k "python -m uvicorn ml_service.main:app --host 127.0.0.1 --port 8001"

timeout /t 3 /nobreak >nul

echo [2/3] Starting Node.js Express Backend (Port 8000)...
start "RetainIQ - Express Backend (:8000)" cmd /k "cd backend && node server.js"

timeout /t 2 /nobreak >nul

echo [3/3] Starting Vite React Frontend (Port 5173)...
start "RetainIQ - Vite Frontend (:5173)" cmd /k "cd frontend && npm run dev"

timeout /t 3 /nobreak >nul

echo.
echo All services launched!
echo Opening http://localhost:5173 in browser...
start http://localhost:5173

echo ===================================================
echo RetainIQ is running:
echo   - Frontend:   http://localhost:5173
echo   - Backend:    http://localhost:8000
echo   - ML Service: http://localhost:8001
echo ===================================================
pause
