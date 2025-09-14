# Code Review Checklist - SQL Generator

## 📋 Complete Technical Documentation of the SQL Generation Flow

### 🎯 System Overview
The SQL Generator is a FastAPI service that converts natural-language questions into SQL queries using a multi-agent architecture based on PydanticAI.

---

## 1️⃣ ENTRY POINT E REQUEST FLOW

### 1.1 Main Entry Point
- [ ] **File**: `main.py`
- [ ] **Primary endpoint**: `POST /generate-sql`
- [ ] **Default port**: 8001 (configurable)
- [ ] **CORS configured**: localhost:3000, localhost:3001

### 1.2 Request Model
- [ ] **GenerateSQLRequest**:
  - `question`: str - User question
  - `workspace_id`: int - Workspace ID
  - `sql_generator`: str - Strategy (Basic, Advanced, Expert)
  - `flags`: Dict[str, bool] - Sidebar flags:
    - [ ] `show_sql`: Show generated SQL
    - [ ] `explain_sql`: Generate SQL explanation

### 1.3 Response Flow
- [ ] **StreamingResponse** with `media_type="text/plain"`
- [ ] **Special markers**:
  - `THOTHLOG:` - Operation logs
  - `SQL_READY:` - SQL ready for execution
  - `SQL_EXPLANATION:` - Generated explanation

---

## 2️⃣ FASI DEL PROCESSO DI GENERAZIONE

### 📌 PHASE 0: Setup and Initialization

#### Checklist Setup
- [ ] **Funzione**: `_setup_dbmanager_and_agents()`
  - **File**: `helpers/main_helpers/main_methods.py`
- [ ] **DBManager initialization**:
  - [ ] Fetch workspace config from Django API
  - [ ] Extract SQL database configuration
  - [ ] Create database connection
- [ ] **VDBManager initialization** (Vector Database):
  - [ ] Configure Qdrant
  - [ ] Connect to port 6334
  - [ ] Verify available collections
- [ ] **Agent Manager creation**:
  - [ ] Instantiate `ThothAgentManager`
  - [ ] Initialize agent pools

#### SystemState Initialization
- [ ] **File**: `model/system_state.py`
- [ ] **Main fields**:
  - [ ] `question`: Original question
  - [ ] `username`: Username from header
  - [ ] `started_at`: Start timestamp
  - [ ] `workspace_name`: Workspace name
  - [ ] `dbmanager`: Database manager
  - [ ] `vdbmanager`: Vector DB manager

---

### 📌 PHASE 1: Question Validation and Translation

#### 1.1 Question Validation
- [ ] **Agent**: `question_validator_agent`
  - **File**: `agents/core/agent_initializer.py`
  - **Template**: `templates/template_validate_question_with_language.txt`
  - **System Template**: `templates/system_templates/system_template_check_question.txt`
- [ ] **Funzione**: `state.run_question_validation_with_translation()`
  - **File**: `model/system_state.py`
- [ ] **Checks performed**:
  - [ ] Language detection
  - [ ] SQL question validity
  - [ ] Request translation if needed

#### 1.2 Question Translation (if needed)
- [ ] **Agent**: `question_translator_agent`
  - **Template**: `templates/template_translate_question.txt`
  - **System Template**: `templates/system_templates/system_template_translate_question.txt`
- [ ] **Funzione**: `translate_question_template()`
  - **File**: `helpers/template_preparation.py`
- [ ] **State updates**:
  - [ ] `state.original_question`: Original question
  - [ ] `state.original_language`: Original language
  - [ ] `state.question`: Translated question

---

### 📌 PHASE 2: Keyword Extraction

#### Keyword Extraction
- [ ] **Agent**: `keyword_extraction_agent`
  - **Template**: `templates/template_extract_keywords.txt`
  - **System Template**: `templates/system_templates/system_template_extract_keywords_from_question.txt`
- [ ] **Funzione**: `extract_keywords()`
  - **File**: `helpers/main_helpers/main_keyword_extraction.py`
- [ ] **Tools used**:
  - [ ] `RetrieveEntityTool`: Retrieves entities from the database
  - [ ] `vectordb_context_retrieval helpers`: Retrieves context from the vector DB
- [ ] **Output**: `state.keywords` - List of keywords

---

### 📌 PHASE 3: Evidence and SQL Shots Retrieval

#### 3.1 Evidence Retrieval
- [ ] **Funzione**: `state.get_evidence_from_vector_db()`
- [ ] **Vector DB Query**:
  - [ ] Collection: evidence collection
  - [ ] Similarity search with keywords
  - [ ] Limit: top 5 results
- [ ] **Output**: `state.evidence` - Evidence list

#### 3.2 SQL Shots Retrieval
- [ ] **Funzione**: `state.get_sql_from_vector_db()`
- [ ] **Vector DB Query**:
  - [ ] Collection: SQL examples
  - [ ] Similarity search with question
  - [ ] Limit: top 5 examples
- [ ] **Output**: `state.sql_shots` - Similar SQL examples

---

### 📌 PHASE 4: Schema Extraction and Filtering

#### 4.1 LSH Schema Extraction
- [ ] **Funzione**: `state.extract_schema_via_lsh()`
  - **File**: `helpers/main_helpers/main_schema_extraction_from_lsh.py`
- [ ] **Process**:
  - [ ] Search similar columns with LSH
  - [ ] Extract example values
  - [ ] Enrich schema with examples
- [ ] **Output**:
  - [ ] `state.similar_columns`: Relevant columns
  - [ ] `state.schema_with_examples`: Schema with examples

#### 4.2 Schema Link Strategy Decision
- [ ] **Funzione**: `decide_schema_link_strategy()`
  - **File**: `helpers/main_helpers/main_schema_link_strategy.py`
- [ ] **Strategies**:
  - [ ] `WITHOUT_SCHEMA_LINK`: Full schema
  - [ ] `WITH_SCHEMA_LINK`: Filtered schema (to implement)

#### 4.3 Schema Preparation
- [ ] **If WITHOUT_SCHEMA_LINK**:
  - [ ] `state.create_enriched_schema()`
  - [ ] `state.full_mschema = to_mschema(state.enriched_schema)`
- [ ] **Tools**:
  - [ ] `PrepareSchemaStringTool`: Prepara schema base

---

### 📌 PHASE 5: SQL Generation with Escalation

#### 5.1 SQL Generation Strategy
- [ ] **Funzione**: `ai_assisted_sql_generation()`
  - **File**: `helpers/main_helpers/main_ai_assisted_sql_generation.py`
- [ ] **Available strategies**:
  - [ ] `Basic`: Uses `sql_basic_agent`
  - [ ] `Advanced`: Uses `sql_advanced_agent`
  - [ ] `Expert`: Uses `sql_expert_agent`

#### 5.2 Agent SQL Pools
- [ ] **Basic Agent**:
  - **Templates**: 
    - `templates/template_generate_sql_default.txt`
    - `templates/template_generate_sql_step_by_step.txt`
    - `templates/template_generate_sql_divide_and_conquer.txt`
  - **System**: `templates/system_templates/system_template_generate_sql.txt`
- [ ] **Advanced Agent**: Same templates with different model
- [ ] **Expert Agent**: Same templates with a stronger model

#### 5.3 SQL Escalation (REMOVED - No longer used)
- ~~Previous function: `sql_escalation_with_pool()`~~ 
- ~~Previous file: `helpers/main_helpers/main_sql_escalation.py`~~
- **Note**: Escalation workflow removed; now only `generate_sql_units()` with multiple methods is used

#### 5.4 Test Generation & Validation
- [ ] **Agent**: `test_gen_agent_1` e `test_gen_agent_2`
  - **Template**: `templates/template_generate_unit_tests.txt`
- [ ] **Validators**:
  - [ ] `SqlValidators`: SQL syntax validation
  - [ ] `TestValidators`: Generated tests validation

---

### 📌 PHASE 6: Conditional Output

#### 6.1 SQL Display (Conditional)
- [ ] **Flag check**: `request.flags.get("show_sql", False)`
- [ ] **If True**:
  - [ ] SQL formatting with `sqlparse.format()`
  - [ ] Yield formatted SQL
- [ ] **If False**: Do not display SQL

#### 6.2 SQL Ready Marker
- [ ] **Always sent** to signal the frontend
- [ ] **JSON format**:
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

### 📌 PHASE 7: Explanation Generation (Conditional)

#### Explanation Generation
- [ ] **Flag check**: `request.flags.get("explain_sql", False)`
- [ ] **If True**:
  - [ ] **Agent**: `sql_explainer_agent`
    - **Template**: `templates/template_explain_generated_sql.txt`
    - **System**: `templates/system_templates/system_template_explain_generated_sql.txt`
  - [ ] **Funzione**: `agent_manager.explain_generated_sql()`
  - [ ] **Explanation input**:
    - [ ] Question
    - [ ] Generated SQL
    - [ ] Database schema
    - [ ] Hints/Evidence
    - [ ] Chain of thought
    - [ ] Language (from validator)
  - [ ] **JSON output**:
    ```json
    {
      "type": "sql_explanation",
      "explanation": "...",
      "language": "Italian/English"
    }
    ```
- [ ] **If False**: Skip explanation generation

---

### 📌 PHASE 8: Logging and Completion

#### 8.1 Thoth Log
- [ ] **Funzione**: `send_thoth_log()`
  - **File**: `helpers/thoth_log_api.py`
- [ ] **Logged data**:
  - [ ] Full state
  - [ ] Workspace ID and name
  - [ ] Username
  - [ ] Start/end timestamp
  - [ ] Generated SQL
  - [ ] Agent used

#### 8.2 Final Messages
- [ ] **If success**: Agent name and confirmation
- [ ] **If failure**: Detailed error message

---

## 3️⃣ OTHER ENDPOINTS

### `/explain-sql` Endpoint
- [ ] **Purpose**: Standalone explanation generation
- [ ] **Input**: SqlExplanationRequest
- [ ] **Output**: SqlExplanationResponse
- [ ] **Usa cache sessione**

### `/execute-query` Endpoint
- [ ] **Purpose**: Paginated query execution
- [ ] **Service**: `PaginatedQueryService`
- [ ] **Output**: PaginationResponse per AGGrid

### `/health` Endpoint
- [ ] **Service** health check

---

## 4️⃣ TEMPLATES AND FORMATTING

### Template Files Structure
```
templates/
├── system_templates/          # System prompts for agents
│   ├── system_template_check_question.txt
│   ├── system_template_explain_generated_sql.txt
│   ├── system_template_extract_keywords_from_question.txt
│   ├── system_template_generate_sql.txt
│   ├── system_template_test_generator.txt
│   └── system_template_translate_question.txt
├── template_*.txt             # User prompts
└── few_shots.txt             # Fallback examples
```

### Template Formatting Functions
- [ ] **`format_example_shots()`**: Format SQL examples
- [ ] **`load_fallback_shots()`**: Load few_shots.txt
- [ ] **`clean_template_for_llm()`**: Clean template for LLM
- [ ] **`check_question_template()`**: Prepare validation template
- [ ] **`translate_question_template()`**: Prepare translation template
- [ ] **`extract_keywords_template()`**: Prepare keywords template
- [ ] **`generate_sql_template()`**: Prepare SQL template
- [ ] **`explain_sql_template()`**: Prepare explanation template

---

## 5️⃣ CONFIGURATION AND DEPENDENCIES

### Environment Variables
- [ ] **DJANGO_API_KEY**: Django backend API key
- [ ] **DJANGO_SERVER**: Django server URL (from .env.local)
- [ ] **QDRANT_HOST**: Qdrant host (default: localhost)
- [ ] **QDRANT_PORT**: Qdrant port (default: 6334)

### External Services
- [ ] **Django Backend**: Porta 8200
- [ ] **Qdrant Vector DB**: Porta 6334
- [ ] **PostgreSQL**: Porta 5432 (via Django)

### Python Dependencies
- [ ] **FastAPI**: Framework web
- [ ] **PydanticAI**: AI agent framework
- [ ] **thoth-dbmanager**: Database management
- [ ] **thoth-vdbmanager**: Vector DB management
- [ ] **sqlparse**: SQL formatting
- [ ] **httpx**: Async HTTP client

---

## 6️⃣ CRITICAL CHECKPOINTS

### 🔴 Critical Flag Checks
1. [ ] **Show SQL Flag**:
   - Linea 301-308 in `main.py`
   - Check: `request.flags.get("show_sql", False)`
   - Output: Formatted SQL only if True

2. [ ] **Explain SQL Flag**:
   - Linea 333-334 in `main.py`
   - Check: `request.flags.get("explain_sql", False)`
   - Output: Explanation only if True

### 🔴 Required Validations
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

### Basic Manual Test
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

### Test Scenarios
1. [ ] **show_sql=true, explain_sql=true**: Show both SQL and explanation
2. [ ] **show_sql=false, explain_sql=true**: Explanation only, no SQL
3. [ ] **show_sql=true, explain_sql=false**: SQL only, no explanation
4. [ ] **show_sql=false, explain_sql=false**: Neither SQL nor explanation
5. [ ] **Question in Italian**: Must translate and process
6. [ ] **Invalid question**: Must return an error

### Services to Verify
- [ ] **Qdrant active** on port 6334
- [ ] **Django backend active** on port 8200
- [ ] **SQL Generator active** on port 8001

---

## 8️⃣ MONITORING AND LOGGING

### Log Files
- [ ] **Location**: `sql_generator/logs/temp/`
- [ ] **Files**:
  - `thoth_app.log`: Main log
  - `agents.*.log`: Per-agent logs
  - `agents.validators.*.log`: Validator logs

### Log Levels
- [ ] **INFO**: Operazioni normali
- [ ] **WARNING**: Anomalous situations
- [ ] **ERROR**: Recoverable errors
- [ ] **CRITICAL**: Fatal errors

### Metrics to Monitor
- [ ] **Response time** for SQL generation
- [ ] **Success rate** per agent
- [ ] **Escalation frequency**
- [ ] **Translation rate**
- [ ] **Cache hit rate**

---

## 9️⃣ OPTIMIZATIONS AND PERFORMANCE

### Cache Strategy
- [ ] **Session cache** for workspace setup
- [ ] **Vector DB cache** for similar queries
- [ ] **Template cache** for repeated prompts

### Performance Targets
- [ ] **SQL generation**: < 5 seconds
- [ ] **Explanation generation**: < 3 seconds
- [ ] **Keyword extraction**: < 1 second
- [ ] **Translation**: < 2 seconds

### Common Bottlenecks
- [ ] **Vector DB queries**: Optimize similarity search
- [ ] **LLM calls**: Minimize round trips
- [ ] **Database schema**: Cache heavy schemas
- [ ] **Template rendering**: Precompile templates

---

## 📝 FINAL NOTES

### Verification Priorities
1. **🔴 High**: Conditional flags, error handling
2. **🟡 Medium**: Template formatting, agent flow
3. **🟢 Low**: Logging, monitoring

### Identified Risks
- Token limit on very large templates
- Timeout on complex queries
- Memory leaks from uncleared caches
- Race conditions on parallel requests

### Suggested Improvements
- Implement a robust retry mechanism
- Add circuit breaker for external services
- Improve cache invalidation
- Add detailed health checks

---

**Last update**: January 2025
**Version**: 1.0.0
**Author**: Automatic Documentation System
