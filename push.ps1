param(
    [string]$RegistryUrl = "registry.uni.com/tylconsulting/thothai",
    [string]$Version = "0.1",
    [switch]$NoCache,
    [switch]$PushOnly,
    [string]$Platforms = "linux/amd64,linux/arm64"
)

$ErrorActionPreference = "Stop"

function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

function Fail($msg) { Write-ColorOutput $msg "Red"; exit 1 }

# Change working directory to script folder
$scriptPath = if ($PSScriptRoot) { $PSScriptRoot } else { Get-Location }
Set-Location $scriptPath

Write-ColorOutput "=================================================" "Blue"
Write-ColorOutput "  ThothAI - Multi-platform Build and Push" "Blue"
Write-ColorOutput "=================================================" "Blue"
Write-Host ""
Write-ColorOutput "Registry:  $RegistryUrl" "Yellow"
Write-ColorOutput "Version:   $Version" "Yellow"
Write-ColorOutput "Platforms: $Platforms" "Yellow"
Write-Host ""

# Check Prerequisites
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Fail "Error: Docker not found" }

# Ensure buildx builder exists and is used
Write-ColorOutput "Checking buildx setup..." "Yellow"
$builders = docker buildx ls
if ($builders -notmatch "thoth-builder") {
    Write-ColorOutput "Creating new buildx builder 'thoth-builder'..." "Cyan"
    docker buildx create --name thoth-builder --use --bootstrap
} else {
    docker buildx use thoth-builder
}
Write-ColorOutput "[OK] Buildx ready" "Green"
Write-Host ""

# === PHASE 1: BUILD ===
if (-not $PushOnly.IsPresent) {
    Write-ColorOutput "=== PHASE 1: Build and Push (Multi-platform) ===" "Blue"
    Write-Host ""

    # Python Check
    $python = if (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" }
              elseif (Get-Command python -ErrorAction SilentlyContinue) { "python" }
              else { Fail "Python 3.9+ not found" }

    # Generate Configurations
    Write-ColorOutput "Generating configuration files..." "Yellow"
    & $python -m pip install --quiet pyyaml requests toml
    & $python scripts/validate_config.py config.yml.local
    & $python scripts/configure_embedding.py config.yml.local
    & $python scripts/installer.py --generate-env-only
    & $python scripts/merge_pyproject.py backend
    & $python scripts/merge_pyproject.py frontend/sql_generator

    # Define Images
    $imagesToBuild = @{
        "thoth-backend"         = @{ Dockerfile="docker/backend.Dockerfile"; Context="." }
        "thoth-frontend"        = @{ Dockerfile="docker/frontend.Dockerfile"; Context="./frontend" }
        "thoth-sql-generator"   = @{ Dockerfile="docker/sql-generator.Dockerfile"; Context="." }
        "thoth-proxy"           = @{ Dockerfile="docker/proxy.Dockerfile"; Context="./backend/proxy" }
        "thoth-mermaid-service" = @{ Dockerfile="docker/mermaid-service/Dockerfile"; Context="./docker/mermaid-service" }
    }

    $cacheFlag = if ($NoCache.IsPresent) { "--no-cache" } else { "" }

    foreach ($name in $imagesToBuild.Keys) {
        $cfg = $imagesToBuild[$name]
        Write-ColorOutput "Building and Pushing $name..." "Yellow"
        
        $params = @("buildx", "build", $cacheFlag, 
                    "-f", $cfg.Dockerfile, 
                    "--platform", $Platforms,
                    "-t", "$RegistryUrl/$name`:$Version", 
                    "-t", "$RegistryUrl/$name`:latest", 
                    "--push",
                    $cfg.Context)
        # Filter empty strings
        $params = $params | Where-Object { $_ -ne "" }
        
        docker @params
        if ($LASTEXITCODE -ne 0) { Fail "Build/Push failed for $name" }
        Write-ColorOutput "[OK] Completed for $name" "Green"
        Write-Host ""
    }

    # Process Qdrant via imagetools
    Write-ColorOutput "Processing Qdrant via imagetools..." "Yellow"
    docker buildx imagetools create -t "$RegistryUrl/thoth-qdrant:$Version" qdrant/qdrant:latest
    docker buildx imagetools create -t "$RegistryUrl/thoth-qdrant:latest" qdrant/qdrant:latest
    if ($LASTEXITCODE -ne 0) { Fail "Qdrant processing failed" }
    Write-ColorOutput "[OK] Qdrant ready (multi-platform preserved)" "Green"
    Write-Host ""

} else {
    Write-ColorOutput "=== PHASE 1: Build skipped (-PushOnly) ===" "Yellow"
    Write-Host ""
}

Write-ColorOutput "=================================================" "Green"
Write-ColorOutput "  Success! Multi-platform images pushed." "Green"
Write-ColorOutput "=================================================" "Green"
Write-Host ""
Write-ColorOutput "Next step: Deploy with .\install-swarm.ps1" "Cyan"
Write-Host ""
