@echo off
REM Copyright (c) 2025 Marco Pancotti
REM This file is part of Thoth and is released under the Apache License 2.0.
REM See the LICENSE.md file in the project root for full license information.

REM Thoth AI Installer for Windows (CMD)

setlocal enabledelayedexpansion

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
%PYTHON_CMD% -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)" 2>nul
if %errorlevel% neq 0 (
    echo Error: Python 3.9+ is required
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

REM Run installer
echo Starting installation...
%PYTHON_CMD% scripts\installer.py
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

endlocal