@echo off
REM Copyright (c) 2025 Marco Pancotti
REM This file is part of Thoth and is released under the Apache License 2.0.
REM See the LICENSE.md file in the project root for full license information.

REM ThothAI Interactive Installer with FastAPI
REM Allows database selection and manages both backend and UI containers

setlocal EnableDelayedExpansion

echo.
echo ===================================
echo     ThothAI Interactive Installer
echo ===================================
echo.

REM Check if we are in the correct directory
if not exist "pyproject.toml" (
    echo ERROR: pyproject.toml not found in current directory
    echo    Make sure you are in the thoth_be root directory
    exit /b 1
)

REM Check if uv is installed
echo Checking uv installation...
where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo uv not found. Installing uv permanently...
    
    REM Install uv using PowerShell with permanent PATH configuration
    powershell -NoProfile -ExecutionPolicy Bypass -Command "& {irm https://astral.sh/uv/install.ps1 | iex}"
    
    REM The PowerShell installer above should add uv to PATH permanently
    REM But we also add it to current session to continue installation
    set "PATH=%LOCALAPPDATA%\uv\bin;%PATH%"
    
    REM Additionally ensure it's in the system PATH (requires admin rights)
    REM Try to add to user PATH if not admin
    echo Adding uv to permanent PATH...
    setx PATH "%LOCALAPPDATA%\uv\bin;%PATH%" >nul 2>&1
    
    REM Verify installation in current session
    where uv >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo WARNING: uv was installed but not found in current session.
        echo          Please close this window and run install.bat again.
        echo          Or manually add %LOCALAPPDATA%\uv\bin to your PATH.
        pause
        exit /b 1
    )
    
    echo uv installed successfully and added to PATH permanently!
    echo Note: You may need to restart your terminal for permanent PATH changes.
) else (
    echo uv is already installed
)

REM Install Python dependencies
echo.
echo Installing Python dependencies...
uv sync --extra dev

if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    exit /b 1
)

echo Dependencies installed

REM Check if _env file exists, create from template if not
if not exist "_env" (
    echo.
    echo Creating _env file from template...
    
    if exist "_env.template" (
        copy "_env.template" "_env" >nul
        echo _env file created from template
        echo WARNING: Please edit _env file and add your API keys
    ) else (
        echo ERROR: _env.template not found. Please create _env file manually.
        exit /b 1
    )
)

REM Check if Docker is installed
echo.
echo Checking Docker installation...
where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not installed. Please install Docker Desktop first.
    exit /b 1
)

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running. Please start Docker Desktop.
    exit /b 1
)

echo Docker is installed and running

REM Setup Docker network and volumes
echo.
echo Setting up Docker network and volumes...

REM Create network if not exists
docker network ls | findstr "thothnet" >nul 2>&1
if %errorlevel% neq 0 (
    docker network create thothnet
    echo Created Docker network: thothnet
) else (
    echo Docker network thothnet already exists
)

REM Create shared volume if not exists
docker volume ls | findstr "thoth-shared-data" >nul 2>&1
if %errorlevel% neq 0 (
    docker volume create thoth-shared-data
    echo Created Docker volume: thoth-shared-data
) else (
    echo Docker volume thoth-shared-data already exists
)

REM Copy dev_databases to Docker volume if they exist
if exist "data\dev_databases" (
    echo.
    echo Checking Docker volume contents...
    
    REM Get current directory with proper escaping for Docker
    set "CURRENT_DIR=%CD%"
    set "CURRENT_DIR=!CURRENT_DIR:\=/!"
    
    REM First, list what's actually in the volume for debugging
    echo Current Docker volume contents:
    docker run --rm -v thoth-shared-data:/target alpine sh -c "ls -la /target/ 2>/dev/null || echo 'Volume is empty'"
    
    REM Check if dev_databases really exists in volume (more reliable check)
    docker run --rm -v thoth-shared-data:/target alpine sh -c "test -d /target/dev_databases && echo EXISTS || echo NOT_EXISTS" > temp_check.txt
    set /p CHECK_RESULT=<temp_check.txt
    del temp_check.txt
    
    if "!CHECK_RESULT!"=="NOT_EXISTS" (
        echo dev_databases not found in volume, copying now...
        
        REM Copy dev_databases directory
        docker run --rm -v "!CURRENT_DIR!/data:/source:ro" -v thoth-shared-data:/target alpine sh -c "cp -r /source/dev_databases /target/ && echo 'COPY_SUCCESS' || echo 'COPY_FAILED'"
        
        REM Verify the copy worked
        docker run --rm -v thoth-shared-data:/target alpine sh -c "test -d /target/dev_databases && echo 'Verified: dev_databases copied successfully' || echo 'ERROR: dev_databases copy failed'"
        
        REM Also copy db.sqlite3 if it exists
        if exist "data\db.sqlite3" (
            docker run --rm -v "!CURRENT_DIR!/data:/source:ro" -v thoth-shared-data:/target alpine sh -c "cp /source/db.sqlite3 /target/ 2>/dev/null"
            echo db.sqlite3 copied
        )
    ) else (
        echo dev_databases already exists in Docker volume
    )
    
    REM Show final volume contents
    echo.
    echo Final Docker volume contents:
    docker run --rm -v thoth-shared-data:/target alpine sh -c "ls -la /target/"
) else (
    echo INFO: No dev_databases found in data directory
)

REM Kill any existing process on port 8199
echo.
echo Checking for existing installer on port 8199...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8199.*LISTENING"') do (
    echo Stopping existing installer...
    taskkill /F /PID %%a >nul 2>&1
    timeout /t 2 /nobreak >nul
)

REM Start the FastAPI installer
echo.
echo Starting interactive database configuration...
echo    The installer will open in your browser
echo.

REM Start the FastAPI server in background
start /b cmd /c "uv run python installer_main.py"

REM Wait for server to start
timeout /t 3 /nobreak >nul

REM Check if server is running by trying to connect to port
powershell -Command "try { $client = New-Object System.Net.Sockets.TcpClient('localhost', 8199); $client.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Failed to start installer server
    exit /b 1
)

REM Try to open browser
echo Opening installer in browser...
echo.

REM Open browser
start "" "http://localhost:8199"

echo +----------------------------------------------------------+
echo ^|                                                          ^|
echo ^|  Installer is running at: http://localhost:8199         ^|
echo ^|                                                          ^|
echo ^|  1. Select your SQL databases (SQLite always included)  ^|
echo ^|  2. Click 'Deploy Backend' to start thoth_be            ^|
echo ^|  3. Click 'Deploy Frontend' to start thoth_ui           ^|
echo ^|  4. Click 'Shutdown Installer' when done                ^|
echo ^|                                                          ^|
echo +----------------------------------------------------------+
echo.
echo Press Ctrl+C to stop the installer
echo.

REM Wait for user to stop
pause >nul

echo.
echo Installation process completed!
echo.
echo Access points:
echo   - Backend API:  http://localhost:8040
echo   - Admin panel:  http://localhost:8040/admin
echo   - Frontend UI:  http://localhost:3001 (if deployed)
echo   - Qdrant:       http://localhost:6333/dashboard
echo.
echo To stop services: docker-compose down

endlocal