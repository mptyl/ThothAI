param(
    [string]$RegistryUrl = "registry.uni.com/tylconsulting/thothai",
    [string]$Version = "0.1",
    [switch]$NoCache
)

$ErrorActionPreference = "Stop"

function Fail($msg) { Write-Host $msg -ForegroundColor Red; exit 1 }

# Change working directory to script folder
$scriptPath = if ($PSScriptRoot) { $PSScriptRoot } else { Get-Location }
Set-Location $scriptPath

# Normalize CRLF -> LF for scripts used in build (requires dos2unix in PATH)
if (Get-Command dos2unix -ErrorAction SilentlyContinue) {
    $targets = @()
    $targets += Get-ChildItem -Path "docker" -Recurse -Include *.sh -File -ErrorAction SilentlyContinue
    $targets += Get-ChildItem -Path "backend" -Recurse -Include *.sh -File -ErrorAction SilentlyContinue
    $targets += Get-ChildItem -Path "frontend" -Recurse -Include *.sh -File -ErrorAction SilentlyContinue
    if ($targets.Count -gt 0) {
        Write-Host "Normalizing line ending with dos2unix..." -ForegroundColor Cyan
        foreach ($f in $targets) { dos2unix $f.FullName *> $null }
    } else {
        Write-Host "No .sh files found for dos2unix" -ForegroundColor DarkGray
    }
} else {
    Write-Host "dos2unix not found: skip CRLF normalization. Install it or use Git for Windows to add it to PATH." -ForegroundColor Yellow
}

# Prerequisites
if (-not (Test-Path "config.yml.local")) { Fail "config.yml.local missing" }
$python = if (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" }
          elseif (Get-Command python -ErrorAction SilentlyContinue) { "python" }
          else { Fail "Python 3.9+ not found" }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Fail "Docker not found" }

# Minimum Python dependencies (silent)
& $python -m pip install --quiet pyyaml requests toml

# Generate necessary files (.env.docker, backend/pyproject.toml.merged, backend/uv.lock)
& $python scripts/validate_config.py config.yml.local
& $python scripts/configure_embedding.py config.yml.local
& $python scripts/installer.py --generate-env-only
& $python scripts/merge_pyproject.py backend
& $python scripts/merge_pyproject.py frontend/sql_generator

# Verify generated files exist before build
if (-not (Test-Path "backend/pyproject.toml.merged")) {
    Fail "backend/pyproject.toml.merged missing. Regenerate with: $python scripts/merge_pyproject.py backend"
}
if (-not (Test-Path "backend/uv.lock")) {
    Fail "backend/uv.lock missing. Regenerate with: $python scripts/installer.py --generate-env-only"
}
if (-not (Test-Path "frontend/sql_generator/pyproject.toml.merged")) {
    Fail "frontend/sql_generator/pyproject.toml.merged missing. Regenerate with: $python scripts/merge_pyproject.py frontend/sql_generator"
}

# PowerShell 5.1 compat: no ternary operator
if ($NoCache.IsPresent) {
    $cacheFlag = "--no-cache"
} else {
    $cacheFlag = ""
}

# Build images (context root, Dockerfile in docker/)
docker build $cacheFlag -f docker/backend.Dockerfile           -t "$RegistryUrl/thoth-backend:$Version"           .
docker build $cacheFlag -f docker/frontend.Dockerfile          -t "$RegistryUrl/thoth-frontend:$Version"          ./frontend
docker build $cacheFlag -f docker/sql-generator.Dockerfile     -t "$RegistryUrl/thoth-sql-generator:$Version"     .
docker build $cacheFlag -f docker/proxy.Dockerfile             -t "$RegistryUrl/thoth-proxy:$Version"             ./backend/proxy
docker build $cacheFlag -f docker/mermaid-service/Dockerfile   -t "$RegistryUrl/thoth-mermaid-service:$Version"   ./docker/mermaid-service

# Optional latest tags
docker tag "$RegistryUrl/thoth-backend:$Version"           "$RegistryUrl/thoth-backend:latest"
docker tag "$RegistryUrl/thoth-frontend:$Version"          "$RegistryUrl/thoth-frontend:latest"
docker tag "$RegistryUrl/thoth-sql-generator:$Version"     "$RegistryUrl/thoth-sql-generator:latest"
docker tag "$RegistryUrl/thoth-proxy:$Version"             "$RegistryUrl/thoth-proxy:latest"
docker tag "$RegistryUrl/thoth-mermaid-service:$Version"   "$RegistryUrl/thoth-mermaid-service:latest"

Write-Host "Build completed. Now you can execute docker push/tag or deploy swarm." -ForegroundColor Green
