# Panoramica Installazione ThothAI

Benvenuti nella documentazione di installazione di ThothAI. L'installazione di ThothAI è flessibile e progettata per adattarsi a diverse esigenze, dallo sviluppo locale alla produzione su cluster distribuiti.

Questa guida vi aiuterà a scegliere la modalità di installazione più adatta alle vostre esigenze.

## Declinazioni dell'Installazione

Esistono tre principali "declinazioni" o dimensioni da considerare per l'installazione:

### 1. Modalità di Installazione
Questa è la scelta fondamentale su come ottenere il software:

*   **Installazione da Sorgente**: Ideale per sviluppatori che vogliono contribuire al codice o necessitano di personalizzazioni profonde. Permette di compilare le immagini Docker (Build) e fare il Push su un registry personalizzato. Richiede il clone del repository GitHub.
    *   *Vedi Manuale 2: Installazione da Sorgente*

*   **Installazione Assistita da CLI**: Ideale per utenti finali e amministratori di sistema. Usa lo strumento `thothai-cli` (che può essere installato via `uv` o `pip`) per scaricare e configurare automaticamente l'ambiente senza dover gestire manualmente il codice sorgente.
    *   *Vedi Manuale 3 e 4*

### 2. Topologia dell'Infrastruttura
ThothAI supporta due architetture Docker:

*   **Singolo Nodo (Docker Compose)**: L'intera applicazione gira su una singola macchina (laptop, server o VM). È la modalità più semplice e consigliata per test, sviluppo e piccole installazioni.
    *   *Vedi Manuale 3: Installazione CLI su Docker Compose*

*   **Cluster (Docker Swarm)**: L'applicazione è distribuita su più nodi per alta disponibilità e scalabilità. È la modalità consigliata per produzione e ambienti aziendali.
    *   *Vedi Manuale 4: Installazione CLI su Docker Swarm*

### 3. Posizione dell'Installazione
Indipendentemente dalla modalità e topologia, potete installare ThothAI:

*   **In Locale**: Sul vostro computer attuale (es. sviluppatore che installa sul proprio laptop) o accedendo direttamente al server di destinazione.
*   **In Remoto**: Dal vostro computer locale verso un server remoto (es. VPS o server aziendale) tramite connessione SSH gestita automaticamente dalla CLI.

## Indice dei Manuali

Per proseguire, selezionate il manuale appropriato:

1.  **[1_INSTALLATION_OVERVIEW_IT.md](1_INSTALLATION_OVERVIEW_IT.md)**: Questo documento.
2.  **[2_SOURCE_INSTALLATION_IT.md](2_SOURCE_INSTALLATION_IT.md)**: Guida per l'installazione da sorgente (clone git, build personalizzata, uso script `install.sh`/`install.ps1`).
3.  **[3_CLI_COMPOSE_INSTALLATION_IT.md](3_CLI_COMPOSE_INSTALLATION_IT.md)**: Guida per l'installazione tramite CLI su singolo nodo (Compose), locale o remoto. Include opzioni per Docker Hub o Registry privato.
4.  **[4_CLI_SWARM_INSTALLATION_IT.md](4_CLI_SWARM_INSTALLATION_IT.md)**: Guida per l'installazione tramite CLI su cluster Swarm, locale o remoto. Include opzioni per Docker Hub o Registry privato.
5.  **[5_CLI_MANAGEMENT_IT.md](5_CLI_MANAGEMENT_IT.md)**: Guida alla gestione post-installazione (aggiornamenti automatici, pulizia, verifica stato) tramite CLI.
