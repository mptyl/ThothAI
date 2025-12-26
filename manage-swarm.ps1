# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

param(
    [string]$RemoteHost,
    [string]$ConfigFile,
    [switch]$SkipBackup,
    [switch]$RollbackOnly,
    [switch]$StatusOnly,
    [switch]$Logs,
    [switch]$HealthCheck
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

# Configuration Defaults
$RegistryUrl = "your-dockerhub-username"
$Version = "latest"
$StackName = "thothai-swarm"
$BackupDir = "/backup/thoth"

# Default Ports
$WebPort = "7000"
$FrontendPort = "7001"
$BackendPort = "7002"
$SqlGeneratorPort = "7003"
$MermaidServicePort = "7004"
$QdrantPort = "7005"

# Load Config File if provided
if ($ConfigFile) {
    if (Test-Path $ConfigFile) {
        Write-ColorOutput "Loading configuration from $ConfigFile" "Cyan"
        Get-Content $ConfigFile | Where-Object { $_ -match "^[^#].*=" } | ForEach-Object {
            $name, $value = $_.Split('=', 2)
            Set-Variable -Name $name.Trim() -Value $value.Trim() -Scope Script
        }
    } else {
        Write-ColorOutput "Error: Config file $ConfigFile not found" "Red"
        exit 1
    }
}

# Docker Command Wrapper (handles remote host)
function Invoke-Docker {
    param([string[]]$Arguments)
    
    if ($RemoteHost) {
        # Using ssh protocol for remote docker host
        docker -H "ssh://$RemoteHost" @Arguments
    } else {
        docker @Arguments
    }
}

function Check-Prerequisites {
    Write-ColorOutput "=== Check prerequisites ===" "Blue"

    # Check Docker
    try {
        Invoke-Docker "info" > $null 2>&1
        if ($LASTEXITCODE -ne 0) { throw }
    } catch {
        Write-ColorOutput "Error: Docker is not reachable" "Red"
        exit 1
    }

    # Check Swarm
    $info = Invoke-Docker "info"
    if ($info -notmatch "Swarm: active") {
        Write-ColorOutput "Error: Docker Swarm is not active on target. Run 'docker swarm init'" "Red"
        exit 1
    }

    # Check config files (local check)
    if (-not (Test-Path "config.yml.local")) {
        Write-ColorOutput "Error: config.yml.local not found" "Red"
        exit 1
    }

    if (-not (Test-Path ".env.docker")) {
        Write-ColorOutput "Error: .env.docker not found. Run configuration script first" "Red"
        exit 1
    }

    if (-not (Test-Path "docker-stack.yml")) {
        Write-ColorOutput "Error: docker-stack.yml not found" "Red"
        exit 1
    }

    Write-ColorOutput "✓ Prerequisites verified" "Green"
}

function Backup-Volumes {
    Write-ColorOutput "=== Backup volumes ===" "Blue"

    $Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $BackupPath = "$BackupDir/$Timestamp"
    
    # Backup database
    Write-ColorOutput "Backing up database..." "Yellow"
    Invoke-Docker "run", "--rm",
        "-v", "${StackName}_thoth-backend-db:/data",
        "-v", "$BackupPath`:/backup",
        "alpine", "sh", "-c", "mkdir -p /backup && tar czf /backup/backend-db.tar.gz -C /data . 2>/dev/null || true" | Out-Null

    # Backup Qdrant
    Write-ColorOutput "Backing up Qdrant..." "Yellow"
    Invoke-Docker "run", "--rm",
        "-v", "${StackName}_qdrant-data:/data",
        "-v", "$BackupPath`:/backup",
        "alpine", "sh", "-c", "mkdir -p /backup && tar czf /backup/qdrant-data.tar.gz -C /data . 2>/dev/null || true" | Out-Null
        
    # Backup data-exchange
    Write-ColorOutput "Backing up thoth-data-exchange..." "Yellow"
    Invoke-Docker "run", "--rm",
        "-v", "thoth-data-exchange:/data",
        "-v", "$BackupPath`:/backup",
        "alpine", "sh", "-c", "mkdir -p /backup && tar czf /backup/data-exchange.tar.gz -C /data . 2>/dev/null || true" | Out-Null

    Write-ColorOutput "✓ Backup (best effort) completed in $BackupPath on swarm node" "Green"
}

function Update-Secrets {
    Write-ColorOutput "=== Update Secrets ===" "Blue"

    Invoke-Docker "secret", "rm", "${StackName}_thoth_env_config" 2>$null | Out-Null
    Invoke-Docker "secret", "rm", "${StackName}_thoth_config_yml" 2>$null | Out-Null

    Invoke-Docker "secret", "create", "${StackName}_thoth_env_config", ".env.docker" | Out-Null
    Write-ColorOutput "✓ Created secret: ${StackName}_thoth_env_config" "Green"

    Invoke-Docker "secret", "create", "${StackName}_thoth_config_yml", "config.yml.local" | Out-Null
    Write-ColorOutput "✓ Created secret: ${StackName}_thoth_config_yml" "Green"

    Write-ColorOutput "✓ Secrets updated" "Green"
}

function Update-Configs {
    Write-ColorOutput "=== Update Configs ===" "Blue"

    Invoke-Docker "config", "rm", "${StackName}_thoth_env_docker" 2>$null | Out-Null

    Invoke-Docker "config", "create", "${StackName}_thoth_env_docker", ".env.docker" | Out-Null
    Write-ColorOutput "✓ Created config: ${StackName}_thoth_env_docker" "Green"

    Write-ColorOutput "✓ Configs updated" "Green"
}

function Prepare-StackFile {
    Write-ColorOutput "=== Prepare Stack File ===" "Blue"

    if (-not (Test-Path "docker-stack.yml")) {
        Write-ColorOutput "Error: docker-stack.yml not found" "Red"
        exit 1
    }

    # Set env vars for docker stack
    $env:REGISTRY_URL = $RegistryUrl
    $env:VERSION = $Version
    $env:WEB_PORT = $WebPort
    $env:FRONTEND_PORT = $FrontendPort
    $env:BACKEND_PORT = $BackendPort
    $env:SQL_GENERATOR_PORT = $SqlGeneratorPort
    $env:MERMAID_SERVICE_PORT = $MermaidServicePort
    $env:QDRANT_PORT = $QdrantPort

    Write-ColorOutput "Port configuration:" "Yellow"
    Write-ColorOutput "  Web (Proxy):        $env:WEB_PORT"
    Write-ColorOutput "  Frontend:           $env:FRONTEND_PORT"
    Write-ColorOutput "  Backend:            $env:BACKEND_PORT"
    Write-ColorOutput "  SQL Generator:      $env:SQL_GENERATOR_PORT"
    Write-ColorOutput "  Mermaid Service:    $env:MERMAID_SERVICE_PORT"
    Write-ColorOutput "  Qdrant:             $env:QDRANT_PORT"
    Write-Host ""
    
    if ($RemoteHost) {
        Write-ColorOutput "Deploy on remote host: $RemoteHost" "Magenta"
    }

    # Read the stack file
    $stackContent = Get-Content "docker-stack.yml" -Raw

    # Perform environment variable substitutions
    $replacements = @{
        '${REGISTRY_URL}' = $RegistryUrl
        '${VERSION}' = $Version
        '${WEB_PORT}' = $WebPort
        '${FRONTEND_PORT}' = $FrontendPort
        '${BACKEND_PORT}' = $BackendPort
        '${SQL_GENERATOR_PORT}' = $SqlGeneratorPort
        '${MERMAID_SERVICE_PORT}' = $MermaidServicePort
        '${QDRANT_PORT}' = $QdrantPort
    }

    foreach ($key in $replacements.Keys) {
        $stackContent = $stackContent -replace [regex]::Escape($key), $replacements[$key]
    }

    # Write to docker-stack-swarm.yml
    Write-ColorOutput "Creating docker-stack-swarm.yml with port substitutions..." "Yellow"
    $stackContent | Out-File -FilePath "docker-stack-swarm.yml" -Encoding utf8
    Write-ColorOutput "✓ docker-stack-swarm.yml created" "Green"

    # Update with stack-specific names
    $stackContent = $stackContent -replace 'thoth_env_config', "${StackName}_thoth_env_config"
    $stackContent = $stackContent -replace 'thoth_config_yml', "${StackName}_thoth_config_yml"
    $stackContent = $stackContent -replace 'thoth_env_docker', "${StackName}_thoth_env_docker"
    $stackContent | Out-File -FilePath "docker-stack-swarm.yml" -Encoding utf8
    Write-ColorOutput "✓ Updated docker-stack-swarm.yml with stack-specific names" "Green"
}

function Deploy-Stack {
    Write-ColorOutput "=== Deploy Stack ===" "Blue"

    Invoke-Docker "stack", "deploy", "-c", "docker-stack-swarm.yml", $StackName
    Write-ColorOutput "✓ Deploy started" "Green"
}

function Wait-For-Services {
    Write-ColorOutput "=== Wait for services to start ===" "Blue"
    $MaxWait = 1200 # 20 mins
    $Elapsed = 0

    while ($Elapsed -lt $MaxWait) {
        $services = Invoke-Docker "stack", "services", $StackName, "--format", "{{.Replicas}}"
        $allRunning = $true
        
        if (-not $services) { 
            # Stack might not be up yet
            $allRunning = $false 
        } else {
            foreach ($line in $services) {
                # Look for "1/1" or "2/2" etc.
                if ($line -notmatch "(\d+)/\1") {
                    $allRunning = $false
                    break
                }
            }
        }

        if ($allRunning) {
            Write-ColorOutput "✓ All services are running" "Green"
            return $true
        }

        Write-ColorOutput "Waiting... ($Elapsed/$MaxWait seconds)" "Yellow"
        Start-Sleep -Seconds 10
        $Elapsed += 10
    }

    Write-ColorOutput "Timeout: Services not started in time" "Red"
    return $false
}

function Rollback-Stack {
    Write-ColorOutput "=== Rollback ===" "Red"
    # Rollback main services
    Invoke-Docker "service", "rollback", "${StackName}_backend" 2>$null | Out-Null
    Invoke-Docker "service", "rollback", "${StackName}_frontend" 2>$null | Out-Null
    Invoke-Docker "service", "rollback", "${StackName}_sql-generator" 2>$null | Out-Null
    Write-ColorOutput "Rollback completed" "Yellow"
}

function Show-Logs {
    Write-ColorOutput "=== Backend Logs (last 20 lines) ===" "Blue"
    Invoke-Docker "service", "logs", "--tail", "20", "${StackName}_backend" 2>$null
}

function Show-Status {
    Write-ColorOutput "=== Service Status ===" "Blue"
    Invoke-Docker "stack", "services", $StackName
}

# --- Main ---

Write-ColorOutput "============================================" "Blue"
Write-ColorOutput "  ThothAI - Deploy Automatizzato Swarm (PS)" "Blue"
Write-ColorOutput "============================================" "Blue"
Write-Host ""

if ($RollbackOnly) { Rollback-Stack; exit 0 }
if ($StatusOnly) { Show-Status; exit 0 }
if ($Logs) { Show-Logs; exit 0 }

Check-Prerequisites

if (-not $SkipBackup) {
    Backup-Volumes
}

Update-Secrets
Update-Configs
Prepare-StackFile
Deploy-Stack

if (-not (Wait-For-Services)) {
    Write-ColorOutput "Deploy failed. Executing rollback..." "Red"
    Rollback-Stack
    Show-Logs
    exit 1
}

Show-Status

Write-ColorOutput "============================================" "Green"
Write-ColorOutput "  Deploy completed successfully!" "Green"
Write-ColorOutput "============================================" "Green"
