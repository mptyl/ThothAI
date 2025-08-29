# Thoth - Applicazione Backend di ThothAI

Thoth è il componente backend di ThothAI, un'applicazione che consente di interrogare database relazionali utilizzando il linguaggio naturale. ThothAI si basa su un backend Django e un frontend composto da un insieme di Agenti AI.

![docs/assets/home_Thoth_nocomments.png](docs/assets/home_Thoth_nocomments.png)

Nel complesso, ThothAI produce:

- **Query SQL** generate dall'AI che, se corrette, vengono eseguite automaticamente.
- **Risultati** delle query SQL eseguite, visualizzabili e scaricabili in formato CSV.
- **Spiegazioni** in linguaggio non tecnico dell'SQL generato (opzionale).
- **Dettagli del Workflow** che consentono agli utenti di seguire il processo passo-passo di generazione SQL a partire dalla domanda di input. I passaggi specifici da visualizzare sono a discrezione dell'utente.

La componente di frontend è disponibile su [https://github.com/mptyl/ThothSL.git](https://github.com/mptyl/ThothSL.git)

## Iniziare

### Prerequisiti
- Docker e Docker Compose
- Git

### Procedura di Configurazione

### Installazione Rapida

Per un'installazione veloce dalla directory root del progetto:

**Linux/macOS:**
```bash
./install.sh
```

**Windows:**
```cmd
install.bat
```

Questi script lanceranno automaticamente l'installer interattivo che vi guiderà attraverso:
- Selezione del database (PostgreSQL, MySQL, SQLite, ecc.)
- Configurazione del database vettoriale (Qdrant, Milvus, Chroma, PGVector)
- Installazione delle dipendenze e configurazione dei container Docker

## 1. Attività Preliminari
ThothAI è un'applicazione abbastanza complessa e articolata. Richiede alcuni sforzi di configurazione, che abbiamo cercato di mitigare attraverso l'uso estensivo di valori predefiniti.

### 1.1 Prerequisiti
- Docker e Docker Compose
- Git

Per semplificare e velocizzare l'installazione, la procedura standard da seguire si basa su Docker. Pertanto, se desideri seguire le istruzioni standard, assicurati che Docker sia installato e che tu possa eseguire correttamente il comando `docker-compose`.

Git è richiesto per clonare l'applicazione e, se desideri, per mantenere il software aggiornato con i comandi `git pull` ogni volta che vengono rilasciate patch o miglioramenti.

Il codice sorgente dell'applicazione, rilasciato sotto licenza MIT, è disponibile su GitHub ai seguenti indirizzi: [https://github.com/mptyl/Thoth.git](https://github.com/mptyl/Thoth.git) e [https://github.com/mptyl/ThothSL.git](https://github.com/mptyl/ThothSL.git).

**Nota**:  
L'applicazione può anche essere compilata ed eseguita localmente in un ambiente virtuale Python tipico (ad esempio, `venv` o `conda`). Non consigliamo questa soluzione a meno che non desideri studiare o personalizzare il codice, o se desideri contribuire allo sviluppo. Per un utilizzo standard, ti consigliamo fortemente di utilizzare l'installazione basata su Docker, poiché fornisce un ambiente più affidabile e coerente con tutte le dipendenze correttamente configurate.

## 2. Architettura del Sistema

L'applicazione è composta da quattro servizi, ciascuno disponibile come contenitore Docker. Il file `docker-compose.yml` definisce la configurazione di questi contenitori Docker.

La configurazione standard assegna i seguenti nomi ai servizi all'interno dell'ambiente Docker:

### 2.1 thoth-be (Django Backend)
Gestisce la configurazione e i metadati del sistema, che includono:
- Database SQL da interrogare;
- Collezioni di database vettoriali (in una relazione 1:1 con i database SQL) contenenti metadati dei database relazionali associati, in particolare suggerimenti, coppie domanda/SQL utilizzabili come few-shots e descrizioni di tabelle e colonne;
- Modelli LLM utilizzabili da ThothAI (OpenAI, Mistral, Anthropic, ecc.). Solo modelli in grado di interagire con strumenti esterni possono essere utilizzati. La maggior parte dei modelli recentemente rilasciati ha questa capacità;
- Agenti (basati su PydanticAI) utilizzati nel flusso di lavoro di generazione SQL, ciascuno associato a un LLM. Fai riferimento alla documentazione di PydanticAI ([https://ai.pydantic.dev/](https://ai.pydantic.dev/)) per dettagli sulle caratteristiche dei loro Agenti;
- Utenti autorizzati e la loro associazione a uno o più Gruppi per definire le autorizzazioni di accesso e i valori predefiniti dell'attività frontend;
- Spazi di lavoro, che collegano un utente a una coppia di database SQL-vettoriale e gli agenti da utilizzare nel flusso di lavoro.

### 2.2 thoth-db (PostgreSQL)
Questo è il gestore del database PostgreSQL interno del sistema. Viene utilizzato per gestire i database di prova e di esempio provenienti da BIRD o altri benchmark. È accessibile agli indirizzi seguenti:
- **Interno**: `thoth-db:5432`
- **Esterno**: `localhost:5443`
- **Credenziali**: I database di esempio forniti hanno le credenziali `thoth_user` / `thoth_password`.  
Tutti questi parametri possono essere modificati nel file `docker-compose.yml`.

### 2.3 thoth-be-proxy (Nginx)
Un proxy per utilizzare l'applicazione Django in modalità di produzione. Gestisce i file statici e consente l'accesso del browser a `thoth-be` a [http://localhost:8040](http://localhost:8040). La porta può essere modificata nel file `docker-compose.yml`.

### 2.4 thoth-qdrant (Database Vettoriale)
Archivia i metadati del database che l'IA deve interrogare:
- Suggerimenti da utilizzare nel processo di generazione SQL per 'spiegare' termini specifici all'IA;
- Associazioni domanda-SQL predefinite e verificate;
- Descrizioni di tabelle e campi, parzialmente estratte dallo schema del database e parzialmente generate come commenti tramite IA;
- Documentazione semantica generica che fornisce indicazioni di alto livello sul database e sul suo contenuto;

## 3. Installazione

Per istruzioni di installazione complete, guida rapida e documentazione di utilizzo esaustiva, visita la nostra documentazione ufficiale a: **[https://mptyl.github.io/ThothDocs/](https://mptyl.github.io/ThothDocs/)**

La documentazione include:
- **Guida passo-passo all'installazione** con procedure di configurazione dettagliate
- **Tutorial rapido** per iniziare immediatamente
- **Manuale utente completo** che copre tutte le funzionalità e capacità di ThothAI
- **Esempi di configurazione** e migliori pratiche
- **Guida alla risoluzione dei problemi** per problemi comuni

Questo README fornisce una panoramica di base, ma la documentazione completa contiene tutte le informazioni dettagliate necessarie per installare, configurare e utilizzare ThothAI in ambienti di produzione.

## 4. Configurazione per lo Sviluppo

Per lo sviluppo locale senza Docker:

```bash
# Installa il gestore di pacchetti uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Installa le dipendenze
uv sync --extra dev

# Copia il template dell'ambiente
cp _env.template _env
# Modifica il file _env con la tua configurazione

# Esegui le migrazioni
uv run python manage.py migrate

# Crea un superutente
uv run python manage.py createsuperuser

# Avvia il server di sviluppo
uv run python manage.py runserver
```

## 5. Test

```bash
# Esegui test rapidi
./scripts/run-tests-local.sh quick

# Esegui la suite completa di test
./scripts/run-tests-local.sh full

# Esegui categorie specifiche di test
./scripts/run-tests-local.sh views     # Solo test delle view
./scripts/run-tests-local.sh security  # Solo test di sicurezza
```

## 6. Link Utili
- **Home Page Backend**: [http://localhost:8040](http://localhost:8040)
- **Pannello Amministrativo**: [http://localhost:8040/admin](http://localhost:8040/admin)
- **Pagina Frontend**: [http://localhost:8501](http://localhost:8501)
- **Dashboard Qdrant**: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)
- **Database da Esterno**: `localhost:5443`

## 7. Contribuire

Questo progetto utilizza strumenti Python moderni:
- **Gestore di Pacchetti**: [uv](https://docs.astral.sh/uv/) per la gestione rapida delle dipendenze
- **Test**: pytest con reporting della coverage
- **Qualità del Codice**: ruff per linting e formattazione
- **Framework**: Django 5.2 con Django REST Framework
- **Integrazione AI**: PydanticAI per gli agenti AI

Si prega di consultare `CLAUDE.md` per le linee guida quando si lavora con questo codebase usando Claude Code.

## 8. Licenza

Questo progetto è rilasciato sotto la Licenza MIT. Vedere `LICENSE.md` per i dettagli.