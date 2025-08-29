@echo off
REM Copyright (c) 2025 Marco Pancotti
REM This file is part of Thoth and is released under the MIT License.
REM See the LICENSE.md file in the project root for full license information.

echo Setting up Docker Buildx for cache export...

REM Create a new buildx builder instance
docker buildx create --name thoth-builder --driver docker-container --use

REM Bootstrap the builder
docker buildx inspect --bootstrap

echo.
echo Buildx builder 'thoth-builder' created and set as default
echo.
echo You can now use cache export with commands like:
echo   docker buildx build --cache-to type=local,dest=.buildcache ...
echo   docker buildx build --cache-from type=local,src=.buildcache ...