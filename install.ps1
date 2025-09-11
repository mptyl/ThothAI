# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

param(
    [switch]$CleanCache,
    [switch]$PruneAll,
    [switch]$DryRun,
    [switch]$Force,
    [switch]$Help
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Colors for output (using Write-Host)
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

# Function to check command availability
function Test-Command {
    param([string]$Command)
    
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    if ($?) {
        return $true
    }
    return $false
}

# Function to check Python version
function Test-PythonVersion {
    param([string]$PythonCmd)
    
    try {
        $result = & $PythonCmd -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            return $true
        }
    } catch {
        return $false
    }
    return $false
}

# Function to show usage
function Show-Usage {
    Write-ColorOutput "Usage: .\install.ps1 [OPTIONS]" "Blue"
    Write-ColorOutput ""
    Write-ColorOutput "Options:" "Yellow"
    Write-ColorOutput "  -CleanCache    Clean Docker build cache before building"
    Write-ColorOutput "  -PruneAll      Remove all ThothAI Docker resources (containers, images, volumes, networks)"
    Write-ColorOutput "  -DryRun        Show what would be removed without actually removing anything"
    Write-ColorOutput "  -Force         Skip confirmation prompt"
    Write-ColorOutput "  -Help          Show this help message"
    Write-Host ""
}

# Function to prune Docker resources
function Remove-DockerResources {
    param(
        [bool]$IsDryRun,
        [bool]$IsForce
    )
    
    if ($IsDryRun) {
        Write-ColorOutput "[DRY RUN] The following resources would be removed:" "Yellow"
        
        Write-Host "`n[Containers]"
        $containers = @()
        $containers += docker ps -a --filter "name=^thoth-" --format "{{.Names}}" 2>$null
        $containers += docker ps -a --filter "name=^/thoth-" --format "{{.Names}}" 2>$null
        $containers | Select-Object -Unique | Where-Object { $_ }
        
        Write-Host "`n[Volumes]"
        docker volume ls -q --filter "name=^thoth-" 2>$null
        
        Write-Host "`n[Networks]"
        docker network ls -q --filter "name=^thoth-" 2>$null
        
        Write-Host "`n[Images]"
        docker images --format "{{.Repository}}:{{.Tag}}" | Select-String -Pattern "^thoth-" -SimpleMatch
        
        return
    }
    
    if (-not $IsForce) {
        Write-ColorOutput "WARNING: This will remove all ThothAI containers, images, volumes, and networks!" "Red"
        $reply = Read-Host "Are you sure you want to continue? (y/N)"
        if ($reply -notmatch "^[Yy]$") {
            Write-ColorOutput "Operation cancelled" "Yellow"
            return
        }
    }
    
    Write-ColorOutput "Removing all ThothAI Docker resources..." "Yellow"
    
    # 1. Stop and remove all ThothAI containers
    Write-ColorOutput "Stopping and removing ThothAI containers..." "Yellow"
    $containers = @()
    $containers += docker ps -a -q --filter "name=^thoth-" --format "{{.ID}}" 2>$null
    $containers += docker ps -a -q --filter "name=^/thoth-" --format "{{.ID}}" 2>$null
    $containers = $containers | Select-Object -Unique | Where-Object { $_ }
    if ($containers) {
        $containers | ForEach-Object { docker rm -f $_ 2>$null | Out-Null }
    }
    
    # 2. Remove all ThothAI volumes
    Write-ColorOutput "Removing ThothAI volumes..." "Yellow"
    $volumes = docker volume ls -q --filter "name=^thoth-" 2>$null
    if ($volumes) {
        $volumes | ForEach-Object { docker volume rm $_ 2>$null | Out-Null }
    }
    
    # 3. Remove all ThothAI networks
    Write-ColorOutput "Removing ThothAI networks..." "Yellow"
    $networks = docker network ls -q --filter "name=^thoth-" 2>$null
    if ($networks) {
        $networks | ForEach-Object { docker network rm $_ 2>$null | Out-Null }
    }
    
    # 4. Remove all ThothAI images
    Write-ColorOutput "Removing ThothAI images..." "Yellow"
    $images = docker images --format "{{.Repository}}:{{.Tag}}" | Select-String -Pattern "^thoth-" -SimpleMatch
    if ($images) {
        $images | ForEach-Object { docker rmi -f $_.Line 2>$null | Out-Null }
    }
    
    # 5. Remove any dangling ThothAI images
    Write-ColorOutput "Removing dangling ThothAI images..." "Yellow"
    $danglingImages = docker images -f "dangling=true" --format "{{.ID}}" 2>$null
    foreach ($imageId in $danglingImages) {
        $history = docker history --no-trunc $imageId 2>$null
        if ($history -match "thoth") {
            docker rmi -f $imageId 2>$null | Out-Null
        }
    }
    
    Write-ColorOutput "All ThothAI Docker resources have been removed" "Green"
}

# Main installation flow
function Main {
    Write-ColorOutput "============================================" "Blue"
    Write-ColorOutput "       Thoth AI Installer" "Blue"
    Write-ColorOutput "============================================" "Blue"
    Write-Host ""
    
    # Handle help
    if ($Help) {
        Show-Usage
        exit 0
    }
    
    # Change to script directory
    $scriptPath = if ($PSScriptRoot) {
        $PSScriptRoot
    } elseif ($MyInvocation.MyCommand.Path) {
        Split-Path -Parent $MyInvocation.MyCommand.Path
    } else {
        Get-Location
    }
    
    if ($scriptPath) {
        Set-Location $scriptPath
    }
    
    # Check for config.yml.local first
    if (-not (Test-Path "config.yml.local")) {
        Write-ColorOutput "Error: Configuration file not found" "Red"
        Write-ColorOutput ""
        Write-ColorOutput "Please create config.yml.local with your installation parameters." "Yellow"
        Write-ColorOutput "You can copy config.yml as a template:" "Yellow"
        Write-ColorOutput "  Copy-Item config.yml config.yml.local" "Green"
        Write-ColorOutput ""
        Write-ColorOutput "Then edit config.yml.local with your:" "Yellow"
        Write-ColorOutput "  - AI provider API keys"
        Write-ColorOutput "  - Embedding service configuration"
        Write-ColorOutput "  - Database preferences"
        Write-ColorOutput "  - Admin email (optional)"
        Write-ColorOutput "  - Service ports (if defaults conflict)"
        exit 1
    }
    
    # Determine Python command
    $PythonCmd = $null
    if (Test-Command "python3") {
        $PythonCmd = "python3"
    } elseif (Test-Command "python") {
        $PythonCmd = "python"
    } else {
        Write-ColorOutput "Please install Python 3.9+: https://www.python.org" "Red"
        exit 1
    }
    
    # Check prerequisites
    Write-ColorOutput "Checking prerequisites..." "Yellow"
    
    # Check for Docker
    if (-not (Test-Command "docker")) {
        Write-ColorOutput "Please install Docker first: https://www.docker.com" "Red"
        exit 1
    }
    
    # Check for Docker Compose
    try {
        docker compose version 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw
        }
    } catch {
        Write-ColorOutput "Error: Docker Compose is not available" "Red"
        Write-ColorOutput "Please ensure Docker Desktop is installed with Compose support" "Red"
        exit 1
    }
    
    # Check Python version
    if (-not (Test-PythonVersion $PythonCmd)) {
        Write-ColorOutput "Error: Python 3.9+ is required" "Red"
        exit 1
    }
    
    # Check for required Python packages
    Write-ColorOutput "Installing required Python packages..." "Yellow"
    
    # Check if we're in a virtual environment
    $InVenv = $env:VIRTUAL_ENV
    
    try {
        if ($InVenv) {
            # In virtual environment, don't use --user
            & $PythonCmd -m pip install --quiet pyyaml requests toml 2>$null
        } else {
            # Not in virtual environment, use --user
            & $PythonCmd -m pip install --quiet --user pyyaml requests toml 2>$null
        }
        
        if ($LASTEXITCODE -ne 0) {
            throw
        }
    } catch {
        Write-ColorOutput "Warning: Could not install Python packages. Trying alternative method..." "Yellow"
        try {
            if ($InVenv) {
                & $PythonCmd -m pip install pyyaml requests toml
            } else {
                & $PythonCmd -m pip install --user pyyaml requests toml
            }
            
            if ($LASTEXITCODE -ne 0) {
                throw
            }
        } catch {
            Write-ColorOutput "Error: Failed to install required Python packages" "Red"
            if ($InVenv) {
                Write-ColorOutput "Please run: pip install pyyaml requests toml" "Red"
            } else {
                Write-ColorOutput "Please run: pip install --user pyyaml requests toml" "Red"
            }
            exit 1
        }
    }
    
    Write-ColorOutput "Prerequisites OK" "Green"
    Write-Host ""
    
    # Clean Docker cache if requested
    if ($PruneAll) {
        Remove-DockerResources -IsDryRun $DryRun -IsForce $Force
        Write-Host ""
    } elseif ($CleanCache) {
        Write-ColorOutput "Cleaning Docker build cache..." "Yellow"
        docker builder prune -a -f
        Write-ColorOutput "Docker build cache cleaned" "Green"
        Write-Host ""
    }
    
    # Validate configuration
    Write-ColorOutput "Validating configuration..." "Yellow"
    & $PythonCmd scripts/validate_config.py config.yml.local
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "Configuration validation passed" "Green"
    } else {
        Write-ColorOutput "Configuration validation failed" "Red"
        Write-ColorOutput "Please fix the errors above and run again" "Red"
        exit 1
    }
    Write-Host ""
    
    # Configure embedding provider dependencies
    Write-ColorOutput "Configuring embedding provider dependencies..." "Yellow"
    & $PythonCmd scripts/configure_embedding.py config.yml.local
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput ""
        Write-ColorOutput "============================================" "Red"
        Write-ColorOutput "  CRITICAL: Failed to configure thoth-qdrant" "Red"
        Write-ColorOutput "  The embedding service cannot be configured." "Red"
        Write-ColorOutput "  Please check your configuration and try again." "Red"
        Write-ColorOutput "============================================" "Red"
        Write-ColorOutput ""
        exit 1
    }
    Write-ColorOutput "Embedding configuration completed" "Green"
    Write-Host ""
    
    # Pass clean cache option to Python installer
    $InstallerArgs = @()
    if ($CleanCache -or $PruneAll) {
        $InstallerArgs += "--no-cache"
    }
    
    # Run installer
    Write-ColorOutput "Starting installation..." "Blue"
    if ($InstallerArgs.Count -gt 0) {
        & $PythonCmd scripts/installer.py $InstallerArgs
    } else {
        & $PythonCmd scripts/installer.py
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput ""
        Write-ColorOutput "============================================" "Green"
        Write-ColorOutput "    Installation completed successfully!" "Green"
        Write-ColorOutput "============================================" "Green"
    } else {
        Write-ColorOutput ""
        Write-ColorOutput "Installation failed" "Red"
        Write-ColorOutput "Please check the error messages above" "Red"
        exit 1
    }
}

# Run main function
Main