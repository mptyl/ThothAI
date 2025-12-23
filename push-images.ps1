param(
    [string]$RegistryUrl = "registry.uni.com/tylconsulting/thothai",
    [string]$Version = "0.1",
    [switch]$PushLatest
)

$ErrorActionPreference = "Stop"

function Fail($msg) { Write-Host $msg -ForegroundColor Red; exit 1 }

# Porta la working directory nella cartella dello script
$scriptPath = if ($PSScriptRoot) { $PSScriptRoot } else { Get-Location }
Set-Location $scriptPath

# Controlli minimi
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Fail "Docker non trovato" }

# Liste immagini da pushare
$images = @(
    "thoth-backend",
    "thoth-frontend",
    "thoth-sql-generator",
    "thoth-proxy",
    "thoth-mermaid-service"
)

Write-Host "Push verso $RegistryUrl con tag $Version" -ForegroundColor Cyan
Write-Host "Assicurati di aver eseguito 'docker login $RegistryUrl'" -ForegroundColor Yellow

foreach ($img in $images) {
    $tag = "$RegistryUrl/$img`:$Version"
    Write-Host "Push $tag" -ForegroundColor Gray
    docker push $tag
    if ($LASTEXITCODE -ne 0) { Fail "Push fallito per $tag" }

    if ($PushLatest.IsPresent) {
        $latestTag = "$RegistryUrl/$img`:latest"
        Write-Host "Push $latestTag" -ForegroundColor DarkGray
        docker push $latestTag
        if ($LASTEXITCODE -ne 0) { Fail "Push fallito per $latestTag" }
    }
}

Write-Host "Push completato. Ora copia i file sul server e lancia stackswarm.sh" -ForegroundColor Green
