# Code Review Checklist - SQL Generator

## 📋 Documentazione Tecnica Completa del Flusso di Generazione SQL

### 🎯 Panoramica del Sistema
Il sistema SQL Generator è un servizio FastAPI che converte domande in linguaggio naturale in query SQL utilizzando un'architettura multi-agente basata su PydanticAI.

---

## 1️⃣ ENTRY POINT E REQUEST FLOW

### 1.1 Main Entry Point
- [ ] **File**: `main.py`
- [ ] **Endpoint principale**: `POST /generate-sql`
- [ ] **Porta default**: 8001 (configurabile)
- [ ] **CORS configurato**: localhost:3000, localhost:3001

### 1.2 Request Model
- [ ] **GenerateSQLRequest**:
  - `question`: str - La domanda dell'utente
  - `workspace_id`: int - ID del workspace
  - `sql_generator`: str - Strategia (Basic, Advanced, Expert)
  - `flags`: Dict[str, bool] - Flag della sidebar:
    - [ ] `show_sql`: Mostra SQL generato
    - [ ] `explain_sql`: Genera spiegazione SQL

### 1.3 Response Flow
- [ ] **StreamingResponse** con `media_type="text/plain"`
- [ ] **Marcatori speciali**:
  - `THOTHLOG:` - Log operazioni
  - `SQL_READY:` - SQL pronto per esecuzione
  - `SQL_EXPLANATION:` - Spiegazione generata

---

## 2️⃣ FASI DEL PROCESSO DI GENERAZIONE

### 📌 FASE 0: Setup e Inizializzazione

#### Checklist Setup
- [ ] **Funzione**: `_setup_dbmanager_and_agents()`
  - **File**: `helpers/main_helpers/main_methods.py`
- [ ] **Inizializzazione DBManager**:
  - [ ] Recupero workspace config da Django API
  - [ ] Estrazione configurazione SQL database
  - [ ] Creazione connessione database
- [ ] **Inizializzazione VDBManager** (Vector Database):
  - [ ] Configurazione Qdrant
  - [ ] Connessione a porta 6334
  - [ ] Verifica collection disponibili
- [ ] **Creazione Agent Manager**:
  - [ ] Istanziazione `ThothAgentManager`
  - [ ] Inizializzazione pool agenti

#### SystemState Initialization
- [ ] **File**: `model/system_state.py`
- [ ] **Campi principali**:
  - [ ] `question`: Domanda originale
  - [ ] `username`: Username dall'header
  - [ ] `started_at`: Timestamp inizio
  - [ ] `workspace_name`: Nome workspace
  - [ ] `dbmanager`: Gestore database
  - [ ] `vdbmanager`: Gestore vector DB

---

### 📌 FASE 1: Validazione e Traduzione Domanda

#### 1.1 Question Validation
- [ ] **Agent**: `question_validator_agent`
  - **File**: `agents/core/agent_initializer.py`
  - **Template**: `templates/template_validate_question_with_language.txt`
  - **System Template**: `templates/system_templates/system_template_check_question.txt`
- [ ] **Funzione**: `state.run_question_validation_with_translation()`
  - **File**: `model/system_state.py`
- [ ] **Controlli eseguiti**:
  - [ ] Rilevamento lingua
  - [ ] Validità domanda SQL
  - [ ] Richiesta traduzione se necessario

#### 1.2 Question Translation (se necessario)
- [ ] **Agent**: `question_translator_agent`
  - **Template**: `templates/template_translate_question.txt`
  - **System Template**: `templates/system_templates/system_template_translate_question.txt`
- [ ] **Funzione**: `translate_question_template()`
  - **File**: `helpers/template_preparation.py`
- [ ] **Aggiornamento stato**:
  - [ ] `state.original_question`: Domanda originale
  - [ ] `state.original_language`: Lingua originale
  - [ ] `state.question`: Domanda tradotta

---

### 📌 FASE 2: Estrazione Keywords

#### Keyword Extraction
- [ ] **Agent**: `keyword_extraction_agent`
  - **Template**: `templates/template_extract_keywords.txt`
  - **System Template**: `templates/system_templates/system_template_extract_keywords_from_question.txt`
- [ ] **Funzione**: `extract_keywords()`
  - **File**: `helpers/main_helpers/main_keyword_extraction.py`
- [ ] **Tools utilizzati**:
  - [ ] `RetrieveEntityTool`: Recupera entità dal database
  - [ ] `vectordb_context_retrieval helpers`: Recupera contesto dal vector DB
- [ ] **Output**: `state.keywords` - Lista di parole chiave

---

### 📌 FASE 3: Recupero Evidenze e SQL Shots

#### 3.1 Evidence Retrieval
- [ ] **Funzione**: `state.get_evidence_from_vector_db()`
- [ ] **Vector DB Query**:
  - [ ] Collection: evidence collection
  - [ ] Similarity search con keywords
  - [ ] Limite: top 5 risultati
- [ ] **Output**: `state.evidence` - Lista evidenze

#### 3.2 SQL Shots Retrieval
- [ ] **Funzione**: `state.get_sql_from_vector_db()`
- [ ] **Vector DB Query**:
  - [ ] Collection: SQL examples
  - [ ] Similarity search con question
  - [ ] Limite: top 5 esempi
- [ ] **Output**: `state.sql_shots` - Esempi SQL simili

---

### 📌 FASE 4: Schema Extraction e Filtering

#### 4.1 LSH Schema Extraction
- [ ] **Funzione**: `state.extract_schema_via_lsh()`
  - **File**: `helpers/main_helpers/main_schema_extraction_from_lsh.py`
- [ ] **Processo**:
  - [ ] Ricerca colonne simili con LSH
  - [ ] Estrazione valori esempio
  - [ ] Arricchimento schema con esempi
- [ ] **Output**:
  - [ ] `state.similar_columns`: Colonne rilevanti
  - [ ] `state.schema_with_examples`: Schema con esempi

#### 4.2 Schema Link Strategy Decision
- [ ] **Funzione**: `decide_schema_link_strategy()`
  - **File**: `helpers/main_helpers/main_schema_link_strategy.py`
- [ ] **Strategie**:
  - [ ] `WITHOUT_SCHEMA_LINK`: Schema completo
  - [ ] `WITH_SCHEMA_LINK`: Schema filtrato (da implementare)

#### 4.3 Schema Preparation
- [ ] **Se WITHOUT_SCHEMA_LINK**:
  - [ ] `state.create_enriched_schema()`
  - [ ] `state.full_mschema = to_mschema(state.enriched_schema)`
- [ ] **Tools**:
  - [ ] `PrepareSchemaStringTool`: Prepara schema base

---

### 📌 FASE 5: Generazione SQL con Escalation

#### 5.1 SQL Generation Strategy
- [ ] **Funzione**: `ai_assisted_sql_generation()`
  - **File**: `helpers/main_helpers/main_ai_assisted_sql_generation.py`
- [ ] **Strategie disponibili**:
  - [ ] `Basic`: Usa `sql_basic_agent`
  - [ ] `Advanced`: Usa `sql_advanced_agent`
  - [ ] `Expert`: Usa `sql_expert_agent`

#### 5.2 Agent SQL Pools
- [ ] **Basic Agent**:
  - **Templates**: 
    - `templates/template_generate_sql_default.txt`
    - `templates/template_generate_sql_step_by_step.txt`
    - `templates/template_generate_sql_divide_and_conquer.txt`
  - **System**: `templates/system_templates/system_template_generate_sql.txt`
- [ ] **Advanced Agent**: Stessi template con model diverso
- [ ] **Expert Agent**: Stessi template con model più potente

#### 5.3 SQL Escalation (RIMOSSO - Non più utilizzato)
- ~~Funzione precedente: `sql_escalation_with_pool()`~~ 
- ~~File precedente: `helpers/main_helpers/main_sql_escalation.py`~~
- **Nota**: Workflow di escalation rimosso, ora si usa solo `generate_sql_units()` con metodi multipli

#### 5.4 Test Generation & Validation
- [ ] **Agent**: `test_gen_agent_1` e `test_gen_agent_2`
  - **Template**: `templates/template_generate_unit_tests.txt`
- [ ] **Validatori**:
  - [ ] `SqlValidators`: Validazione sintassi SQL
  - [ ] `TestValidators`: Validazione test generati

---

### 📌 FASE 6: Output Condizionale

#### 6.1 SQL Display (Condizionale)
- [ ] **Controllo flag**: `request.flags.get("show_sql", False)`
- [ ] **Se True**:
  - [ ] Formattazione SQL con `sqlparse.format()`
  - [ ] Yield SQL formattato
- [ ] **Se False**: Non mostrare SQL

#### 6.2 SQL Ready Marker
- [ ] **Sempre inviato** per segnalare frontend
- [ ] **Formato JSON**:
  ```json
  {
    "type": "sql_ready",
    "sql": "...",
    "workspace_id": 123,
    "timestamp": "...",
    "username": "...",
    "agent": "..."
  }
  ```

---

### 📌 FASE 7: Generazione Spiegazione (Condizionale)

#### Explanation Generation
- [ ] **Controllo flag**: `request.flags.get("explain_sql", False)`
- [ ] **Se True**:
  - [ ] **Agent**: `sql_explainer_agent`
    - **Template**: `templates/template_explain_generated_sql.txt`
    - **System**: `templates/system_templates/system_template_explain_generated_sql.txt`
  - [ ] **Funzione**: `agent_manager.explain_generated_sql()`
  - [ ] **Input per spiegazione**:
    - [ ] Question
    - [ ] Generated SQL
    - [ ] Database schema
    - [ ] Hints/Evidence
    - [ ] Chain of thought
    - [ ] Language (da validator)
  - [ ] **Output formato JSON**:
    ```json
    {
      "type": "sql_explanation",
      "explanation": "...",
      "language": "Italian/English"
    }
    ```
- [ ] **Se False**: Skip generazione spiegazione

---

### 📌 FASE 8: Logging e Completamento

#### 8.1 Thoth Log
- [ ] **Funzione**: `send_thoth_log()`
  - **File**: `helpers/thoth_log_api.py`
- [ ] **Dati loggati**:
  - [ ] State completo
  - [ ] Workspace ID e nome
  - [ ] Username
  - [ ] Timestamp inizio/fine
  - [ ] SQL generato
  - [ ] Agent utilizzato

#### 8.2 Final Messages
- [ ] **Se successo**: Agent name e conferma
- [ ] **Se fallimento**: Messaggio errore dettagliato

---

## 3️⃣ ALTRI ENDPOINT

### `/explain-sql` Endpoint
- [ ] **Scopo**: Generazione spiegazione standalone
- [ ] **Input**: SqlExplanationRequest
- [ ] **Output**: SqlExplanationResponse
- [ ] **Usa cache sessione**

### `/execute-query` Endpoint
- [ ] **Scopo**: Esecuzione paginata query
- [ ] **Service**: `PaginatedQueryService`
- [ ] **Output**: PaginationResponse per AGGrid

### `/health` Endpoint
- [ ] **Health check** del servizio

---

## 4️⃣ TEMPLATE E FORMATTING

### Template Files Structure
```
templates/
├── system_templates/          # System prompts per agenti
│   ├── system_template_check_question.txt
│   ├── system_template_explain_generated_sql.txt
│   ├── system_template_extract_keywords_from_question.txt
│   ├── system_template_generate_sql.txt
│   ├── system_template_test_generator.txt
│   └── system_template_translate_question.txt
├── template_*.txt             # User prompts
└── few_shots.txt             # Esempi fallback
```

### Template Formatting Functions
- [ ] **`format_example_shots()`**: Formatta esempi SQL
- [ ] **`load_fallback_shots()`**: Carica few_shots.txt
- [ ] **`clean_template_for_llm()`**: Pulisce template per LLM
- [ ] **`check_question_template()`**: Prepara template validazione
- [ ] **`translate_question_template()`**: Prepara template traduzione
- [ ] **`extract_keywords_template()`**: Prepara template keywords
- [ ] **`generate_sql_template()`**: Prepara template SQL
- [ ] **`explain_sql_template()`**: Prepara template spiegazione

---

## 5️⃣ CONFIGURAZIONE E DIPENDENZE

### Environment Variables
- [ ] **DJANGO_API_KEY**: Chiave API Django backend
- [ ] **DJANGO_SERVER**: URL server Django (da .env.local)
- [ ] **QDRANT_HOST**: Host Qdrant (default: localhost)
- [ ] **QDRANT_PORT**: Porta Qdrant (default: 6334)

### External Services
- [ ] **Django Backend**: Porta 8200
- [ ] **Qdrant Vector DB**: Porta 6334
- [ ] **PostgreSQL**: Porta 5432 (via Django)

### Python Dependencies
- [ ] **FastAPI**: Framework web
- [ ] **PydanticAI**: Framework agenti AI
- [ ] **thoth-dbmanager**: Gestione database
- [ ] **thoth-vdbmanager**: Gestione vector DB
- [ ] **sqlparse**: Formattazione SQL
- [ ] **httpx**: Client HTTP async

---

## 6️⃣ PUNTI DI VERIFICA CRITICI

### 🔴 Controlli Critici Flag
1. [ ] **Show SQL Flag**:
   - Linea 301-308 in `main.py`
   - Verifica: `request.flags.get("show_sql", False)`
   - Output: SQL formattato solo se True

2. [ ] **Explain SQL Flag**:
   - Linea 333-334 in `main.py`
   - Verifica: `request.flags.get("explain_sql", False)`
   - Output: Spiegazione solo se True

### 🔴 Validazioni Necessarie
1. [ ] **DBManager Status**: Deve essere "ready"
2. [ ] **VDBManager Status**: Deve essere "ready"
3. [ ] **Agent Manager**: Deve essere inizializzato
4. [ ] **Question Validation**: Non deve essere vuota
5. [ ] **SQL Generation**: Deve produrre SQL valido

### 🔴 Error Handling
1. [ ] **Setup Failure**: HTTP 500 con dettagli
2. [ ] **Invalid Question**: Messaggio di errore
3. [ ] **SQL Generation Failure**: Escalation o errore
4. [ ] **Explanation Failure**: Warning log

---

## 7️⃣ TESTING CHECKLIST

### Test Manuali Base
```bash
# Test locale senza Docker
curl -X POST "http://localhost:8001/generate-sql" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": 4,
    "question": "How many schools are virtual?",
    "sql_generator": "Basic",
    "flags": {
      "show_sql": true,
      "explain_sql": true
    }
  }'
```

### Scenari di Test
1. [ ] **Con show_sql=true, explain_sql=true**: Deve mostrare SQL e spiegazione
2. [ ] **Con show_sql=false, explain_sql=true**: Solo spiegazione, no SQL
3. [ ] **Con show_sql=true, explain_sql=false**: Solo SQL, no spiegazione
4. [ ] **Con show_sql=false, explain_sql=false**: Né SQL né spiegazione
5. [ ] **Domanda in italiano**: Deve tradurre e processare
6. [ ] **Domanda invalida**: Deve restituire errore

### Servizi da Verificare
- [ ] **Qdrant attivo** su porta 6334
- [ ] **Django backend attivo** su porta 8200
- [ ] **SQL Generator attivo** su porta 8001

---

## 8️⃣ MONITORING E LOGGING

### Log Files
- [ ] **Location**: `sql_generator/logs/temp/`
- [ ] **Files**:
  - `thoth_app.log`: Log principale
  - `agents.*.log`: Log per agente
  - `agents.validators.*.log`: Log validatori

### Log Levels
- [ ] **INFO**: Operazioni normali
- [ ] **WARNING**: Situazioni anomale
- [ ] **ERROR**: Errori recuperabili
- [ ] **CRITICAL**: Errori fatali

### Metriche da Monitorare
- [ ] **Response time** per generazione SQL
- [ ] **Success rate** per agente
- [ ] **Escalation frequency**
- [ ] **Translation rate**
- [ ] **Cache hit rate**

---

## 9️⃣ OTTIMIZZAZIONI E PERFORMANCE

### Cache Strategy
- [ ] **Session cache** per workspace setup
- [ ] **Vector DB cache** per query simili
- [ ] **Template cache** per prompt ripetuti

### Performance Targets
- [ ] **SQL generation**: < 5 secondi
- [ ] **Explanation generation**: < 3 secondi
- [ ] **Keyword extraction**: < 1 secondo
- [ ] **Translation**: < 2 secondi

### Bottlenecks Comuni
- [ ] **Vector DB queries**: Ottimizzare similarity search
- [ ] **LLM calls**: Minimizzare round-trip
- [ ] **Database schema**: Cache schema pesanti
- [ ] **Template rendering**: Pre-compilare template

---

## 📝 NOTE FINALI

### Priorità di Verifica
1. **🔴 Alta**: Flag condizionali, error handling
2. **🟡 Media**: Template formatting, agent flow
3. **🟢 Bassa**: Logging, monitoring

### Rischi Identificati
- Token limit su template molto grandi
- Timeout su query complesse
- Memory leak su cache non pulita
- Race condition su richieste parallele

### Miglioramenti Suggeriti
- Implementare retry mechanism robusto
- Aggiungere circuit breaker per servizi esterni
- Migliorare cache invalidation
- Aggiungere health check dettagliati

---

**Ultimo aggiornamento**: Gennaio 2025
**Versione**: 1.0.0
**Autore**: Sistema di Documentazione Automatica