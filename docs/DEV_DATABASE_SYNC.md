# Guida alla Sincronizzazione dei Database di Sviluppo

## Panoramica

Il sistema ThothAI utilizza uno script specializzato (`sync-to-volume.sh`) per sincronizzare i database di sviluppo dal filesystem locale ai container Docker. Questa guida spiega come utilizzare questo strumento per aggiungere nuovi database al sistema.

## Architettura della Sincronizzazione

### Come Funziona

Lo script `sync-to-volume.sh` esegue una sincronizzazione **non distruttiva** dei database:

1. **Legge** i file dalla directory locale `data/dev_databases/`
2. **Crea** un container Alpine temporaneo (che viene automaticamente eliminato)
3. **Copia** solo i nuovi file nel volume Docker `thoth-shared-data`
4. **Preserva** tutti i file esistenti nel volume (mai sovrascritti)

### Caratteristiche di Sicurezza

- **Non distruttivo**: I file esistenti nel volume Docker non vengono mai sovrascritti
- **Read-only mount**: La directory sorgente è montata in sola lettura
- **Container temporaneo**: Il container Alpine viene eliminato automaticamente
- **Conferma richiesta**: In modalità interattiva chiede sempre conferma

## Guida Passo-Passo per Aggiungere un Database

### 1. Preparare la Struttura del Database

Creare una directory per il nuovo database in `data/dev_databases/`:

```bash
# Esempio: aggiungere un database "company_data"
cd /Users/mp/ThothAI/data/dev_databases/
mkdir company_data
```

### 2. Aggiungere i File del Database

Struttura consigliata per ogni database:

```
data/dev_databases/
└── company_data/
    ├── company_data.sqlite         # File database SQLite
    └── database_description/        # Directory opzionale per documentazione
        ├── schema.sql              # Schema del database
        ├── sample_queries.sql      # Query di esempio
        └── README.md               # Documentazione
```

Copiare il file database:

```bash
# Copiare un database SQLite esistente
cp /path/to/your/database.sqlite data/dev_databases/company_data/company_data.sqlite
```

### 3. Eseguire la Sincronizzazione Interattiva

Dalla root del progetto ThothAI:

```bash
./scripts/sync-to-volume.sh
```

Il processo interattivo:

1. **Verifica**: Lo script controlla se i container Docker sono in esecuzione
2. **Anteprima**: Mostra quali file verranno aggiunti
3. **Conferma**: Chiede conferma prima di procedere
4. **Sincronizzazione**: Copia i nuovi file nel volume Docker
5. **Report**: Mostra un riepilogo dell'operazione

### Esempio di Sessione Interattiva

```bash
$ ./scripts/sync-to-volume.sh

==========================================
Quick Sync: dev_databases → Docker Volume
==========================================
✓ Docker containers are running

Checking for new files to sync...

New directories that will be added:
  + /company_data

New files that will be added:
  + company_data/company_data.sqlite
  + company_data/database_description/schema.sql
  + company_data/database_description/README.md

Do you want to proceed with the sync? (y/n) y

Starting sync operation...
sending incremental file list
company_data/
company_data/company_data.sqlite
company_data/database_description/
company_data/database_description/schema.sql
company_data/database_description/README.md

Sync completed. Current structure in volume:
/target/dev_databases
/target/dev_databases/california_schools
/target/dev_databases/company_data

Total files in volume:
8

✓ Sync completed successfully

==========================================
Sync operation completed
==========================================
```

## Modalità di Esecuzione

### Modalità Interattiva (Default)

```bash
./scripts/sync-to-volume.sh
```
- Mostra anteprima dei file da sincronizzare
- Richiede conferma esplicita
- Ideale per uso normale

### Modalità Force

```bash
./scripts/sync-to-volume.sh --force
```
- Sincronizza immediatamente senza conferma
- Utile per script automatici
- Mantiene comunque il comportamento non distruttivo

### Modalità Dry-Run

```bash
./scripts/sync-to-volume.sh --dry-run
```
- Mostra solo cosa verrebbe sincronizzato
- Non effettua alcuna modifica
- Perfetto per verificare prima di sincronizzare

## Verifica della Sincronizzazione

### Controllare i File nel Volume Docker

Per verificare che i database siano stati sincronizzati correttamente:

```bash
# Vedere i database nel volume
docker run --rm -v thoth-shared-data:/data alpine ls -la /data/dev_databases/

# Controllare un database specifico
docker run --rm -v thoth-shared-data:/data alpine ls -la /data/dev_databases/company_data/
```

### Verificare dall'Interno di un Container

Se i container sono in esecuzione:

```bash
# Entrare nel container backend
docker exec -it thoth-backend bash

# Verificare i database
ls -la /shared-data/dev_databases/
```

## Caso d'Uso Pratico: Aggiungere un Database California Schools

Esempio completo per aggiungere un database simile a quello esistente:

```bash
# 1. Creare la struttura
cd /Users/mp/ThothAI/data/dev_databases/
mkdir texas_schools
cd texas_schools

# 2. Copiare il database
cp /Downloads/texas_schools.sqlite ./texas_schools.sqlite

# 3. Aggiungere documentazione (opzionale)
mkdir database_description
echo "# Texas Schools Database" > database_description/README.md
echo "Database containing Texas public schools data" >> database_description/README.md

# 4. Sincronizzare
cd /Users/mp/ThothAI
./scripts/sync-to-volume.sh

# 5. Verificare
docker run --rm -v thoth-shared-data:/data alpine \
  find /data/dev_databases/texas_schools -type f
```

## Troubleshooting

### Errore: Docker volume 'thoth-shared-data' does not exist

**Problema**: Il volume Docker non è stato ancora creato.

**Soluzione**:
```bash
# Avviare i container almeno una volta per creare il volume
docker-compose up -d
docker-compose down
# Ora riprovare la sincronizzazione
./scripts/sync-to-volume.sh
```

### Errore: Source directory does not exist

**Problema**: La directory `data/dev_databases` non esiste.

**Soluzione**:
```bash
# Creare la directory
mkdir -p /Users/mp/ThothAI/data/dev_databases
```

### I Container Non Vedono i Nuovi Database

**Problema**: I database sono stati sincronizzati ma i container non li vedono.

**Soluzione**:
1. Verificare che la sincronizzazione sia completata con successo
2. Se i container erano già in esecuzione, potrebbero aver bisogno di un riavvio:
   ```bash
   docker-compose restart backend
   ```

### Come Verificare il Contenuto del Volume

Per ispezionare direttamente il contenuto del volume:

```bash
# Metodo 1: Container temporaneo
docker run --rm -v thoth-shared-data:/data alpine sh -c "
  echo 'Database directories:'
  ls -la /data/dev_databases/
  echo ''
  echo 'Total size:'
  du -sh /data/dev_databases/
"

# Metodo 2: Usando Docker volume inspect
docker volume inspect thoth-shared-data
```

## Note Importanti

1. **Non Distruttivo**: Lo script non sovrascrive MAI file esistenti nel volume
2. **Container Temporaneo**: Il container Alpine usato per la sincronizzazione viene automaticamente eliminato
3. **Nessun Riavvio Necessario**: I database sincronizzati sono immediatamente disponibili ai container in esecuzione
4. **Formato Database**: Attualmente supporta principalmente SQLite, ma può sincronizzare qualsiasi tipo di file

## FAQ

### D: Posso sincronizzare database mentre i container sono spenti?
**R**: Sì, basta che il volume Docker esista. Verrà mostrato un avviso ma la sincronizzazione procederà.

### D: Cosa succede se eseguo la sincronizzazione più volte?
**R**: Nessun problema. I file esistenti non vengono sovrascritti, quindi è sicuro eseguirla multiple volte.

### D: Posso rimuovere database dal volume?
**R**: Lo script `sync-to-volume.sh` aggiunge solo file. Per rimuovere database dal volume, dovrai farlo manualmente entrando in un container.

### D: Il container Alpine rimane nel mio Docker Desktop?
**R**: No, viene automaticamente rimosso grazie al flag `--rm`. Non lascia tracce.

### D: Quanto spazio occupa l'immagine Alpine?
**R**: Circa 5MB. Viene scaricata una sola volta e riutilizzata per tutte le sincronizzazioni future.

## Supporto

Per problemi o domande sulla sincronizzazione dei database, consultare:
- La documentazione principale del progetto in `/README.md`
- I log di Docker con `docker logs thoth-backend`
- Il codice sorgente degli script in `/scripts/`