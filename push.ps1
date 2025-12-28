param(
    [string]$RegistryUrl = "registry.uni.com/tylconsulting/thothai",
    [string]$Version = "0.1",
    [switch]$NoCache,
    [switch]$PushOnly
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

Write-ColorOutput "============================================" "Blue"
Write-ColorOutput "  ThothAI - Build and Push Docker Images" "Blue"
Write-ColorOutput "============================================" "Blue"
Write-Host ""
Write-ColorOutput "Registry: $RegistryUrl" "Yellow"
Write-ColorOutput "Version:  $Version" "Yellow"
Write-Host ""

# Check Prerequisites
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Fail "Error: Docker not found" }

# === PHASE 1: BUILD ===
if (-not $PushOnly.IsPresent) {
    Write-ColorOutput "=== PHASE 1: Build images ===" "Blue"
    Write-Host ""

    # Python Check
    $python = if (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" }
              elseif (Get-Command python -ErrorAction SilentlyContinue) { "python" }
              else { Fail "Python 3.9+ not found" }

    # Config Check
    if (-not (Test-Path "config.yml.local")) { Fail "config.yml.local missing" }

    # Normalize CRLF -> LF (optional but recommended for Windows)
    if (Get-Command dos2unix -ErrorAction SilentlyContinue) {
        $targets = @()
        $targets += Get-ChildItem -Path "docker" -Recurse -Include *.sh -File -ErrorAction SilentlyContinue
        $targets += Get-ChildItem -Path "backend" -Recurse -Include *.sh -File -ErrorAction SilentlyContinue
        $targets += Get-ChildItem -Path "frontend" -Recurse -Include *.sh -File -ErrorAction SilentlyContinue
        if ($targets.Count -gt 0) {
            Write-ColorOutput "Normalizing line endings with dos2unix..." "Cyan"
            foreach ($f in $targets) { dos2unix $f.FullName *> $null }
        }
    } else {
        Write-ColorOutput "dos2unix not found: skipping CRLF normalization." "Yellow"
    }

    # Generate Configurations
    Write-ColorOutput "Generating configuration files..." "Yellow"
    & $python -m pip install --quiet pyyaml requests toml
    & $python scripts/validate_config.py config.yml.local
    & $python scripts/configure_embedding.py config.yml.local
    & $python scripts/installer.py --generate-env-only
    & $python scripts/merge_pyproject.py backend
    & $python scripts/merge_pyproject.py frontend/sql_generator

    # Verify Generations
    if (-not (Test-Path "backend/pyproject.toml.merged")) { Fail "backend/pyproject.toml.merged missing" }
    if (-not (Test-Path "backend/uv.lock")) { Fail "backend/uv.lock missing" }
    if (-not (Test-Path "frontend/sql_generator/pyproject.toml.merged")) { Fail "frontend/sql_generator/pyproject.toml.merged missing" }

    # Build Flags
    $cacheFlag = if ($NoCache.IsPresent) { "--no-cache" } else { "" }

    # Define Images
    $imagesToBuild = @{
        "thoth-backend"         = @{ Dockerfile="docker/backend.Dockerfile"; Context="." }
        "thoth-frontend"        = @{ Dockerfile="docker/frontend.Dockerfile"; Context="./frontend" }
        "thoth-sql-generator"   = @{ Dockerfile="docker/sql-generator.Dockerfile"; Context="." }
        "thoth-proxy"           = @{ Dockerfile="docker/proxy.Dockerfile"; Context="./backend/proxy" }
        "thoth-mermaid-service" = @{ Dockerfile="docker/mermaid-service/Dockerfile"; Context="./docker/mermaid-service" }
    }

    foreach ($name in $imagesToBuild.Keys) {
        $cfg = $imagesToBuild[$name]
        Write-ColorOutput "Building $name..." "Yellow"
        
        $params = @("build", $cacheFlag, "-f", $cfg.Dockerfile, 
                    "-t", "$RegistryUrl/$name`:$Version", 
                    "-t", "$RegistryUrl/$name`:latest", 
                    $cfg.Context)
        # Filter empty strings
        $params = $params | Where-Object { $_ -ne "" }
        
        docker @params
        if ($LASTEXITCODE -ne 0) { Fail "Build failed for $name" }
        Write-ColorOutput "✓ Build completed for $name" "Green"
        Write-Host ""
    }

    # Pull Qdrant
    Write-ColorOutput "Pulling Qdrant..." "Yellow"
    docker pull qdrant/qdrant:latest
    docker tag qdrant/qdrant:latest "$RegistryUrl/thoth-qdrant:$Version"
    docker tag qdrant/qdrant:latest "$RegistryUrl/thoth-qdrant:latest"
    Write-Host ""

} else {
    Write-ColorOutput "=== PHASE 1: Build skipped (-PushOnly) ===" "Yellow"
    Write-Host ""
}

# === PHASE 2: PUSH ===
Write-ColorOutput "=== PHASE 2: Push images to registry ===" "Blue"
Write-Host ""

Write-ColorOutput "Remember: You must be logged in to $RegistryUrl" "Yellow"

$allImages = @(
    "thoth-backend",
    "thoth-frontend",
    "thoth-sql-generator",
    "thoth-proxy",
    "thoth-mermaid-service",
    "thoth-qdrant"
)

foreach ($img in $allImages) {
    # Push Version Tag
    $tagVer = "$RegistryUrl/$img`:$Version"
    Write-ColorOutput "Pushing $tagVer..." "Yellow"
    docker push $tagVer
    if ($LASTEXITCODE -ne 0) { Fail "Push failed for $tagVer" }
    Write-ColorOutput "✓ Push completed for $img`:$Version" "Green"

    # Push Latest Tag
    $tagLatest = "$RegistryUrl/$img`:latest"
    Write-ColorOutput "Pushing $tagLatest..." "Yellow"
    docker push $tagLatest
    if ($LASTEXITCODE -ne 0) { Fail "Push failed for $tagLatest" }
    Write-ColorOutput "✓ Push completed for $img`:latest" "Green"
    
    Write-Host ""
}

Write-ColorOutput "============================================" "Green"
Write-ColorOutput "  Build and Push completed successfully!" "Green"
Write-ColorOutput "============================================" "Green"
Write-Host ""
Write-ColorOutput "Next step: Deploy with .\install-swarm.ps1" "Cyan"
