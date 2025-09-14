@echo off
setlocal ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION
REM ThothAI installer (CMD wrapper) — delegates to install.ps1

REM Change to the directory of this script
cd /d "%~dp0"

REM Prefer PowerShell Core (pwsh) if available, otherwise Windows PowerShell
set "PWSH=pwsh.exe"
where "%PWSH%" >nul 2>&1
if errorlevel 1 (
  set "PWSH=powershell.exe"
  where "%PWSH%" >nul 2>&1
  if errorlevel 1 (
    echo [ERROR] PowerShell non trovato. Esegui questo comando da PowerShell: ^.^\install.ps1
    exit /b 1
  )
)

REM Run the PowerShell installer, forwarding all arguments
"%PWSH%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
set "EXITCODE=%ERRORLEVEL%"

exit /b %EXITCODE%

