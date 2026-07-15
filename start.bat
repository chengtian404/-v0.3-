@echo off
title DataFinderAgentOS v0.1
echo ======================================
echo   DataFinderAgentOS v0.1
echo ======================================
echo.

netstat -ano 2>nul | findstr "TCP" | findstr ":10010 " | findstr "LISTENING" >nul
if %errorlevel% equ 0 (
    echo [WARN] Port 10010 is already in use!
    echo Please visit http://localhost:10010/
    echo If you cannot access it, close all Python processes and retry.
    echo.
    pause
    exit /b 1
)

if not exist ".\venv\Scripts\python.exe" (
    echo [1/3] Creating virtual environment...
    python -m venv venv
    .\venv\Scripts\python.exe -m pip install -r requirements.txt -q
) else (
    echo [1/3] Environment is ready
)

echo [2/3] Checking dependencies...
.\venv\Scripts\python.exe -m pip install -r requirements.txt -q

echo [3/3] Initializing admin account...
.\venv\Scripts\python.exe make_admin.py
echo.

echo ======================================
echo   Server started!
echo   Preferred frontend: http://localhost:10010/
echo   Preferred backend:  http://localhost:10010/admin/
echo   If port 10010 is unavailable, use the address printed by app.py.
echo   Admin account: admin / 123456
echo ======================================
echo.
echo Press Ctrl+C to stop
echo.

.\venv\Scripts\python.exe app.py
pause
