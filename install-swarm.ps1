# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.
#
# Script for deploying ThothAI to a remote Docker Swarm server from Windows

param(
    [Parameter(Mandatory=$true, HelpMessage="SSH connection string (e.g., user@hostname or user@ip)")]
    [string]$Server,

    [Parameter(HelpMessage="SSH port (default: 22)")]
    [int]$Port = 22,

    [Parameter(HelpMessage="Path to SSH private key (default: ~/.ssh/id_rsa)")]
    [string]$Key = "$env:USERPROFILE\.ssh\id_rsa"
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
    Write-ColorOutput "Usage: .\install-swarm.ps1 -Server <SSH_CONNECTION_STRING> [OPTIONS]" "Cyan"
    Write-ColorOutput "" "White"
    Write-ColorOutput "Required Arguments:" "Yellow"
    Write-ColorOutput "  -Server <SSH_CONNECTION_STRING>  SSH connection string (e.g., user@hostname or user@ip)" "White"
    Write-ColorOutput "" "White"
    Write-ColorOutput "Optional Arguments:" "Yellow"
    Write-ColorOutput "  -Port <SSH_PORT>                 SSH port (default: 22)" "White"
    Write-ColorOutput "  -Key <SSH_KEY_PATH>              Path to SSH private key (default: ~/.ssh/id_rsa)" "White"
    Write-ColorOutput "  -Help                            Show this help message" "White"
    Write-ColorOutput "" "White"
    Write-ColorOutput "Example:" "Green"
    Write-ColorOutput "  .\install-swarm.ps1 -Server user@192.168.1.100" "White"
    Write-ColorOutput "  .\install-swarm.ps1 -Server user@swarm.example.com -Port 2222 -Key C:\Users\user\.ssh\custom_key" "White"
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
        $Config['STACK_NAME'] = 'thoth'
    }
    if (-not $Config.ContainsKey('FRONTEND_PORT')) {
        $Config['FRONTEND_PORT'] = '3040'
    }
    if (-not $Config.ContainsKey('BACKEND_PROXY_PORT')) {
        $Config['BACKEND_PROXY_PORT'] = '8040'
    }
    if (-not $Config.ContainsKey('SQL_GENERATOR_PORT')) {
        $Config['SQL_GENERATOR_PORT'] = '8020'
    }
    if (-not $Config.ContainsKey('QDRANT_PORT')) {
        $Config['QDRANT_PORT'] = '6333'
    }
    if (-not $Config.ContainsKey('MERMAID_SERVICE_PORT')) {
        $Config['MERMAID_SERVICE_PORT'] = '8003'
    }
    if (-not $Config.ContainsKey('WEB_PORT')) {
        $Config['WEB_PORT'] = '7000'
    }
    if (-not $Config.ContainsKey('BACKEND_PORT')) {
        $Config['BACKEND_PORT'] = '7002'
    }

    Write-ColorOutput "Configuration validated:" "Green"
    Write-ColorOutput "  DOCKER_USERNAME:         $($Config['DOCKER_USERNAME'])" "White"
    Write-ColorOutput "  STACK_NAME:              $($Config['STACK_NAME'])" "White"
    Write-ColorOutput "  FRONTEND_PORT:           $($Config['FRONTEND_PORT'])" "White"
    Write-ColorOutput "  BACKEND_PROXY_PORT:      $($Config['BACKEND_PROXY_PORT'])" "White"
    Write-ColorOutput "  SQL_GENERATOR_PORT:      $($Config['SQL_GENERATOR_PORT'])" "White"
    Write-ColorOutput "  QDRANT_PORT:             $($Config['QDRANT_PORT'])" "White"
    Write-ColorOutput "  MERMAID_SERVICE_PORT:    $($Config['MERMAID_SERVICE_PORT'])" "White"
    Write-ColorOutput "  WEB_PORT:                $($Config['WEB_PORT'])" "White"
    Write-ColorOutput "  BACKEND_PORT:            $($Config['BACKEND_PORT'])" "White"

    return $Config
}

# Function to build images locally
function Build-Images {
    Write-ColorOutput "=== Building Docker images locally ===" "Cyan"
    Write-ColorOutput "" "White"

    # Check if install.sh exists (for WSL/Git Bash) or install.ps1
    $usePowerShell = $false
    if (Test-Path "install.ps1") {
        $usePowerShell = $true
    }
    elseif (-not (Test-Path "install.sh")) {
        Write-ColorOutput "Error: Neither install.sh nor install.ps1 found in current directory" "Red"
        exit 1
    }

    if ($usePowerShell) {
        Write-ColorOutput "Running .\install.ps1 to build images and generate .env.docker..." "Yellow"
        if ($LASTEXITCODE -eq 0) {
            & ".\install.ps1"
        } else {
            & ".\install.ps1"
        }
    } else {
        # Try WSL first, then Git Bash
        $bashCmd = $null
        if (Test-Command "wsl") {
            Write-ColorOutput "Running ./install.sh via WSL to build images and generate .env.docker..." "Yellow"
            $bashCmd = "wsl bash ./install.sh"
        } elseif (Test-Command "bash") {
            Write-ColorOutput "Running ./install.sh via Git Bash to build images and generate .env.docker..." "Yellow"
            $bashCmd = "bash ./install.sh"
        } else {
            Write-ColorOutput "Error: Neither WSL nor Git Bash is available. Please install WSL or Git for Windows." "Red"
            exit 1
        }

        Invoke-Expression $bashCmd
    }

    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "✓ Images built successfully" "Green"
    } else {
        Write-ColorOutput "✗ Failed to build images" "Red"
        exit 1
    }
}

# Function to tag images with Docker Hub username
function Tag-Images {
    param(
        [string]$DockerUsername
    )

    Write-ColorOutput "=== Tagging images for Docker Hub ===" "Cyan"
    Write-ColorOutput "" "White"

    $registryUrl = $DockerUsername
    $version = "latest"

    # Images to tag
    $images = @{
        "backend" = "thoth-backend"
        "frontend" = "thoth-frontend"
        "sql-generator" = "thoth-sql-generator"
        "proxy" = "thoth-proxy"
        "mermaid-service" = "thoth-mermaid-service"
        "qdrant" = "thoth-qdrant"
    }

    foreach ($localName in $images.Keys) {
        $imageName = $images[$localName]

        if ($localName -eq "qdrant") {
            # Qdrant is pulled from official registry
            Write-ColorOutput "Tagging qdrant/qdrant:latest..." "Yellow"
            try {
                docker tag qdrant/qdrant:latest "$registryUrl/$imageName`:$version" 2>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-ColorOutput "✓ Tagged $registryUrl/$imageName`:$version" "Green"
                } else {
                    Write-ColorOutput "Warning: Could not tag qdrant/qdrant (may not exist locally)" "Yellow"
                }
            }
            catch {
                Write-ColorOutput "Warning: Could not tag qdrant/qdrant (may not exist locally)" "Yellow"
            }
        } else {
            # Check if local image exists
            $localImage = "thoth-$localName`:latest"
            $imageExists = docker images -q $localImage 2>$null
            if (-not [string]::IsNullOrWhiteSpace($imageExists)) {
                Write-ColorOutput "Tagging thoth-$localName`:latest..." "Yellow"
                docker tag $localImage "$registryUrl/$imageName`:$version"
                if ($LASTEXITCODE -eq 0) {
                    Write-ColorOutput "✓ Tagged $registryUrl/$imageName`:$version" "Green"
                } else {
                    Write-ColorOutput "✗ Failed to tag $imageName" "Red"
                    exit 1
                }
            } else {
                Write-ColorOutput "Warning: thoth-$localName`:latest not found, skipping" "Yellow"
            }
        }
    }
}

# Function to push images to Docker Hub
function Push-Images {
    param(
        [string]$DockerUsername
    )

    Write-ColorOutput "=== Pushing images to Docker Hub ===" "Cyan"
    Write-ColorOutput "" "White"

    $registryUrl = $DockerUsername
    $version = "latest"

    # Check if logged in to Docker Hub
    Write-ColorOutput "Checking Docker Hub login..." "Yellow"
    $dockerInfo = docker info 2>&1
    if ($dockerInfo -notmatch "Username:\s+$DockerUsername") {
        Write-ColorOutput "Please login to Docker Hub:" "Yellow"
        docker login
        if ($LASTEXITCODE -ne 0) {
            Write-ColorOutput "✗ Docker Hub login failed" "Red"
            exit 1
        }
    }
    Write-ColorOutput "✓ Docker Hub login verified" "Green"
    Write-ColorOutput "" "White"

    # Images to push
    $images = @{
        "backend" = "thoth-backend"
        "frontend" = "thoth-frontend"
        "sql-generator" = "thoth-sql-generator"
        "proxy" = "thoth-proxy"
        "mermaid-service" = "thoth-mermaid-service"
        "qdrant" = "thoth-qdrant"
    }

    foreach ($localName in $images.Keys) {
        $imageName = $images[$localName]
        $fullTag = "$registryUrl/$imageName`:$version"

        Write-ColorOutput "Pushing $fullTag..." "Yellow"
        docker push $fullTag
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✓ Pushed $fullTag" "Green"
        } else {
            Write-ColorOutput "✗ Failed to push $fullTag" "Red"
            exit 1
        }
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
        '${VERSION}' = "latest"
        '${FRONTEND_PORT}' = $Config['FRONTEND_PORT']
        '${BACKEND_PORT}' = $Config['BACKEND_PORT']
        '${SQL_GENERATOR_PORT}' = $Config['SQL_GENERATOR_PORT']
        '${MERMAID_SERVICE_PORT}' = $Config['MERMAID_SERVICE_PORT']
        '${WEB_PORT}' = $Config['WEB_PORT']
    }

    foreach ($key in $replacements.Keys) {
        $stackContent = $stackContent -replace [regex]::Escape($key), $replacements[$key]
    }

    # Write to docker-stack-swarm.yml
    Write-ColorOutput "Creating docker-stack-swarm.yml with port substitutions..." "Yellow"
    $stackContent | Out-File -FilePath "docker-stack-swarm.yml" -Encoding utf8
    Write-ColorOutput "✓ docker-stack-swarm.yml created" "Green"
}

# Function to deploy stack to remote Swarm
function Deploy-Stack {
    param(
        [string]$SshServer,
        [int]$SshPort,
        [string]$SshKey,
        [hashtable]$Config
    )

    Write-ColorOutput "=== Deploying to remote Docker Swarm ===" "Cyan"
    Write-ColorOutput "" "White"

    # Set DOCKER_HOST for SSH connection
    $dockerHost = "ssh://$SshServer`:$SshPort"
    Write-ColorOutput "Setting DOCKER_HOST=$dockerHost" "Yellow"
    $env:DOCKER_HOST = $dockerHost

    # Add SSH key to agent if specified (requires Pageant for PuTTY or ssh-agent for OpenSSH)
    if (Test-Path $SshKey) {
        Write-ColorOutput "SSH key found at $SshKey" "Yellow"
        Write-ColorOutput "Note: Ensure your SSH key is loaded in ssh-agent or Pageant" "Yellow"
    } else {
        Write-ColorOutput "Warning: SSH key not found at $SshKey" "Yellow"
        Write-ColorOutput "Continuing anyway (assuming SSH agent has the key or password auth)" "Yellow"
    }

    # Check if Swarm is active on remote
    Write-ColorOutput "Checking Swarm status on remote host..." "Yellow"
    $dockerInfo = docker info 2>&1
    if ($dockerInfo -notmatch "Swarm:\s+active") {
        Write-ColorOutput "Error: Docker Swarm is not active on the remote host" "Red"
        Write-ColorOutput "Please initialize Swarm on the remote host: docker swarm init" "Yellow"
        exit 1
    }
    Write-ColorOutput "✓ Swarm is active on remote host" "Green"
    Write-ColorOutput "" "White"

    # Create secrets and configs on remote
    Write-ColorOutput "Creating secrets and configs on remote Swarm..." "Yellow"

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

    # Deploy stack
    Write-ColorOutput "Deploying stack '$stackName' to remote Swarm..." "Yellow"
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
        [string]$SshServer,
        [hashtable]$Config
    )

    Write-ColorOutput "=== Access URLs ===" "Green"
    Write-ColorOutput "" "White"

    Write-ColorOutput "The following services should be accessible at:" "White"
    Write-ColorOutput "  Frontend (Next.js):     http://$SshServer`:$($Config['FRONTEND_PORT'])" "Yellow"
    Write-ColorOutput "  Backend (Django):       http://$SshServer`:$($Config['BACKEND_PROXY_PORT'])/api" "Yellow"
    Write-ColorOutput "  Admin Panel:             http://$SshServer`:$($Config['BACKEND_PROXY_PORT'])/admin" "Yellow"
    Write-ColorOutput "  SQL Generator:          http://$SshServer`:$($Config['SQL_GENERATOR_PORT'])" "Yellow"
    Write-ColorOutput "  Mermaid Service:        http://$SshServer`:$($Config['MERMAID_SERVICE_PORT'])" "Yellow"
    Write-ColorOutput "  Qdrant Dashboard:       http://$SshServer`:$($Config['QDRANT_PORT'])/dashboard" "Yellow"
    Write-ColorOutput "  Web (Proxy):            http://$SshServer`:$($Config['WEB_PORT'])" "Yellow"
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
    if ($PSBoundParameters.ContainsKey('Help') -or $args -contains '-help' -or $args -contains '--help') {
        Show-Usage
        exit 0
    }

    Write-ColorOutput "============================================" "Cyan"
    Write-ColorOutput "  ThothAI - Docker Swarm Deployment" "Cyan"
    Write-ColorOutput "============================================" "Cyan"
    Write-ColorOutput "" "White"

    Write-ColorOutput "Remote Server:" "Yellow"
    Write-ColorOutput "  Server:  $Server" "White"
    Write-ColorOutput "  Port:    $Port" "White"
    Write-ColorOutput "  SSH Key: $Key" "White"
    Write-ColorOutput "" "White"

    # Check prerequisites
    Write-ColorOutput "Checking prerequisites..." "Yellow"

    if (-not (Test-Command "docker")) {
        Write-ColorOutput "Error: Docker is not installed" "Red"
        exit 1
    }

    if (-not (Test-Command "ssh")) {
        Write-ColorOutput "Error: SSH client is not installed" "Red"
        exit 1
    }

    Write-ColorOutput "✓ Prerequisites OK" "Green"
    Write-ColorOutput "" "White"

    # Load and validate configuration
    $config = Load-SwarmConfig
    $config = Test-Config -Config $config
    Write-ColorOutput "" "White"

    # Build images locally
    Build-Images
    Write-ColorOutput "" "White"

    # Tag images
    Tag-Images -DockerUsername $config['DOCKER_USERNAME']
    Write-ColorOutput "" "White"

    # Push images
    Push-Images -DockerUsername $config['DOCKER_USERNAME']
    Write-ColorOutput "" "White"

    # Prepare stack file
    Prepare-StackFile -Config $config
    Write-ColorOutput "" "White"

    # Deploy to remote Swarm
    Deploy-Stack -SshServer $Server -SshPort $Port -SshKey $Key -Config $config
    Write-ColorOutput "" "White"

    # Wait for services
    if (Wait-ForServices -StackName $config['STACK_NAME']) {
        Write-ColorOutput "✓ Services started successfully" "Green"
    } else {
        Write-ColorOutput "⚠ Some services may still be starting" "Yellow"
    }
    Write-ColorOutput "" "White"

    # Show deployment status
    Show-DeploymentStatus -StackName $config['STACK_NAME']
    Write-ColorOutput "" "White"

    # Show access URLs
    Show-AccessUrls -SshServer $Server -Config $config

    Write-ColorOutput "============================================" "Green"
    Write-ColorOutput "  Deployment completed!" "Green"
    Write-ColorOutput "============================================" "Green"
    Write-ColorOutput "" "White"
}
catch {
    Write-ColorOutput "Error: $($_.Exception.Message)" "Red"
    Write-ColorOutput $_.ScriptStackTrace "Red"
    exit 1
}
