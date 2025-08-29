# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Piano di Migrazione: Gestione Centralizzata degli Embedding

## Obiettivo

Ripristinare la gestione lato libreria degli embedding in `thoth-vdbmanager` per risolvere i problemi di Docker e garantire consistenza architetturale tra `thoth_be` e `thoth_ui`.

## Architettura Target

### Principi di Design

1. **Centralizzazione**: Gli embedding sono gestiti interamente dalla libreria `thoth-vdbmanager`
2. **Docker Compatibility**: Funzionamento robusto in ambienti containerizzati
3. **Performance**: Caching intelligente e lazy loading dei modelli
4. **Backward Compatibility**: Transizione trasparente per i progetti esistenti

### Schema Architetturale

```
┌─────────────────────────────────────────┐
│           Client Applications           │
│  ┌─────────────┐    ┌─────────────┐    │
│  │  thoth_be   │    │  thoth_ui   │    │
│  └─────────────┘    └─────────────┘    │
└─────────────┬───────────────────────────┘
              │ Simple API Calls
              ▼
┌─────────────────────────────────────────┐
│         thoth-vdbmanager v2.0           │
│  ┌─────────────────────────────────────┐ │
│  │     Embedding Manager Core         │ │
│  │  ┌─────────────┐ ┌─────────────┐  │ │
│  │  │Model Cache  │ │Environment  │  │ │
│  │  │   Manager   │ │  Detector   │  │ │
│  │  └─────────────┘ └─────────────┘  │ │
│  │  ┌─────────────┐ ┌─────────────┐  │ │
│  │  │SentenceXfmr │ │Error Handler│  │ │
│  │  │   Factory   │ │   & Retry   │  │ │
│  │  └─────────────┘ └─────────────┘  │ │
│  └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## Fase 1: Progettazione e Implementazione della Libreria

### 1.1 Analisi della Situazione Attuale

#### Task: Audit delle Versioni
```bash
# Comparazione delle versioni
pip show thoth-vdbmanager==0.2.24
pip show thoth-vdbmanager==0.4.0

# Analisi delle differenze
git clone https://github.com/mptyl/thoth_vdbmanager
cd thoth_vdbmanager
git diff v0.2.24..v0.4.0 --name-only
```

#### Deliverables
- [ ] **Documento di comparazione** delle API tra versioni
- [ ] **Lista delle breaking changes** identificate
- [ ] **Mappa delle dipendenze** attuali nei progetti

### 1.2 Design del Nuovo Embedding Manager

#### Core Components

##### EmbeddingManager Class
```python
# Pseudocode dell'architettura target
class EmbeddingManager:
    """Gestore centralizzato per tutti gli embedding operations."""
    
    def __init__(self, config: EmbeddingConfig):
        self.model_cache = ModelCache()
        self.env_detector = EnvironmentDetector()
        self.error_handler = RetryHandler()
    
    def encode(self, texts: List[str], model: str = "default") -> np.ndarray:
        """Main encoding interface - nasconde la complessità del modello."""
        
    def get_model(self, model_name: str) -> SentenceTransformer:
        """Lazy loading con caching intelligente."""
        
    def preload_models(self, models: List[str]) -> None:
        """Pre-caricamento per ambienti Docker."""
```

##### Environment Detection
```python
class EnvironmentDetector:
    """Rileva l'ambiente di esecuzione e adatta il comportamento."""
    
    def is_docker(self) -> bool:
        """Rileva se siamo in un container Docker."""
        
    def get_cache_strategy(self) -> CacheStrategy:
        """Strategia di cache basata sull'ambiente."""
        
    def get_download_strategy(self) -> DownloadStrategy:
        """Strategia di download modelli basata sull'ambiente."""
```

#### Task di Implementazione
- [ ] **Progettare le interfacce** pubbliche del nuovo EmbeddingManager
- [ ] **Implementare il model caching** con strategie per Docker/locale
- [ ] **Creare il sistema di retry** robusto per download failures
- [ ] **Implementare environment detection** automatica

### 1.3 Docker Optimization Strategy

#### Problemi da Risolvere
1. **Download runtime**: Evitare download di modelli a runtime in Docker
2. **Network isolation**: Gestire problemi di connettività in container
3. **Memory management**: Ottimizzare uso memoria per modelli grandi

#### Soluzioni Proposte

##### Pre-download Strategy
```python
class DockerModelManager:
    """Gestore specifico per ambienti Docker."""
    
    def preload_common_models(self) -> None:
        """Pre-carica i modelli più comuni durante la build."""
        common_models = [
            "sentence-transformers/all-MiniLM-L6-v2",
            "paraphrase-multilingual-MiniLM-L12-v2"
        ]
        for model in common_models:
            self._download_and_cache(model)
    
    def get_model_with_fallback(self, model_name: str) -> SentenceTransformer:
        """Strategia di fallback per modelli non disponibili."""
```

##### Dockerfile Integration
```dockerfile
# Esempio di integrazione nel Dockerfile della libreria
RUN pip install thoth-vdbmanager[qdrant]==2.0.0
RUN python -c "from thoth_vdbmanager import EmbeddingManager; EmbeddingManager.preload_common_models()"
```

#### Task di Implementazione
- [ ] **Creare DockerModelManager** per gestione container-specific
- [ ] **Implementare pre-download** dei modelli comuni
- [ ] **Creare fallback strategies** per modelli non disponibili
- [ ] **Ottimizzare memory footprint** dei modelli caricati

## Fase 2: Migrazione dei Progetti

### 2.1 Migrazione thoth_be

#### Situazione Attuale
```python
# Attuale in thoth_be (problematico)
from sentence_transformers import SentenceTransformer
embedding_function = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
embeddings = embedding_function.encode(texts)
```

#### Migrazione Target
```python
# Target con nuova libreria
from thoth_vdbmanager import EmbeddingManager
embedding_manager = EmbeddingManager.get_instance()
embeddings = embedding_manager.encode(texts, model="multilingual-mini")
```

#### Task di Migrazione
- [ ] **Identificare tutti i punti** di utilizzo SentenceTransformer in thoth_be
- [ ] **Creare wrapper compatibility** per transizione graduale
- [ ] **Aggiornare i requirements** e dependency management
- [ ] **Testare tutti i workflow** esistenti

### 2.2 Migrazione thoth_ui/sql_generator

#### Situazione Attuale
```python
# Attuale in sql_generator (problematico)
from helpers.setups import build_embedding_function
embedding_function = build_embedding_function()
embeddings = embedding_function.encode(to_embed_strings)
```

#### Migrazione Target
```python
# Target con nuova libreria
from thoth_vdbmanager import EmbeddingManager
embedding_manager = EmbeddingManager.get_instance()
embeddings = embedding_manager.encode(to_embed_strings)
```

#### Task di Migrazione
- [ ] **Rimuovere SafeSentenceTransformer** custom class
- [ ] **Aggiornare helpers/setups.py** per utilizzare la nuova API
- [ ] **Modificare main_schema_extraction_from_lsh.py** per la nuova gestione
- [ ] **Aggiornare pyproject.toml** con la nuova versione libreria
- [ ] **Testare il fix** del problema Docker hung up

### 2.3 Strategia di Backward Compatibility

#### Compatibility Layer
```python
# Temporary compatibility per transizione graduale
class LegacyEmbeddingAdapter:
    """Adapter per mantenere compatibility con API esistenti."""
    
    def __init__(self, model_name: str):
        self.embedding_manager = EmbeddingManager.get_instance()
        self.model_name = model_name
    
    def encode(self, texts, **kwargs):
        """Mantiene l'interfaccia esistente."""
        return self.embedding_manager.encode(texts, model=self.model_name, **kwargs)
```

## Fase 3: Testing e Validazione

### 3.1 Test Strategy

#### Unit Tests
```python
# Test per il nuovo EmbeddingManager
class TestEmbeddingManager:
    def test_model_caching(self):
        """Verifica che i modelli vengano cached correttamente."""
        
    def test_docker_environment_detection(self):
        """Verifica rilevamento ambiente Docker."""
        
    def test_fallback_strategies(self):
        """Verifica strategie di fallback per errori."""
```

#### Integration Tests
```python
# Test di integrazione con progetti
class TestThothAIBeIntegration:
    def test_embedding_workflow_complete(self):
        """Test complete workflow thoth_be con nuovi embedding."""
        
class TestThothAIUiIntegration:
    def test_sql_generator_no_hang(self):
        """Verifica che sql_generator non si blocchi più."""
```

#### Docker Tests
```bash
# Script per test Docker automated
#!/bin/bash
docker-compose build sql-generator
docker-compose up -d sql-generator
# Test API call che prima causava hung up
curl -X POST http://localhost:8005/generate-sql \
  -H "Content-Type: application/json" \
  -d '{"question": "test question", "workspace_id": 4}'
```

### 3.2 Performance Validation

#### Benchmark Setup
- [ ] **Baseline measurements** con versione attuale funzionante
- [ ] **Performance tests** per encoding operations
- [ ] **Memory usage profiling** per modelli caricati
- [ ] **Startup time comparison** tra vecchia e nuova architettura

## Fase 4: Deployment e Rollout

### 4.1 Staged Rollout Strategy

#### Stage 1: Library Release
1. **Rilasciare thoth-vdbmanager v2.0** con nuovo EmbeddingManager
2. **Backward compatibility** garantita tramite adapter layer
3. **Extensive testing** su ambienti di staging

#### Stage 2: thoth_be Migration
1. **Deploy thoth_be** con nuova libreria in staging
2. **Validazione completa** di tutti i workflow
3. **Rollout production** con rollback plan

#### Stage 3: thoth_ui Migration  
1. **Deploy sql_generator** con fix Docker
2. **Validazione** che il hung up sia risolto
3. **Monitor production** per stabilità

### 4.2 Rollback Plan

#### Preparazione
- [ ] **Backup delle versioni** attuali funzionanti
- [ ] **Scripts di rollback** automatizzati
- [ ] **Monitoring alerts** per rilevare problemi rapidamente

#### Trigger Conditions
- Performance degradation >20%
- Failure rate >5% su endpoint critici  
- Docker hung up ancora presente
- Memory usage increase >50%

## Timeline e Milestones

### Milestone 1: Library Foundation (Settimane 1-2)
- [ ] Analisi completata delle versioni attuali
- [ ] Design approvato del nuovo EmbeddingManager
- [ ] Implementazione core del model caching
- [ ] Environment detection funzionante

### Milestone 2: Docker Optimization (Settimane 2-3)
- [ ] DockerModelManager implementato
- [ ] Pre-download strategy testata
- [ ] Memory optimization completata
- [ ] Fallback strategies validate

### Milestone 3: Project Migration (Settimane 3-4)
- [ ] thoth_be migrazione completata
- [ ] thoth_ui/sql_generator migrazione completata
- [ ] Backward compatibility layer validata
- [ ] Integration tests passing al 100%

### Milestone 4: Production Ready (Settimane 4-5)
- [ ] Performance validation superata
- [ ] Docker tests completamente verdi
- [ ] Staging deployment successful
- [ ] Monitoring e alerting configurati

### Milestone 5: Production Rollout (Settimana 6)
- [ ] Production deployment completato
- [ ] Hung up issue risolto definitivamente
- [ ] Performance baseline mantenuto
- [ ] Documentazione aggiornata

## Success Metrics

### Technical KPIs
- **Docker hung up**: 0 occorrenze dopo deployment
- **Performance impact**: <±5% rispetto al baseline
- **Memory usage**: <+20% per il nuovo caching
- **Test coverage**: >90% per nuovo codice

### Operational KPIs  
- **Deployment time**: <30 minuti per rollout completo
- **Rollback time**: <5 minuti se necessario
- **Zero downtime**: Durante migrazione
- **Developer satisfaction**: Feedback positivo su nuova API

## Risk Management

### High Risk: Breaking Changes
- **Mitigation**: Extensive backward compatibility testing
- **Contingency**: Gradual migration con feature flags

### Medium Risk: Performance Degradation
- **Mitigation**: Continuous benchmarking durante sviluppo
- **Contingency**: Performance tuning dedicato

### Low Risk: Docker Complexity
- **Mitigation**: Docker-specific testing environment
- **Contingency**: Fallback a deployment non-containerizzato

---

**Piano redatto da**: Claude Code Analysis  
**Data**: 2025-08-10  
**Versione**: 1.0  
**Stato**: READY FOR REVIEW