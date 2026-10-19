# PowerShell script to launch all 3 RetainIQ services in separate windows
$root = $PSScriptRoot

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host " Starting RetainIQ Services (ML + Backend + Frontend)" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

# 1. FastAPI ML Service
Write-Host "[1/3] Starting Python FastAPI ML Service on port 8001..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root'; python -m uvicorn ml_service.main:app --host 127.0.0.1 --port 8001"

Start-Sleep -Seconds 3

# 2. Node Express Backend
Write-Host "[2/3] Starting Express Backend on port 8000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; node server.js"

Start-Sleep -Seconds 2

# 3. Vite React Frontend
Write-Host "[3/3] Starting React Vite Frontend on port 5173..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"

Start-Sleep -Seconds 3

Write-Host "`nAll services started successfully!" -ForegroundColor Green
Write-Host "Frontend:   http://localhost:5173" -ForegroundColor Green
Write-Host "Backend:    http://localhost:8000" -ForegroundColor Green
Write-Host "ML Service: http://localhost:8001" -ForegroundColor Green

Start-Process "http://localhost:5173"
