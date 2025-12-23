# Workaround per Bug Informix in thoth-dbmanager 0.7.0

**Data:** 2025-10-05  
**Stato:** ✅ Risolto con workaround temporaneo  
**Versione thoth-dbmanager:** 0.7.0

---

## Problema Identificato

### Sintomo
Quando si tenta di testare la connettività con un database Informix, si riceve l'errore:

```
Database 'olimpix' - Connection failed: Database type 'informix' is not known to the plugin system. 
Available types: ['postgresql', 'mariadb', 'sqlserver', 'sqlite']
```

### Causa Root
Il plugin Informix è stato implementato in `thoth-dbmanager` 0.7.0 e il file `informix.py` esiste nel package PyPI, ma **manca la registrazione in `DATABASE_DEPENDENCIES`** nel file `dynamic_imports.py`.

**Evidenza:**
```python
# In thoth_dbmanager/dynamic_imports.py (versione 0.7.0)
DATABASE_DEPENDENCIES = {
    "postgresql": ["psycopg2"],
    "mariadb": ["mariadb"],
    "sqlserver": ["pyodbc"],
    "sqlite": []
    # ❌ MANCANTE: "informix": ["paramiko"]
}
```

Il plugin è correttamente registrato nel registry (`DbPluginRegistry.list_plugins()` include `'informix'`), ma `get_available_databases()` non lo riconosce perché non è in `DATABASE_DEPENDENCIES`.

---

## Soluzione Implementata

### Workaround Temporaneo in ThothAI

Modificato `/Users/mp/ThothAI/backend/thoth_core/utilities/utils.py` nella funzione `initialize_database_plugins()`:

```python
# WORKAROUND for thoth-dbmanager 0.7.0 bug: Informix plugin exists but is missing from DATABASE_DEPENDENCIES
# Check if Informix plugin is registered but not in available_databases
try:
    from thoth_dbmanager.core.registry import DbPluginRegistry
    registered_plugins = DbPluginRegistry.list_plugins()
    
    if 'informix' in registered_plugins and 'informix' not in available_databases:
        # Check if paramiko is available (Informix only dependency)
        try:
            import paramiko
            available_databases['informix'] = True
            logger.info("Informix plugin manually enabled (workaround for thoth-dbmanager 0.7.0 bug)")
        except ImportError:
            available_databases['informix'] = False
            logger.debug("Informix plugin registered but paramiko not available")
except Exception as workaround_error:
    logger.debug(f"Informix workaround check failed: {workaround_error}")
```

### Risultato
Dopo il workaround, `initialize_database_plugins()` restituisce:
```python
{
    'postgresql': True,
    'mariadb': False,
    'sqlserver': False,
    'sqlite': True,
    'informix': True  # ✅ Ora disponibile
}
```

---

## Installazione Dipendenze

Per abilitare Informix in ambiente locale:

```bash
cd backend
uv pip install "thoth-dbmanager[informix]==0.7.0"
```

Questo installa:
- `paramiko>=3.4.0` (per SSH tunnel)
- `pyodbc>=4.0.0` (dichiarato nell'extra ma non usato dal plugin SSH-based)

**Nota:** Il plugin Informix di ThothAI usa **solo `paramiko`** (SSH + dbaccess), non richiede ODBC.

---

## Fix Permanente Richiesto

### In thoth-dbmanager (prossima versione)

Aggiungere in `thoth_dbmanager/dynamic_imports.py`:

```python
DATABASE_DEPENDENCIES = {
    "postgresql": ["psycopg2"],
    "mariadb": ["mariadb"],
    "sqlserver": ["pyodbc"],
    "sqlite": [],
    "informix": ["paramiko"]  # ✅ AGGIUNGERE QUESTA RIGA
}
```

### Versione Target
- **thoth-dbmanager 0.7.1** o successiva

### Rimozione Workaround
Quando thoth-dbmanager sarà fixato, rimuovere il blocco workaround da `backend/thoth_core/utilities/utils.py` (linee 593-609).

---

## Test di Verifica

### 1. Verifica Plugin Disponibili
```bash
cd backend
uv run python manage.py shell -c "
from thoth_core.utilities.utils import initialize_database_plugins
print(initialize_database_plugins())
"
```

**Output atteso:**
```
INFO Informix plugin manually enabled (workaround for thoth-dbmanager 0.7.0 bug)
INFO Available database plugins: postgresql, sqlite, informix
{'postgresql': True, 'mariadb': False, 'sqlserver': False, 'sqlite': True, 'informix': True}
```

### 2. Test Connessione Informix
1. Accedi all'admin Django: http://localhost:8200/admin
2. Crea un nuovo `SqlDb` con:
   - `db_type`: Informix
   - Configura SSH tunnel (obbligatorio)
   - Imposta parametri Informix (server, database, user, password)
3. Esegui "Test Connection" action

**Risultato atteso:** Connessione riuscita (se credenziali SSH e Informix corrette).

---

## Riferimenti

- **Issue thoth-dbmanager:** Bug in DATABASE_DEPENDENCIES (da segnalare)
- **Plugin Informix:** `/Users/mp/ThothAI/backend/.venv/lib/python3.13/site-packages/thoth_dbmanager/plugins/informix.py`
- **Documentazione Informix:** `docs/INFORMIX_IMPLEMENTATION_SUMMARY.md`
- **Workaround implementato:** `backend/thoth_core/utilities/utils.py` (linee 593-609)

---

## Changelog

- **2025-10-05:** Bug identificato e workaround implementato
- **2025-10-05:** Installato `thoth-dbmanager[informix]==0.7.0` con `paramiko` e `pyodbc`
- **2025-10-05:** Verificato funzionamento con `initialize_database_plugins()`
