# Installazione da Sorgente (Source Installation)

Questa modalità è pensata per **sviluppatori**, **contributor** o chiunque necessiti di una personalizzazione profonda del codice o delle immagini Docker.

## 1. Prerequisiti

Assicurarsi di avere installato:
*   **Git**: Per clonare il repository.
*   **Docker Desktop** (Mac/Windows) o **Docker Engine** (Linux): Attivo e funzionante.
*   **Python 3.9+** (opzionale ma consigliato per script di utilità).
*   **uv** (opzionale, consigliato per la gestione dei pacchetti Python).

### Nota per Utenti Windows
Se usate Windows, assicuratevi di avere **WSL 2** abilitato e configurato con Docker Desktop. I comandi shell (`.sh`) vanno eseguiti in WSL, mentre gli script PowerShell (`.ps1`) possono essere eseguiti direttamente da Windows PowerShell.

## 2. Clone del Repository

Scaricare il codice sorgente completato:

```bash
git clone https://github.com/mptyl/ThothAI.git
cd ThothAI
```

## 3. Configurazione

Prima dell'avvio, è necessario creare e modificare il file di configurazione locale.

1.  Copia il template:
    *   **Mac/Linux:** `cp config.yml config.yml.local`
    *   **Windows:** `Copy-Item config.yml config.yml.local`

2.  Edita `config.yml.local` inserendo:
    *   Le tue **API Key** (OpenAI, Anthropic, Gemini, ecc.).
    *   Eventuali override di configurazione (porte, database, ecc.).

> [!IMPORTANT]
> Non committare mai `config.yml.local` o file `.env` contenenti segreti!

## 4. Installazione e Avvio Rapido

Sono forniti script di installazione automatica che gestiscono la creazione dell'ambiente Docker, il download delle immagini e l'avvio.

### Mac/Linux
Eseguire lo script bash:
```bash
./install.sh
```

### Windows
Eseguire lo script PowerShell (da Windows PowerShell):
```powershell
.\install.ps1
```

Lo script eseguirà:
1.  Verifica presenza `config.yml.local`.
2.  Generazione file environment (es. `.env.docker`).
3.  Pull o Build delle immagini.
4.  Avvio servizi (`docker compose up`).

## 5. Build Personalizzata e Push (Avanzato)

Se hai modificato il codice e vuoi distribuire le tue immagini personalizzate (invece di usare quelle ufficiali `tylconsulting`), devi compilare e fare il push su un tuo registry.

### Requisiti per il Push
*   Account Docker Hub (o altro registry).
*   Accesso in scrittura al registry (eseguire `docker login`).

### Uso di `push.sh`

Lo script `push.sh` automatizza la build multi-architettura e il push.

```bash
# Sintassi: ./push.sh <REGISTRY_URL> <VERSION> [OPTIONS]

# Esempio: Push su Docker Hub personale (utente 'mioutente'), versione 1.0
./push.sh docker.io/mioutente 1.0
```

Questo creerà e caricherà le immagini (es. `docker.io/mioutente/thoth-backend:1.0` e `:latest`).

#### Configurazione Registry Personalizzato
Dopo il push, aggiorna `config.yml.local` per usare le tue nuove immagini:

```yaml
docker:
  image_registry: "mioutente" # Namespace del tuo registry
  # Se è un registry privato, aggiungi username/password qui
```

Poi riesegui `./install.sh` per aggiornare lo stack in esecuzione.

## 6. Uso della CLI da Sorgente

Il repository include il codice sorgente della `thothai-cli`. Puoi usarla direttamente senza installarla via pip, utile per testare modifiche alla CLI stessa.

```bash
# Esempio: Esecuzione comando 'up' usando uv
uv run thothai up
```

Per maggiori dettagli sui comandi disponibili, vedi i manuali [3_CLI_COMPOSE_INSTALLATION_IT.md](3_CLI_COMPOSE_INSTALLATION_IT.md) e [4_CLI_SWARM_INSTALLATION_IT.md](4_CLI_SWARM_INSTALLATION_IT.md) e [5_CLI_MANAGEMENT_IT.md](5_CLI_MANAGEMENT_IT.md).
