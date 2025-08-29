@echo off
REM Copyright (c) 2025 Marco Pancotti
REM This file is part of Thoth and is released under the Apache License 2.0.
REM See the LICENSE.md file in the project root for full license information.

echo ============================================================
echo ThothAI Docker Setup for Windows
echo ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.7+ from https://www.python.org
    pause
    exit /b 1
)

REM Run the Python setup script
echo Running setup script...
python setup-docker.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Setup failed! Please check the errors above.
    pause
    exit /b 1
)

echo.
echo Setup completed successfully!
pause