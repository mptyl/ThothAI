# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.
#
# Script for deploying ThothAI to Docker Swarm (Local or Remote)

param(
    [Parameter(Mandatory=$false, HelpMessage="SSH connection string for remote deployment (e.g., user@hostname)")]
    [string]$Server,

    [Parameter(HelpMessage="SSH port for remote deploy (default: 22)")]
    [int]$Port = 22,

    [Parameter(HelpMessage="Path to SSH private key (default: ~/.ssh/id_rsa)")]
    [string]$Key = "$env:USERPROFILE\.ssh\id_rsa",

    [switch]$SkipPull,
    [switch]$SkipSecrets,
    [switch]$Prune,
    [switch]$Help
)

# Set strict mode for better error handling
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Colors for output
function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

function Write-Header {
    param([string]$Title)
    Write-Host ""
    Write-ColorOutput "============================================" "Cyan"
    Write-ColorOutput "  $Title" "Cyan"
    Write-ColorOutput "============================================" "Cyan"
    Write-Host ""
}

function Show-Usage {
    Write-ColorOutput "Usage: .\install-swarm.ps1 [OPTIONS]" "Cyan"
    Write-Host ""
    Write-ColorOutput "ThothAI Docker Swarm Installer" "Yellow"
    Write-Host "Deploys ThothAI to a Docker Swarm cluster (local or remote)."
    Write-Host ""
    Write-ColorOutput "Options:" "Yellow"
    Write-Host "  -Server <SSH_STRING>  Deploy to remote server via SSH (e.g., user@hostname)"
    Write-Host "  -Port <SSH_PORT>      SSH port for remote deploy (default: 22)"
    Write-Host "  -Key <SSH_KEY_PATH>   Path to SSH private key (default: ~/.ssh/id_rsa)"
    Write-Host "  -SkipPull             Skip pulling images from Docker Hub"
    Write-Host "  -SkipSecrets          Skip creating/recreating secrets and configs"
    Write-Host "  -Prune                Remove the stack and associated secrets/configs"
    Write-Host "  -Help                 Show this help message"
    Write-Host ""
    Write-ColorOutput "Examples:" "Yellow"
    Write-Host "  .\install-swarm.ps1                  # Local Swarm deployment"
    Write-Host "  .\install-swarm.ps1 -Server user@ip   # Remote Swarm deployment"
    Write-Host "  .\install-swarm.ps1 -Prune            # Remove local stack"
    Write-Host ""
}

# Check command availability
function Test-Command {
    param([string]$Command)
    try { $null = Get-Command $Command -ErrorAction Stop; return $true }
    catch { return $false }
}

# Load swarm configuration
function Load-SwarmConfig {
    $configFile = "swarm_config.env"
    if (-not (Test-Path $configFile)) {
        if (Test-Path "swarm_config.env.template") {
            Copy-Item "swarm_config.env.template" $configFile
            Write-ColorOutput "Created $configFile from template. Please edit it and re-run." "Yellow"
            exit 1
        } else {
            Write-ColorOutput "Error: $configFile not found." "Red"
            exit 1
        }
    }

    $config = @{}
    Get-Content $configFile | ForEach-Object {
        if ($_ -match '^([^#].+?)=(.+)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            $config[$name] = $value
            # Export to environment for envsubst or tool logic
            [System.Environment]::SetEnvironmentVariable($name, $value)
        }
    }
    Write-ColorOutput "✓ Configuration loaded from $configFile" "Green"
    return $config
}

# Validate configuration
function Test-Config {
    param([hashtable]$Config)
    
    $dockerUser = if ($Config.ContainsKey('DOCKER_USERNAME')) { $Config['DOCKER_USERNAME'] } else { "tylconsulting" }
    if ($dockerUser -eq "your-dockerhub-username") {
        Write-ColorOutput "Error: Please set DOCKER_USERNAME in swarm_config.env" "Red"
        exit 1
    }
    
    $stackName = if ($Config.ContainsKey('STACK_NAME')) { $Config['STACK_NAME'] } else { "thothai-swarm" }
    $version = if ($Config.ContainsKey('VERSION')) { $Config['VERSION'] } else { "latest" }

    # Setup defaults for ports
    $ports = @{
        'FRONTEND_PORT' = if ($Config.ContainsKey('FRONTEND_PORT')) { $Config['FRONTEND_PORT'] } else { '7001' }
        'BACKEND_PORT' = if ($Config.ContainsKey('BACKEND_PORT')) { $Config['BACKEND_PORT'] } else { '7002' }
        'SQL_GENERATOR_PORT' = if ($Config.ContainsKey('SQL_GENERATOR_PORT')) { $Config['SQL_GENERATOR_PORT'] } else { '7003' }
        'MERMAID_SERVICE_PORT' = if ($Config.ContainsKey('MERMAID_SERVICE_PORT')) { $Config['MERMAID_SERVICE_PORT'] } else { '7004' }
        'QDRANT_PORT' = if ($Config.ContainsKey('QDRANT_PORT')) { $Config['QDRANT_PORT'] } else { '7005' }
        'WEB_PORT' = if ($Config.ContainsKey('WEB_PORT')) { $Config['WEB_PORT'] } else { '7000' }
    }
    $ports['BACKEND_PROXY_PORT'] = if ($Config.ContainsKey('BACKEND_PROXY_PORT')) { $Config['BACKEND_PROXY_PORT'] } else { $ports['WEB_PORT'] }

    foreach ($key in $ports.Keys) { [System.Environment]::SetEnvironmentVariable($key, $ports[$key]) }
    [System.Environment]::SetEnvironmentVariable('DOCKER_USERNAME', $dockerUser)
    [System.Environment]::SetEnvironmentVariable('STACK_NAME', $stackName)
    [System.Environment]::SetEnvironmentVariable('VERSION', $version)

    return $Config
}

# Pull images
function Pull-Images {
    param([hashtable]$Config)
    Write-Header "Pulling Images..."
    $dockerUser = [System.Environment]::GetEnvironmentVariable('DOCKER_USERNAME')
    $version = [System.Environment]::GetEnvironmentVariable('VERSION')
    
    $images = @("thoth-backend", "thoth-frontend", "thoth-sql-generator", "thoth-proxy", "thoth-mermaid-service")
    foreach ($img in $images) {
        Write-ColorOutput "Pulling $dockerUser/$img`:$version..." "Yellow"
        docker pull "$dockerUser/$img`:$version"
    }
    docker pull qdrant/qdrant:latest
    Write-ColorOutput "✓ All images pulled" "Green"
}

# Prepare stack file
function Prepare-StackFile {
    param([hashtable]$Config)
    Write-ColorOutput "Preparing deployment file..." "Yellow"
    
    $stackName = [System.Environment]::GetEnvironmentVariable('STACK_NAME')
    $dockerUser = [System.Environment]::GetEnvironmentVariable('DOCKER_USERNAME')
    
    # Export vars for replacements
    $env:REGISTRY_URL = $dockerUser
    $env:APP_HOST = "${stackName}_backend"
    $env:FRONTEND_HOST = "${stackName}_frontend"
    $env:SQL_GEN_HOST = "${stackName}_sql-generator"
    
    # Simple substitution since PowerShell handles variables well in strings
    $content = Get-Content "docker-stack.yml" -Raw
    $replacements = @{
        '${REGISTRY_URL}' = [System.Environment]::GetEnvironmentVariable('DOCKER_USERNAME')
        '${VERSION}' = [System.Environment]::GetEnvironmentVariable('VERSION')
        '${FRONTEND_PORT}' = [System.Environment]::GetEnvironmentVariable('FRONTEND_PORT')
        '${BACKEND_PORT}' = [System.Environment]::GetEnvironmentVariable('BACKEND_PORT')
        '${SQL_GENERATOR_PORT}' = [System.Environment]::GetEnvironmentVariable('SQL_GENERATOR_PORT')
        '${MERMAID_SERVICE_PORT}' = [System.Environment]::GetEnvironmentVariable('MERMAID_SERVICE_PORT')
        '${WEB_PORT}' = [System.Environment]::GetEnvironmentVariable('WEB_PORT')
    }

    foreach ($key in $replacements.Keys) {
        $content = $content.Replace($key, $replacements[$key])
    }

    # Stack specific names
    $content = $content.Replace('thoth_env_config', "${stackName}_thoth_env_config")
    $content = $content.Replace('thoth_config_yml', "${stackName}_thoth_config_yml")
    $content = $content.Replace('thoth_env_docker', "${stackName}_thoth_env_docker")

    $content | Out-File -FilePath "docker-stack-swarm.yml" -Encoding utf8
    Write-ColorOutput "✓ docker-stack-swarm.yml ready" "Green"
}

# Manage secrets
function Manage-Secrets {
    param([hashtable]$Config)
    Write-Header "Managing Secrets and Configs..."
    $stackName = [System.Environment]::GetEnvironmentVariable('STACK_NAME')

    # Generate .env.docker if script exists
    if (Test-Path "scripts/installer.py") {
        python3 scripts/installer.py --generate-env-only
    }

    # Remove existing
    docker secret rm "${stackName}_thoth_env_config" "${stackName}_thoth_config_yml" 2>$null | Out-Null
    docker config rm "${stackName}_thoth_env_docker" 2>$null | Out-Null

    # Create new
    if (Test-Path ".env.docker") { docker secret create "${stackName}_thoth_env_config" .env.docker }
    if (Test-Path "config.yml.local") { docker secret create "${stackName}_thoth_config_yml" config.yml.local }
    if (Test-Path ".env.docker") { docker config create "${stackName}_thoth_env_docker" .env.docker }
    
    Write-ColorOutput "✓ Secrets and configs created" "Green"
}

# Prune resources
function Prune-Swarm {
    param([hashtable]$Config)
    $stackName = if ($Config.ContainsKey('STACK_NAME')) { $Config['STACK_NAME'] } else { "thothai-swarm" }
    Write-Header "Pruning Swarm Stack: $stackName"
    docker stack rm $stackName 2>$null | Out-Null
    Write-ColorOutput "Stack removal initiated. Cleaning up secrets..." "Yellow"
    Start-Sleep -Seconds 5
    docker secret rm "${stackName}_thoth_env_config" "${stackName}_thoth_config_yml" 2>$null | Out-Null
    docker config rm "${stackName}_thoth_env_docker" 2>$null | Out-Null
    Write-ColorOutput "✓ Prune completed" "Green"
}

# Wait for services
function Wait-ForServices {
    param([string]$StackName)
    Write-Header "Waiting for services to start..."
    $maxWait = 300
    $elapsed = 0
    while ($elapsed -lt $maxWait) {
        $services = docker stack services $StackName --format "{{.Replicas}}" 2>$null | Where-Object { $_ -ne "0/0" -and $_ -ne "" }
        if ($services) {
            $allReady = $true
            foreach ($s in $services) {
                $parts = $s -split '/'
                if ($parts[0].Trim() -ne $parts[1].Trim()) { $allReady = $false; break }
            }
            if ($allReady) {
                Write-ColorOutput "✓ All services are running" "Green"
                return
            }
        }
        Write-Host -NoNewline "."
        Start-Sleep -Seconds 5
        $elapsed += 5
    }
    Write-ColorOutput "Timeout waiting for services" "Yellow"
}

# Main Execution
try {
    if ($Help) { Show-Usage; exit 0 }

    Write-ColorOutput "============================================" "Cyan"
    Write-ColorOutput "  ThothAI Swarm Deployment" "Cyan"
    Write-ColorOutput "============================================" "Cyan"

    # 1. Prerequisites
    if (-not (Test-Command "docker")) { Write-ColorOutput "Error: Docker not found" "Red"; exit 1 }

    # 2. Remote setup
    if ([string]::IsNullOrWhiteSpace($Server)) {
        Write-ColorOutput "Target: Local Swarm" "Cyan"
    } else {
        Write-ColorOutput "Target: Remote Swarm ($Server)" "Cyan"
        $env:DOCKER_HOST = "ssh://$Server`:$Port"
        if (Test-Path $Key) { $env:DOCKER_SSH_CLIENT_KEY = $Key }
    }

    # 3. Load and validate config
    $config = Load-SwarmConfig
    $config = Test-Config -Config $config

    # 4. Prune if requested
    if ($Prune) { Prune-Swarm -Config $config; exit 0 }

    # 5. Execute deployment
    if (-not $SkipPull) { Pull-Images -Config $config }
    if (-not $SkipSecrets) { Manage-Secrets -Config $config }

    # Ensure required volumes exist
    Write-ColorOutput "Ensuring required volumes exist..." "Yellow"
    $volumes = @("thoth-secrets", "thoth-backend-static", "thoth-backend-media", "thoth-frontend-cache", "thoth-qdrant-data", "thoth-shared-data", "thoth-data-exchange")
    $existingVolumes = docker volume ls --format '{{.Name}}'
    foreach ($vol in $volumes) {
        if ($existingVolumes -notcontains $vol) {
            docker volume create $vol 2>$null | Out-Null
            Write-ColorOutput "  Created volume '$vol'" "Green"
        }
    }
    
    # Ensure network exists
    $stackName = [System.Environment]::GetEnvironmentVariable('STACK_NAME')
    docker network create --driver overlay --attachable "${stackName}_thoth-network" 2>$null | Out-Null

    Prepare-StackFile -Config $config
    
    Write-ColorOutput "Deploying stack $stackName..." "Yellow"
    docker stack deploy -c docker-stack-swarm.yml $stackName

    Wait-ForServices -StackName $stackName

    # 6. Show URLs
    $hostAddr = if ([string]::IsNullOrWhiteSpace($Server)) { "localhost" } else { $Server -split '@' | Select-Object -Last 1 }
    $webPort = [System.Environment]::GetEnvironmentVariable('WEB_PORT')
    $frontendPort = [System.Environment]::GetEnvironmentVariable('FRONTEND_PORT')
    $backendProxyPort = [System.Environment]::GetEnvironmentVariable('BACKEND_PROXY_PORT')

    Write-Header "Deployment Complete!"
    Write-ColorOutput "Main Access: http://$hostAddr`:$webPort" "Green"
    Write-ColorOutput "Frontend Service: http://$hostAddr`:$frontendPort" "Green"
    Write-ColorOutput "Backend Admin: http://$hostAddr`:$backendProxyPort/admin" "Green"

    if (Test-Path "docker-stack-swarm.yml") { Remove-Item "docker-stack-swarm.yml" }

} catch {
    Write-ColorOutput "Error: $($_.Exception.Message)" "Red"
    exit 1
}
