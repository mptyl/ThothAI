param(
    [string]$RegistryUrl = "registry.uni.com/tylconsulting/thothai",
    [string]$Version = "0.1",
    [int]$FrontendPort = 3040,
    [int]$BackendPort = 8040,
    [int]$SqlGeneratorPort = 8020,
    [int]$MermaidPort = 8003,
    [int]$WebPort = 8040
)

$ErrorActionPreference = "Stop"

function Fail($msg) { Write-Host $msg -ForegroundColor Red; exit 1 }

# Porta la working directory nella cartella dello script
$scriptPath = if ($PSScriptRoot) { $PSScriptRoot } else { Get-Location }
Set-Location $scriptPath

# Controlli minimi
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Fail "Docker non trovato" }

# Verifica requisiti Swarm
try { docker info --format '{{.Swarm.LocalNodeState}}' | Select-String -Pattern "active" -Quiet | Out-Null } catch { }
if ($LASTEXITCODE -ne 0) { Fail "Swarm non attivo. Esegui 'docker swarm init' o unisciti a un cluster." }

# Richiede secrets/config già creati: thoth_env_config, thoth_config_yml, thoth_env_docker
# Richiede immagini già buildate e presenti nel registry con $RegistryUrl e $Version

# Imposta variabili d'ambiente per docker stack deploy
$env:REGISTRY_URL = $RegistryUrl
$env:VERSION = $Version
$env:FRONTEND_PORT = $FrontendPort
$env:BACKEND_PORT = $BackendPort
$env:SQL_GENERATOR_PORT = $SqlGeneratorPort
$env:MERMAID_SERVICE_PORT = $MermaidPort
$env:WEB_PORT = $WebPort

Write-Host "Deploy stack con le porte pubblicate:" -ForegroundColor Cyan
Write-Host "  FRONTEND_PORT=$FrontendPort" -ForegroundColor Gray
Write-Host "  BACKEND_PORT=$BackendPort" -ForegroundColor Gray
Write-Host "  SQL_GENERATOR_PORT=$SqlGeneratorPort" -ForegroundColor Gray
Write-Host "  MERMAID_SERVICE_PORT=$MermaidPort" -ForegroundColor Gray
Write-Host "  WEB_PORT=$WebPort" -ForegroundColor Gray

# Deploy dello stack
$stackName = "thoth"
docker stack deploy -c docker-stack.yml $stackName

if ($LASTEXITCODE -eq 0) {
    Write-Host "Deploy avviato. Verifica con: docker stack services $stackName" -ForegroundColor Green
} else {
    Fail "Deploy fallito"
}
