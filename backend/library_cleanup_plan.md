# Piano di Pulizia Librerie Thoth

## thoth-qdrant (v0.1.1)
**Status**: ✅ COMPLETATO

### Modifiche effettuate:
- ✅ Rimosso `twine>=6.1.0` dalle dipendenze principali
- ✅ Spostato `twine` nelle dipendenze dev (dove dovrebbe stare)

### Dipendenze finali (minimali):
```toml
dependencies = [
    "qdrant-client>=1.7.0",
    "pydantic>=2.0.0",
    "typing-extensions>=4.0.0",
]
```

## thoth-dbmanager (v0.5.1)
**Status**: ⚠️ DA VERIFICARE

### Problemi identificati:
1. **pandas** - Probabilmente usato solo per presentazione dati (DataFrame)
   - Le librerie dovrebbero restituire dati grezzi (dict, list, tuple)
   - La presentazione è responsabilità del client
   
2. **tqdm** - Progress bar, non necessario in una libreria
   - Il client può implementare il proprio sistema di progress

3. **datasketch** - Da verificare se necessario per LSH

### Dipendenze attuali:
```
Requires: datasketch, pandas, pydantic, requests, SQLAlchemy, tqdm
```

### Dipendenze proposte (minimali):
```toml
dependencies = [
    "SQLAlchemy>=2.0.0",  # Core per gestione DB
    "pydantic>=2.0.0",    # Per validazione modelli
    "requests>=2.25.0",   # Per comunicazione HTTP se necessaria
    "datasketch>=1.5.0",  # Solo se LSH è core functionality
]
```

## thoth_be - Modifiche effettuate:
- ✅ Rimosso `pytest==8.4.1` dalle dipendenze principali
- ✅ Aggiornato .dockerignore per escludere tutti i test
- ✅ pytest e dipendenze test rimosse dall'ambiente

## thoth_ui/sql_generator - Modifiche effettuate:
- ✅ Rimosso `torch>=2.0.0` (non utilizzato)
- ✅ Aggiornato .dockerignore per escludere test

## Impatto stimato sulle dimensioni Docker:

### Rimozioni completate:
- torch: **-1GB**
- pytest e dipendenze test: **-50MB**
- twine da thoth-qdrant: **-10MB**

### Rimozioni proposte (thoth-dbmanager):
- pandas: **-150MB**
- numpy (dipendenza di pandas): **-50MB**
- tqdm: **-5MB**

### Totale risparmio stimato: ~1.3GB

## Prossimi passi:

1. **thoth-dbmanager**:
   - Clonare il repository
   - Analizzare l'uso di pandas
   - Sostituire DataFrame con dict/list
   - Rimuovere tqdm se usato solo per progress bar
   - Pubblicare nuova versione (0.6.0)

2. **thoth-qdrant**:
   - Rebuild della libreria
   - Test per verificare che tutto funzioni
   - Pubblicare nuova versione (0.1.2)

3. **Aggiornare thoth_be**:
   - Aggiornare versioni delle librerie in pyproject.toml
   - Rebuild Docker images
   - Test completo dell'applicazione

## Principi da seguire:

1. **Librerie minimali**: Solo dipendenze essenziali per la funzionalità core
2. **Niente presentazione**: Le librerie restituiscono dati grezzi, non formattati
3. **Niente UI/UX**: Niente progress bar, colori, tabelle formattate
4. **Niente tool di sviluppo**: Test, linting, publishing vanno in dev dependencies
5. **Responsabilità chiare**: 
   - Libreria = logica business
   - Client = presentazione e UX