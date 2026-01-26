# Guida alla Configurazione

La configurazione di ThothAI è centralizzata in semplici file di environment. Questo approccio assicura che i segreti non vengano mai committati su git e che le distribuzioni siano riproducibili.

## Panoramica File

| File | Scopo | Ambiente | Stato Git |
|------|-------|----------|-----------|
| **`.env.docker`** | Config attiva (Copiata da template) | Produzione / Docker Dev | `gitignored` |
| **`.env.local`** | Config per esecuzione nativa locale | Sviluppo Locale | `gitignored` |
| **`swarm_config.env`** | Config infrastruttura Swarm (Porte, Stack) | Docker Swarm | `gitignored` |
| `.env.compose.template` | Template sorgente per Docker Compose Locale | - | Committato |
| `.env.swarm.template` | Template sorgente per Swarm Produzione | - | Committato |
| `swarm_config.env.template` | Template sorgente per `swarm_config.env` | - | Committato |

## Riferimento Variabili

### Distribuzione & Build

| Variabile | Descrizione | Valori Validi | Default |
|-----------|-------------|---------------|---------|
| `DEPLOYMENT_MODE` | Selezione orchestratore | `compose`, `swarm` | `compose` |
| `BUILD_MODE` | Strategia sorgente immagine | `hub` (pull), `build` (compila) | `hub` |
| `THOTH_DATA_PATH` | Percorso base NFS/Bind Mount (Solo Swarm) | Percorso Assoluto | `/mnt/nfs/thothai` |
| `DOCKER_REGISTRY` | Registro per immagini | Nome Utente/Org | `tylconsulting` |
| `IMAGE_VERSION` | Tag da distribuire | `latest`, `v1.0.0` | `latest` |

### Infrastruttura & Porte

Queste porte definiscono dove i servizi ascoltano sulla **macchina host**. In ambiente Swarm, queste variabili sono caricate da `swarm_config.env`.

| Variabile | Servizio | Porta Default (Compose) | Porta Default (Swarm) |
|-----------|----------|-------------------------|------------------------|
| `WEB_PORT` | Nginx Proxy (Ingresso Main) | `8040` | `7010` |
| `FRONTEND_PORT` | Next.js Frontend (Diretto) | `3040` | `7001` |
| `BACKEND_PORT` | Django Admin/API (via Proxy) | `8040` | `7002` |
| `SQL_GENERATOR_PORT` | SQL Gen Agent API | `8020` | `7003` |
| `MERMAID_SERVICE_PORT`| Diagram Service | `8003` | `7004` |
| `QDRANT_PORT` | Vector DB | `6333` | `7005` |

> [!NOTE]
> Lo script `docker-swarm-up.sh` caricherà prioritariamente le impostazioni da `swarm_config.env` per evitare conflitti con installazioni Docker Compose esistenti sullo stesso manager.

### Configurazione Database

| Variabile | Descrizione | Default |
|-----------|-------------|---------|
| `POSTGRES_INTERNAL` | Usare container DB interno? | `true` |
| `AUTO_CREATE_SCHEMA`| Auto-creare schema all'avvio? | `false` |
| `DB_HOST` | Host DB Esterno | - |
| `DB_PORT` | Porta DB Esterno | `5432` |
| `DB_SCHEMA` | Nome Schema | `thoth_db_swarm` |

> [!TIP]
> **DB Esterno su Host (Locale)**: Se stai eseguendo Swarm su Mac/Windows e vuoi connetterti a un DB sull'host (es. Supabase locale), usa `host.docker.internal` come `DB_HOST`.

### Provider AI (Logica Applicativa)

Devi configurare **almeno un** provider LLM affinché l'applicazione funzioni.

| Variabile | Descrizione |
|-----------|-------------|
| `OPENAI_API_KEY` | Chiave per OpenAI (GPT-4o, ecc.) |
| `ANTHROPIC_API_KEY` | Chiave per modelli Claude |
| `GEMINI_API_KEY` | Chiave per modelli Google Gemini |
| `EMBEDDING_PROVIDER` | Provider per embedding vettoriali (`openai`, `azure`, ecc.) |
| `EMBEDDING_API_KEY` | Chiave per servizio embedding (spesso uguale a chiave OpenAI) |

### Runtime & Applicazione

| Variabile | Descrizione |
|-----------|-------------|
| `DEBUG` | Abilita modalità debug Django/Next.js | `true`, `false` |
| `LOGFIRE_TOKEN` | Token per osservabilità Pydantic Logfire |
| `DB_ROOT_PATH` | **Percorso assoluto** cartella database test | Docker: `/app/data` |
| `ENTRA_ENABLED` | Abilita integrazione Microsoft IdP | `true`, `false` |

## Generazione Chiavi di Sicurezza
 
Alcune variabili come `SECRET_KEY` (per Django) e `DJANGO_API_KEY` (per la comunicazione tra frontend e backend) sono fondamentali per la sicurezza del sistema. Mentre in Docker Compose queste vengono auto-generate, per le installazioni locali o in Swarm è necessario configurarle manualmente.
 
Per facilitare questa operazione, è disponibile uno script dedicato nella root del progetto:
 
```bash
./generate-keys.sh
```
 
**Perché usarlo?**
* **Sicurezza**: Genera chiavi casuali ad alta entropia.
* **Semplicità**: Non devi conoscere i comandi Python interni per generare segreti validi.
* **Standardizzazione**: Assicura che le chiavi siano nel formato corretto atteso da ThothAI.
 
Copia i valori generati e incollali nelle rispettive variabili nei tuoi file `.env.local` o `.env.swarm`.
 
## Best Practices

1.  **Non Committare Mai Segreti**: Assicurati che i file `.env.docker` e `.env.local` non vengano mai aggiunti a git.
2.  **Usa i Template**: Parti sempre dal file `.template` per assicurarti di avere tutte le chiavi richieste.
3.  **Gestione Porte**: Se cambi `WEB_PORT`, ricorda di aggiornare l'URL del tuo browser.
4.  **Password**: Cambia le password di default (`admin`/`changeme123`) immediatamente in produzione.
