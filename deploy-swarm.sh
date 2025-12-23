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

# Configuration
REGISTRY_URL="${REGISTRY_URL:-registry.uni.com/tylconsulting/ThothAI}"
VERSION="${VERSION:-latest}"
STACK_NAME="thoth"
BACKUP_DIR="/backup/thoth"

# Porte default per Docker Swarm (7000-7050)
WEB_PORT="${WEB_PORT:-7000}"              # Proxy Nginx
FRONTEND_PORT="${FRONTEND_PORT:-7001}"   # Frontend Next.js
BACKEND_PORT="${BACKEND_PORT:-7002}"     # Backend Django (via proxy)
SQL_GENERATOR_PORT="${SQL_GENERATOR_PORT:-7003}"  # SQL Generator FastAPI
MERMAID_SERVICE_PORT="${MERMAID_SERVICE_PORT:-7004}"  # Mermaid Service
QDRANT_PORT="${QDRANT_PORT:-7005}"       # Qdrant Vector DB

print_color() {
    echo -e "${2}${1}${NC}"
}

# Functions
check_prerequisites() {
    print_color "=== Verifica prerequisiti ===" "$BLUE"
    
    # Check Docker
    if ! docker info > /dev/null 2>&1; then
        print_color "Errore: Docker non è in esecuzione" "$RED"
        exit 1
    fi
    
    # Check Swarm
    if ! docker info | grep -q "Swarm: active"; then
        print_color "Errore: Docker Swarm non è attivo. Esegui 'docker swarm init'" "$RED"
        exit 1
    fi
    
    # Check config files
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
    mkdir -p "$BACKUP_PATH"
    
    # Backup database
    print_color "Backup database..." "$YELLOW"
    docker run --rm \
        -v thoth_backend-db:/data \
        -v "$BACKUP_PATH":/backup \
        alpine tar czf /backup/backend-db.tar.gz -C /data . 2>/dev/null || true
    
    # Backup Qdrant
    print_color "Backup Qdrant..." "$YELLOW"
    docker run --rm \
        -v thoth_qdrant-data:/data \
        -v "$BACKUP_PATH":/backup \
        alpine tar czf /backup/qdrant-data.tar.gz -C /data . 2>/dev/null || true
    
    # Backup data-exchange (volume condiviso)
    print_color "Backup thoth-data-exchange..." "$YELLOW"
    docker run --rm \
        -v thoth-data-exchange:/data \
        -v "$BACKUP_PATH":/backup \
        alpine tar czf /backup/data-exchange.tar.gz -C /data . 2>/dev/null || true
    
    # Backup configs
    cp .env.docker "$BACKUP_PATH/"
    cp config.yml.local "$BACKUP_PATH/"
    
    print_color "✓ Backup completato in $BACKUP_PATH" "$GREEN"
}

update_secrets() {
    print_color "=== Aggiornamento Secrets ===" "$BLUE"
    
    # Remove old secrets if exist
    docker secret rm thoth_env_config 2>/dev/null || true
    docker secret rm thoth_config_yml 2>/dev/null || true
    docker config rm thoth_env_docker 2>/dev/null || true
    
    # Create new secrets
    docker secret create thoth_env_config .env.docker
    docker secret create thoth_config_yml config.yml.local
    
    # Create config (non-sensitive)
    docker config create thoth_env_docker .env.docker
    
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
    
    # Deploy stack
    docker stack deploy -c docker-stack.yml "$STACK_NAME"
    
    print_color "✓ Deploy avviato" "$GREEN"
}

wait_for_services() {
    print_color "=== Attesa avvio servizi ===" "$BLUE"
    
    local max_wait=1200  # 20 minuti
    local elapsed=0
    
    while [ $elapsed -lt $max_wait ]; do
        local running=$(docker stack services "$STACK_NAME" --format "{{.Replicas}}" | grep -v "0/0" | wc -l)
        local total=$(docker stack services "$STACK_NAME" --format "{{.Replicas}}" | wc -l)
        
        # Check if all replicas are running
        local all_running=true
        while IFS= read -r line; do
            if [[ $line != *"1/1"* && $line != *"2/2"* ]]; then
                all_running=false
                break
            fi
        done < <(docker stack services "$STACK_NAME" --format "{{.Replicas}}")
        
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

health_check() {
    print_color "=== Health Check ===" "$BLUE"
    
    # Check backend via proxy
    if curl -f -s http://localhost:$WEB_PORT/admin/login/ > /dev/null 2>&1; then
        print_color "✓ Backend (via proxy): OK" "$GREEN"
    else
        print_color "✗ Backend (via proxy): FAILED" "$RED"
    fi
    
    # Check frontend
    if curl -f -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
        print_color "✓ Frontend: OK" "$GREEN"
    else
        print_color "✗ Frontend: FAILED" "$RED"
    fi
    
    # Check SQL Generator
    if curl -f -s http://localhost:$SQL_GENERATOR_PORT/health > /dev/null 2>&1; then
        print_color "✓ SQL Generator: OK" "$GREEN"
    else
        print_color "✗ SQL Generator: FAILED" "$RED"
    fi
    
    # Check Qdrant
    if curl -f -s http://localhost:$QDRANT_PORT/ > /dev/null 2>&1; then
        print_color "✓ Qdrant: OK" "$GREEN"
    else
        print_color "✗ Qdrant: FAILED" "$RED"
    fi
}

show_services_status() {
    print_color "=== Stato dei Servizi ===" "$BLUE"
    docker stack services "$STACK_NAME"
}

show_logs() {
    print_color "=== Logs Backend (ultime 20 righe) ===" "$BLUE"
    docker service logs --tail 20 "${STACK_NAME}_backend" 2>&1 || true
}

rollback() {
    print_color "=== Rollback ===" "$RED"
    
    docker service rollback "${STACK_NAME}_backend" 2>/dev/null || true
    docker service rollback "${STACK_NAME}_frontend" 2>/dev/null || true
    docker service rollback "${STACK_NAME}_sql-generator" 2>/dev/null || true
    
    print_color "Rollback completato" "$YELLOW"
}

# Main execution
main() {
    print_color "============================================" "$BLUE"
    print_color "  ThothAI - Deploy Automatizzato Swarm" "$BLUE"
    print_color "============================================" "$BLUE"
    echo ""
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
    health_check
    
    print_color "============================================" "$GREEN"
    print_color "  Deploy completato con successo!" "$GREEN"
    print_color "============================================" "$GREEN"
    echo ""
    print_color "Accessi:" "$YELLOW"
    print_color "" "$NC"
    print_color "  Accesso Diretto:" "$BLUE"
    print_color "    Frontend:       http://localhost:$FRONTEND_PORT" "$NC"
    print_color "    SQL Generator:  http://localhost:$SQL_GENERATOR_PORT/docs" "$NC"
    print_color "    Mermaid:        http://localhost:$MERMAID_SERVICE_PORT" "$NC"
    print_color "    Qdrant:         http://localhost:$QDRANT_PORT/dashboard" "$NC"
    print_color "    Backend:        http://localhost:$BACKEND_PORT" "$YELLOW"
    print_color "" "$NC"
    print_color "  Accesso via Proxy (porta $WEB_PORT):" "$BLUE"
    print_color "    Backend (home):  http://localhost:$WEB_PORT/" "$NC"
    print_color "    Admin:          http://localhost:$WEB_PORT/admin" "$NC"
    print_color "    API:            http://localhost:$WEB_PORT/api" "$NC"
    print_color "    Frontend:       http://localhost:$WEB_PORT/frontend/" "$NC"
    print_color "    SQL Generator:  http://localhost:$WEB_PORT/sql-generator/" "$NC"
    print_color "" "$NC"
    print_color "  NOTA: Per abilitare l'accesso diretto al backend, modifica docker-stack.yml" "$YELLOW"
    print_color "        aggiungendo 'ports: - target: 8000 published: \$BACKEND_PORT'" "$NC"
    echo ""
    print_color "Volumi condivisi:" "$YELLOW"
    print_color "  thoth-data-exchange: Montato su backend (RW), frontend (RO), sql-generator (RW), proxy (RO)" "$NC"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-backup)
            SKIP_BACKUP=true
            shift
            ;;
        --rollback-only)
            rollback
            exit 0
            ;;
        --status-only)
            show_services_status
            exit 0
            ;;
        --logs)
            show_logs
            exit 0
            ;;
        --health-check)
            health_check
            exit 0
            ;;
        *)
            print_color "Opzione sconosciuta: $1" "$RED"
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-backup      Salta il backup dei volumi"
            echo "  --rollback-only    Esegue solo il rollback"
            echo "  --status-only      Mostra solo lo stato dei servizi"
            echo "  --logs             Mostra i log del backend"
            echo "  --health-check     Esegue solo l'health check"
            exit 1
            ;;
    esac
done

main
