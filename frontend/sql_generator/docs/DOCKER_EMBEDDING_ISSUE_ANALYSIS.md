# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under the Apache License 2.0.
# See the LICENSE.md file in the project root for full license information.

# Analisi del Problema Docker: Hung Up del SQL Generator

## Executive Summary

Il servizio `thoth-sql-generator` si blocca sistematicamente in ambiente Docker subito dopo l'estrazione delle keywords, mentre funziona correttamente in locale. L'analisi ha identificato la causa root nel cambiamento dell'architettura di gestione degli embedding tra le versioni di `thoth-vdbmanager`.

## Descrizione del Problema

### Sintomi Osservati
- **Ambiente**: Docker container `thoth-sql-generator`
- **Momento del blocco**: Subito dopo l'estrazione delle keywords
- **Errori nei log**: HTTP 500 con retry infiniti durante il caricamento del modello SentenceTransformer
- **Ambiente locale**: Funziona correttamente senza problemi

### Log di Errore Chiave
```
INFO:sentence_transformers.SentenceTransformer:Load pretrained SentenceTransformer: paraphrase-multilingual-MiniLM-L12-v2
[2m2025-08-10T21:35:04.219406Z[0m [33m WARN[0m  [33mStatus Code: 500. Retrying..., [1;33mrequest_id[0m[33m: "01K2AYH4XEN3EM91409YS38JQV"[0m
[2m2025-08-10T21:35:04.219482Z[0m [33m WARN[0m  [33mRetry attempt #0. Sleeping 2.750699682s before the next attempt[0m
```

## Causa Root Identificata

### Differenze Architetturali tra Progetti

| Progetto | Versione thoth-vdbmanager | Gestione Embedding | Stato Docker |
|----------|--------------------------|-------------------|--------------|
| **thoth_sl** | `v0.2.24` (dev locale) | **Lato libreria** | ✅ Funziona |
| **thoth_ui/sql_generator** | `>=0.4.0` (PyPI) | **Lato client** | ❌ Si blocca |

### Evoluzione dell'Architettura

1. **Versione 0.2.24** (thoth_sl):
   - SentenceTransformer gestito internamente dalla libreria
   - Modelli pre-caricati o gestiti dalla libreria stessa
   - Funziona in Docker senza problemi

2. **Versione 0.4.0+** (sql_generator):
   - Gestione embedding spostata lato client
   - Download runtime dei modelli SentenceTransformer
   - Problemi in ambiente Docker containerizzato

### Punto di Fallimento Tecnico

Il blocco avviene esattamente in:
```python
# helpers/main_helpers/main_schema_extraction_from_lsh.py:307
embeddings = embedding_function.encode(to_embed_strings)
```

Quando il client tenta di scaricare il modello `paraphrase-multilingual-MiniLM-L12-v2` all'interno del container Docker.

## Impatti del Problema

### Impatti Immediati
- **Servizio sql_generator non utilizzabile** in ambiente Docker
- **Workflow interrotti** per tutti i processi che dipendono dalla generazione SQL
- **Inconsistenza** tra ambienti di sviluppo (locale funziona, Docker no)

### Impatti a Lungo Termine
- **Scalabilità compromessa**: impossibile deployare in produzione
- **Manutenzione complessa**: due architetture diverse da mantenere
- **Developer experience degradata**: comportamenti diversi tra ambienti

## Piano di Risoluzione

### Fase 1: Allineamento Architetturale (Priority: HIGH)

#### Obiettivo
Ripristinare la gestione lato libreria degli embedding in `thoth-vdbmanager` per garantire consistenza tra tutti i progetti.

#### Scope del Progetto
- **In Scope**: thoth_be, thoth_ui, thoth-vdbmanager library
- **Out of Scope**: thoth_sl (mantenerlo come riferimento funzionante)

#### Task Principali

##### 1.1 Analisi della Libreria thoth-vdbmanager
- [ ] **Audit delle versioni**: Comparare 0.2.24 vs 0.4.0+ per identificare i cambiamenti esatti
- [ ] **Identificare API changes**: Documentare le differenze nelle interfacce pubbliche
- [ ] **Mappare le dipendenze**: Capire come la gestione embedding influenza i progetti downstream

##### 1.2 Riprogettazione dell'Architettura Embedding
- [ ] **Design pattern**: Definire un pattern per la gestione centralizzata degli embedding
- [ ] **Backward compatibility**: Garantire che le modifiche non rompano l'esistente
- [ ] **Docker optimization**: Assicurare che la gestione funzioni correttamente in container

##### 1.3 Implementazione nella Libreria
- [ ] **Core embedding manager**: Creare un gestore centralizzato degli embedding
- [ ] **Model caching**: Implementare caching intelligente dei modelli SentenceTransformer
- [ ] **Environment detection**: Gestire automaticamente differenze tra locale/Docker
- [ ] **Error handling**: Robusto error handling per il download e caricamento modelli

##### 1.4 Testing e Validazione
- [ ] **Unit tests**: Copertura completa per il nuovo embedding manager
- [ ] **Integration tests**: Testare l'integrazione con thoth_be e thoth_ui
- [ ] **Docker tests**: Validare il funzionamento in ambiente containerizzato
- [ ] **Performance tests**: Assicurare che le performance non siano degradate

### Fase 2: Migrazione dei Progetti (Priority: MEDIUM)

#### 2.1 Aggiornamento thoth_be
- [ ] **Dependency update**: Aggiornare alla nuova versione di thoth-vdbmanager
- [ ] **Code migration**: Adattare il codice per utilizzare la nuova API
- [ ] **Configuration**: Aggiornare le configurazioni per la gestione embedding
- [ ] **Testing**: Validare tutti i workflow esistenti

#### 2.2 Aggiornamento thoth_ui/sql_generator
- [ ] **Dependency update**: Aggiornare pyproject.toml con la nuova versione
- [ ] **Code refactoring**: Rimuovere la gestione client-side degli embedding
- [ ] **Docker optimization**: Aggiornare il Dockerfile per la nuova architettura
- [ ] **Testing**: Validare il fix del problema di hung up

### Fase 3: Stabilizzazione e Monitoraggio (Priority: LOW)

#### 3.1 Monitoraggio e Alerting
- [ ] **Health checks**: Implementare health check per la gestione embedding
- [ ] **Logging**: Aggiungere logging dettagliato per debugging
- [ ] **Metrics**: Monitorare performance e utilizzo memoria

#### 3.2 Documentazione
- [ ] **Architecture documentation**: Documentare la nuova architettura
- [ ] **Migration guide**: Creare guida per futuri aggiornamenti
- [ ] **Best practices**: Documentare best practices per embedding management

## Stima Tempi e Risorse

### Timeline Stimata
- **Fase 1**: 2-3 settimane (analisi + implementazione libreria)
- **Fase 2**: 1-2 settimane (migrazione progetti)
- **Fase 3**: 1 settimana (stabilizzazione)

**Totale**: 4-6 settimane

### Risorse Richieste
- **Developer senior**: Per l'architettura e implementazione core
- **DevOps support**: Per testing e validazione Docker
- **QA testing**: Per validazione completa dei workflow

## Rischi e Mitigazioni

### Rischi Principali
1. **Breaking changes**: Modifiche alla libreria potrebbero rompere codice esistente
2. **Performance degradation**: Gestione centralizzata potrebbe impattare performance
3. **Docker complexity**: Problemi specifici di containerizzazione

### Mitigazioni
1. **Backward compatibility**: Mantenere API retrocompatibili durante la transizione
2. **Performance testing**: Benchmark continui durante sviluppo
3. **Staged rollout**: Deploy graduale per validare ogni componente

## Success Criteria

### Criteri di Successo Tecnici
- [ ] **sql_generator funziona in Docker** senza hung up
- [ ] **Performance mantenute** (±5% rispetto al baseline)
- [ ] **Zero breaking changes** per thoth_be e thoth_ui
- [ ] **Test coverage ≥90%** per il nuovo embedding manager

### Criteri di Successo Operativi
- [ ] **Deploy automatizzato** senza interventi manuali
- [ ] **Monitoring attivo** su tutti gli ambienti
- [ ] **Documentazione completa** e aggiornata

## Prossimi Passi

1. **Approval**: Ottenere approvazione per il piano e prioritizzazione
2. **Resource allocation**: Assegnare developer e timeline specifici  
3. **Kick-off**: Iniziare con l'analisi dettagliata della libreria
4. **Milestone tracking**: Stabilire checkpoint settimanali per monitorare progress

---

**Documento redatto da**: Claude Code Analysis  
**Data**: 2025-08-10  
**Versione**: 1.0  
**Status**: DRAFT - In attesa di approvazione