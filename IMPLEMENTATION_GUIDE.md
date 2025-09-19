# Guida all'Implementazione del Sistema di Creazione Asincrona di Elementi Database

## Panoramica

Questa guida descrive come implementare il sistema di creazione asincrona di elementi database (tabelle, colonne, relazioni) utilizzando un sistema di logging semplice che scrive solo su console e file.

## File Creati

1. `backend/thoth_core/models_patch.py` - Contiene i campi da aggiungere al modello SqlDb
2. `backend/thoth_core/thoth_ai/thoth_workflow/simple_logger.py` - Sistema di logging semplice
3. `backend/thoth_core/utilities/task_validation_patch.py` - Funzioni di validazione per i task asincroni
4. `backend/thoth_core/thoth_ai/thoth_workflow/async_db_elements.py` - Classe AsyncDbElementsTask
5. `backend/thoth_core/logging_setup.py` - Setup delle directory dei log
6. `backend/thoth_core/apps_patch.py` - Patch per l'inizializzazione delle directory dei log
7. `backend/thoth_core/admin_models/admin_sqldb_patch.py` - Aggiunta dell'azione admin asincrona

## Istruzioni di Implementazione

### 1. Aggiornare il Modello SqlDb

Modifica il file `backend/thoth_core/models.py` aggiungendo i campi definiti in `models_patch.py`:

1. Apri `backend/thoth_core/models.py`
2. Vai alla classe `SqlDb` (circa riga 277)
3. Dopo il campo `column_comment_end_time` (riga 331), aggiungi i seguenti campi:

```python
# Async database element creation status and logs
db_elements_status = models.CharField(
    max_length=20,
    choices=TaskStatus.choices,
    default=TaskStatus.IDLE,
)
db_elements_task_id = models.CharField(max_length=255, blank=True, null=True)
db_elements_start_time = models.DateTimeField(blank=True, null=True)
db_elements_end_time = models.DateTimeField(blank=True, null=True)
```

### 2. Creare il Sistema di Logging Semplice

1. Crea la directory `backend/thoth_core/thoth_ai/thoth_workflow/` se non esiste
2. Copia il contenuto di `simple_logger.py` in `backend/thoth_core/thoth_ai/thoth_workflow/simple_logger.py`

### 3. Aggiornare le Funzioni di Validazione

Modifica il file `backend/thoth_core/utilities/task_validation.py` aggiungendo le funzioni definite in `task_validation_patch.py`:

1. Apri `backend/thoth_core/utilities/task_validation.py`
2. Alla fine del file (dopo riga 378), aggiungi le funzioni da `task_validation_patch.py`:

```python
def check_sqldb_db_elements_can_start(sql_db: SqlDb):
    """
    Check if database elements creation task can start.
    
    Args:
        sql_db: SqlDb instance
        
    Returns:
        tuple: (can_start: bool, message: str)
    """
    sql_db.refresh_from_db()
    
    current_status = sql_db.db_elements_status
    
    if current_status in (TaskStatus.IDLE, TaskStatus.COMPLETED, TaskStatus.FAILED):
        return True, "Ready to start"
    
    if current_status == TaskStatus.RUNNING:
        is_running = validate_and_cleanup_running_sqldb_db_elements_task(sql_db)
        if not is_running:
            sql_db.refresh_from_db()
            return True, "Previous task was stale and has been cleaned up"
        return False, "A database elements creation task is currently running"
    
    return False, f"Unknown status: {current_status}"


def validate_and_cleanup_running_sqldb_db_elements_task(
    sql_db: SqlDb, timeout_hours: int = 2
) -> bool:
    """
    Validates if a database elements creation task marked as RUNNING is still legitimate.
    
    Args:
        sql_db: SqlDb instance
        timeout_hours: hours after which a running task is considered stale
        
    Returns:
        bool: True if task should still be considered running; False if reset
    """
    current_status = sql_db.db_elements_status
    if current_status != TaskStatus.RUNNING:
        return False
    
    start_time = sql_db.db_elements_start_time
    if start_time:
        cutoff_time = timezone.now() - timedelta(hours=timeout_hours)
        if start_time < cutoff_time:
            sql_db.db_elements_status = TaskStatus.FAILED
            sql_db.db_elements_end_time = timezone.now()
            sql_db.save(
                update_fields=["db_elements_status", "db_elements_end_time"]
            )
            return False
    
    return True


def force_reset_sqldb_db_elements_task_status(
    sql_db: SqlDb, reason: str = "Manual reset"
) -> bool:
    """
    Force reset of SqlDb database elements creation task status and metadata.
    """
    try:
        old_status = sql_db.db_elements_status
        old_task_id = sql_db.db_elements_task_id
        
        sql_db.db_elements_status = TaskStatus.IDLE
        sql_db.db_elements_task_id = None
        sql_db.db_elements_end_time = timezone.now()
        
        sql_db.save(update_fields=[
            "db_elements_status", 
            "db_elements_task_id", 
            "db_elements_end_time"
        ])
        
        logger.warning(
            f"Force reset db_elements for SqlDb {sql_db.id}: {reason} "
            f"(was: {old_status}, task_id: {old_task_id})"
        )
        return True
    except Exception as e:
        logger.error(
            f"Failed to force reset db_elements for SqlDb {sql_db.id}: {e}"
        )
        return False
```

### 4. Creare la Classe AsyncDbElementsTask

1. Crea la directory `backend/thoth_core/thoth_ai/thoth_workflow/` se non esiste
2. Copia il contenuto di `async_db_elements.py` in `backend/thoth_core/thoth_ai/thoth_workflow/async_db_elements.py`

### 5. Configurare le Directory dei Log

1. Copia il contenuto di `logging_setup.py` in `backend/thoth_core/logging_setup.py`
2. Modifica `backend/thoth_core/apps.py` aggiungendo l'import e la chiamata a `ensure_log_directories()`:

```python
from django.apps import AppConfig

class ThothCoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "thoth_core"

    def ready(self):
        # Import dei signals per la registrazione dei receiver

        # Initialize database plugins using the new plugin discovery system
        try:
            from .utilities.utils import initialize_database_plugins

            available_plugins = initialize_database_plugins()
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to initialize database plugins: {e}")
        
        # Ensure log directories exist
        from .logging_setup import ensure_log_directories
        ensure_log_directories()
```

### 6. Aggiornare l'Admin di SqlDb

Modifica il file `backend/thoth_core/admin_models/admin_sqldb.py` come segue:

1. Aggiungi gli import all'inizio del file:

```python
from thoth_core.thoth_ai.thoth_workflow.async_db_elements import (
    start_async_db_elements_creation,
)
from thoth_core.utilities.task_validation import (
    check_sqldb_db_elements_can_start,
)
```

2. Aggiungi `"create_db_elements_async"` alla tupla `actions` (circa riga 119):

```python
actions = (
    export_csv,
    import_csv,
    create_tables,
    create_relationships,
    create_db_elements,
    "create_db_elements_async",  # Add this new action
    "validate_db_fk_fields",
    export_db_structure_to_csv,
    "duplicate_sqldb",
    "associate_candidates_fk_to_pk",
    "test_connection",
    "generate_all_comments",
    generate_scope,
    generate_db_erd,
    generate_db_documentation,
    "scan_gdpr_compliance",
)
```

3. Aggiungi `"db_elements_status"` a `list_display` (circa riga 100):

```python
list_display = (
    "name",
    "db_host",
    "db_type",
    "db_name",
    "schema",
    "vector_db_name",
    "column_comment_status",
    "table_comment_status",
    "db_elements_status",  # Add this
),
```

4. Aggiungi un nuovo fieldset per lo stato dei task di creazione elementi database (circa riga 200):

```python
(
    "Database Elements Task Status",
    {
        "fields": (
            "db_elements_status",
            "db_elements_task_id",
            "db_elements_start_time",
            "db_elements_end_time",
        ),
        "classes": ("collapse",),
        "description": "Status for database elements creation tasks. Check console and log files for detailed progress.",
    },
),
```

5. Aggiungi il metodo `create_db_elements_async` alla classe `SqlDbAdmin` (circa riga 894):

```python
def create_db_elements_async(self, request, queryset):
    """
    Async version of create_db_elements that processes tables, columns, and relationships
    in the background without blocking the admin interface.
    Uses simple logging to console and file only.
    """
    if queryset.count() == 0:
        messages.error(request, "Please select at least one database.")
        return

    # Check each database can start the task
    ready_databases = []
    skipped_databases = []
    
    for sqldb in queryset:
        can_start, message = check_sqldb_db_elements_can_start(sqldb)
        if can_start:
            ready_databases.append(sqldb)
        else:
            skipped_databases.append((sqldb.name, message))

    if not ready_databases:
        messages.error(
            request, 
            f"No databases are ready for processing. Skipped: {len(skipped_databases)}"
        )
        for db_name, reason in skipped_databases:
            messages.error(request, f"  - {db_name}: {reason}")
        return

    # Get workspace ID (use first workspace or default)
    workspace_id = 1  # Default fallback
    if hasattr(request, 'current_workspace') and request.current_workspace:
        workspace_id = request.current_workspace.id

    try:
        # Start async processing
        sqldb_ids = [db.id for db in ready_databases]
        task_id = start_async_db_elements_creation(workspace_id, sqldb_ids, request.user.id)

        # Success message
        messages.success(
            request,
            f"Started async database elements creation for {len(ready_databases)} database(s). "
            f"Task ID: {task_id}. Check console and log files for progress.",
        )

        # Log skipped databases
        if skipped_databases:
            messages.warning(
                request,
                f"Skipped {len(skipped_databases)} database(s) that were not ready:"
            )
            for db_name, reason in skipped_databases:
                messages.warning(request, f"  - {db_name}: {reason}")

    except Exception as e:
        messages.error(request, f"Error starting async database elements creation: {str(e)}")

create_db_elements_async.short_description = (
    "Create all database elements (tables, columns, relationships) - ASYNC"
)
```

### 7. Creare e Applicare la Migrazione del Database

Dopo aver modificato il modello, crea e applica la migrazione:

```bash
cd backend
uv run python manage.py makemigrations thoth_core
uv run python manage.py migrate
```

## Verifica dell'Implementazione

1. Riavvia il server Django
2. Accedi all'interfaccia admin di Django
3. Vai alla sezione SqlDb
4. Seleziona uno o più database
5. Scegli l'azione "Create all database elements (tables, columns, relationships) - ASYNC" dal menu a tendina delle azioni
6. Esegui l'azione
7. Verifica che:
   - Lo stato del database cambi in "RUNNING"
   - I messaggi di log appaiano sulla console
   - I file di log vengano creati nella directory `logs/db_elements/`
   - Al termine, lo stato diventi "COMPLETED" o "FAILED"

## Risoluzione dei Problemi

1. **Errore di import**: Assicurati che tutti i percorsi di import siano corretti
2. **Errore di migrazione**: Verifica che tutti i campi del modello siano stati aggiunti correttamente
3. **Log non creati**: Controlla che le directory dei log abbiano i permessi di scrittura
4. **Task non parte**: Verifica che l'azione admin sia stata aggiunta correttamente

## Note Finali

Questa implementazione fornisce un sistema di creazione asincrona di elementi database con logging semplice che scrive solo su console e file, senza impattare le performance del database. I log vengono organizzati in directory strutturate per facilitare il tracciamento e il debugging.