#!/usr/bin/env bash
# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.
#
# Script di deployment automatizzato per ThothAI su Docker Swarm
# Versione aggiornata con porte 7000-7050 e gestione volume thoth-data-exchange

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration Defaults (can be overridden by config file)
REGISTRY_URL="registry.uni.com/tylconsulting/ThothAI"
VERSION="latest"
STACK_NAME="thoth"
BACKUP_DIR="/backup/thoth"

# Porte default per Docker Swarm (7000-7050)
WEB_PORT="7000"              # Proxy Nginx
FRONTEND_PORT="7001"   # Frontend Next.js
BACKEND_PORT="7002"     # Backend Django (via proxy)
SQL_GENERATOR_PORT="7003"  # SQL Generator FastAPI
MERMAID_SERVICE_PORT="7004"  # Mermaid Service
QDRANT_PORT="7005"       # Qdrant Vector DB

DOCKER_CMD="docker"

print_color() {
    echo -e "${2}${1}${NC}"
}

# Functions
check_prerequisites() {
    print_color "=== Verifica prerequisiti ===" "$BLUE"
    
    # Check Docker
    if ! $DOCKER_CMD info > /dev/null 2>&1; then
        print_color "Errore: Docker non è in esecuzione o non raggiungibile" "$RED"
        exit 1
    fi
    
    # Check Swarm (on target)
    if ! $DOCKER_CMD info | grep -q "Swarm: active"; then
        print_color "Errore: Docker Swarm non è attivo sul target. Esegui 'docker swarm init'" "$RED"
        exit 1
    fi
    
    # Check config files (local)
    if [ ! -f "config.yml.local" ]; then
        print_color "Errore: config.yml.local non trovato" "$RED"
        exit 1
    fi
    
    if [ ! -f ".env.docker" ]; then
        print_color "Errore: .env.docker non trovato. Esegui prima lo script di configurazione" "$RED"
        exit 1
    fi
    
    # Check docker-stack.yml
    if [ ! -f "docker-stack.yml" ]; then
        print_color "Errore: docker-stack.yml non trovato" "$RED"
        exit 1
    fi
    
    print_color "✓ Prerequisiti verificati" "$GREEN"
}

backup_volumes() {
    print_color "=== Backup dei volumi ===" "$BLUE"
    
    BACKUP_PATH="$BACKUP_DIR/$(date +%Y%m%d_%H%M%S)"
    # Note: checks/mkdirs run on target via docker context or -H?
    # Actually docker run commands execute on technical target, but volumes are on target.
    # The file path in container is local to container. 
    # Where does -v /backup:/backup map to? The Host filesystem.
    # So this assumes /backup exists on the Swarm node (or is created).
    
    # Backup database
    print_color "Backup database..." "$YELLOW"
    $DOCKER_CMD run --rm \
        -v thoth_backend-db:/data \
        -v "$BACKUP_PATH":/backup \
        alpine sh -c "mkdir -p /backup && tar czf /backup/backend-db.tar.gz -C /data . 2>/dev/null || true"
    
    # Backup Qdrant
    print_color "Backup Qdrant..." "$YELLOW"
    $DOCKER_CMD run --rm \
        -v thoth_qdrant-data:/data \
        -v "$BACKUP_PATH":/backup \
        alpine sh -c "mkdir -p /backup && tar czf /backup/qdrant-data.tar.gz -C /data . 2>/dev/null || true"
    
    # Backup data-exchange (volume condiviso)
    print_color "Backup thoth-data-exchange..." "$YELLOW"
    $DOCKER_CMD run --rm \
        -v thoth-data-exchange:/data \
        -v "$BACKUP_PATH":/backup \
        alpine sh -c "mkdir -p /backup && tar czf /backup/data-exchange.tar.gz -C /data . 2>/dev/null || true"
    
    # Note: Copying .env.docker and config.yml.local to remote would require scp or similar.
    # For now we skip local file copy to remote host filesystem unless we mount it.
    
    print_color "✓ Backup attempted in $BACKUP_PATH (on swarm node)" "$GREEN"
}

update_secrets() {
    print_color "=== Aggiornamento Secrets ===" "$BLUE"
    
    # Remove old secrets if exist
    $DOCKER_CMD secret rm thoth_env_config 2>/dev/null || true
    $DOCKER_CMD secret rm thoth_config_yml 2>/dev/null || true
    $DOCKER_CMD config rm thoth_env_docker 2>/dev/null || true
    
    # Create new secrets
    $DOCKER_CMD secret create thoth_env_config .env.docker
    $DOCKER_CMD secret create thoth_config_yml config.yml.local
    
    # Create config (non-sensitive)
    $DOCKER_CMD config create thoth_env_docker .env.docker
    
    print_color "✓ Secrets aggiornati" "$GREEN"
}

deploy_stack() {
    print_color "=== Deploy dello Stack ===" "$BLUE"
    
    # Export variables for docker stack
    export REGISTRY_URL VERSION
    export WEB_PORT FRONTEND_PORT BACKEND_PORT SQL_GENERATOR_PORT
    export MERMAID_SERVICE_PORT QDRANT_PORT
    
    print_color "Configurazione porte:" "$YELLOW"
    print_color "  Web (Proxy):        $WEB_PORT" "$NC"
    print_color "  Frontend:           $FRONTEND_PORT" "$NC"
    print_color "  Backend (via proxy): $BACKEND_PORT" "$NC"
    print_color "  SQL Generator:      $SQL_GENERATOR_PORT" "$NC"
    print_color "  Mermaid Service:    $MERMAID_SERVICE_PORT" "$NC"
    print_color "  Qdrant:             $QDRANT_PORT" "$NC"
    echo ""
    
    if [ "$DOCKER_CMD" != "docker" ]; then
        print_color "Deploy su host remoto..." "$BLUE"
    fi

    # Deploy stack
    $DOCKER_CMD stack deploy -c docker-stack.yml "$STACK_NAME"
    
    print_color "✓ Deploy avviato" "$GREEN"
}

wait_for_services() {
    print_color "=== Attesa avvio servizi ===" "$BLUE"
    
    local max_wait=1200  # 20 minuti
    local elapsed=0
    
    while [ $elapsed -lt $max_wait ]; do
        local running=$($DOCKER_CMD stack services "$STACK_NAME" --format "{{.Replicas}}" | grep -v "0/0" | wc -l)
        local total=$($DOCKER_CMD stack services "$STACK_NAME" --format "{{.Replicas}}" | wc -l)
        
        # Check if all replicas are running
        local all_running=true
        if [ "$total" -eq 0 ]; then
             all_running=false
        else
            while IFS= read -r line; do
                if [[ $line != *"1/1"* && $line != *"2/2"* ]]; then
                    all_running=false
                    break
                fi
            done < <($DOCKER_CMD stack services "$STACK_NAME" --format "{{.Replicas}}")
        fi
        
        if [ "$all_running" = true ]; then
            print_color "✓ Tutti i servizi sono attivi" "$GREEN"
            return 0
        fi
        
        print_color "In attesa... ($elapsed/$max_wait secondi)" "$YELLOW"
        sleep 10
        elapsed=$((elapsed + 10))
    done
    
    print_color "Timeout: servizi non avviati in tempo" "$RED"
    return 1
}

# Health check logic removed/simplified because simple curl localhost won't work easily for remote host
# unless we tunnel or curl the remote IP. Assuming localhost for now if no remote args, or just skip if valid remote.

show_services_status() {
    print_color "=== Stato dei Servizi ===" "$BLUE"
    $DOCKER_CMD stack services "$STACK_NAME"
}

show_logs() {
    print_color "=== Logs Backend (ultime 20 righe) ===" "$BLUE"
    $DOCKER_CMD service logs --tail 20 "${STACK_NAME}_backend" 2>&1 || true
}

rollback() {
    print_color "=== Rollback ===" "$RED"
    
    $DOCKER_CMD service rollback "${STACK_NAME}_backend" 2>/dev/null || true
    $DOCKER_CMD service rollback "${STACK_NAME}_frontend" 2>/dev/null || true
    $DOCKER_CMD service rollback "${STACK_NAME}_sql-generator" 2>/dev/null || true
    
    print_color "Rollback completato" "$YELLOW"
}

# Main execution
main() {
    # Parse arguments
    SKIP_BACKUP=false
    ROLLBACK_ONLY=false
    STATUS_ONLY=false
    LOGS_ONLY=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-backup)
                SKIP_BACKUP=true
                shift
                ;;
            --rollback-only)
                ROLLBACK_ONLY=true
                shift
                ;;
            --status-only)
                STATUS_ONLY=true
                shift
                ;;
            --logs)
                LOGS_ONLY=true
                shift
                ;;
            -H|--host)
                DOCKER_HOST="$2"
                DOCKER_CMD="docker -H $DOCKER_HOST"
                shift 2
                ;;
            --config)
                # Load config file (shell script sourcing)
                if [ -f "$2" ]; then
                    print_color "Loading config from $2" "$BLUE"
                    set -a
                    source "$2"
                    set +a
                else
                    print_color "Config file $2 not found" "$RED"
                    exit 1
                fi
                shift 2
                ;;
            *)
                print_color "Opzione sconosciuta: $1" "$RED"
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --skip-backup         Salta il backup dei volumi"
                echo "  --rollback-only       Esegue solo il rollback"
                echo "  --status-only         Mostra solo lo stato dei servizi"
                echo "  --logs                Mostra i log del backend"
                echo "  -H, --host <HOST>     Docker host remoto (es. ssh://user@host)"
                echo "  --config <FILE>       Carica configurazione porte da file"
                exit 1
                ;;
        esac
    done

    print_color "============================================" "$BLUE"
    print_color "  ThothAI - Deploy Automatizzato Swarm" "$BLUE"
    print_color "============================================" "$BLUE"
    echo ""

    if [ "$ROLLBACK_ONLY" = true ]; then rollback; exit 0; fi
    if [ "$STATUS_ONLY" = true ]; then show_services_status; exit 0; fi
    if [ "$LOGS_ONLY" = true ]; then show_logs; exit 0; fi

    print_color "Registry: $REGISTRY_URL" "$YELLOW"
    print_color "Version:  $VERSION" "$YELLOW"
    print_color "Stack:    $STACK_NAME" "$YELLOW"
    echo ""
    
    check_prerequisites
    
    if [ "$SKIP_BACKUP" != "true" ]; then
        backup_volumes
    fi
    
    update_secrets
    deploy_stack
    
    if ! wait_for_services; then
        print_color "Deploy fallito. Eseguo rollback..." "$RED"
        rollback
        show_logs
        exit 1
    fi
    
    show_services_status
    
    print_color "============================================" "$GREEN"
    print_color "  Deploy completato con successo!" "$GREEN"
    print_color "============================================" "$GREEN"
}

main "$@"

