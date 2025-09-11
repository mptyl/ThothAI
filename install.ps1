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
        Write-Color "============================================" "Red"
        Write-Color "  WARNING: This will remove ThothAI Docker resources!" "Red"
        Write-Color "  This will affect ONLY resources with 'thoth' in their name:" "Red"
        Write-Color "  - All ThothAI containers" "Red"
        Write-Color "  - All ThothAI images" "Red"
        Write-Color "  - All ThothAI volumes" "Red"
        Write-Color "  - All ThothAI networks" "Red"
        Write-Color "  - All unused ThothAI build cache" "Red"
        Write-Color "  Other Docker resources will remain untouched" "Green"
        Write-Color "============================================" "Red"
        $confirmation = Read-Host "Are you sure you want to continue? (y/N)"
        
        if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
            Write-Color "Operation cancelled by user." "Yellow"
            exit 0
        }

        try {
            # Function to safely remove resources with error handling
            function Remove-DockerResources {
                param(
                    [string]$ResourceType,
                    [string]$ListCommand,
                    [string]$RemoveCommand,
                    [string]$Filter = "*thoth*"
                )
                Write-Color "Processing $ResourceType..." "Yellow"
                $resources = Invoke-Expression $ListCommand | Where-Object { $_ -like $Filter }
                
                if (-not $resources) {
                    Write-Color "  No matching $ResourceType found" "Green"
                    return
                }

                Write-Color "  Found $($resources.Count) $ResourceType to remove" "Yellow"
                $resources | ForEach-Object {
                    try {
                        Invoke-Expression "$RemoveCommand $_" 2>&1 | Out-Null
                        Write-Color "    Removed: $_" "Green"
                    }
                    catch {
                        Write-Color "    Failed to remove $_ : $($_.Exception.Message)" "Red"
                    }
                }
            }

            # Step 1: Stop and remove ThothAI containers
            Write-Color "[1/4] Stopping and removing ThothAI containers..." "Yellow"
            $containers = docker ps -a --filter "name=thoth" --format "{{.ID}}"
            if ($containers) {
                $containers | ForEach-Object {
                    docker stop $_ 2>&1 | Out-Null
                    docker rm -f $_ 2>&1 | Out-Null
                    Write-Color "  Removed container: $_" "Green"
                }
            } else {
                Write-Color "  No ThothAI containers found" "Green"
            }

            # Step 2: Remove ThothAI images
            Write-Color "[2/4] Removing ThothAI images..." "Yellow"
            $images = docker images --format "{{.Repository}}:{{.Tag}}" | Where-Object { $_ -like "*thoth*" }
            if ($images) {
                $images | ForEach-Object {
                    docker rmi -f $_ 2>&1 | Out-Null
                    Write-Color "  Removed image: $_" "Green"
                }
            } else {
                Write-Color "  No ThothAI images found" "Green"
            }

            # Step 3: Remove ThothAI volumes
            Write-Color "[3/4] Removing ThothAI volumes..." "Yellow"
            $volumes = docker volume ls --format "{{.Name}}" | Where-Object { $_ -like "*thoth*" }
            if ($volumes) {
                $volumes | ForEach-Object {
                    docker volume rm $_ 2>&1 | Out-Null
                    Write-Color "  Removed volume: $_" "Green"
                }
            } else {
                Write-Color "  No ThothAI volumes found" "Green"
            }

            # Step 4: Remove ThothAI networks
            Write-Color "[4/4] Removing ThothAI networks..." "Yellow"
            $networks = docker network ls --format "{{.Name}}" | Where-Object { $_ -like "*thoth*" }
            if ($networks) {
                $networks | ForEach-Object {
                    docker network rm $_ 2>&1 | Out-Null
                    Write-Color "  Removed network: $_" "Green"
                }
            } else {
                Write-Color "  No ThothAI networks found" "Green"
            }

            # Final cleanup of any dangling ThothAI resources
            Write-Color "Performing final cleanup..." "Yellow"
            docker system prune -f --filter "label=com.docker.compose.project=thoth" 2>&1 | Out-Null
            
            Write-Host ""
            Write-Color "✓ ThothAI Docker resources cleanup completed!" "Green"
            Write-Color "Other Docker resources remain untouched." "Green"
        }
        catch {
            Write-Color "Error during cleanup: $_" "Red"
            Write-Color "Some ThothAI resources might not have been removed properly." "Yellow"
            exit 1
        }
        
        exit 0
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
        Write-Color "$($_.Exception.Message)" "Red"
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