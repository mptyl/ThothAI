param(
    [string]$RegistryUrl = "registry.uni.com/tylconsulting/thothai",
    [string]$Version = "0.1",
    [switch]$NoCache
)

$ErrorActionPreference = "Stop"

function Fail($msg) { Write-Host $msg -ForegroundColor Red; exit 1 }

# Porta la working directory nella cartella dello script
$scriptPath = if ($PSScriptRoot) { $PSScriptRoot } else { Get-Location }
Set-Location $scriptPath

# Prerequisiti
if (-not (Test-Path "config.yml.local")) { Fail "config.yml.local mancante" }
$python = if (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" }
          elseif (Get-Command python -ErrorAction SilentlyContinue) { "python" }
          else { Fail "Python 3.9+ non trovato" }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Fail "Docker non trovato" }

# Dipendenze Python minime (silenzioso)
& $python -m pip install --quiet pyyaml requests toml

# Genera i file necessari (.env.docker, backend/pyproject.toml.merged, backend/uv.lock)
& $python scripts/validate_config.py config.yml.local
& $python scripts/configure_embedding.py config.yml.local
& $python scripts/installer.py --generate-env-only

$cacheFlag = $NoCache.IsPresent ? "--no-cache" : ""

# Build immagini (context root, Dockerfile in docker/)
docker build $cacheFlag -f docker/backend.Dockerfile           -t "$RegistryUrl/thoth-backend:$Version"           .
docker build $cacheFlag -f docker/frontend.Dockerfile          -t "$RegistryUrl/thoth-frontend:$Version"          ./frontend
docker build $cacheFlag -f docker/sql-generator.Dockerfile     -t "$RegistryUrl/thoth-sql-generator:$Version"     .
docker build $cacheFlag -f docker/proxy.Dockerfile             -t "$RegistryUrl/thoth-proxy:$Version"             ./backend/proxy
docker build $cacheFlag -f docker/mermaid-service/Dockerfile   -t "$RegistryUrl/thoth-mermaid-service:$Version"   ./docker/mermaid-service

# Tag facoltativi latest
docker tag "$RegistryUrl/thoth-backend:$Version"           "$RegistryUrl/thoth-backend:latest"
docker tag "$RegistryUrl/thoth-frontend:$Version"          "$RegistryUrl/thoth-frontend:latest"
docker tag "$RegistryUrl/thoth-sql-generator:$Version"     "$RegistryUrl/thoth-sql-generator:latest"
docker tag "$RegistryUrl/thoth-proxy:$Version"             "$RegistryUrl/thoth-proxy:latest"
docker tag "$RegistryUrl/thoth-mermaid-service:$Version"   "$RegistryUrl/thoth-mermaid-service:latest"

Write-Host "Build completata. Ora puoi eseguire docker push/tag o deploy swarm." -ForegroundColor Green
