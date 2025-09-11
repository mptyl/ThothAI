@echo off
REM Copyright (c) 2025 Marco Pancotti
REM This file is part of Thoth and is released under the Apache License 2.0.
REM See the LICENSE.md file in the project root for full license information.

REM Thoth AI Installer for Windows (CMD)

setlocal enabledelayedexpansion
pushd "%~dp0"

REM Parse command line arguments
set CLEAN_CACHE=false
set PRUNE_ALL=false
set DRY_RUN=false
set FORCE=false
set SHOW_HELP=false

:parse_args
if "%~1"=="" goto :end_parse
if /i "%~1"=="--clean-cache" (
    set CLEAN_CACHE=true
    shift
    goto :parse_args
)
if /i "%~1"=="--prune-all" (
    set PRUNE_ALL=true
    shift
    goto :parse_args
)
if /i "%~1"=="--dry-run" (
    set DRY_RUN=true
    shift
    goto :parse_args
)
if /i "%~1"=="--force" (
    set FORCE=true
    shift
    goto :parse_args
)
if /i "%~1"=="--help" (
    set SHOW_HELP=true
    shift
    goto :parse_args
)
if /i "%~1"=="/?" (
    set SHOW_HELP=true
    shift
    goto :parse_args
)
echo Unknown option: %~1
set SHOW_HELP=true
shift
goto :parse_args

:end_parse

REM Show help if requested
if "%SHOW_HELP%"=="true" (
    echo Usage: install.bat [OPTIONS]
    echo.
    echo Options:
    echo   --clean-cache    Clean Docker build cache before building
    echo   --prune-all      Remove all ThothAI Docker resources (containers, images, volumes, networks)
    echo   --dry-run        Show what would be removed without actually removing anything
    echo   --force          Skip confirmation prompt
    echo   --help, /?       Show this help message
    echo.
    exit /b 0
)

REM Function to execute Docker command with error handling
:docker_cmd
setlocal
set "DOCKER_CMD=docker %*"
if "%DRY_RUN%"=="true" (
    echo [DRY RUN] Would run: %DOCKER_CMD%
    exit /b 0
)
%DOCKER_CMD%
if %ERRORLEVEL% neq 0 (
    echo Error executing: %DOCKER_CMD%
    if "%FORCE%" neq "true" (
        pause
        exit /b 1
    )
)
exit /b 0

REM Function to prune Docker resources
:prune_resources
setlocal

if "%DRY_RUN%"=="true" (
    echo [DRY RUN] The following resources would be removed:
    
    echo [Containers]
    docker ps -a --filter "name=^thoth-|^/thoth-" --format "{{.Names}}" 2>nul
    
    echo [Volumes]
    docker volume ls -q --filter "name=^thoth-" 2>nul
    
    echo [Networks]
    docker network ls -q --filter "name=^thoth-" 2>nul
    
    echo [Images]
    docker images --format "{{.Repository}}:{{.Tag}}" | findstr /i "^thoth-"
    
    exit /b 0
)

if "%FORCE%" neq "true" (
    echo WARNING: This will remove all ThothAI containers, images, volumes, and networks!
    set /p "confirmation=Are you sure you want to continue? (y/N): "
    if /i not "%confirmation%"=="y" (
        echo Operation cancelled
        exit /b 0
    )
)

echo Removing all ThothAI Docker resources...

REM 1. Stop and remove all ThothAI containers
echo Stopping and removing ThothAI containers...
for /f "tokens=*" %%i in ('docker ps -a -q --filter "name=^thoth-|^/thoth-" --format "{{.ID}}" 2^>nul') do (
    call :docker_cmd rm -f "%%i"
)

REM 2. Remove all ThothAI volumes
echo Removing ThothAI volumes...
for /f "tokens=*" %%i in ('docker volume ls -q --filter "name=^thoth-" 2^>nul') do (
    call :docker_cmd volume rm "%%i"
)

REM 3. Remove all ThothAI networks
echo Removing ThothAI networks...
for /f "tokens=*" %%i in ('docker network ls -q --filter "name=^thoth-" 2^>nul') do (
    call :docker_cmd network rm "%%i"
)

REM 4. Remove all ThothAI images
echo Removing ThothAI images...
for /f "tokens=*" %%i in ('docker images --format "{{.Repository}}:{{.Tag}}" ^| findstr /i "^thoth-" 2^>nul') do (
    call :docker_cmd rmi -f "%%i"
)

REM 5. Remove any dangling ThothAI images
echo Removing dangling ThothAI images...
for /f "tokens=*" %%i in ('docker images -f "dangling=true" --format "{{.ID}}" 2^>nul') do (
    for /f "tokens=*" %%h in ('docker history --no-trunc %%i 2^>nul ^| findstr /i "thoth"') do (
        call :docker_cmd rmi -f "%%i"
    )
)

echo All ThothAI Docker resources have been removed
endlocal
goto :eof

REM Colors are not easily supported in CMD, so we'll use plain output
echo ============================================
echo        Thoth AI Installer
echo ============================================
echo.

REM Check for config.yml.local first
if not exist "config.yml.local" (
    echo Error: Configuration file not found
    echo.
    echo Please create config.yml.local with your installation parameters.
    echo You can copy config.yml as a template:
    echo   copy config.yml config.yml.local
    echo.
    echo Then edit config.yml.local with your:
    echo   - AI provider API keys
    echo   - Embedding service configuration
    echo   - Database preferences
    echo   - Admin email ^(optional^)
    echo   - Service ports ^(if defaults conflict^)
    exit /b 1
)

REM Check prerequisites
echo Checking prerequisites...

REM Check for Docker
where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Docker is not installed
    echo Please install Docker Desktop first: https://www.docker.com/products/docker-desktop
    exit /b 1
)

REM Check for Docker Compose
docker compose version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Docker Compose is not available
    echo Please ensure Docker Desktop is installed with Compose support
    exit /b 1
)

REM Check for Python (try python3 first, then python)
set PYTHON_CMD=
where python3 >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python3
) else (
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=python
    ) else (
        echo Error: Python is not installed
        echo Please install Python 3.9+: https://www.python.org
        exit /b 1
    )
)

REM Check Python version
for /f "tokens=*" %%i in ('%PYTHON_CMD% -c "import sys; print('OK' if sys.version_info ^>= (3, 9) else 'OLD')" 2^>nul') do set PY_VERSION=%%i
if not "!PY_VERSION!"=="OK" (
    echo Error: Python 3.9+ is required
    echo Current Python version:
    %PYTHON_CMD% --version
    exit /b 1
)

REM Check for required Python packages
echo Installing required Python packages...

REM Check if we're in a virtual environment
if defined VIRTUAL_ENV (
    REM In virtual environment, don't use --user
    %PYTHON_CMD% -m pip install --quiet pyyaml requests toml 2>nul
    if %errorlevel% neq 0 (
        echo Warning: Could not install Python packages. Trying again...
        %PYTHON_CMD% -m pip install pyyaml requests toml
        if %errorlevel% neq 0 (
            echo Error: Failed to install required Python packages
            echo Please run: pip install pyyaml requests toml
            exit /b 1
        )
    )
) else (
    REM Not in virtual environment, use --user
    %PYTHON_CMD% -m pip install --quiet --user pyyaml requests toml 2>nul
    if %errorlevel% neq 0 (
        echo Warning: Could not install Python packages. Trying with system pip...
        %PYTHON_CMD% -m pip install --quiet pyyaml requests toml
        if %errorlevel% neq 0 (
            echo Error: Failed to install required Python packages
            echo Please run: pip install pyyaml requests toml
            exit /b 1
        )
    )
)

echo Prerequisites OK
echo.

REM Clean Docker cache if requested
if "%PRUNE_ALL%"=="true" (
    call :prune_resources
    echo.
) else if "%CLEAN_CACHE%"=="true" (
    echo Cleaning Docker build cache...
    call :docker_cmd builder prune -a -f
    echo Docker build cache cleaned
    echo.
)

REM Validate configuration
echo Validating configuration...
%PYTHON_CMD% scripts\validate_config.py config.yml.local
if %errorlevel% neq 0 (
    echo Configuration validation failed
    echo Please fix the errors above and run again
    exit /b 1
)
echo Configuration validation passed
echo.

REM Configure embedding provider dependencies
echo Configuring embedding provider dependencies...
%PYTHON_CMD% scripts\configure_embedding.py config.yml.local
if %errorlevel% neq 0 (
    echo.
    echo ============================================
    echo   CRITICAL: Failed to configure thoth-qdrant
    echo   The embedding service cannot be configured.
    echo   Please check your configuration and try again.
    echo ============================================
    echo.
    exit /b 1
)
echo Embedding configuration completed
echo.

REM Pass clean cache option to Python installer
set INSTALLER_ARGS=
if "%CLEAN_CACHE%"=="true" set INSTALLER_ARGS=--no-cache
if "%PRUNE_ALL%"=="true" set INSTALLER_ARGS=--no-cache

REM Run installer
echo Starting installation...
%PYTHON_CMD% scripts\installer.py %INSTALLER_ARGS%
if %errorlevel% neq 0 (
    echo.
    echo Installation failed
    echo Please check the error messages above
    exit /b 1
)

echo.
echo ============================================
echo     Installation completed successfully!
echo ============================================

popd
endlocal