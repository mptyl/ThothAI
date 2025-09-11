# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

param(
    [switch]$CleanCache,
    [switch]$PruneAll,
    [switch]$Help
)

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
    param([string]$Command)
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
    param([string]$PythonCmd)
    try {
        $result = & $PythonCmd -c "import sys; print('OK' if sys.version_info >= (3, 9) else 'OLD')" 2>$null
        return ($result -eq "OK")
    }
    catch {
        return $false
    }
}

# Function to fix line endings for .sh files
function Fix-LineEndings {
    Write-Color "Fixing line endings for all .sh files..." "Green"
    Write-Host ""
    
    # Find all .sh files and convert to Unix line endings
    $shFiles = Get-ChildItem -Path . -Filter *.sh -Recurse -ErrorAction SilentlyContinue | 
        Where-Object { 
            $_.FullName -notmatch "\\node_modules\\" -and 
            $_.FullName -notmatch "\\venv\\" -and
            $_.FullName -notmatch "\\.venv\\" 
        }
    
    $count = 0
    foreach ($file in $shFiles) {
        $relativePath = $file.FullName.Replace("$PWD\", "")
        
        # Read file and convert CRLF to LF
        $content = [System.IO.File]::ReadAllText($file.FullName)
        $unixContent = $content -replace "`r`n", "`n"
        [System.IO.File]::WriteAllText($file.FullName, $unixContent)
        
        Write-Color "  Fixed: $relativePath" "Green"
        $count++
    }
    
    Write-Host ""
    Write-Color "Total files converted: $count" "Green"
    Write-Host ""
}

# Function to show usage
function Show-Usage {
    Write-Color "Usage: .\install.ps1 [OPTIONS]" "Blue"
    Write-Host ""
    Write-Color "Options:" "Yellow"
    Write-Host "  -CleanCache    Clean Docker build cache before building"
    Write-Host "  -PruneAll      Remove all ThothAI Docker resources (containers, images, volumes)"
    Write-Host "  -Help          Show this help message"
    Write-Host ""
}

# Main installation flow
function Main {
    if ($Help) {
        Show-Usage
        exit 0
    }
    
    Write-Color "============================================" "Blue"
    Write-Color "       Thoth AI Installer for Windows" "Blue"
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
        Write-Host "  - AI provider API keys"
        Write-Host "  - Embedding service configuration"
        Write-Host "  - Database preferences"
        Write-Host "  - Admin email (optional)"
        Write-Host "  - Service ports (if defaults conflict)"
        exit 1
    }
    
    # Determine Python command
    $PYTHON_CMD = $null
    if (Test-Command "python3") {
        $PYTHON_CMD = "python3"
    }
    elseif (Test-Command "python") {
        $PYTHON_CMD = "python"
    }
    else {
        Write-Color "Error: Python is not installed" "Red"
        Write-Color "Please install Python 3.9+: https://www.python.org" "Red"
        exit 1
    }
    
    # Check prerequisites
    Write-Color "Checking prerequisites..." "Yellow"
    
    # Check for Docker
    if (-not (Test-Command "docker")) {
        Write-Color "Error: Docker is not installed" "Red"
        Write-Color "Please install Docker Desktop: https://www.docker.com" "Red"
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
    
    # Check Python version
    if (-not (Test-PythonVersion $PYTHON_CMD)) {
        Write-Color "Error: Python 3.9+ is required" "Red"
        exit 1
    }
    
    # Check for required Python packages
    Write-Color "Installing required Python packages..." "Yellow"
    
    try {
        # Check if we're in a virtual environment
        if ($env:VIRTUAL_ENV) {
            & $PYTHON_CMD -m pip install --quiet pyyaml requests toml 2>$null
        }
        else {
            & $PYTHON_CMD -m pip install --quiet --user pyyaml requests toml 2>$null
        }
    }
    catch {
        Write-Color "Warning: Could not install Python packages automatically" "Yellow"
        Write-Color "Please run: pip install pyyaml requests toml" "Yellow"
    }
    
    Write-Color "Prerequisites OK" "Green"
    Write-Host ""
    
    # Fix line endings for shell scripts (Windows-specific)
    Fix-LineEndings
    
    # Clean Docker cache if requested
    if ($PruneAll) {
        Write-Color "Removing all ThothAI Docker resources..." "Yellow"
        Write-Color "WARNING: This will remove all ThothAI containers, images, and volumes!" "Red"
        $confirmation = Read-Host "Are you sure? (y/N)"
        if ($confirmation -eq 'y' -or $confirmation -eq 'Y') {
            # Stop and remove all ThothAI containers and volumes
            Write-Color "Stopping ThothAI containers..." "Yellow"
            try {
                docker compose down -v 2>$null
            } catch { }
            
            # Remove ThothAI images
            Write-Color "Removing ThothAI images..." "Yellow"
            try {
                $thothImages = docker images --format "{{.Repository}}:{{.Tag}}" | Where-Object { $_ -match "^thoth-" }
                if ($thothImages) {
                    $thothImages | ForEach-Object { docker rmi -f $_ 2>$null }
                }
            } catch { }
            
            # Remove any dangling ThothAI volumes
            try {
                $thothVolumes = docker volume ls --format "{{.Name}}" | Where-Object { $_ -match "^thoth" }
                if ($thothVolumes) {
                    $thothVolumes | ForEach-Object { docker volume rm -f $_ 2>$null }
                }
            } catch { }
            
            # Remove ThothAI network if exists
            try {
                $thothNetworks = docker network ls --format "{{.Name}}" | Where-Object { $_ -match "^thoth" }
                if ($thothNetworks) {
                    $thothNetworks | ForEach-Object { docker network rm $_ 2>$null }
                }
            } catch { }
            
            Write-Color "All ThothAI Docker resources removed" "Green"
        }
        else {
            Write-Color "Skipping ThothAI cleanup" "Yellow"
        }
        Write-Host ""
    }
    elseif ($CleanCache) {
        Write-Color "Cleaning Docker build cache..." "Yellow"
        docker builder prune -a -f
        Write-Color "Docker build cache cleaned" "Green"
        Write-Host ""
    }
    
    # Validate configuration
    Write-Color "Validating configuration..." "Yellow"
    try {
        & $PYTHON_CMD scripts/validate_config.py config.yml.local
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
        Write-Color "Error running configuration validation" "Red"
        Write-Color $_.Exception.Message "Red"
        exit 1
    }
    Write-Host ""

    # Configure embedding provider dependencies
    Write-Color "Configuring embedding provider dependencies..." "Yellow"
    try {
        & $PYTHON_CMD scripts/configure_embedding.py config.yml.local
        if ($LASTEXITCODE -ne 0) {
            Write-Host ""
            Write-Color "============================================" "Red"
            Write-Color "  CRITICAL: Failed to configure thoth-qdrant" "Red"
            Write-Color "  The embedding service cannot be configured." "Red"
            Write-Color "  Please check your configuration and try again." "Red"
            Write-Color "============================================" "Red"
            Write-Host ""
            exit 1
        }
        Write-Color "Embedding configuration completed" "Green"
    }
    catch {
        Write-Host ""
        Write-Color "============================================" "Red"
        Write-Color "  CRITICAL: Failed to configure thoth-qdrant" "Red"
        Write-Color "  Error: $_" "Red"
        Write-Color "  The embedding service cannot be configured." "Red"
        Write-Color "  Please check your configuration and try again." "Red"
        Write-Color "============================================" "Red"
        Write-Host ""
        exit 1
    }
    Write-Host ""
    
    # Pass clean cache option to Python installer
    $INSTALLER_ARGS = @()
    if ($CleanCache -or $PruneAll) {
        $INSTALLER_ARGS += "--no-cache"
    }
    
    # Run installer
    Write-Color "Starting installation..." "Blue"
    try {
        if ($INSTALLER_ARGS.Count -gt 0) {
            & $PYTHON_CMD scripts/installer.py $INSTALLER_ARGS
        }
        else {
            & $PYTHON_CMD scripts/installer.py
        }
        
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
        Write-Color "Installation failed with error:" "Red"
        Write-Color $_.Exception.Message "Red"
        exit 1
    }
}

# Handle script directory
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($SCRIPT_DIR) {
    Set-Location $SCRIPT_DIR
}

# Run main function
Main