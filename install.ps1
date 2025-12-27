# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# PowerShell-style switches
param(
    [switch]$Build,
    [switch]$Pull,
    [switch]$CleanCache,
    [switch]$Prune,
    [switch]$Force,
    [switch]$Help
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Colors for output
function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

# Function to check command availability
function Test-Command {
    param([string]$Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

# Function to show usage
function Show-Usage {
    Write-ColorOutput "Usage: .\install.ps1 [OPTIONS]" "Blue"
    Write-Host ""
    Write-ColorOutput "ThothAI Docker Compose Installer" "Yellow"
    Write-Host "This script installs ThothAI using Docker Compose for local deployment."
    Write-Host ""
    Write-ColorOutput "Options:" "Yellow"
    Write-Host "  -Build         Build images locally instead of pulling from Docker Hub"
    Write-Host "  -Pull          Pull images from Docker Hub (default)"
    Write-Host "  -CleanCache    Clean Docker build cache before building"
    Write-Host "  -Prune         Remove all ThothAI Docker resources (containers, images, volumes, networks)"
    Write-Host "  -Force         Skip confirmation prompt (use with -Prune)"
    Write-Host "  -Help          Show this help message"
    Write-Host ""
    Write-ColorOutput "Examples:" "Yellow"
    Write-Host "  .\install.ps1                # Standard installation (pull from Hub)"
    Write-Host "  .\install.ps1 -Build         # Build images locally"
    Write-Host "  .\install.ps1 -Prune         # Remove all ThothAI resources"
    Write-Host ""
}

# Main installation flow
function Main {
    # Handle help
    if ($Help) { Show-Usage; exit 0 }
    
    Write-ColorOutput "============================================" "Blue"
    Write-ColorOutput "  ThothAI Docker Compose Installer" "Blue"
    Write-ColorOutput "============================================" "Blue"
    Write-Host ""
    
    # Change to script directory
    $scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
    if ($scriptRoot) { Set-Location $scriptRoot }
    
    # Check prerequisites
    if (-not (Test-Command "docker")) { Write-ColorOutput "Error: Docker not found" "Red"; exit 1 }
    
    # Determine Python command
    $PythonCmd = if (Test-Command "python3") { "python3" } elseif (Test-Command "python") { "python" } else { 
        Write-ColorOutput "Error: Python 3.9+ not found" "Red"; exit 1 
    }
    
    # Install Python dependencies
    Write-ColorOutput "Checking Python dependencies..." "Yellow"
    & $PythonCmd -m pip install --quiet pyyaml requests toml --user 2>$null
    if ($LASTEXITCODE -ne 0) { & $PythonCmd -m pip install --quiet pyyaml requests toml }

    # Clean up local services to avoid port conflicts (if not pruning)
    if (-not $Prune) {
        if (Test-Path "docker-compose-local.yml") {
            Write-ColorOutput "Stopping local development services to avoid port conflicts..." "Yellow"
            docker compose -f docker-compose-local.yml down 2>$null | Out-Null
        }
    }

    # Check for config.yml.local
    if (-not (Test-Path "config.yml.local")) {
        if (Test-Path "config.yml") {
            Copy-Item config.yml config.yml.local
            Write-ColorOutput "Created config.yml.local from template." "Yellow"
            Write-ColorOutput "Please edit config.yml.local with your AI API keys and re-run this script." "Red"
            exit 1
        } else {
            Write-ColorOutput "Error: config.yml.local and config.yml not found." "Red"
            exit 1
        }
    }
    
    # Prepare Installer arguments
    $InstallerArgs = @()
    if ($Build)      { $InstallerArgs += "--build" }
    if ($Pull)       { $InstallerArgs += "--pull" }
    if ($CleanCache) { $InstallerArgs += "--clean-cache" }
    if ($Prune)      { $InstallerArgs += "--prune" }
    if ($Force)      { $InstallerArgs += "--force" }

    # Run Validation and Configuration (if not pruning)
    if (-not $Prune) {
        Write-ColorOutput "Validating configuration..." "Yellow"
        & $PythonCmd scripts/validate_config.py config.yml.local
        if ($LASTEXITCODE -ne 0) { exit 1 }
        
        Write-ColorOutput "Configuring embedding provider dependencies..." "Yellow"
        & $PythonCmd scripts/configure_embedding.py config.yml.local
        if ($LASTEXITCODE -ne 0) { exit 1 }
    }

    # Execute Installer
    if ($InstallerArgs.Count -gt 0) {
        & $PythonCmd scripts/installer.py $InstallerArgs
    } else {
        & $PythonCmd scripts/installer.py
    }
}

# Run main function
Main
