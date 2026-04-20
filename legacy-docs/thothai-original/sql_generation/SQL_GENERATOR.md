ThothAI SQL Generator – UML Documentation

Overview
- Purpose: FastAPI service that turns natural language questions into validated SQL, executes queries with pagination, and can explain SQL. It coordinates PydanticAI agents, vector DB context retrieval, schema preparation, SQL generation/evaluation, and response formatting.
- Entrypoint: `frontend/sql_generator/main.py:1`
- Core orchestrators: `helpers/main_helpers/*`
- Agents: `agents/core/*`, validators in `agents/validators/*`
- Models/state: `model/*`

Mermaid Class Diagram
```mermaid
classDiagram
    class FastAPIApp {
      +/generate-sql(request) StreamingResponse
      +/explain-sql(request) SqlExplanationResponse
      +/execute-query(request) PaginationResponse
      +/save-sql-feedback(request) dict
      +/health() HealthResponse
    }

    class GenerateSQLRequest {
      +str question
      +int workspace_id
      +str functionality_level
      +dict flags
    }

    class SystemState {
      +int workspace_id
      +str workspace_name
      +str question
      +str original_question
      +str translated_question
      +list keywords
      +dict enriched_schema
      +dict filtered_schema
      +str full_mschema
      +str reduced_mschema
      +str used_mschema
      +Any dbmanager
      +Any vdbmanager
      +AgentsAndTools agents_and_tools
      +ExecutionState execution
      +list generated_sqls
      +str last_SQL
      +list evidence
      +str schema_link_strategy
      +bool number_of_sql_to_generate
      +run_question_validation_with_translation()
      +get_evidence_from_vector_db() -> (bool, list, str)
      +get_sql_from_vector_db() -> (bool, list, str)
      +extract_schema_via_lsh()
      +extract_schema_from_vectordb()
      +create_enriched_schema()
      +create_filtered_schema()
    }

    class ExecutionState {
      +datetime validation_start_time
      +datetime validation_end_time
      +float validation_duration_ms
      +datetime keyword_generation_start_time
      +datetime keyword_generation_end_time
      +float keyword_generation_duration_ms
      +datetime context_retrieval_start_time
      +datetime context_retrieval_end_time
      +float context_retrieval_duration_ms
      +datetime sql_generation_start_time
      +datetime sql_generation_end_time
      +float sql_generation_duration_ms
      +str sql_status  // GOLD|SILVER|FAILED
      +str evaluation_case
      +float selected_sql_complexity
      +str sql_generation_failure_message
    }

    class ThothAgentManager {
      +dbmanager
      +agent_pool_config
      +question_validator_agent
      +question_translator_agent
      +keyword_extraction_agent
      +sql_basic_agent
      +sql_advanced_agent
      +sql_expert_agent
      +test_gen_agent_1..3
      +evaluator_agent
      +sql_explainer_agent
      +sql_evaluator_agent
      +agent_pools: AgentPools
      +sql_validators: SqlValidators
      +test_validators: TestValidators
      +initialize() ThothAgentManager
      +explain_generated_sql(...): str?
    }

    class AgentInitializer {
      +create_question_validator_agent(...): Agent
      +create_question_translator_agent(...): Agent
      +create_keyword_extraction_agent(...): Agent
      +create_sql_generation_agent(...): Agent
      +create_test_generation_agent(...): Agent
      +create_evaluator_agent(...): Agent
      +create_sql_evaluator_agent(...): Agent
      +create_sql_explanation_agent(...): Agent
    }

    class SqlValidators {
      +create_sql_validator(): OutputValidator
    }

    class TestValidators {
    }

    class AgentPools {
      +add_to_sql_generation_pool(agent)
      +add_to_test_generation_pool(agent)
      +add_sql_agent(agent, level)
      +add_test_agent(agent, level)
      +get_pool_stats() dict
    }

    class TemplateLoader {
      +format(template_key, ...): str
    }

    class PaginatedQueryService {
      +execute_paginated_query(PaginationRequest) PaginationResponse
    }

    class SqlDocument {
      +str question
      +str sql
      +str evidence
    }

    class VDBManager {
      +add_sql(SqlDocument)
    }

    FastAPIApp --> GenerateSQLRequest
    FastAPIApp --> SystemState
    FastAPIApp --> PaginatedQueryService
    FastAPIApp --> SqlDocument
    SystemState --> ThothAgentManager : agents_and_tools
    ThothAgentManager --> AgentInitializer
    ThothAgentManager --> SqlValidators
    ThothAgentManager --> TestValidators
    ThothAgentManager --> AgentPools
    ThothAgentManager --> TemplateLoader
    SystemState --> VDBManager : vdbmanager
```

Mermaid Collaboration (Sequence) Diagrams

1) Generate SQL end-to-end
```mermaid
sequenceDiagram
    participant FE as Frontend (Next.js)
    participant API as FastAPI /generate-sql
    participant Init as _initialize_request_state
    participant Pre1 as _validate_question_phase
    participant Pre2 as _extract_keywords_phase
    participant Pre3 as _retrieve_context_phase
    participant Gen as _generate_sql_candidates_phase
    participant Sel as _evaluate_and_select_phase
    participant Resp as _prepare_final_response_phase

    FE->>API: POST /generate-sql (question, workspace_id, level, flags)
    API->>Init: init and validate request/state
    Init-->>API: state or error
    API-->>FE: THOTHLOG: start stream

    API->>Pre1: validate question (+optional translation)
    Pre1-->>API: progress or CRITICAL_ERROR

    API->>Pre2: extract keywords
    Pre2-->>API: progress or CRITICAL_ERROR

    API->>Pre3: retrieve evidences, SQL shots, LSH, schema
    Pre3-->>API: progress, warnings, or CRITICAL_ERROR

    API->>Gen: generate N SQL candidates (parallel)
    Gen-->>API: progress or CRITICAL_ERROR

    API->>Sel: evaluate + select best SQL
    Sel-->>API: RESULT(success, selected_sql) or failure

    API->>Resp: prepare final response
    Resp-->>API: final messages (status, hints, SQL)
    API-->>FE: stream ends
```

2) Explain SQL
```mermaid
sequenceDiagram
    participant FE as Frontend
    participant API as FastAPI /explain-sql
    participant AM as ThothAgentManager.sql_explainer_agent
    participant TL as TemplateLoader

    FE->>API: POST /explain-sql (question, sql, schema, hints, cot, lang)
    API->>TL: format("user_sql_explain", ...)
    API->>AM: run(formatted_prompt)
    AM-->>API: explanation text
    API-->>FE: SqlExplanationResponse
```

3) Execute query with pagination
```mermaid
sequenceDiagram
    participant FE as Frontend
    participant API as FastAPI /execute-query
    participant Setup as _setup_dbmanager_and_agents
    participant PGS as PaginatedQueryService
    FE->>API: POST /execute-query (sql, workspace_id, page,...)
    API->>Setup: init dbmanager+agents
    Setup-->>API: setup_result (dbmanager)
    API->>PGS: execute_paginated_query(request)
    PGS-->>API: PaginationResponse
    API-->>FE: PaginationResponse
```

Mermaid Activity (Workflow) Diagram
```mermaid
flowchart TD
    A[Request /generate-sql] --> B[Initialize request/state]
    B -->|ok| C[Validate question (+translate)]
    B -->|error| Z1[Return error]
    C -->|invalid| Z2[CRITICAL_ERROR + stop]
    C -->|valid| D[Extract keywords]
    D -->|error| Z3[CRITICAL_ERROR + stop]
    D --> E[Retrieve context: evidences, sql shots, LSH, schema]
    E -->|vdb missing| Z4[CRITICAL_ERROR + stop]
    E -->|warnings| E2[Log warnings, continue]
    E2 --> F[Decide schema strategy]
    E --> F
    F -->|WITH_SCHEMA_LINK| G[Build reduced schema -> mschema]
    F -->|WITHOUT_SCHEMA_LINK| H[Build full schema -> mschema]
    G --> I[Generate SQL candidates]
    H --> I
    I -->|error| Z5[CRITICAL_ERROR + stop]
    I --> J[Evaluate + select best SQL]
    J -->|cancelled| Z6[Stop]
    J --> K[Prepare final response]
    K --> L[Stream to client]
```

Key Modules and Functions (by responsibility)

- API Orchestration: `frontend/sql_generator/main.py:1`
  - `generate_sql`: streams the full pipeline; phases: `_validate_question_phase`, `_extract_keywords_phase`, `_retrieve_context_phase`, `_generate_sql_candidates_phase`, `_evaluate_and_select_phase`, `_prepare_final_response_phase`.
  - `explain_sql`: builds explainer prompt and calls `ThothAgentManager.explain_generated_sql`.
  - `execute_query`: initializes dbmanager and runs `PaginatedQueryService.execute_paginated_query`.
  - `save_sql_feedback`: persists last SQL into vector DB via `thoth_qdrant.SqlDocument` and `vdbmanager.add_sql`.

- Initialization and Setup:
  - `helpers/main_helpers/main_request_initialization.py:_initialize_request_state`: creates `SystemState`, loads workspace, resolves env, attaches managers, session cache.
  - `helpers/main_helpers/main_methods.py:_setup_dbmanager_and_agents`: returns `dbmanager` and `ThothAgentManager` per workspace; `initialize_database_plugins` registers DB drivers.
  - `helpers/session_cache.py:ensure_cached_setup`: caches heavy setup per session/workspace.

- Preprocessing Phases: `helpers/main_helpers/main_preprocessing_phases.py:1`
  - `_validate_question_phase`: optional question validation and translation via agents; timestamps + streaming errors.
  - `_extract_keywords_phase`: runs keyword extraction agent, stores `state.keywords`.
  - `_retrieve_context_phase`: gets evidences/SQL shots, extracts schema via LSH and vector DB, decides schema strategy, builds mschema.

- Generation and Selection: `helpers/main_helpers/main_generation_phases.py:1`
  - `_generate_sql_candidates_phase`: runs parallel SQL generation via configured agents; sets timings and handles critical errors; uses `generate_sql_units` and `clean_sql_results`.
  - `_evaluate_and_select_phase`: evaluates candidates with tests/scores and emits a `RESULT(success, selected_sql)` tuple plus logs.
  - `_finalize_execution_state_status`: consolidates GOLD/SILVER/FAILED and evaluation cases.

- Agents and Validators:
  - `agents/core/agent_manager.py: ThothAgentManager.initialize`: builds agents via `AgentInitializer`, attaches `SqlValidators` to SQL agents, configures pools.
  - `agents/core/agent_initializer.py`: factory for all agent types; applies model providers via `agent_ai_model_factory` and prompt templates.
  - `agents/core/agent_ai_model_factory.py`: resolves AI providers/keys, fallback chaining.
  - `agents/validators/sql_validators.py: SqlValidators.create_sql_validator`: output validator executing SQL safely against `dbmanager` and applying delimiter/compatibility fixes.

- Context and Templates:
  - `helpers/template_preparation.py: TemplateLoader`: loads and formats system/user templates for agents (unified system template for SQL generation; specific user prompts by level).
  - `helpers/vectordb_context_retrieval.py`, `helpers/vectordb_utils.py`: vector DB access (Qdrant), evidence retrieval, schema enrichment.
  - `helpers/sql_delimiter_corrector.py`, `helpers/sql_compatibility.py`: adjust SQL for engine differences.

- Execution and Pagination:
  - `services/paginated_query_service.py: PaginatedQueryService.execute_paginated_query`: executes SQL with sorting/filtering/pagination and returns `PaginationResponse` for AG Grid.

- Logging and Errors:
  - `helpers/logging_config.py: configure_root_logger, get_logging_level` and `helpers/dual_logger.py: log_debug, log_error` unify logging.
  - `helpers/error_response.py: handle_exception` standardizes error payloads for API exceptions.

General Workflow
- Input: question, workspace_id, functionality_level, flags.
- Validate/translate question; extract keywords.
- Retrieve context: evidences, similar SQL, LSH examples, schema with descriptions.
- Decide schema link strategy; construct mschema (reduced or full) per query.
- Generate SQL candidates using Basic/Advanced/Expert agents, attach SQL validator (executes against dbmanager).
- Evaluate and select best SQL (test generation and evaluator agents in pipeline).
- Stream status and results to client; allow pagination of execution and explanation on demand.
- Optional: save user feedback (Like) back into vector DB as `SqlDocument`.

Meaningful Functions and Notes
- `main.generate_sql`: top-level orchestrator, streams THOTHLOG/system warnings/errors; checks for client disconnects between phases.
- `_initialize_request_state`: validates env, loads workspace configuration, injects db and vector managers, wires agent manager.
- `_validate_question_phase`: timestamps, translation, and validation errors as CRITICAL_ERROR to the stream.
- `_extract_keywords_phase`: requires keyword agent; missing agent is a CRITICAL_ERROR.
- `_retrieve_context_phase`: handles vdb absence as CRITICAL_ERROR; emits warnings for partial failures; runs LSH and schema extraction; chooses schema link strategy.
- `_generate_sql_candidates_phase`: measures gen time; calls `generate_sql_units` with functionality level and agent pools; cleans results.
- `_evaluate_and_select_phase`: aggregates tests/scores, returns tuple `("RESULT", success, selected_sql)`; pipeline uses it to branch.
- `_prepare_final_response_phase`: always runs; finalizes state, formats output rows/columns, emits CSV, agent metadata, timings.
- `ThothAgentManager.initialize`: creates question validator/translator, keyword extractor, SQL basic/advanced/expert, test generators, evaluator, SQL explainer; attaches SQL validators with `dbmanager` context.
- `ThothAgentManager.explain_generated_sql`: formats template and runs `sql_explainer_agent` to produce explanation string.
- `SqlValidators.create_sql_validator`: ensures generated SQL is syntactically/semantically sound, optionally executes test queries safely.
- `PaginatedQueryService.execute_paginated_query`: centralizes result paging for UI tables.
- `save_sql_feedback`: converts last state to `SqlDocument` and stores via `vdbmanager.add_sql`.

Operational Considerations
- Env selection: if `DOCKER_CONTAINER=true`, Docker env is used; else `.env.local` at repo root is loaded.
- Logging/telemetry: `logfire.instrument_pydantic_ai()` active if token present; centralized logger configured early.
- CORS: allows localhost ports used by Next.js; streaming responses are plain text with markers (THOTHLOG, SYSTEM_WARNING, CRITICAL_ERROR, CANCELLED, RESULT).
- Disconnection handling: each long phase checks `http_request.is_disconnected()` to stop work early.

Appendix: Additional Mermaid Snippets

Agent Construction Flow
```mermaid
flowchart LR
  A[Workspace config] --> B[AgentInitializer]
  B --> C[question_validator]
  B --> D[question_translator]
  B --> E[keyword_extraction]
  B --> F[sql_basic]
  B --> G[sql_advanced]
  B --> H[sql_expert]
  B --> I[test_gen 1..3]
  B --> J[test_evaluator]
  B --> K[sql_explainer]
  F & G & H --> L[SqlValidators.attach]
  L --> M[AgentPools]
```

SQL Generation/Evaluation High-Level
```mermaid
sequenceDiagram
  participant AM as AgentManager
  participant G as generate_sql_units
  participant V as SqlValidators
  participant EV as evaluate/select
  AM->>G: run basic/advanced/expert
  G-->>AM: candidates[]
  loop Validator per candidate
    AM->>V: validate(output)
    V-->>AM: valid/fixed result
  end
  AM->>EV: evaluate(candidates)
  EV-->>AM: best SQL + metrics
```

