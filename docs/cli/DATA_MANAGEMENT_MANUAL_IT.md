# ThothAI - Manuale Gestione Dati e Database (BIRD)

Questa guida spiega come utilizzare la CLI `thothai-data-cli` (comando `thothai-data`) per gestire l'interscambio di file CSV e l'inserimento di nuovi database SQLite (come quelli del dataset benchmark BIRD) all'interno di ThothAI.

## 1. Introduzione

ThothAI utilizza due volumi principali per i dati:
1.  **thoth-data-exchange**: Utilizzato per caricare CSV (importazione) o scaricare risultati (esportazione).
2.  **thoth-shared-data**: Utilizzato per ospitare i database SQLite che verranno interrogati dall'IA.

La CLI `thothai-data` permette di interagire con questi volumi senza dover manipolare manualmente i file all'interno dei container Docker.

---

## 2. Installazione della CLI

Se hai già installato `thothai-cli` seguendo il manuale di installazione, puoi aggiungere la gestione dati nello stesso ambiente virtuale:

```bash
# Entra nella cartella del tuo progetto
cd my-thothai
source .venv/bin/activate

# Installa la CLI per i dati
uv pip install thothai-data-cli
```

---

## 3. Configurazione

Al primo comando, la CLI ti guiderà nella configurazione automatica:

```bash
uv run thothai-data config test
```

Rispondi alle domande per configurare il tipo di connessione (`local` se Docker gira sulla tua macchina) e la modalità (`compose` per l'installazione semplificata).

---

## 4. Gestione File CSV (Data Exchange)

Questi comandi servono per scambiare dati con il volume di exchange di ThothAI.

### Caricare un file CSV per l'importazione
```bash
uv run thothai-data csv upload mio_file_da_importare.csv
```

### Elencare i file presenti nel volume
```bash
uv run thothai-data csv list
```

### Scaricare un file generato da ThothAI (es. un export)
```bash
uv run thothai-data csv download nome_file_remoto.csv -o ./cartella_locale/
```

---

## 5. Inserimento di un Database BIRD

Il dataset BIRD (o qualsiasi altro database SQLite) deve essere inserito seguendo una struttura specifica affinché ThothAI possa rilevarlo correttamente. Ogni database deve trovarsi in una sottocartella dedicata con lo stesso nome del file.

### Procedura di inserimento

Supponiamo di avere un database scaricato chiamato `california_schools.sqlite`.

1.  **Comando di inserimento**:
    ```bash
    uv run thothai-data db insert ./california_schools.sqlite
    ```

### Cosa succede dietro le quinte?
La CLI creerà nel volume condiviso la seguente struttura:
`/app/data/california_schools/california_schools.sqlite`

### Verificare l'inserimento
Puoi controllare i database registrati nel volume con:
```bash
uv run thothai-data db list
```

---

## 6. Registrazione in ThothAI

Dopo aver inserito il file fisico tramite la CLI, devi registrarlo nell'interfaccia di ThothAI:

1.  Accedi al **Pannello Admin** ([http://localhost:8040/admin](http://localhost:8040/admin)).
2.  Vai su **SQL Databases** e clicca su **Add SQL Database**.
3.  Configura i parametri del database SQLite:
    *   **DB Type**: `sqlite`
    *   **DB Name**: `california_schools`
    *   **DB Path**: `/app/data/california_schools/california_schools.sqlite` (questo è il path interno al container generato dalla CLI).
4.  Salva e clicca su **Test Connection**.

---

## 7. Troubleshooting

*   **Connessione Docker fallita**: Assicurati che Docker sia attivo e che i container di ThothAI siano in esecuzione (`thothai up`).
*   **File non trovato**: Verifica che il file `.sqlite` locale esista veramente nel percorso specificato.
*   **Permessi SSH**: Se operi su un server remoto, verifica di aver configurato correttamente la chiave SSH nel file `~/.thothai-data.yml`.
