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
$RegistryUrl = "registry.uni.com/tylconsulting/ThothAI"
$Version = "latest"
$StackName = "thoth"
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
    Write-ColorOutput "=== Verifica prerequisiti ===" "Blue"

    # Check Docker
    try {
        Invoke-Docker "info" > $null 2>&1
        if ($LASTEXITCODE -ne 0) { throw }
    } catch {
        Write-ColorOutput "Errore: Docker non è raggiungibile" "Red"
        exit 1
    }

    # Check Swarm
    $info = Invoke-Docker "info"
    if ($info -notmatch "Swarm: active") {
        Write-ColorOutput "Errore: Docker Swarm non è attivo sul target. Esegui 'docker swarm init'" "Red"
        exit 1
    }

    # Check config files (local check)
    if (-not (Test-Path "config.yml.local")) {
        Write-ColorOutput "Errore: config.yml.local non trovato" "Red"
        exit 1
    }

    if (-not (Test-Path ".env.docker")) {
        Write-ColorOutput "Errore: .env.docker non trovato. Esegui prima lo script di configurazione" "Red"
        exit 1
    }

    if (-not (Test-Path "docker-stack.yml")) {
        Write-ColorOutput "Errore: docker-stack.yml non trovato" "Red"
        exit 1
    }

    Write-ColorOutput "✓ Prerequisiti verificati" "Green"
}

function Backup-Volumes {
    Write-ColorOutput "=== Backup dei volumi ===" "Blue"

    $Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $BackupPath = "$BackupDir/$Timestamp"
    
    # Questo comando crea la directory sul REMOTE host se usiamo remote host?
    # No, i comandi docker run vengono eseguiti nel contesto del daemon docker.
    # Se il daemon è remoto, il backup avviene sui volumi remoti, ma dove salviamo il tar?
    # Se montiamo -v /backup:/backup, è path del server remoto.
    
    # Creiamo la directory di backup (se remoto, questo comando mkdir locale non serve a nulla per il docker remoto bind mount)
    # Assumiamo che la directory esista o venga creata nel container
    
    # Backup database
    Write-ColorOutput "Backup database..." "Yellow"
    Invoke-Docker "run", "--rm",
        "-v", "thoth_backend-db:/data",
        "-v", "$BackupPath`:/backup",
        "alpine", "sh", "-c", "mkdir -p /backup && tar czf /backup/backend-db.tar.gz -C /data . 2>/dev/null || true" | Out-Null

    # Backup Qdrant
    Write-ColorOutput "Backup Qdrant..." "Yellow"
    Invoke-Docker "run", "--rm",
        "-v", "thoth_qdrant-data:/data",
        "-v", "$BackupPath`:/backup",
        "alpine", "sh", "-c", "mkdir -p /backup && tar czf /backup/qdrant-data.tar.gz -C /data . 2>/dev/null || true" | Out-Null
        
    # Backup data-exchange
    Write-ColorOutput "Backup thoth-data-exchange..." "Yellow"
    Invoke-Docker "run", "--rm",
        "-v", "thoth-data-exchange:/data",
        "-v", "$BackupPath`:/backup",
        "alpine", "sh", "-c", "mkdir -p /backup && tar czf /backup/data-exchange.tar.gz -C /data . 2>/dev/null || true" | Out-Null

    Write-ColorOutput "✓ Backup (best effort) completato in $BackupPath sul nodo swarm" "Green"
}

function Update-Secrets {
    Write-ColorOutput "=== Aggiornamento Secrets ===" "Blue"

    Invoke-Docker "secret", "rm", "thoth_env_config" 2>$null | Out-Null
    Invoke-Docker "secret", "rm", "thoth_config_yml" 2>$null | Out-Null
    Invoke-Docker "config", "rm", "thoth_env_docker" 2>$null | Out-Null

    Invoke-Docker "secret", "create", "thoth_env_config", ".env.docker" | Out-Null
    Invoke-Docker "secret", "create", "thoth_config_yml", "config.yml.local" | Out-Null
    Invoke-Docker "config", "create", "thoth_env_docker", ".env.docker" | Out-Null

    Write-ColorOutput "✓ Secrets aggiornati" "Green"
}

function Deploy-Stack {
    Write-ColorOutput "=== Deploy dello Stack ===" "Blue"

    # Set env vars for docker stack
    $env:REGISTRY_URL = $RegistryUrl
    $env:VERSION = $Version
    $env:WEB_PORT = $WebPort
    $env:FRONTEND_PORT = $FrontendPort
    $env:BACKEND_PORT = $BackendPort
    $env:SQL_GENERATOR_PORT = $SqlGeneratorPort
    $env:MERMAID_SERVICE_PORT = $MermaidServicePort
    $env:QDRANT_PORT = $QdrantPort

    Write-ColorOutput "Configurazione porte:" "Yellow"
    Write-ColorOutput "  Web (Proxy):        $env:WEB_PORT"
    Write-ColorOutput "  Frontend:           $env:FRONTEND_PORT"
    Write-ColorOutput "  Backend:            $env:BACKEND_PORT"
    Write-ColorOutput "  SQL Generator:      $env:SQL_GENERATOR_PORT"
    Write-ColorOutput "  Mermaid Service:    $env:MERMAID_SERVICE_PORT"
    Write-ColorOutput "  Qdrant:             $env:QDRANT_PORT"
    Write-Host ""
    
    if ($RemoteHost) {
        Write-ColorOutput "Deploy su host remoto: $RemoteHost" "Magenta"
    }

    Invoke-Docker "stack", "deploy", "-c", "docker-stack.yml", $StackName
    Write-ColorOutput "✓ Deploy avviato" "Green"
}

function Wait-For-Services {
    Write-ColorOutput "=== Attesa avvio servizi ===" "Blue"
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
            Write-ColorOutput "✓ Tutti i servizi sono attivi" "Green"
            return $true
        }

        Write-ColorOutput "In attesa... ($Elapsed/$MaxWait secondi)" "Yellow"
        Start-Sleep -Seconds 10
        $Elapsed += 10
    }

    Write-ColorOutput "Timeout: servizi non avviati in tempo" "Red"
    return $false

}

function Rollback-Stack {
    Write-ColorOutput "=== Rollback ===" "Red"
    # Rollback main services
    Invoke-Docker "service", "rollback", "${StackName}_backend" 2>$null | Out-Null
    Invoke-Docker "service", "rollback", "${StackName}_frontend" 2>$null | Out-Null
    Invoke-Docker "service", "rollback", "${StackName}_sql-generator" 2>$null | Out-Null
    Write-ColorOutput "Rollback completato" "Yellow"
}

function Show-Logs {
    Write-ColorOutput "=== Logs Backend (ultime 20 righe) ===" "Blue"
    Invoke-Docker "service", "logs", "--tail", "20", "${StackName}_backend" 2>$null
}

function Show-Status {
    Write-ColorOutput "=== Stato dei Servizi ===" "Blue"
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
Deploy-Stack

if (-not (Wait-For-Services)) {
    Write-ColorOutput "Deploy fallito. Eseguo rollback..." "Red"
    Rollback-Stack
    Show-Logs
    exit 1
}

Show-Status

Write-ColorOutput "============================================" "Green"
Write-ColorOutput "  Deploy completato con successo!" "Green"
Write-ColorOutput "============================================" "Green"
