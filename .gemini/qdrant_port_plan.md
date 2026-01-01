# Piano: Configurazione Qdrant 6334 per Ambiente Locale

## Problema
Il preprocess in locale cerca Qdrant sulla porta 6333 invece della porta 6334 che abbiamo configurato. Questo accade perché ci sono hardcoded default e variabili d'ambiente non correttamente propagate.

## Analisi dei File Coinvolti

### 1. **`frontend/sql_generator/helpers/config_manager.py` (CRITICO)**
**Linee 106-114**: La classe `VectorDBConfig` imposta i default:
```python
default_host = 'thoth-qdrant' if is_docker else 'localhost'
default_port = 6333 if is_docker else 6334  # ✓ Già corretto!
```
**Problema**: Legge `VECTOR_DB_PORT` da env, ma questo non è generato da `generate_env_local.py`.

### 2. **`scripts/generate_env_local.py`**
**Linee 155-163**: Genera `QDRANT_PORT` e `QDRANT_URL` ma **NON** genera `VECTOR_DB_PORT` o `VECTOR_DB_HOST`.

### 3. **`backend/thoth_ai_backend/preprocessing/preprocess.py`**
Il preprocess del backend usa `VectorDatabase` model da Django, che legge configurazione salvata nel database (porta hardcoded a 6333).

### 4. **`scripts/configure_vector_db.py`**
**Linee 42, 58**: Hardcoded `"port": 6333`.

## Soluzione Proposta

### Fase 1: Aggiornare `generate_env_local.py`
Aggiungere generazione di `VECTOR_DB_HOST` e `VECTOR_DB_PORT` affinché il SQL Generator (che usa `config_manager.py`) legga le configurazioni corrette.

**Modifiche**:
```python
# Dopo la linea 172 (dopo QDRANT_URL)
env_lines.append(f"VECTOR_DB_HOST=localhost")  # Per locale
env_lines.append(f"VECTOR_DB_PORT={qdrant_port}")  # Usa 6334
```

### Fase 2: Aggiornare `scripts/configure_vector_db.py`
Parametrizzare la porta invece di hardcode 6333.

**Modifiche**:
- Leggere `QDRANT_PORT` da environment (default 6334 per locale, 6333 per Docker)
- Usare questa porta per configurare `VectorDatabase`

### Fase 3: Verificare `scripts/installer.py`
L'installer genera `.env.docker` e **non include** `VECTOR_DB_PORT` o `VECTOR_DB_HOST`. Per Docker è corretto usare i default hardcoded (host=thoth-qdrant, port=6333).

**Nessuna modifica necessaria** - Docker continuerà a usare i default interni.

## Dettaglio Modifiche

### File 1: `scripts/generate_env_local.py`
```python
# Linea ~172, dopo env_lines.append(f"QDRANT_URL={qdrant_url}")
env_lines.append(f"VECTOR_DB_HOST=localhost")
env_lines.append(f"VECTOR_DB_PORT={qdrant_port}")
```

### File 2: `scripts/configure_vector_db.py`
```python
# Linea 1-14, aggiungere import
import os

# Linea 40-46, modificare:
is_docker = os.getenv('DOCKER_CONTAINER', 'false').lower() == 'true'
qdrant_host = 'thoth-qdrant' if is_docker else 'localhost'
qdrant_port = int(os.getenv('QDRANT_PORT', '6333' if is_docker else '6334'))

vdb.configuration = {
    "host": qdrant_host,
    "port": qdrant_port,
    # ... resto invariato
}

# Linea 56-62, stessa modifica per creazione:
configuration={
    "host": qdrant_host,
    "port": qdrant_port,
    # ... resto invariato
}
```

## Analisi Regressioni

### Docker Compose
- **`.env.docker`**: Generato da `installer.py`, non include `VECTOR_DB_PORT/HOST`.
- **Default in `config_manager.py`**: Con `DOCKER_CONTAINER=true`, usa `default_port=6333` e `default_host=thoth-qdrant`.
- **Risultato**: **NESSUNA REGRESSIONE** ✓

### Docker Swarm
- Usa stessi meccanismi di Docker Compose.
- **Risultato**: **NESSUNA REGRESSIONE** ✓

### Local (start-all.sh)
- **`.env.local`**: Generato da `generate_env_local.py`, includerà `VECTOR_DB_PORT=6334`.
- **Default in `config_manager.py`**: Con `DOCKER_CONTAINER=false`, usa `default_port=6334`.
- **Risultato**: **Funzionalità migliorata**, nessuna regressione ✓

## Test di Verifica

1. **Locale**: Eseguire `./start-all.sh`, verificare che il preprocess usi porta 6334.
   ```bash
   cat .env.local | grep VECTOR_DB_PORT  # Dovrebbe mostrare 6334
   ```

2. **Docker Compose**: Eseguire `docker compose up`, verificare che il preprocess usi porta 6333.
   ```bash
   docker compose exec backend env | grep VECTOR_DB  # Non dovrebbe esserci
   docker compose exec sql-generator env | grep VECTOR_DB  # Non dovrebbe esserci
   # I default hardcoded verranno usati
   ```

3. **Swarm**: Come Docker Compose.

## Riepilogo
- ✅ Local usa 6334
- ✅ Docker Compose usa 6333
- ✅ Swarm usa 6333
- ✅ Zero regressioni
