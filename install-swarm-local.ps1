# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache 2.0.
# See the LICENSE.md file in the project root for full license information.
#
# Script for deploying ThothAI to local Docker Swarm using images from Docker Hub

param(
    [switch]$SkipPull,
    [switch]$SkipSecrets,
    [switch]$Help
)

# Set strict mode for better error handling
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Helper function for colored output
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

# Function to show usage
function Show-Usage {
    Write-ColorOutput "Usage: .\install-swarm-local.ps1 [OPTIONS]" "Cyan"
    Write-ColorOutput "" "White"
    Write-ColorOutput "Options:" "Yellow"
    Write-ColorOutput "  -SkipPull                        Skip pulling images from Docker Hub" "White"
    Write-ColorOutput "  -SkipSecrets                     Skip creating secrets and configs" "White"
    Write-ColorOutput "  -Help                            Show this help message" "White"
    Write-ColorOutput "" "White"
    Write-ColorOutput "Description:" "Green"
    Write-ColorOutput "  Deploys ThothAI to local Docker Swarm using pre-built images from Docker Hub." "White"
    Write-ColorOutput "  No local build is required - images are pulled directly from Docker Hub." "White"
    Write-ColorOutput "" "White"
    Write-ColorOutput "Examples:" "Green"
    Write-ColorOutput "  .\install-swarm-local.ps1                        # Full deployment" "White"
    Write-ColorOutput "  .\install-swarm-local.ps1 -SkipPull              # Deploy without pulling images" "White"
    Write-ColorOutput "  .\install-swarm-local.ps1 -SkipSecrets           # Deploy without recreating secrets" "White"
    Write-ColorOutput "" "White"
}

# Function to check command availability
function Test-Command {
    param(
        [string]$Command
    )
    try {
        $null = Get-Command $Command -ErrorAction Stop
        return $true
    }
    catch {
        return $false
    }
}

# Function to load swarm configuration
function Load-SwarmConfig {
    $configFile = "swarm_config.env"

    if (-not (Test-Path $configFile)) {
        Write-ColorOutput "Error: $configFile not found" "Red"
        Write-ColorOutput "" "White"
        Write-ColorOutput "Please create $configFile by copying from the template:" "Yellow"
        Write-ColorOutput "  Copy-Item swarm_config.env.template swarm_config.env" "Green"
        Write-ColorOutput "" "White"
        Write-ColorOutput "Then edit $configFile with your configuration:" "Yellow"
        Write-ColorOutput "  - DOCKER_USERNAME (required for Docker Hub)" "White"
        Write-ColorOutput "  - STACK_NAME" "White"
        Write-ColorOutput "  - Service ports (if defaults conflict)" "White"
        exit 1
    }

    # Parse the configuration file
    $config = @{}
    Get-Content $configFile | ForEach-Object {
        if ($_ -match '^([^#].+?)=(.+)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            $config[$name] = $value
        }
    }

    Write-ColorOutput "Configuration loaded from $configFile" "Green"
    return $config
}

# Function to validate configuration
function Test-Config {
    param(
        [hashtable]$Config
    )

    if (-not $Config.ContainsKey('DOCKER_USERNAME') -or [string]::IsNullOrWhiteSpace($Config['DOCKER_USERNAME'])) {
        Write-ColorOutput "Error: DOCKER_USERNAME is not set in swarm_config.env" "Red"
        Write-ColorOutput "Please set DOCKER_USERNAME to your Docker Hub username" "Yellow"
        exit 1
    }

    if ($Config['DOCKER_USERNAME'] -eq "your-dockerhub-username") {
        Write-ColorOutput "Error: DOCKER_USERNAME is still set to the default value" "Red"
        Write-ColorOutput "Please edit swarm_config.env and set your actual Docker Hub username" "Yellow"
        exit 1
    }

    # Set defaults for optional variables
    if (-not $Config.ContainsKey('STACK_NAME') -or [string]::IsNullOrWhiteSpace($Config['STACK_NAME'])) {
        $Config['STACK_NAME'] = 'thothai-swarm'
    }
    if (-not $Config.ContainsKey('FRONTEND_PORT')) {
        $Config['FRONTEND_PORT'] = '7001'
    }
    if (-not $Config.ContainsKey('BACKEND_PROXY_PORT')) {
        $Config['BACKEND_PROXY_PORT'] = $Config['WEB_PORT']
    }
    if (-not $Config.ContainsKey('SQL_GENERATOR_PORT')) {
        $Config['SQL_GENERATOR_PORT'] = '7003'
    }
    if (-not $Config.ContainsKey('QDRANT_PORT')) {
        $Config['QDRANT_PORT'] = '7005'
    }
    if (-not $Config.ContainsKey('MERMAID_SERVICE_PORT')) {
        $Config['MERMAID_SERVICE_PORT'] = '7004'
    }
    if (-not $Config.ContainsKey('WEB_PORT')) {
        $Config['WEB_PORT'] = '7000'
    }
    if (-not $Config.ContainsKey('BACKEND_PORT')) {
        $Config['BACKEND_PORT'] = '7002'
    }
    if (-not $Config.ContainsKey('VERSION')) {
        $Config['VERSION'] = 'latest'
    }

    Write-ColorOutput "Configuration validated:" "Green"
    Write-ColorOutput "  DOCKER_USERNAME:         $($Config['DOCKER_USERNAME'])" "White"
    Write-ColorOutput "  STACK_NAME:              $($Config['STACK_NAME'])" "White"
    Write-ColorOutput "  VERSION:                 $($Config['VERSION'])" "White"
    Write-ColorOutput "  FRONTEND_PORT:           $($Config['FRONTEND_PORT'])" "White"
    Write-ColorOutput "  BACKEND_PROXY_PORT:      $($Config['BACKEND_PROXY_PORT'])" "White"
    Write-ColorOutput "  SQL_GENERATOR_PORT:      $($Config['SQL_GENERATOR_PORT'])" "White"
    Write-ColorOutput "  QDRANT_PORT:             $($Config['QDRANT_PORT'])" "White"
    Write-ColorOutput "  MERMAID_SERVICE_PORT:    $($Config['MERMAID_SERVICE_PORT'])" "White"
    Write-ColorOutput "  WEB_PORT:                $($Config['WEB_PORT'])" "White"
    Write-ColorOutput "  BACKEND_PORT:            $($Config['BACKEND_PORT'])" "White"

    return $Config
}

# Function to pull images from Docker Hub
function Pull-Images {
    param(
        [hashtable]$Config
    )

    Write-ColorOutput "=== Pulling images from Docker Hub ===" "Cyan"
    Write-ColorOutput "" "White"

    $registryUrl = $Config['DOCKER_USERNAME']
    $version = $Config['VERSION']

    # Images to pull
    $images = @{
        "backend" = "thoth-backend"
        "frontend" = "thoth-frontend"
        "sql-generator" = "thoth-sql-generator"
        "proxy" = "thoth-proxy"
        "mermaid-service" = "thoth-mermaid-service"
    }

    foreach ($localName in $images.Keys) {
        $imageName = $images[$localName]
        $fullTag = "$registryUrl/$imageName`:$version"

        Write-ColorOutput "Pulling $fullTag..." "Yellow"
        docker pull $fullTag
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✓ Pulled $fullTag" "Green"
        } else {
            Write-ColorOutput "✗ Failed to pull $fullTag" "Red"
            Write-ColorOutput "Note: Make sure images exist on Docker Hub at $registryUrl/$imageName`:$version" "Yellow"
            exit 1
        }
    }

    # Pull Qdrant from official registry
    Write-ColorOutput "Pulling qdrant/qdrant:latest..." "Yellow"
    docker pull qdrant/qdrant:latest
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "✓ Pulled qdrant/qdrant:latest" "Green"
    } else {
        Write-ColorOutput "✗ Failed to pull qdrant/qdrant:latest" "Red"
        exit 1
    }
}

# Function to prepare docker-stack-swarm.yml
function Prepare-StackFile {
    param(
        [hashtable]$Config
    )

    Write-ColorOutput "=== Preparing docker-stack-swarm.yml ===" "Cyan"
    Write-ColorOutput "" "White"

    if (-not (Test-Path "docker-stack.yml")) {
        Write-ColorOutput "Error: docker-stack.yml not found" "Red"
        exit 1
    }

    # Read the stack file
    $stackContent = Get-Content "docker-stack.yml" -Raw

    # Perform environment variable substitutions
    $replacements = @{
        '${REGISTRY_URL}' = $Config['DOCKER_USERNAME']
        '${VERSION}' = $Config['VERSION']
        '${FRONTEND_PORT}' = $Config['FRONTEND_PORT']
        '${BACKEND_PORT}' = $Config['BACKEND_PORT']
        '${SQL_GENERATOR_PORT}' = $Config['SQL_GENERATOR_PORT']
        '${MERMAID_SERVICE_PORT}' = $Config['MERMAID_SERVICE_PORT']
        '${WEB_PORT}' = $Config['WEB_PORT']
        '${BACKEND_PROXY_PORT}' = $Config['BACKEND_PROXY_PORT']
        '${APP_HOST}' = 'backend'
        '${APP_PORT}' = '8000'
        '${FRONTEND_HOST}' = 'frontend'
        '${SQL_GEN_HOST}' = 'sql-generator'
        '${SQL_GEN_PORT}' = '8020'
        '${DEBUG}' = 'False'
    }

    foreach ($key in $replacements.Keys) {
        $stackContent = $stackContent -replace [regex]::Escape($key), $replacements[$key]
    }

    # Write to docker-stack-swarm.yml
    Write-ColorOutput "Creating docker-stack-swarm.yml with port substitutions..." "Yellow"
    $stackContent | Out-File -FilePath "docker-stack-swarm.yml" -Encoding utf8
    Write-ColorOutput "✓ docker-stack-swarm.yml created" "Green"
}

# Function to create secrets and configs
function Create-SecretsAndConfigs {
    param(
        [hashtable]$Config
    )

    Write-ColorOutput "=== Creating secrets and configs ===" "Cyan"
    Write-ColorOutput "" "White"

    $stackName = $Config['STACK_NAME']

    # Remove old secrets/configs if they exist
    docker secret rm "${stackName}_thoth_env_config" 2>$null | Out-Null
    docker secret rm "${stackName}_thoth_config_yml" 2>$null | Out-Null
    docker config rm "${stackName}_thoth_env_docker" 2>$null | Out-Null

    # Create new secrets and configs
    if (Test-Path ".env.docker") {
        docker secret create "${stackName}_thoth_env_config" .env.docker
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✓ Created secret: ${stackName}_thoth_env_config" "Green"
        } else {
            Write-ColorOutput "✗ Failed to create secret" "Red"
            exit 1
        }
    } else {
        Write-ColorOutput "Warning: .env.docker not found, skipping secret creation" "Yellow"
    }

    if (Test-Path "config.yml.local") {
        docker secret create "${stackName}_thoth_config_yml" config.yml.local
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✓ Created secret: ${stackName}_thoth_config_yml" "Green"
        } else {
            Write-ColorOutput "✗ Failed to create secret" "Red"
            exit 1
        }
    } else {
        Write-ColorOutput "Warning: config.yml.local not found, skipping secret creation" "Yellow"
    }

    if (Test-Path ".env.docker") {
        docker config create "${stackName}_thoth_env_docker" .env.docker
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✓ Created config: ${stackName}_thoth_env_docker" "Green"
        } else {
            Write-ColorOutput "✗ Failed to create config" "Red"
            exit 1
        }
    }
    Write-ColorOutput "" "White"

    # Update docker-stack-swarm.yml with stack-specific secret/config names
    Write-ColorOutput "Updating docker-stack-swarm.yml with stack-specific names..." "Yellow"
    $stackContent = Get-Content "docker-stack-swarm.yml" -Raw
    $stackContent = $stackContent -replace 'thoth_env_config', "${stackName}_thoth_env_config"
    $stackContent = $stackContent -replace 'thoth_config_yml', "${stackName}_thoth_config_yml"
    $stackContent = $stackContent -replace 'thoth_env_docker', "${stackName}_thoth_env_docker"
    $stackContent | Out-File -FilePath "docker-stack-swarm.yml" -Encoding utf8
    Write-ColorOutput "✓ Updated docker-stack-swarm.yml" "Green"
    Write-ColorOutput "" "White"
}

# Function to deploy stack to local Swarm
function Deploy-Stack {
    param(
        [hashtable]$Config
    )

    Write-ColorOutput "=== Deploying to local Docker Swarm ===" "Cyan"
    Write-ColorOutput "" "White"

    # Check if Swarm is active locally
    Write-ColorOutput "Checking Swarm status..." "Yellow"
    $dockerInfo = docker info 2>&1
    if ($dockerInfo -notmatch "Swarm:\s+active") {
        Write-ColorOutput "Error: Docker Swarm is not active" "Red"
        Write-ColorOutput "Please initialize Swarm: docker swarm init" "Yellow"
        exit 1
    }
    Write-ColorOutput "✓ Swarm is active" "Green"
    Write-ColorOutput "" "White"

    # Deploy stack
    $stackName = $Config['STACK_NAME']
    Write-ColorOutput "Deploying stack '$stackName' to local Swarm..." "Yellow"
    docker stack deploy -c docker-stack-swarm.yml $stackName
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "✓ Stack deployment initiated" "Green"
    } else {
        Write-ColorOutput "✗ Stack deployment failed" "Red"
        exit 1
    }
}

# Function to wait for services to start
function Wait-ForServices {
    param(
        [string]$StackName
    )

    Write-ColorOutput "=== Waiting for services to start ===" "Cyan"
    Write-ColorOutput "" "White"

    $maxWait = 600  # 10 minutes
    $elapsed = 0

    while ($elapsed -lt $maxWait) {
        $servicesOutput = docker stack services $StackName --format "{{.Name}} {{.Replicas}}" 2>&1

        if ([string]::IsNullOrWhiteSpace($servicesOutput) -or $servicesOutput -match "error") {
            Write-ColorOutput "Waiting for services to be created... ($elapsed/$maxWait seconds)" "Yellow"
            Start-Sleep -Seconds 5
            $elapsed += 5
            continue
        }

        # Check if all services are running
        $allRunning = $true
        foreach ($line in $servicesOutput -split "`n") {
            if (-not [string]::IsNullOrWhiteSpace($line)) {
                $parts = $line -split '\s+'
                if ($parts.Length -ge 2) {
                    $replicas = $parts[1]
                    if ($replicas -match '^(\d+)/(\d+)$') {
                        $running = [int]$matches[1]
                        $total = [int]$matches[2]
                        if ($running -ne $total) {
                            $allRunning = $false
                            break
                        }
                    } else {
                        $allRunning = $false
                        break
                    }
                }
            }
        }

        if ($allRunning) {
            Write-ColorOutput "✓ All services are running" "Green"
            return $true
        }

        Write-ColorOutput "Waiting for services... ($elapsed/$maxWait seconds)" "Yellow"
        Write-ColorOutput $servicesOutput "White"
        Start-Sleep -Seconds 10
        $elapsed += 10
    }

    Write-ColorOutput "Timeout: Services did not start within $maxWait seconds" "Red"
    return $false
}

# Function to show deployment status
function Show-DeploymentStatus {
    param(
        [string]$StackName
    )

    Write-ColorOutput "=== Deployment Status ===" "Cyan"
    Write-ColorOutput "" "White"

    Write-ColorOutput "Stack services:" "Yellow"
    $services = docker stack services $StackName 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput $services "White"
    } else {
        Write-ColorOutput "Could not retrieve services" "Red"
    }
    Write-ColorOutput "" "White"

    Write-ColorOutput "Stack tasks:" "Yellow"
    $tasks = docker stack ps $StackName 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput $tasks "White"
    } else {
        Write-ColorOutput "Could not retrieve tasks" "Red"
    }
    Write-ColorOutput "" "White"
}

# Function to show access URLs
function Show-AccessUrls {
    param(
        [hashtable]$Config
    )

    Write-ColorOutput "=== Access URLs ===" "Green"
    Write-ColorOutput "" "White"

    Write-ColorOutput "The following services should be accessible at:" "White"
    Write-ColorOutput "  Frontend (Next.js):     http://localhost:$($Config['FRONTEND_PORT'])" "Yellow"
    Write-ColorOutput "  Backend (Django):       http://localhost:$($Config['BACKEND_PROXY_PORT'])/api" "Yellow"
    Write-ColorOutput "  Admin Panel:             http://localhost:$($Config['BACKEND_PROXY_PORT'])/admin" "Yellow"
    Write-ColorOutput "  SQL Generator:          http://localhost:$($Config['SQL_GENERATOR_PORT'])" "Yellow"
    Write-ColorOutput "  Mermaid Service:        http://localhost:$($Config['MERMAID_SERVICE_PORT'])" "Yellow"
    Write-ColorOutput "  Qdrant Dashboard:       http://localhost:$($Config['QDRANT_PORT'])/dashboard" "Yellow"
    Write-ColorOutput "  Web (Proxy):            http://localhost:$($Config['WEB_PORT'])" "Yellow"
    Write-ColorOutput "" "White"

    Write-ColorOutput "Useful commands:" "Yellow"
    Write-ColorOutput "  View stack services:    docker stack services $($Config['STACK_NAME'])" "White"
    Write-ColorOutput "  View stack tasks:       docker stack ps $($Config['STACK_NAME'])" "White"
    Write-ColorOutput "  View service logs:      docker service logs $($Config['STACK_NAME'])_backend" "White"
    Write-ColorOutput "  Remove stack:           docker stack rm $($Config['STACK_NAME'])" "White"
    Write-ColorOutput "" "White"
}

# Main execution
try {
    # Check for help
    if ($Help) {
        Show-Usage
        exit 0
    }

    Write-ColorOutput "============================================" "Cyan"
    Write-ColorOutput "  ThothAI - Local Docker Swarm Deployment" "Cyan"
    Write-ColorOutput "  Using images from Docker Hub" "Cyan"
    Write-ColorOutput "============================================" "Cyan"
    Write-ColorOutput "" "White"

    # Check prerequisites
    Write-ColorOutput "Checking prerequisites..." "Yellow"

    if (-not (Test-Command "docker")) {
        Write-ColorOutput "Error: Docker is not installed" "Red"
        exit 1
    }

    Write-ColorOutput "✓ Prerequisites OK" "Green"
    Write-ColorOutput "" "White"

    # Load and validate configuration
    $config = Load-SwarmConfig
    $config = Test-Config -Config $config
    Write-ColorOutput "" "White"

    # Pull images from Docker Hub
    if (-not $SkipPull) {
        Pull-Images -Config $config
        Write-ColorOutput "" "White"
    } else {
        Write-ColorOutput "Skipping image pull (using cached images)" "Yellow"
        Write-ColorOutput "" "White"
    }

    # Prepare stack file
    Prepare-StackFile -Config $config
    Write-ColorOutput "" "White"

    # Create secrets and configs
    if (-not $SkipSecrets) {
        Create-SecretsAndConfigs -Config $config
    } else {
        Write-ColorOutput "Skipping secrets and configs creation" "Yellow"
        Write-ColorOutput "" "White"
    }

    # Deploy to local Swarm
    Deploy-Stack -Config $config
    Write-ColorOutput "" "White"

    # Wait for services
    if (Wait-ForServices -StackName $config['STACK_NAME']) {
        Write-ColorOutput "✓ Services started successfully" "Green"
        Write-ColorOutput "" "White"
        
        # Show deployment status
        Show-DeploymentStatus -StackName $config['STACK_NAME']
        Write-ColorOutput "" "White"
        
        # Show access URLs
        Show-AccessUrls -Config $config
        
        Write-ColorOutput "============================================" "Green"
        Write-ColorOutput "  Local deployment completed!" "Green"
        Write-ColorOutput "============================================" "Green"
        Write-ColorOutput "" "White"
    } else {
        Write-ColorOutput "✗ Services failed to start within timeout" "Red"
        Write-ColorOutput "" "White"
        
        Write-ColorOutput "=== Deployment Status ===" "Yellow"
        Show-DeploymentStatus -StackName $config['STACK_NAME']
        Write-ColorOutput "" "White"
        
        Write-ColorOutput "To debug, check service logs:" "Yellow"
        Write-ColorOutput "  docker service logs $($config['STACK_NAME'])_backend" "White"
        Write-ColorOutput "  docker service logs $($config['STACK_NAME'])_proxy" "White"
        Write-ColorOutput "  docker service logs $($config['STACK_NAME'])_frontend" "White"
        Write-ColorOutput "" "White"
        
        Write-ColorOutput "To remove the failed stack:" "Yellow"
        Write-ColorOutput "  docker stack rm $($config['STACK_NAME'])" "White"
        Write-ColorOutput "" "White"
        
        exit 1
    }
}
catch {
    Write-ColorOutput "Error: $($_.Exception.Message)" "Red"
    Write-ColorOutput $_.ScriptStackTrace "Red"
    exit 1
}
