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
        [switch]$IsDryRun,
        [switch]$IsForce
    )
    
    if ($IsDryRun) {
        Write-ColorOutput "[DRY RUN] The following resources would be removed:" "Yellow"
        
        Write-Host "`n[Containers]"
        $containers = @(docker ps -a --format "{{.Names}}" 2>$null)
        $thothContainers = $containers | Where-Object { $_ -like "thoth-*" -or $_ -like "thothui-*" }
        if ($thothContainers) { 
            $thothContainers | ForEach-Object { Write-Host "  $_" }
        } else { 
            Write-Host "  None found" -ForegroundColor Gray 
        }
        
        Write-Host "`n[Volumes]"
        $volumes = @(docker volume ls --format "{{.Name}}" 2>$null)
        $thothVolumes = $volumes | Where-Object { $_ -like "thoth*" }
        if ($thothVolumes) { 
            $thothVolumes | ForEach-Object { Write-Host "  $_" }
        } else { 
            Write-Host "  None found" -ForegroundColor Gray 
        }
        
        Write-Host "`n[Networks]"
        $networks = @(docker network ls --format "{{.Name}}" 2>$null)
        $thothNetworks = $networks | Where-Object { $_ -like "thoth*" }
        if ($thothNetworks) { 
            $thothNetworks | ForEach-Object { Write-Host "  $_" }
        } else { 
            Write-Host "  None found" -ForegroundColor Gray 
        }
        
        Write-Host "`n[Images]"
        $images = docker images --format "{{.Repository}}:{{.Tag}}" 2>$null
        $thothImages = $images | Where-Object { $_ -like "thoth-*" }
        if ($thothImages) { $thothImages } else { Write-Host "  None found" -ForegroundColor Gray }
        
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
    $containers = @(docker ps -a --format "{{.Names}}" 2>$null)
    Write-Host "  Total containers found: $($containers.Count)" -ForegroundColor DarkGray
    $thothContainers = $containers | Where-Object { $_ -like "thoth*" -or $_ -like "*thoth*" }
    Write-Host "  Thoth containers to remove: $($thothContainers.Count)" -ForegroundColor DarkGray
    if ($thothContainers -and $thothContainers.Count -gt 0) {
        $thothContainers | ForEach-Object { 
            if ($_) {
                Write-Host "  Removing container: $_" -ForegroundColor Gray
                $result = docker rm -f $_ 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "    Successfully removed" -ForegroundColor DarkGreen
                } else {
                    Write-Host "    Failed to remove: $result" -ForegroundColor DarkRed
                }
            }
        }
    } else {
        Write-Host "  No Thoth containers found" -ForegroundColor Gray
    }
    
    # 2. Remove all ThothAI volumes
    Write-ColorOutput "Removing ThothAI volumes..." "Yellow"
    $volumes = @(docker volume ls --format "{{.Name}}" 2>$null)
    Write-Host "  Total volumes found: $($volumes.Count)" -ForegroundColor DarkGray
    $thothVolumes = $volumes | Where-Object { $_ -like "thoth*" -or $_ -like "*thoth*" }
    Write-Host "  Thoth volumes to remove: $($thothVolumes.Count)" -ForegroundColor DarkGray
    if ($thothVolumes -and $thothVolumes.Count -gt 0) {
        $thothVolumes | ForEach-Object { 
            if ($_) {
                Write-Host "  Removing volume: $_" -ForegroundColor Gray
                $result = docker volume rm $_ 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "    Successfully removed" -ForegroundColor DarkGreen
                } else {
                    Write-Host "    Failed to remove: $result" -ForegroundColor DarkRed
                }
            }
        }
    } else {
        Write-Host "  No Thoth volumes found" -ForegroundColor Gray
    }
    
    # 3. Remove all ThothAI networks
    Write-ColorOutput "Removing ThothAI networks..." "Yellow"
    $networks = @(docker network ls --format "{{.Name}}" 2>$null)
    Write-Host "  Total networks found: $($networks.Count)" -ForegroundColor DarkGray
    $thothNetworks = $networks | Where-Object { $_ -like "thoth*" -or $_ -like "*thoth*" }
    Write-Host "  Thoth networks to remove: $($thothNetworks.Count)" -ForegroundColor DarkGray
    if ($thothNetworks -and $thothNetworks.Count -gt 0) {
        $thothNetworks | ForEach-Object { 
            if ($_) {
                Write-Host "  Removing network: $_" -ForegroundColor Gray
                $result = docker network rm $_ 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "    Successfully removed" -ForegroundColor DarkGreen
                } else {
                    Write-Host "    Failed to remove: $result" -ForegroundColor DarkRed
                }
            }
        }
    } else {
        Write-Host "  No Thoth networks found" -ForegroundColor Gray
    }
    
    # 4. Remove all ThothAI images
    Write-ColorOutput "Removing ThothAI images..." "Yellow"
    $images = @(docker images --format "{{.Repository}}:{{.Tag}}" 2>$null)
    Write-Host "  Total images found: $($images.Count)" -ForegroundColor DarkGray
    $thothImages = $images | Where-Object { $_ -like "thoth*" -or $_ -like "*thoth*" }
    Write-Host "  Thoth images to remove: $($thothImages.Count)" -ForegroundColor DarkGray
    if ($thothImages -and $thothImages.Count -gt 0) {
        $thothImages | ForEach-Object { 
            if ($_) {
                Write-Host "  Removing image: $_" -ForegroundColor Gray
                $result = docker rmi -f $_ 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "    Successfully removed" -ForegroundColor DarkGreen
                } else {
                    Write-Host "    Failed to remove: $result" -ForegroundColor DarkRed
                }
            }
        }
    } else {
        Write-Host "  No Thoth images found" -ForegroundColor Gray
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

# Function to fix line endings for shell scripts and Docker files
function Fix-LineEndings {
    Write-ColorOutput "Fixing line endings for shell scripts and Docker files..." "Yellow"
    
    # Find all .sh files and Dockerfiles
    $filesToFix = @()
    $filesToFix += Get-ChildItem -Path . -Filter *.sh -Recurse -ErrorAction SilentlyContinue
    $filesToFix += Get-ChildItem -Path . -Filter Dockerfile* -Recurse -ErrorAction SilentlyContinue
    $filesToFix += Get-ChildItem -Path . -Filter *.yml -Recurse -ErrorAction SilentlyContinue
    $filesToFix += Get-ChildItem -Path . -Filter *.yaml -Recurse -ErrorAction SilentlyContinue
    
    # Filter out unwanted directories
    $filesToFix = $filesToFix | Where-Object { 
        $_.FullName -notmatch "\\node_modules\\" -and 
        $_.FullName -notmatch "\\venv\\" -and
        $_.FullName -notmatch "\\.venv\\" -and
        $_.FullName -notmatch "\\.git\\"
    }
    
    $count = 0
    foreach ($file in $filesToFix) {
        try {
            $relativePath = $file.FullName.Replace($PWD.Path + "\", "")
            
            # Read file and check if it has CRLF
            $content = [System.IO.File]::ReadAllText($file.FullName)
            if ($content.Contains("`r`n")) {
                # Convert CRLF to LF
                $unixContent = $content -replace "`r`n", "`n"
                [System.IO.File]::WriteAllText($file.FullName, $unixContent)
                
                Write-Host "  Fixed: $relativePath" -ForegroundColor Gray
                $count++
            }
        } catch {
            # Silently skip files that can't be converted
        }
    }
    
    if ($count -gt 0) {
        Write-ColorOutput "Converted $count files to Unix line endings" "Green"
    } else {
        Write-ColorOutput "No files needed line ending conversion" "Green"
    }
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
    
    # Fix line endings first (critical for Docker on Windows)
    Fix-LineEndings
    Write-Host ""
    
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
        if ($DryRun) {
            Remove-DockerResources -IsDryRun
        } elseif ($Force) {
            Remove-DockerResources -IsForce
        } else {
            Remove-DockerResources
        }
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