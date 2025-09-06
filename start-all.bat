@echo off
REM Copyright (c) 2025 Marco Pancotti
REM This file is part of ThothAI and is released under the Apache License 2.0.
REM See the LICENSE.md file in the project root for full license information.

REM Start all ThothAI services
REM This script starts Frontend, Django backend, Qdrant, and SQL Generator services

setlocal enabledelayedexpansion

echo Starting ThothAI Services...
echo =============================

REM Configuration
set SQL_GEN_DIR=frontend\sql_generator

REM Load environment variables from root .env.local
if exist ".env.local" (
    echo Loading environment from .env.local
    
    REM Simple .env parsing - read each line and set environment variables
    for /f "usebackq tokens=1,2 delims==" %%a in (".env.local") do (
        if not "%%a"=="" if not "%%a:~0,1%"=="#" (
            set "%%a=%%b"
        )
    )
    
    REM Avoid leaking a generic PORT that could clash with service-specific ports
    set PORT=
) else (
    echo Error: .env.local not found in root directory
    
    REM Try to create from template
    if exist ".env.local.template" (
        echo Creating .env.local from .env.local.template...
        copy ".env.local.template" ".env.local" >nul
        echo ^✓ .env.local created successfully
        echo.
        echo IMPORTANT: Please edit .env.local and add your API keys:
        echo   - At least one AI provider ^(OpenAI, Anthropic, Gemini, etc.^)
        echo   - DJANGO_API_KEY ^(change from default^)
        echo   - Other configuration as needed
        echo.
        echo After editing .env.local, run start-all.bat again
        exit /b 0
    ) else (
        echo Template file .env.local.template not found
        echo Please create .env.local manually or restore .env.local.template
        exit /b 1
    )
)

REM Port configuration from environment (with defaults)
if not defined FRONTEND_PORT set FRONTEND_PORT=3200
if not defined SQL_GENERATOR_PORT set SQL_GENERATOR_PORT=8180
if not defined BACKEND_PORT set BACKEND_PORT=8200
set QDRANT_PORT=6334

echo ThothAI Service Startup Script
echo ===============================
echo.
echo Step 1: Starting all services...

REM Check and start Django backend
echo Checking Django backend on port %BACKEND_PORT%...
netstat -an | find ":%BACKEND_PORT% " >nul
if %errorlevel% equ 0 (
    echo ^✓ Django backend is already running on port %BACKEND_PORT%
) else (
    echo Django backend is NOT running on port %BACKEND_PORT%
    echo Starting Django backend...
    
    if exist "backend" (
        cd backend
        
        REM Check if uv is available
        where uv >nul 2>&1
        if %errorlevel% equ 0 (
            echo Starting Django with uv...
            start /b uv run python manage.py runserver %BACKEND_PORT%
        ) else (
            echo Starting Django with Python...
            if exist ".venv\Scripts\activate.bat" (
                call .venv\Scripts\activate.bat
            )
            start /b python manage.py runserver %BACKEND_PORT%
        )
        
        cd ..
        
        REM Wait for Django to start
        echo Waiting for Django to start...
        timeout /t 5 /nobreak >nul
        
        netstat -an | find ":%BACKEND_PORT% " >nul
        if %errorlevel% neq 0 (
            echo Failed to start Django backend
            exit /b 1
        ) else (
            echo ^✓ Django backend started successfully on port %BACKEND_PORT%
        )
    ) else (
        echo Backend directory not found!
        exit /b 1
    )
)

REM Check and start Qdrant
echo Checking Qdrant on port %QDRANT_PORT%...
netstat -an | find ":%QDRANT_PORT% " >nul
if %errorlevel% equ 0 (
    echo ^✓ Qdrant is already running on port %QDRANT_PORT%
) else (
    echo Qdrant is NOT running on port %QDRANT_PORT%
    
    REM Check if Docker is available
    where docker >nul 2>&1
    if %errorlevel% neq 0 (
        echo Docker is not installed or not available
        echo Please install Docker to run Qdrant
        exit /b 1
    )
    
    REM Check if qdrant-thoth container exists
    docker ps -a --format "table {{.Names}}" | find "qdrant-thoth" >nul
    if %errorlevel% equ 0 (
        echo Starting existing qdrant-thoth container...
        docker start qdrant-thoth
    ) else (
        echo Creating and starting new qdrant-thoth container...
        docker run -d --name qdrant-thoth -p 6334:6333 -v "%cd%\qdrant_storage:/qdrant/storage:z" qdrant/qdrant
    )
    
    REM Wait for Qdrant to start
    echo Waiting for Qdrant to start...
    timeout /t 5 /nobreak >nul
    
    netstat -an | find ":%QDRANT_PORT% " >nul
    if %errorlevel% neq 0 (
        echo Failed to start Qdrant
        exit /b 1
    ) else (
        echo ^✓ Qdrant started successfully on port %QDRANT_PORT%
    )
)

REM Check and start SQL Generator
echo Checking SQL Generator on port %SQL_GENERATOR_PORT%...

REM Kill any existing processes on the port
for /f "tokens=5" %%a in ('netstat -ano ^| find ":%SQL_GENERATOR_PORT% "') do (
    taskkill /pid %%a /f >nul 2>&1
)

echo Starting SQL Generator...

REM Check if uv is available
where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: 'uv' is required to run the SQL Generator locally.
    echo Install with: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    exit /b 1
)

cd %SQL_GEN_DIR%

REM Start SQL Generator
set PORT=%SQL_GENERATOR_PORT%
start /b uv run python main.py

cd ..\..

REM Wait for SQL Generator to start
echo Waiting for SQL Generator to start...
timeout /t 5 /nobreak >nul

netstat -an | find ":%SQL_GENERATOR_PORT% " >nul
if %errorlevel% neq 0 (
    echo Failed to start SQL Generator
    exit /b 1
) else (
    echo ^✓ SQL Generator started successfully on port %SQL_GENERATOR_PORT%
)

REM Check and start Frontend
echo Checking Frontend on port %FRONTEND_PORT%...
netstat -an | find ":%FRONTEND_PORT% " >nul
if %errorlevel% equ 0 (
    echo ^✓ Frontend is already running on port %FRONTEND_PORT%
) else (
    echo Frontend is NOT running on port %FRONTEND_PORT%
    echo Starting Frontend...
    
    if exist "frontend" (
        cd frontend
        
        REM Check if node_modules exists
        if not exist "node_modules" (
            REM Check if npm is available
            where npm >nul 2>&1
            if %errorlevel% neq 0 (
                echo Error: npm is not installed. Please install Node.js ^(v20+^) and retry.
                exit /b 1
            )
            echo Installing Frontend dependencies...
            npm install
        )
        
        REM Start Frontend
        set PORT=%FRONTEND_PORT%
        start /b npm run dev
        
        cd ..
        
        REM Wait for Frontend to start
        echo Waiting for Frontend to start...
        timeout /t 5 /nobreak >nul
        
        netstat -an | find ":%FRONTEND_PORT% " >nul
        if %errorlevel% neq 0 (
            echo Failed to start Frontend
            exit /b 1
        ) else (
            echo ^✓ Frontend started successfully on port %FRONTEND_PORT%
        )
    ) else (
        echo Frontend directory not found!
        exit /b 1
    )
)

REM Display service information
echo.
echo All services started successfully!
echo ===========================================
echo Service URLs:
echo    Frontend App:     http://localhost:%FRONTEND_PORT%
echo    Backend Home:     http://localhost:%BACKEND_PORT%
echo    Django Admin:     http://localhost:%BACKEND_PORT%/admin
echo    SQL Generator:    http://localhost:%SQL_GENERATOR_PORT%
echo    API Docs:         http://localhost:%SQL_GENERATOR_PORT%/docs
echo    Qdrant API:       http://localhost:%QDRANT_PORT%
echo.
echo ===========================================
echo All services are running. Press Ctrl+C to stop.
echo ===========================================

REM Wait for user input
pause >nul

endlocal