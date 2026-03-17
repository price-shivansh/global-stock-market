@echo off
echo Starting Indian Options Signal Dashboard...
echo.

:: Fix: Clear SSLKEYLOGFILE to prevent aiohttp PermissionError on virtual volumes
:: (Python 3.14 + aiohttp tries to write SSL key log to this path and fails)
set SSLKEYLOGFILE=

:: Start Backend
echo Starting Backend Server on port 8000...
start "Backend" cmd /k "set SSLKEYLOGFILE=&& cd /d %~dp0backend && python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"

:: Wait for backend to start
timeout /t 5 /nobreak > nul

:: Start Frontend
echo Starting Frontend Server...
start "Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ========================================
echo Servers Starting...
echo Backend API:  http://localhost:8000
echo Frontend:     http://localhost:3000
echo API Docs:     http://localhost:8000/docs
echo News Export:  http://localhost:8000/api/news/export
echo ========================================
echo.
echo Press any key to exit this window...
pause > nul
 