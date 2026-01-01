# Piano: Risoluzione Problema Avvio Preprocessing in Locale

## Problema Identificato
L'utente sta cercando di avviare il preprocessing del workspace demo in locale, ma il processo non parte.

## Analisi Effettuata

### 1. Verifica Configurazione Database
Il workspace Demo è correttamente configurato:
- **Workspace**: Demo (ID: presumibilmente 1)
- **SQL DB**: california_schools  
- **Vector DB**: Qdrant (california_schools)
- **Setting**: Default
- **Status**: IDLE

### 2. Architettura del Preprocessing
Il sistema usa:
- **Frontend**: Template HTMX in `preprocess.html` (linea 78)
- **URL**: `thoth_ai_backend:run_preprocessing`
- **View**: `run_preprocessing()` in `views.py` (linea 852)
- **Task**: `run_preprocessing_task()` in `async_tasks.py` (linea 30)
- **Core**: `preprocess()` in `preprocessing/preprocess.py` (linea 53)

### 3. Flusso del Preprocessing
1. L'utente clicca il pulsante "Run Preprocessing" nella UI
2. HTMX invia una richiesta POST a `/run_preprocessing/<workspace_id>/`
3. La view crea un thread Python e chiama `run_preprocessing_task()`
4. Il task esegue il preprocessing usando plugin-based architecture

## Possibili Cause del Problema

### A. **Browser/HTMX**
- JavaScript disabilitato
- HTMX non caricato correttamente
- CSRF token mancante o errato

### B. **Backend Django**
- Il server Django non è in ascolto (VERIFICATO: ✓ Attivo su 8200)
- Errori nel middleware
- Problemi con i permessi utente

### C. **Librerie/Dipendenze**
- Plugin `thoth_dbmanager` non installato o incompatibile
- Plugin `thoth_qdrant` non disponibile  
- Driver database SQLite non disponibile

### D. **Configurazione Environment**
- `DB_ROOT_PATH` non impostato o errato
- Porta Qdrant errata (6333 vs 6334 - il problema che abbiamo identificato!)
- Path del database SQLite non trovato

## Piano di Diagnosi e Risoluzione

### Fase 1: Verifica Accesso alla Pagina (IMMEDIATO)
1. Aprire browser su `http://localhost:8200/preprocess/`
2. Verificare che la pagina si carica senza errori
3. Aprire Developer Tools (F12) → Console
4. Cliccare su "Run Preprocessing"
5. Osservare:
   - Richieste HTTP nella tab Network
   - Eventuali errori JavaScript nella Console
   - Risposta del server (status code, body)

### Fase 2: Verifica Backend (SE FASE 1 FALLISCE)
1. Controllare log Django in tempo reale:
   ```bash
   tail -f backend/logs/thoth.log
   ```
2. Tentare chiamata diretta con curl:
   ```bash
   curl -X POST "http://localhost:8200/run_preprocessing/1/" \
     -H "Content-Type: application/json" \
     -H "X-CSRFToken: <token>" \
     -b "sessionid=<session_cookie>"
   ```

### Fase 3: Verifica Dipendenze Python (SE BACKEND FALLISCE)
1. Verificare installazione plugin:
   ```bash
   cd backend
   uv run python -c "import thoth_dbmanager; import thoth_qdrant; print('OK')"
   ```
2. Verificare DB_ROOT_PATH:
   ```bash
   uv run python -c "import os; print(os.getenv('DB_ROOT_PATH'))"
   ```

### Fase 4: Verifica Connessione Qdrant (CRITICO!)
Questo è probabilmente IL problema principale, dato che abbiamo appena scoperto che:
- Local usa porta 6334 per Qdrant
- Ma la configurazione del VectorDB nel database punta a 6333
- Il preprocessing fallisce se non riesce a connettersi a Qdrant

**Verifica:**
```bash
cd backend
uv run python manage.py shell -c "
from thoth_core.models import Workspace
w = Workspace.objects.first()
print(f'Qdrant Host: {w.sql_db.vector_db.host}')
print(f'Qdrant Port: {w.sql_db.vector_db.port}')
"
```

**FIX NECESSARIO:** Se la porta è 6333, modificarla a 6334:
```bash
cd backend
uv run python manage.py shell -c "
from thoth_core.models import VectorDatabase
vdb = VectorDatabase.objects.first()
vdb.port = 6334
vdb.host = 'localhost'
vdb.save()
print('Porta aggiornata a 6334')
"
```

### Fase 5: Test Manuale del Preprocessing (FALLBACK)
Se tutto il resto fallisce, eseguire direttamente:
```bash
cd backend
uv run python thoth_ai_backend/preprocessing/preprocess.py --db_name california_schools
```

## Soluzione Prioritaria

**IPOTESI PRINCIPALE**: Il preprocessing non parte perché Qdrant è configurato con porta 6333 nel database, ma in locale è sulla porta 6334.

**FIX IMMEDIATO**:
1. Aggiornare la porta del VectorDatabase a 6334 nel database Django
2. Riavviare il preprocessing

## Note Aggiuntive
- Il sistema usa threading invece di Celery/background workers
- Non c'è gestione della queue, quindi solo un preprocessing alla volta
- I log sono in `backend/logs/thoth.log`
- Lo status è tracciato nel modello `Workspace.preprocessing_status`

## Richiesta Prossimo Step
Prima di procedere con il fix, vorrei:
1. Confermare l'ipotesi aprendo la pagina di preprocessing nel browser
2. Verificare nel browser Developer Tools se ci sono errori
3. Controllare la porta Qdrant configurata nel database
