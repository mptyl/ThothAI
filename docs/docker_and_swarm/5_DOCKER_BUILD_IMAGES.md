# ThothAI - Architettura delle Immagini Docker

Questo documento descrive come vengono costruite le immagini Docker di ThothAI, quali componenti sono "cablati" (immutabili) al momento della build e come queste interagiscono con la configurazione a runtime.

## 1. Filosofia della Build

ThothAI utilizza un approccio **"Build Once, Run Anywhere"**. Le immagini Docker sono progettate per essere generiche e trasportabili. Tutte le dipendenze necessarie, inclusi i driver per tutti i database supportati, sono installate durante la fase di build.

La scelta di quali funzionalità attivare (es. quali database esporre) viene effettuata esclusivamente a **runtime** tramite variabili d'ambiente.

## 2. Dettagli delle Immagini

### 2.1 Backend (`thoth-backend`)
*   **Base**: `python:3.13-slim-bookworm`
*   **Dipendenze Cablate**:
    - Tutti i driver database: `postgresql`, `mysql`, `mariadb`, `sqlserver` (via Microsoft ODBC), `sqlite`, `informix`.
    - Tool di sistema: `curl`, `build-essential`, `unixodbc`.
    - `uv` per la gestione ultra-rapida del virtualenv.
*   **Dati Statici Inclusi**:
    - Una copia dei database demo (BIRD format) in `/app/data_temp/`.
    - I file CSV di configurazione iniziale in `/setup_csv/`.
*   **Comportamento Immutabile**:
    - La struttura delle directory interne (`/app/backend_db`, `/app/data`, `/app/logs`).
    - Gli entrypoint (`entrypoint.sh` e `start.sh`).

### 2.2 Frontend (`thoth-frontend`)
*   **Base**: `node:20-slim` (tipicamente)
*   **Componenti Cablati**:
    - Il codice Next.js compilato in modalità standalone.
*   **Flessibilità Runtime**:
    - Utilizza un endpoint `/api/config` per caricare dinamicamente le URL del backend e dello SQL Generator, evitando di dover ricompilare l'immagine per cambiare porta o host.

### 2.3 SQL Generator (`thoth-sql-generator`)
*   **Base**: `python:3.12-slim`
*   **Componenti Cablati**:
    - PydanticAI e tutte le librerie per l'integrazione con i vari LLM.
    - Logica di generazione SQL e validazione.

---

## 3. Informazioni Cablate vs Runtime

| Informazione | Tipo | Note |
|--------------|------|------|
| **Driver Database** | Cablato | Tutti i driver sono installati nella build per garantire portabilità. |
| **Endpoint API** | Runtime | Configurati via `.env.docker` o variabili Swarm. |
| **API Keys LLM** | Runtime | Passate come segreti o variabili d'ambiente. |
| **Database Abilitati** | Runtime | Gestiti dalla variabile `ENABLED_DATABASES`. |
| **Database Demo** | Cablato/Volume | Inclusi nell'immagine, ma copiati nel volume persistente al primo avvio. |

## 4. Il Processo di Inizializzazione

Quando un'immagine viene avviata (specialmente il backend), esegue una serie di script di bootstrap che determinano lo stato del sistema:

1.  **`init-shared-data.sh`**: Se il volume `thoth-shared-data` è vuoto, vi copia i database demo inclusi nell'immagine.
2.  **`start.sh`**:
    - Esegue le migrazioni del database.
    - Se non esistono workspace, effettua il **"Full Bootstrap"**:
        - Crea l'utente `admin` e `demo`.
        - Importa le configurazioni di default.
        - Se sono presenti API Key, avvia l'analisi AI automatica (scope generation, documentation) e il preprocessing vettoriale.

Per informazioni su come gestire queste immagini e il deploy, consulta:
- [Guida Docker Locale](./2_DOCKER_LOCAL_IT.md)
- [Guida Docker Swarm](./3_DOCKER_SWARM_IT.md)
- [Gestione Docker](./6_DOCKER_MANAGEMENT.md)
