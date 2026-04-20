# Developer View

This page documents the current SQL Generator runtime from the code outward.

It intentionally describes only what is implemented in the active codebase. The public request contract is limited to `BASIC`, `ADVANCED`, and `EXPERT`.

## Developer Entry Points

The main orchestration starts in:

- `frontend/sql_generator/main.py`
- `frontend/sql_generator/helpers/main_helpers/main_request_initialization.py`
- `frontend/sql_generator/helpers/main_helpers/main_preprocessing_phases.py`
- `frontend/sql_generator/helpers/main_helpers/main_generation_phases.py`

The SQL Generator request model currently exposes:

- `question`
- `workspace_id`
- `functionality_level`
- `flags`

`functionality_level` is validated against `BASIC`, `ADVANCED`, and `EXPERT` by `RequestContext` in `model/contexts/request_context.py`.

## 1. Request Initialization And Runtime State

The runtime does not jump straight into prompting an LLM.
It first normalizes the request and constructs a full `SystemState`.

### What `_initialize_request_state()` does

The helper in `main_request_initialization.py` performs these steps:

1. It normalizes `functionality_level` to uppercase before creating `RequestContext`.
2. It creates a minimal `DatabaseContext`.
3. It calls `_setup_dbmanager_and_agents()` to resolve the workspace configuration, database manager, vector DB manager, and agent manager.
4. It derives `scope` and `language` from the workspace SQL database configuration.
5. It rebuilds `SystemState` with:
   - immutable request data
   - runtime managers
   - workspace configuration
   - execution counters and timers
6. It validates that both `dbmanager` and `vdbmanager` are actually usable.
7. It fetches the authoritative `full_schema` from the target database through `get_db_schema(...)`.

If any of those steps fail, the request stops before generation starts.

### Why this matters

From a developer perspective, every later phase depends on `SystemState` already containing:

- the validated workspace
- the target language and scope
- the SQL database manager
- the vector database manager
- the agent pool
- the full database schema

That means failures in setup are infrastructure failures, not model failures.

## 2. Language Determination, Validation, And Translation

Language handling is not a single "detect language" function. It is a coordinated validator-translation flow.

### Main function

The current logic lives in `SystemState.run_question_validation_with_translation()`.

### Runtime behavior

1. The method checks that both `question_validator_agent` and `question_translator_agent` exist.
2. If one is missing, it falls back to `_run_question_validation()`, which performs the older validator-only flow.
3. If both are available, it dynamically registers `translator_tool` on the validator agent.
4. The validator receives a template built with:
   - the current question
   - the workspace scope
   - the target language stored in request context
5. During evaluation, the validator can invoke `translator_tool(...)`.
6. `translator_tool(...)`:
   - builds a translation-specific template
   - calls `question_translator_agent.run(...)`
   - captures `translated_question`, `original_question`, and `detected_language`
7. The validator then returns:
   - `outcome`
   - `reasons`
   - detected language
   - whether translation was needed

### State mutation after validation

If validation passes and translation happened:

- `state.translated_question` is set
- `state.submitted_question` becomes the translated text
- downstream keyword extraction and retrieval use the translated form

If validation fails:

- the system returns a structured user-facing failure message
- no retrieval or generation phase is executed

### Developer implication

Translation is not a standalone preprocessing step that always runs first.
The validator owns the decision and calls the translator only when needed.
That preserves one control point for:

- language detection
- out-of-scope rejection
- grammar/meaningfulness rejection
- translation coordination

## 3. Keyword Extraction

Keyword extraction happens in `_extract_keywords_phase()` after validation succeeds.

### What it does

1. Confirms the request is still connected.
2. Starts timing in `ExecutionState`.
3. Verifies that `keyword_extraction_agent` exists.
4. Calls `extract_keywords(...)`.
5. Stores the result in `state.keywords`.

### Why it is critical

The code treats keyword extraction as mandatory because the retrieval stack depends on it for:

- evidence search
- similar SQL retrieval
- LSH schema matching
- vector-backed schema enrichment

If `keyword_extraction_agent` is missing, the request fails immediately with a critical error.

## 4. Data Linking And Schema Linking

This is the most important retrieval stage for large schemas.

### Phase owner

The orchestration happens in `_retrieve_context_phase()`.

### Inputs to the linking stage

The phase uses:

- the validated or translated question
- `state.keywords`
- vector-retrieved evidence
- vector-retrieved SQL examples
- LSH-derived schema matches
- vector-derived schema descriptions
- the full authoritative schema from `dbmanager`

### Step-by-step flow

1. `state.get_evidence_from_vector_db()` retrieves short evidence items.
2. `state.get_sql_from_vector_db()` retrieves similar question-SQL-hint examples.
3. `state.extract_schema_via_lsh()` performs value- and name-oriented schema narrowing.
4. `state.extract_schema_from_vectordb()` enriches schema elements with vector-backed descriptions.
5. Evidence is normalized into `state.semantic.evidence_for_template` and `state.evidence_str`.
6. `decide_schema_link_strategy(state)` decides whether the request can use the full schema or needs schema linking.
7. The chosen schema is converted to `mschema` text via `to_mschema()`.

## 5. How Schema Linking Works For Large Databases

When the schema is too large, the runtime does not introduce a different full-context branch.
Instead, it decides whether to keep the full enriched schema or to build a reduced linked schema.

### Decision function

The decision happens in `main_schema_link_strategy.py::decide_schema_link_strategy(state)`.

### Decision inputs

The function uses two independent thresholds:

1. token pressure from the full enriched schema
2. raw column count of the full schema

### Exact logic

1. It requires `state.full_schema`; otherwise it falls back conservatively.
2. It builds `state.enriched_schema`.
3. It converts that schema into full `mschema` text with `to_mschema(...)`.
4. It counts tokens with `count_mschema_tokens(...)`.
5. It computes the total number of columns from `full_schema`.
6. It reads workspace-configurable thresholds from `workspace.setting`:
   - `max_columns_before_schema_linking`
   - `max_context_usage_before_linking`
7. It retrieves the current model context window with `_get_model_context_window(state)`.
8. It estimates context usage with `estimate_context_usage(...)`.

### Decision outputs

- `WITHOUT_SCHEMA_LINK`
  - used when the full enriched schema stays under the configured token pressure threshold
  - and the raw number of columns stays under the configured column threshold
- `WITH_SCHEMA_LINK`
  - forced when the schema is too large by columns
  - or when the full schema would consume too much of the model context window

### Why this matters

The current system solves large-schema complexity through schema reduction rather than by widening the prompt context with a separate strategy.

That reduction is therefore the implemented answer to "the database is too complex for full-context handling."

## 6. What `extract_schema_via_lsh()` Actually Contributes

The LSH layer is not just a fuzzy name matcher.
Its role is to recover high-signal schema fragments and example values before prompt construction.

### Configuration sources

The function reads tuning parameters from workspace settings:

- `signature_size`
- `lsh_top_n`
- `edit_distance_threshold`
- `embedding_similarity_threshold`
- `max_examples_per_column`

### Output shape

It produces:

- `similar_columns`
- `schema_with_examples`

`schema_with_examples` is keyed by table and column and carries example values discovered through the LSH retrieval pass.

### Why the examples matter

These examples give the model concrete value-level hints, which are especially useful when:

- the question contains business terms not obvious from schema names
- the schema is large and many columns are semantically similar
- the later reduced schema must still preserve enough discriminating context

The phase treats LSH as critical. If LSH extraction fails, the request stops.

## 7. How The Reduced Schema Is Built

After the strategy chooses `WITH_SCHEMA_LINK`, the runtime calls `state.create_filtered_schema()`.

That logic is implemented in `main_generate_mschema.py::create_filtered_schema(...)`.

### Inclusion rules

A column is kept in the reduced schema if any of the following are true:

1. it is a primary key
2. it is a foreign key
3. it appears in `schema_with_examples`
4. it appears in `schema_from_vector_db`

### Important consequence

This means the reduced schema is not a blind top-k truncation.
It is a union of:

- structural columns needed to preserve joins
- LSH-selected columns with high lexical/value relevance
- vector-selected columns with strong semantic relevance

That is the core schema-linking methodology in the implemented code.

## 8. How `mschema` Is Produced

The prompt does not receive raw JSON schema.
It receives an `mschema` string built by `to_mschema(...)`.

### What `to_mschema(...)` includes

- table descriptions
- `CREATE TABLE`-style blocks
- column names and types
- inline primary key annotations
- column descriptions or value descriptions
- example values
- a `【Foreign keys】` section extracted from FK metadata

### Why this representation is used

It preserves enough structure for SQL reasoning while remaining compact and LLM-readable.

## 9. SQL Candidate Generation

Candidate generation happens in `generate_sql_units(...)`.

### Current methodology

The system does not rely on a single prompt style.
It cycles across three generation methods:

- `query_plan`
- `step_by_step`
- `divide_and_conquer`

For each generation request it also varies temperature values across low, medium, and high ranges.

### Agent selection

The selected generation agent depends strictly on `functionality_level`:

- `BASIC` -> `sql_basic_agent`
- `ADVANCED` -> `sql_advanced_agent`
- `EXPERT` -> `sql_expert_agent`

If the corresponding agent is missing, generation fails critically.

### Why this matters

The current code gets diversity from:

- prompt methodology rotation
- temperature diversity
- repeated parallel runs

It does not get diversity from switching to a separate full-schema mode.

## 10. Test Generation Before Final Selection

The pipeline precomputes tests before final selection in `_precompute_tests_phase()`.

### How test generation works

1. It uses `test_gen_agent_1` as the fixed generator.
2. It generates multiple test batches with temperatures from `0.5` to `1.0`.
3. It regenerates dynamic `mschema` per batch, without shuffle.
4. It builds test templates using:
   - directives
   - current schema
   - question
   - evidence
   - candidate SQL list
5. It gathers the results in parallel.
6. It deduplicates the resulting tests.

### Why this matters

The final evaluation stage is only as good as the test set.
The system therefore treats test generation as a first-class stage, not as an afterthought after SQL scoring.

## 11. Evaluation And Final SQL Quality Decision

The main evaluation path is `_evaluate_and_select_phase()`.

### What it does

1. Regenerates or reuses test units.
2. Calls `evaluate_sql_candidates(...)`.
3. Stores evaluation output on the request state.
4. Populates execution metrics.
5. Runs `select_best_sql(...)`.
6. Finalizes the execution status as `GOLD`, `SILVER`, or `FAILED`.

### Inside `evaluate_sql_candidates(...)`

The evaluator:

- extracts all test answers from generated test batches
- deduplicates them
- optionally runs semantic reduction with `TestReducer`
- evaluates SQL candidates against the deduplicated test set

This means the evaluator does not score each SQL against one private ad hoc test list.
It scores candidates against a consolidated test basis built from multiple generations.

### Inside `select_best_sql(...)`

Selection is not based on one scalar returned by the LLM.
The code:

- parses detailed evaluator outputs
- counts passed vs total tests
- computes pass rates
- records failure reasons
- compares results against the workspace threshold

### Final quality statuses

- `GOLD`: strong pass outcome
- `SILVER`: acceptable but weaker result
- `FAILED`: no candidate met the required bar

## 12. Escalation Logic

If selection fails, the runtime can escalate:

- from `BASIC` to `ADVANCED`
- from `ADVANCED` to `EXPERT`

It does this by mutating `request.functionality_level` and re-running generation and evaluation.

The escalation is bounded. Once `EXPERT` is exhausted, the pipeline stops.

## 13. Practical Developer Summary

If you want to understand the runtime behavior for large schemas, the key fact is this:

the current system solves schema complexity by choosing between full enriched schema and filtered linked schema, then generating multiple SQL candidates and validating them through a multi-test evaluation loop.

The critical chain is:

1. validate and possibly translate the question
2. extract keywords
3. retrieve evidence and SQL examples
4. run LSH and vector schema enrichment
5. decide `WITH_SCHEMA_LINK` vs `WITHOUT_SCHEMA_LINK`
6. build `mschema`
7. generate multiple SQL candidates
8. generate and reduce tests
9. evaluate candidates
10. select, escalate, or fail
