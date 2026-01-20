# Guida alla Configurazione

La configurazione di ThothAI è centralizzata in semplici file di environment. Questo approccio assicura che i segreti non vengano mai committati su git e che le distribuzioni siano riproducibili.

## Panoramica File

| File | Scopo | Ambiente | Stato Git |
|------|-------|----------|-----------|
| **`.env.docker`** | Config principale per Docker Compose/Swarm | Produzione / Docker Dev | `gitignored` |
| **`.env.local`** | Config per esecuzione nativa locale | Sviluppo Locale | `gitignored` |
| `.env.docker.template` | Sorgente template per `.env.docker` | - | Committato |
| `.env.local.template` | Sorgente template per `.env.local` | - | Committato |

## Riferimento Variabili

### Distribuzione & Build

| Variabile | Descrizione | Valori Validi | Default |
|-----------|-------------|---------------|---------|
| `DEPLOYMENT_MODE` | Selezione orchestratore | `compose`, `swarm` | `compose` |
| `BUILD_MODE` | Strategia sorgente immagine | `hub` (pull), `build` (compila) | `hub` |
| `DOCKER_REGISTRY` | Registro per immagini | Nome Utente/Org | `tylconsulting` |
| `IMAGE_VERSION` | Tag da distribuire | `latest`, `v1.0.0` | `latest` |

### Infrastruttura & Porte

Queste porte definiscono dove i servizi ascoltano sulla **macchina host**.

| Variabile | Servizio | Porta Default |
|-----------|----------|---------------|
| `WEB_PORT` | Nginx Proxy (Ingresso Main) | `8040` |
| `FRONTEND_PORT` | Next.js Frontend (Diretto) | `3040` |
| `SQL_GENERATOR_PORT` | SQL Gen Agent API | `8020` |
| `QDRANT_PORT` | Vector DB | `6333` |
| `MERMAID_SERVICE_PORT`| Diagram Service | `8003` |

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

## Best Practices

1.  **Non Committare Mai Segreti**: Assicurati che i file `.env.docker` e `.env.local` non vengano mai aggiunti a git.
2.  **Usa i Template**: Parti sempre dal file `.template` per assicurarti di avere tutte le chiavi richieste.
3.  **Gestione Porte**: Se cambi `WEB_PORT`, ricorda di aggiornare l'URL del tuo browser.
4.  **Password**: Cambia le password di default (`admin`/`changeme123`) immediatamente in produzione.
