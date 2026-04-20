# Data Linking

In ThothAI, "data linking" is the combined retrieval process that maps a question to the most relevant schema, evidence, and example SQL before generation.

For the module-by-module developer explanation of validation, retrieval, LSH extraction, vector enrichment, schema reduction, and `mschema` generation, see [Preprocessing And Schema Linking](../technical-architecture/developer-pipeline/preprocessing-and-schema-linking.md).

## Inputs Used For Linking

The current pipeline combines:

- validated or translated question text
- extracted keywords
- evidence retrieved from the vector database
- prior SQL examples retrieved from the vector database
- LSH-derived schema matches
- vector-enriched schema descriptions

## Current Linking Flow

The relevant implementation is split across:

- `helpers/main_helpers/main_preprocessing_phases.py`
- `model/system_state.py`
- `helpers/get_evidences_and_sql_shots.py`
- `helpers/main_helpers/main_schema_extraction_from_lsh.py`
- `helpers/main_helpers/main_schema_extraction_from_vectordb.py`
- `helpers/main_helpers/main_schema_link_strategy.py`

## What Happens In Practice

1. The question is validated and optionally translated.
2. The keyword extraction agent produces the retrieval terms.
3. `state.get_evidence_from_vector_db()` retrieves short evidence records.
4. `state.get_sql_from_vector_db()` retrieves similar question-SQL-hint examples.
5. `state.extract_schema_via_lsh()` recovers likely matching schema elements and example values.
6. `state.extract_schema_from_vectordb()` augments the schema with vector-backed descriptions.
7. `decide_schema_link_strategy()` determines how aggressive schema reduction should be.
8. `to_mschema()` builds the final schema string passed into generation.

## Current Schema-Linking Methodology

The current implementation does not solve large schemas by switching to a second full-context strategy.
It solves them by deciding whether schema reduction is necessary and, if so, building a filtered schema that preserves only high-signal and structurally necessary columns.

### Decision Layer

`decide_schema_link_strategy(state)` evaluates:

- the token cost of the full enriched schema
- the total number of columns in the authoritative schema
- the configured threshold for how much of the model context may be consumed before linking
- the configured threshold for maximum columns before linking

The function returns:

- `WITHOUT_SCHEMA_LINK`
- `WITH_SCHEMA_LINK`

### Why Large Databases Trigger Linking

Large databases become difficult for the runtime for two concrete reasons:

1. the full schema text consumes too much of the available model context window
2. the raw column count makes broad prompting too noisy even before hard token exhaustion

That is why the code checks both token pressure and column pressure.

### LSH Contribution

`extract_schema_via_lsh()` contributes:

- column-level matches
- example values for matched columns
- a lexical and value-driven narrowing signal

This pass is critical and request-blocking when it fails.

### Vector DB Contribution

`extract_schema_from_vectordb()` contributes:

- semantic descriptions
- additional enrichment for columns already relevant to the request

This pass is useful but non-blocking: if it fails, the request can continue with reduced enrichment.

### Filtered Schema Construction

When the strategy is `WITH_SCHEMA_LINK`, the runtime uses `create_filtered_schema(state)`.

The reduced schema keeps a column if:

- it is a primary key
- it is a foreign key
- it appears in `schema_with_examples`
- it appears in `schema_from_vector_db`

This is the core of current schema-linking:

- never lose the relational backbone needed for joins
- keep columns with LSH evidence
- keep columns with semantic vector relevance

### Output Representation

The result is then converted to `mschema` through `to_mschema()`.

That representation preserves:

- table descriptions
- column types
- descriptions
- examples
- foreign key mappings

while remaining much smaller than a raw full-schema dump.

## Why This Matters

This linking stage is what lets ThothAI:

- narrow large schemas for smaller models
- preserve business terminology through evidence
- inject good prior examples into the prompt context
- ground SQL testing in retrieved facts rather than prompt-only guesses

## Practical Developer Interpretation

When the database is too large for broad-context prompting, the system does not "try harder" with the same full schema.
Instead, it transforms retrieval signals into a structurally safe reduced schema and passes that reduced `mschema` into generation.
