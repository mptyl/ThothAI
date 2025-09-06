# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Thoth AI Installer for Windows

# Set error action preference
$ErrorActionPreference = "Stop"

# Function to print colored output
function Write-Color {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

# Function to check if command exists
function Test-Command {
    param(
        [string]$Command
    )
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# Function to check Python version
function Test-PythonVersion {
    try {
        # Try python3 first, then python
        $result = $null
        if (Test-Command "python3") {
            $output = & python3 -c "import sys; print('OK' if sys.version_info >= (3, 9) else 'OLD')" 2>$null
            $result = $output -join ""
        }
        elseif (Test-Command "python") {
            $output = & python -c "import sys; print('OK' if sys.version_info >= (3, 9) else 'OLD')" 2>$null
            $result = $output -join ""
        }
        return $result -eq "OK"
    }
    catch {
        return $false
    }
}

# Main installation flow
function Main {
    Write-Color "============================================" "Blue"
    Write-Color "       Thoth AI Installer" "Blue"
    Write-Color "============================================" "Blue"
    Write-Host ""

    # Check for config.yml.local first
    if (-not (Test-Path "config.yml.local")) {
        Write-Color "Error: Configuration file not found" "Red"
        Write-Host ""
        Write-Color "Please create config.yml.local with your installation parameters." "Yellow"
        Write-Color "You can copy config.yml as a template:" "Yellow"
        Write-Color "  Copy-Item config.yml config.yml.local" "Green"
        Write-Host ""
        Write-Color "Then edit config.yml.local with your:" "Yellow"
        Write-Color "  - AI provider API keys" "White"
        Write-Color "  - Embedding service configuration" "White"
        Write-Color "  - Database preferences" "White"
        Write-Color "  - Admin email (optional)" "White"
        Write-Color "  - Service ports (if defaults conflict)" "White"
        exit 1
    }

    # Prepare Docker environment
    Write-Color "Preparing Docker build environment..." "Yellow"
    
    # Fix line endings for all shell scripts (CRLF to LF conversion)
    Write-Color "Converting line endings to Unix format (LF)..." "Yellow"
    
    # Find all .sh files and entrypoint scripts
    Get-ChildItem -Recurse -Include "*.sh", "entrypoint*" | Where-Object { 
        $_.FullName -notmatch "node_modules" -and $_.FullName -notmatch "\.venv" 
    } | ForEach-Object {
        $file = $_.FullName
        # Check if file has CRLF line endings
        $content = Get-Content -Path $file -Raw
        if ($content -match "`r`n") {
            Write-Color "  Converting: $($_.Name)" "White"
            # Convert CRLF to LF
            $content = $content -replace "`r`n", "`n"
            [System.IO.File]::WriteAllText($file, $content)
        }
    }
    
    Write-Color "Docker environment prepared" "Green"

    # Check prerequisites
    Write-Color "Checking prerequisites..." "Yellow"
    
    # Check for Docker
    if (-not (Test-Command "docker")) {
        Write-Color "Error: Docker is not installed" "Red"
        Write-Color "Please install Docker Desktop first: https://www.docker.com/products/docker-desktop" "Red"
        exit 1
    }
    
    # Check for Docker Compose
    try {
        docker compose version | Out-Null
    }
    catch {
        Write-Color "Error: Docker Compose is not available" "Red"
        Write-Color "Please ensure Docker Desktop is installed with Compose support" "Red"
        exit 1
    }
    
    # Check for Python (try python3 first, then python)
    $pythonCmd = $null
    if (Test-Command "python3") {
        $pythonCmd = "python3"
    }
    elseif (Test-Command "python") {
        $pythonCmd = "python"
    }
    else {
        Write-Color "Error: Python is not installed" "Red"
        Write-Color "Please install Python 3.9+: https://www.python.org" "Red"
        exit 1
    }
    
    # Check Python version
    if (-not (Test-PythonVersion)) {
        Write-Color "Error: Python 3.9+ is required" "Red"
        Write-Color "Current Python version:" "Yellow"
        & $pythonCmd --version
        exit 1
    }
    
    # Check for required Python packages
    Write-Color "Installing required Python packages..." "Yellow"
    
    # Determine Python command
    if (Test-Command "python3") {
        $pythonCmd = "python3"
    }
    else {
        $pythonCmd = "python"
    }
    
    # Check if we're in a virtual environment
    $inVirtualEnv = $env:VIRTUAL_ENV -ne $null
    
    try {
        if ($inVirtualEnv) {
            # In virtual environment, don't use --user
            & $pythonCmd -m pip install --quiet pyyaml requests toml 2>$null
        }
        else {
            # Not in virtual environment, use --user
            & $pythonCmd -m pip install --quiet --user pyyaml requests toml 2>$null
        }
    }
    catch {
        Write-Color "Warning: Could not install Python packages. Trying again..." "Yellow"
        try {
            & $pythonCmd -m pip install --quiet pyyaml requests toml
        }
        catch {
            Write-Color "Error: Failed to install required Python packages" "Red"
            Write-Color "Please run: pip install pyyaml requests toml" "Red"
            exit 1
        }
    }
    
    Write-Color "Prerequisites OK" "Green"
    Write-Host ""

    # Validate configuration
    Write-Color "Validating configuration..." "Yellow"
    
    # Determine Python command
    if (Test-Command "python3") {
        $pythonCmd = "python3"
    }
    else {
        $pythonCmd = "python"
    }
    
    try {
        & $pythonCmd scripts\validate_config.py config.yml.local
        if ($LASTEXITCODE -eq 0) {
            Write-Color "Configuration validation passed" "Green"
        }
        else {
            Write-Color "Configuration validation failed" "Red"
            Write-Color "Please fix the errors above and run again" "Red"
            exit 1
        }
    }
    catch {
        Write-Color "Configuration validation failed" "Red"
        Write-Color "Please fix the errors above and run again" "Red"
        exit 1
    }
    Write-Host ""

    # Run installer
    Write-Color "Starting installation..." "Blue"
    
    # Determine Python command
    if (Test-Command "python3") {
        $pythonCmd = "python3"
    }
    else {
        $pythonCmd = "python"
    }
    
    try {
        & $pythonCmd scripts\installer.py
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Color "============================================" "Green"
            Write-Color "    Installation completed successfully!" "Green"
            Write-Color "============================================" "Green"
        }
        else {
            Write-Host ""
            Write-Color "Installation failed" "Red"
            Write-Color "Please check the error messages above" "Red"
            exit 1
        }
    }
    catch {
        Write-Host ""
        Write-Color "Installation failed" "Red"
        Write-Color "Error: $_" "Red"
        exit 1
    }
}

# Handle script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $ScriptDir

try {
    Main
}
finally {
    Pop-Location
}