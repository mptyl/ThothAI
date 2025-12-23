# ThothAI - Manuale di Deployment su Docker Swarm

Questo documento guida l'utente attraverso il processo di installazione e deployment di ThothAI su un cluster Docker Swarm.

Il deployment è configurato per utilizzare di default il range di porte **7000-7050**, evitando conflitti con installazioni locali standard.

## 1. Prerequisiti

### Requisiti di Sistema
*   **Docker Installed**: Docker Engine 20.10+
*   **Swarm Active**: Il nodo deve essere inizializzato come manager.
*   **Network**: Accesso al Registry Docker (se remoto) o immagini costruite localmente.

### Inizializzazione Swarm (Locale)
Se stai testando in locale e non hai ancora attivato Swarm:

**Mac/Linux:**
```bash
docker swarm init
```

**Windows:**
```powershell
docker swarm init
```
*Nota: Se hai più interfacce di rete, Docker potrebbe chiederti di specificare `--advertise-addr <IP>`.*

---

## 2. Configurazione

### File di Configurazione Swarm
Il file `.env.swarm-config` contiene i parametri per il deployment (Versione, Registry, Porte).

**Esempio `.env.swarm-config` (Default):**
```ini
# Registry e Versione
REGISTRY_URL=registry.uni.com/tylconsulting/ThothAI
VERSION=latest
STACK_NAME=thoth

# Porte (Range 7000-7050)
WEB_PORT=7000              # Entrypoint Principale (Proxy)
FRONTEND_PORT=7001         # Frontend Diretto
BACKEND_PORT=7002          # Backend Diretto
SQL_GENERATOR_PORT=7003    # Servizio SQL Gen
MERMAID_SERVICE_PORT=7004  # Servizio Diagrammi
QDRANT_PORT=7005           # Database Vettoriale
```

### Configurazione Applicativa
Assicurati che `config.yml.local` sia presente e configurato correttamente (API Keys, Database settings). Questo file verrà caricato come Docker Secret.

1.  Copia il template se necessario:
    ```bash
    cp config.yml config.yml.local
    ```
2.  Genera l'ambiente docker:
    **Mac/Linux:**
    ```bash
    ./scripts/installer.py --generate-env-only
    ```
    **Windows:**
    ```powershell
    python scripts/installer.py --generate-env-only
    ```

---

## 3. Build e Push delle Immagini

Prima del deploy, le immagini devono essere disponibili. Se usi un registry remoto, devi buildare e pushare.

### Mac/Linux
Usa lo script di build (assicurati di aver fatto login al registry se necessario):
```bash
./build-and-push-images.sh
```

### Windows
Usa lo script PowerShell dedicato:
```powershell
.\push-images.ps1
```
*Nota: Questo script era precedentemente chiamato `deployswarm.ps1`.*

---

## 4. Deployment

Utilizza gli script di automazione che gestiscono:
*   Verifica prerequisiti
*   Backup automatico dei volumi (Database, Qdrant)
*   Aggiornamento Secrets e Configs
*   Deploy dello Stack

### Deployment Locale (Test su Swarm locale)

**Mac/Linux:**
```bash
# Usa la configurazione di default (porte 7000+)
./deploy-swarm.sh --config .env.swarm-config
```

**Windows:**
```powershell
# Usa la configurazione di default
.\deploy-swarm.ps1 -ConfigFile ".env.swarm-config"
```

### Deployment Remoto (Opzionale)
Puoi lanciare il deploy dalla tua macchina verso un manager remoto.

**Mac/Linux:**
```bash
./deploy-swarm.sh --host "ssh://user@remote-server" --config .env.swarm-config
```

**Windows:**
```powershell
.\deploy-swarm.ps1 -RemoteHost "ssh://user@remote-server" -ConfigFile ".env.swarm-config"
```

---

## 5. Verifica e Accesso

Una volta completato il deploy (gli script attendono che i servizi siano `1/1`), l'applicazione sarà accessibile alle seguenti porte:

| Servizio | Porta Default | URL | Descrizione |
|----------|---------------|-----|-------------|
| **Main Access** | **7000** | `http://localhost:7000/` | Proxy Nginx (tutti i servizi) |
| Frontend | 7001 | `http://localhost:7001/` | Accesso diretto UI |
| Backend | 7002 | `http://localhost:7002/` | Accesso diretto Django |
| SQL Gen | 7003 | `http://localhost:7003/docs` | Swagger API |
| Mermaid | 7004 | `http://localhost:7004/` | Rendering Diagrammi |
| Qdrant | 7005 | `http://localhost:7005/dashboard` | Dashboard Vettoriale |

### Comandi Utili

**Controllare lo stato:**
```bash
docker stack services thoth
```

**Vedere i log (Backend):**
```bash
docker service logs -f thoth_backend
```

**Forzare un Rollback:**
```bash
# Mac/Linux
./deploy-swarm.sh --rollback-only

# Windows
.\deploy-swarm.ps1 -RollbackOnly
```

## 6. Risoluzione Problemi Comuni

1.  **Immagini non trovate**: Verifica che `REGISTRY_URL` in `.env.swarm-config` sia corretto e che le immagini siano state pushate (`push-images.ps1`).
2.  **Porte occupate**: Se le porte 7000-7050 sono occupate, modificane i valori in `.env.swarm-config` e rilancia il deploy.
3.  **Database vuoto**: Se è la prima installazione, potresti dover eseguire le migrazioni o caricare i dati iniziali accedendo al container backend.
