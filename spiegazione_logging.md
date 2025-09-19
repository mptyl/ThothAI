# Spiegazione del Sistema di Logging per i Task Asincroni

## Panoramica del Sistema di Logging

Nel sistema ThothAI, il logging per i task asincroni viene gestito attraverso un sistema basato su memory handler che accumula i messaggi di log in memoria e poi li salva nei campi del database. Questo approccio permette di avere un tracciamento dettagliato dell'esecuzione dei task senza dover scrivere su file o su sistemi di logging esterni.

## Componenti Principali

### 1. MemoryLogHandler

Il `MemoryLogHandler` è un handler di logging personalizzato che:

- **Accumula i messaggi in memoria**: I log vengono memorizzati in una lista invece di essere scritti immediatamente su un supporto esterno.
- **Formatta i messaggi in modo consistente**: Usa un formatter standard per tutti i messaggi.
- **Fornisce metodi per recuperare i log**: È possibile ottenere tutti i log come una singola stringa.
- **Aggiunge automaticamente un riepilogo**: Alla fine del task, aggiunge un riepilogo con statistiche e durata.

```python
class MemoryLogHandler(logging.Handler):
    def __init__(self, level=logging.INFO):
        super().__init__(level)
        self.log_messages: List[str] = []
        self.start_time = timezone.now()
        
        # Formattazione standard: [timestamp] messaggio
        formatter = logging.Formatter(
            "[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        self.setFormatter(formatter)
```

### 2. Funzioni di Creazione Logger

Esistono funzioni specifiche per creare logger configurati per diversi tipi di task:

#### Per Workspace:
- `create_table_comment_logger()` - Per la generazione di commenti sulle tabelle
- `create_column_comment_logger()` - Per la generazione di commenti sulle colonne

#### Per SqlDb:
- `create_db_comment_logger()` - Per i task associati a un database SQL

Queste funzioni:
- Creano un logger con un nome univoco per evitare conflitti
- Aggiungono un MemoryLogHandler al logger
- Impediscono la propagazione dei log per evitare duplicazioni

```python
def create_db_comment_logger(sql_db, base_logger_name: str = "async_table_comments") -> tuple[logging.Logger, MemoryLogHandler]:
    # Crea un nome univoco per il logger
    logger_name = f"{base_logger_name}_db_{sql_db.id}_{timezone.now().timestamp()}"
    logger = logging.getLogger(logger_name)
    
    # Rimuovi handler esistenti e imposta il livello
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    
    # Crea e aggiunge il memory handler
    memory_handler = MemoryLogHandler(logging.INFO)
    logger.addHandler(memory_handler)
    
    # Impedisce la propagazione per evitare log duplicati
    logger.propagate = False
    
    return logger, memory_handler
```

### 3. Funzioni di Aggiornamento Log

Le funzioni `update_workspace_log()` e `update_sqldb_log()` si occupano di:

- Recuperare i messaggi di log accumulati nel MemoryLogHandler
- Salvarli nel campo appropriato del database (es. `table_comment_log`, `db_elements_log`)
- Gestire eventuali errori durante il salvataggio

```python
def update_sqldb_log(sql_db, memory_handler: MemoryLogHandler, field_name: str = "table_comment_log"):
    try:
        logs = memory_handler.get_logs()
        setattr(sql_db, field_name, logs)
        sql_db.save(update_fields=[field_name])
    except Exception as e:
        # Logging di fallback in caso di problemi con il database
        fallback_logger = logging.getLogger("thoth_core.async_tasks")
        fallback_logger.error(f"Failed to update SqlDb log: {str(e)}")
```

## Flusso di Logging in un Task Asincrono

### 1. Inizializzazione
All'inizio del task, viene creato un logger specifico:

```python
# Logger per questo DB
custom_logger, memory_handler = create_db_comment_logger(
    sql_db, base_logger_name="async_db_elements"
)
custom_logger.info(f"Starting async database elements creation for DB '{sql_db.name}'")
```

### 2. Logging Durante l'Esecuzione
Durante l'esecuzione del task, vengono registrati vari eventi:

```python
# Step 1: Creazione tabelle
custom_logger.info("Step 1: Creating tables")
custom_logger.info(f"Tables created: {len(created_tables)}")
custom_logger.info(f"Tables skipped: {len(skipped_tables)}")

# Step 2: Creazione colonne
custom_logger.info("Step 2: Creating columns for each table")
for sql_table in SqlTable.objects.filter(sql_db=sql_db):
    custom_logger.info(f"Processing table: {sql_table.name}")
    # ... altro logging ...
```

### 3. Gestione Errori
Gli errori vengono registrati con dettagli sufficienti per il troubleshooting:

```python
except Exception as e:
    custom_logger.error(f"Error processing table {sql_table.name}: {str(e)}")
    tables_failed += 1
```

### 4. Riepilogo e Finalizzazione
Alla fine del task, viene aggiunto un riepilogo e i log vengono salvati:

```python
# Aggiunge riepilogo con statistiche e durata
memory_handler.add_summary(processed_count, failed_count, len(db_table_ids))

# Aggiorna lo stato e salva i log
sql_db.db_elements_end_time = timezone.now()
sql_db.db_elements_status = "COMPLETED"
update_sqldb_log(sql_db, memory_handler, "db_elements_log")
sql_db.save(update_fields=[
    "db_elements_status",
    "db_elements_end_time",
    "db_elements_log",
])
```

## Vantaggi di Questo Approccio

1. **Tracciamento Completo**: Tutti gli eventi del task vengono registrati con timestamp.
2. **Accessibilità**: I log sono direttamente accessibili nell'interfaccia admin.
3. **Persistenza**: I log vengono salvati nel database e non vengono persi.
4. **Performance**: Scrivere in memoria è più veloce che scrivere su file o sistemi esterni.
5. **Diagnostica**: I log dettagliati facilitano il troubleshooting dei problemi.

## Integrazione con il Task di Creazione Elementi Database

Nel nostro piano per la creazione asincrona di tabelle, colonne e relazioni, il logging funzionerà così:

1. **Inizio Task**: Viene creato un logger specifico per il database e registrato l'inizio del task.
2. **Step Intermedi**: Vengono registrati:
   - Inizio di ogni step (creazione tabelle, colonne, relazioni)
   - Numero di elementi creati/saltati per ogni categoria
   - Eventuali errori o problemi encountered
3. **Fine Task**: Viene aggiunto un riepilogo con:
   - Numero totale di tabelle, colonne e relazioni create
   - Eventuali errori o fallimenti
   - Durata totale del task
4. **Salvataggio Log**: Tutti i messaggi vengono salvati nel campo `db_elements_log` del modello SqlDb.

Questo approccio garantisce che gli amministratori possano monitorare lo stato dei task asincroni e diagnosticare eventuali problemi direttamente dall'interfaccia admin di Django.