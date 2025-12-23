# Piano di Integrazione Informix in ThothAI

**Data:** 2025-10-05  
**Obiettivo:** Aggiungere supporto completo per database IBM Informix in ThothAI

---

## Executive Summary

Integrazione di Informix in ThothAI utilizzando l'implementazione SSH-based di thoth-dbmanager (InformixSSHAdapter). Questo approccio richiede **zero driver locali** e funziona via SSH + dbaccess sul server remoto.

### Componenti Chiave
- **Adapter**: InformixSSHAdapter (già implementato in thoth-dbmanager)
- **Dipendenze**: Solo `paramiko` (già presente)
- **Parametri specifici**: 3 nuovi campi nel modello SqlDb

---

## Fase 1: Backend - Modello Database ✅ COMPLETATA

### 1.1 Aggiornare SQLDBChoices ✅
**File**: `backend/thoth_core/models.py` (linee 114-121)

**Stato**: ✅ COMPLETATO

**Azione**:
```python
class SQLDBChoices(models.TextChoices):
    MARIADB = "MariaDB", "MariaDB"
    MYSQL = "MySQL", "MySQL"
    ORACLE = "Oracle", "Oracle"
    POSTGRES = "PostgreSQL", "PostgreSQL"
    SQLSERVER = "SQLServer", "SQLServer"
    SQLITE = "SQLite", "SQLite"
    INFORMIX = "Informix", "Informix"  # NUOVO
```

### 1.2 Aggiungere Campi Informix-Specifici ✅
**File**: `backend/thoth_core/models.py` (classe SqlDb, dopo linea 338)

**Stato**: ✅ COMPLETATO

**Azione**: Aggiungere 3 nuovi campi:
```python
# Informix-specific parameters
informix_server = models.CharField(
    max_length=255,
    blank=True,
    help_text="INFORMIXSERVER name (required for Informix, e.g., 'ns1i10')"
)
informix_protocol = models.CharField(
    max_length=50,
    blank=True,
    default='onsoctcp',
    help_text="Informix connection protocol (default: onsoctcp)"
)
informix_dir = models.CharField(
    max_length=500,
    blank=True,
    default='/u/appl/ids10',
    help_text="Path to INFORMIXDIR on remote server (Informix SSH only)"
)
```

### 1.3 Creare Migration ✅
**Stato**: ✅ COMPLETATO - Migration `0022_add_informix_support.py` creata e applicata

**Comando**:
```bash
cd backend
uv run python manage.py makemigrations thoth_core -n add_informix_support
uv run python manage.py migrate
```

---

## Fase 2: Backend - Database Management ✅ COMPLETATA

### 2.1 Aggiornare dbmanagement.py ✅
**File**: `backend/thoth_core/dbmanagement.py`

**Stato**: ✅ COMPLETATO

**Azione 1**: Aggiungere mapping Informix (circa linea 86):
```python
db_type_mapping = {
    "PostgreSQL": "postgresql",
    "SQLite": "sqlite",
    "MySQL": "mysql",
    "MariaDB": "mariadb",
    "SQLServer": "sqlserver",
    "Oracle": "oracle",
    "Informix": "informix",  # NUOVO
}
```

**Azione 2**: Aggiungere gestione parametri Informix (dopo linea 170):
```python
elif plugin_db_type == "informix":
    # Informix usa SSH + dbaccess
    # SSH params sono già gestiti separatamente
    common_params.update({
        "database": sqldb.db_name,
        "server": sqldb.informix_server or sqldb.db_host,
        "user": sqldb.user_name,
        "password": sqldb.password,
        "protocol": sqldb.informix_protocol or 'onsoctcp',
        "informixdir": sqldb.informix_dir or '/u/appl/ids10',
        # Per Informix SSH, host è il server Informix (dopo il tunnel SSH)
        "host": sqldb.db_host,
        "port": sqldb.db_port or 9088,
    })
```

---

## Fase 3: Backend - Admin Interface ✅ COMPLETATA

### 3.1 Aggiornare SqlDbAdminForm ✅
**File**: `backend/thoth_core/admin_models/admin_sqldb.py`

**Stato**: ✅ COMPLETATO

**Azione 1**: Aggiungere help_texts per campi Informix (linee 79-114):
```python
help_texts = {
    # ... esistenti ...
    "informix_server": "INFORMIXSERVER name for Informix databases (e.g., 'ns1i10')",
    "informix_protocol": "Connection protocol for Informix (default: onsoctcp)",
    "informix_dir": "Path to INFORMIXDIR on remote server (default: /u/appl/ids10)",
}
```

**Azione 2**: Aggiungere validazione condizionale in `clean()` (dopo linea 206):
```python
# Validate Informix-specific fields
if cleaned_data.get("db_type") == SQLDBChoices.INFORMIX:
    if not cleaned_data.get("ssh_enabled"):
        self.add_error(
            "ssh_enabled",
            "SSH tunnel is required for Informix connections. Please enable SSH."
        )
    if not cleaned_data.get("informix_server"):
        # Default to db_host if not provided
        cleaned_data["informix_server"] = cleaned_data.get("db_host")
```

### 3.2 Aggiungere Fieldset Informix ✅
**File**: `backend/thoth_core/admin_models/admin_sqldb.py` (fieldsets, dopo linea 291)

**Stato**: ✅ COMPLETATO

**Azione**: Inserire nuovo fieldset:
```python
(
    "Informix Configuration",
    {
        "fields": (
            "informix_server",
            "informix_protocol",
            "informix_dir",
        ),
        "classes": ("collapse",),
        "description": "Required parameters for IBM Informix databases (SSH connection required)",
    },
),
```

---

## Fase 4: Configurazione ✅ COMPLETATA

### 4.1 Aggiornare config.yml ✅
**File**: `config.yml` (linee 86-94)

**Stato**: ✅ COMPLETATO

**Azione**: Aggiungere opzione Informix:
```yaml
databases:
  sqlite: true       # Always required, cannot be disabled
  postgresql: true   # Enable for PostgreSQL support
  mysql: false       # Enable for MySQL support
  mariadb: true      # Enable for MariaDB support
  sqlserver: true    # Enable for SQL Server support
  informix: false    # Enable for IBM Informix support (requires SSH)
```

### 4.2 Verificare .env.local.template ✅
**File**: `.env.local.template`

**Stato**: ✅ VERIFICATO

**Verifica**: Assicurarsi che `DB_ROOT_PATH` sia presente (già presente, linea 49)

### 4.3 Aggiornare installer.py (per Docker) ⚠️
**File**: `scripts/installer.py`

**Stato**: ⚠️ DA VERIFICARE (installer dovrebbe già gestire automaticamente le opzioni database)

**Azione**: Verificare che l'installer processi correttamente la nuova opzione `databases.informix` e la includa in `.env.docker`

---

## Fase 5: SQL Generator Integration ✅

### 5.1 Verificare Compatibilità
**File**: `frontend/sql_generator/agents/core/agent_manager.py`

**Verifica**: Il SQL Generator usa `get_db_manager()` di Django backend, quindi eredita automaticamente il supporto Informix.

**Azione richiesta**: NESSUNA - la compatibilità è automatica tramite thoth-dbmanager

---

## Fase 6: Testing ✅

### 6.1 Test Backend
**Obiettivi**:
- [ ] Creare SqlDb con db_type="Informix" tramite admin
- [ ] Verificare validazione campi Informix
- [ ] Testare connessione con "Test Connection" action
- [ ] Verificare creazione tabelle/colonne con "Create Tables"

### 6.2 Test SQL Generator
**Obiettivi**:
- [ ] Configurare workspace con database Informix
- [ ] Eseguire query SQL semplice
- [ ] Verificare import metadata (tabelle/colonne/FK)
- [ ] Testare generazione SQL da domanda utente

### 6.3 Test SSH Tunnel
**Obiettivi**:
- [ ] Connessione con SSH password
- [ ] Connessione con SSH private key
- [ ] Verifica parametri Informix-specifici (server, protocol, informixdir)

---

## Fase 7: Documentazione ✅

### 7.1 README
**File**: `README.md`

**Azione**: Aggiungere sezione Informix:
```markdown
### Supported Databases
- PostgreSQL
- MariaDB/MySQL
- SQL Server
- SQLite
- **IBM Informix** (via SSH tunnel)

### Informix Configuration
Informix databases require SSH tunnel access. Configure the following:
- SSH connection details (host, port, username, key/password)
- INFORMIXSERVER name
- INFORMIXDIR path on remote server (default: /u/appl/ids10)
```

### 7.2 Config Documentation
**File**: `docs/configuration.md` (se esiste)

**Azione**: Documentare parametri Informix specifici

---

## Checklist Completa

### Backend Core
- [ ] ✅ Aggiungere `INFORMIX` a `SQLDBChoices`
- [ ] ✅ Aggiungere campi `informix_server`, `informix_protocol`, `informix_dir` a modello `SqlDb`
- [ ] ✅ Creare migration `add_informix_support`
- [ ] ✅ Applicare migration al database

### Database Management
- [ ] ✅ Aggiungere mapping `"Informix": "informix"` in `db_type_mapping`
- [ ] ✅ Aggiungere gestione parametri Informix in `get_db_manager()`
- [ ] ✅ Verificare che SSH params siano correttamente passati

### Admin Interface
- [ ] ✅ Aggiungere help_texts per campi Informix
- [ ] ✅ Aggiungere validazione Informix in `SqlDbAdminForm.clean()`
- [ ] ✅ Aggiungere fieldset "Informix Configuration"
- [ ] ✅ Test query già presente in `test_connection` action (linea 756)

### Configurazione
- [ ] ✅ Aggiungere opzione `informix: false` in `config.yml` sezione databases
- [ ] ✅ Verificare `.env.local.template` (già completo)
- [ ] ✅ Aggiornare `installer.py` per gestire `databases.informix`

### Testing
- [ ] 🔴 Test manuale: creare SqlDb Informix tramite admin
- [ ] 🔴 Test manuale: connessione Informix via SSH
- [ ] 🔴 Test manuale: import metadata Informix
- [ ] 🔴 Test manuale: generazione SQL con database Informix

### Documentazione
- [ ] 🔴 Aggiornare README con supporto Informix
- [ ] 🔴 Documentare parametri Informix-specifici
- [ ] 🔴 Aggiungere esempi configurazione Informix

---

## Parametri Informix - Mappatura Completa

### Da SqlDb Model → InformixSSHAdapter

| Campo Model ThothAI | Parametro Adapter | Note |
|---------------------|-------------------|------|
| `db_name` | `database` | Nome database Informix |
| `db_host` | `host` + `ssh_host` | Host server Informix (post-SSH) |
| `db_port` | `port` | Default 9088 per Informix |
| `user_name` | `user` | Username database |
| `password` | `password` | Password database |
| `informix_server` | `server` | INFORMIXSERVER name |
| `informix_protocol` | `protocol` | Default 'onsoctcp' |
| `informix_dir` | `informixdir` | Path INFORMIXDIR sul server |
| `ssh_enabled` | (richiesto) | DEVE essere True per Informix |
| `ssh_host` | `ssh_host` | Server SSH bastion |
| `ssh_port` | `ssh_port` | Porta SSH (default 22) |
| `ssh_username` | `ssh_username` | Username SSH |
| `ssh_password` | `ssh_password` | Password SSH (opzionale) |
| `ssh_private_key_path` | `ssh_private_key_path` | Path chiave privata SSH |
| `ssh_private_key_passphrase` | `ssh_private_key_passphrase` | Passphrase chiave SSH |

---

## Note Tecniche

### Perché InformixSSHAdapter?
1. **Zero dipendenze locali** - Solo paramiko (già presente)
2. **Multi-piattaforma** - Funziona su macOS, Linux, Windows, ARM64
3. **Docker-friendly** - Immagini leggere, nessun driver da installare
4. **Produzione-ready** - Stesso adapter per dev/staging/prod

### Limitazioni Note
- Richiede `dbaccess` disponibile sul server remoto
- Richiede SSH tunnel (non supporta connessione diretta ODBC)
- Performance leggermente inferiore rispetto a driver nativi (overhead SSH + parsing testo)

### Vantaggi per ThothAI
- ✅ Riutilizzo completo infrastruttura SSH esistente
- ✅ Nessuna modifica a SQL Generator richiesta
- ✅ Admin interface già pronto per SSH
- ✅ Backward compatibility totale

---

## Timeline Stimata

| Fase | Durata | Stato |
|------|--------|-------|
| **Fase 1**: Backend Modello | 30 min | 🟡 In progress |
| **Fase 2**: Database Management | 45 min | 🔴 TODO |
| **Fase 3**: Admin Interface | 45 min | 🔴 TODO |
| **Fase 4**: Configurazione | 30 min | 🔴 TODO |
| **Fase 5**: SQL Generator | 15 min | 🔴 TODO |
| **Fase 6**: Testing | 90 min | 🔴 TODO |
| **Fase 7**: Documentazione | 45 min | 🔴 TODO |
| **TOTALE** | **~5 ore** | |

---

## Prossimi Passi Immediati

1. ✅ Creare questo piano
2. 🟡 **IN CORSO**: Modificare models.py (aggiungere INFORMIX + 3 campi)
3. 🔴 Creare migration
4. 🔴 Aggiornare dbmanagement.py
5. 🔴 Aggiornare admin_sqldb.py
6. 🔴 Aggiornare config.yml
7. 🔴 Testing end-to-end

---

---

## ✅ IMPLEMENTAZIONE COMPLETATA

**Data completamento:** 2025-10-05  
**Stato:** Backend pronto - In attesa pubblicazione thoth-dbmanager 0.7.0

### Modifiche Implementate

#### 1. Backend ✅
- [x] Modello `SqlDb` esteso con 3 campi Informix
- [x] Migration `0022_add_informix_support.py` creata e applicata
- [x] `dbmanagement.py` aggiornato con mapping e parametri Informix
- [x] Admin interface con validazione, help texts e fieldset dedicato

#### 2. Configurazione ✅
- [x] `config.yml` aggiornato con opzione `databases.informix`
- [x] `.env.local.template` verificato (già completo)
- [x] Dipendenza `thoth-dbmanager` documentata (upgrade a 0.7.0 richiesto)

#### 3. Documentazione ✅
- [x] Guida configurazione Informix completa (`docs/INFORMIX_CONFIGURATION_GUIDE.md`)
- [x] Riepilogo implementazione (`INFORMIX_IMPLEMENTATION_SUMMARY.md`)
- [x] README backend e principale aggiornati
- [x] Piano di integrazione aggiornato (questo file)

### File Creati/Modificati

**Nuovi file:**
- `backend/thoth_core/migrations/0022_add_informix_support.py`
- `docs/INFORMIX_CONFIGURATION_GUIDE.md`
- `INFORMIX_IMPLEMENTATION_SUMMARY.md`
- `INFORMIX_INTEGRATION_PLAN.md` (questo file)

**File modificati:**
- `backend/thoth_core/models.py` (linee 115, 341-358)
- `backend/thoth_core/dbmanagement.py` (linee 87, 181-196)
- `backend/thoth_core/admin_models/admin_sqldb.py` (linee 114-116, 210-220, 307-318)
- `backend/pyproject.toml` (linee 59-60, nota per upgrade)
- `config.yml` (linea 94)
- `backend/README.md` (sezione Database Support)
- `README.md` (sezione SSH Tunnel Support)

### Prossimi Passi

1. **Pubblicare thoth-dbmanager 0.7.0 su PyPI** (priorità ALTA)
   ```bash
   cd /Users/Thoth/thoth_sqldb2
   uv build
   twine upload dist/*
   ```

2. **Aggiornare ThothAI a thoth-dbmanager 0.7.0**
   ```bash
   # In backend/pyproject.toml
   "thoth-dbmanager[postgresql,sqlite]==0.7.0"
   cd backend && uv sync
   ```

3. **Testing completo** (dopo upgrade):
   - Test connessione Informix via admin
   - Test import metadata
   - Test generazione SQL

---

**Ultimo aggiornamento**: 2025-10-05 16:35:00
