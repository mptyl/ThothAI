# Data Linking

In ThothAI, "data linking" is the combined retrieval process that maps a question to the most relevant schema, evidence, and example SQL before generation.

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

## Why This Matters

This linking stage is what lets ThothAI:

- narrow large schemas for smaller models
- preserve business terminology through evidence
- inject good prior examples into the prompt context
- ground SQL testing in retrieved facts rather than prompt-only guesses
