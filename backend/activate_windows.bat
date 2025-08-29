@echo off
REM Copyright (c) 2025 Marco Pancotti
REM This file is part of Thoth and is released under the Apache License 2.0.
REM See the LICENSE.md file in the project root for full license information.

REM Activate uv virtual environment on Windows

echo Activating ThothAI virtual environment...

REM Find the virtual environment
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo Virtual environment activated!
    echo You can now use: python manage.py [command]
) else (
    echo ERROR: Virtual environment not found!
    echo Please run install.bat first to create the environment.
    exit /b 1
)