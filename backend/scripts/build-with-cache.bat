@echo off
REM Copyright (c) 2025 Marco Pancotti
REM This file is part of Thoth and is released under the MIT License.
REM See the LICENSE.md file in the project root for full license information.

REM Build Thoth with cache export/import using Docker Buildx on Windows

setlocal enabledelayedexpansion

REM Default values
set CACHE_DIR=.buildcache
set IMAGE_NAME=thoth-be
set DOCKERFILE=Dockerfile
set PLATFORM=linux/amd64
set PUSH_FLAG=

REM Parse arguments
:parse_args
if "%~1"=="" goto end_parse
if "%~1"=="--cache-dir" (
    set CACHE_DIR=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--image" (
    set IMAGE_NAME=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--platform" (
    set PLATFORM=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--push" (
    set PUSH_FLAG=--push
    shift
    goto parse_args
)
echo Unknown option: %~1
exit /b 1

:end_parse

REM Create cache directory if it doesn't exist
if not exist "%CACHE_DIR%" mkdir "%CACHE_DIR%"

echo Building %IMAGE_NAME% with cache...
echo Cache directory: %CACHE_DIR%

REM Build with cache import and export
docker buildx build ^
  --platform=%PLATFORM% ^
  --cache-from type=local,src=%CACHE_DIR% ^
  --cache-to type=local,dest=%CACHE_DIR%,mode=max ^
  --tag %IMAGE_NAME%:latest ^
  --load ^
  %PUSH_FLAG% ^
  -f %DOCKERFILE% ^
  .

echo Build complete. Cache saved to %CACHE_DIR%