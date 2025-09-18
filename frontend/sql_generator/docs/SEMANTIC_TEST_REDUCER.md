Semantic Test Reducer (Python-only)

Overview
- Always-on, non-LLM deduplication pass for generated validation tests.
- Collapses exact and near-duplicate tests using:
  - Normalized exact/substring check
  - Token Jaccard similarity
  - Sequence similarity (difflib)

Code
- Implementation: `frontend/sql_generator/helpers/semantic_test_reducer.py:1`
- Integrated in:
  - Precompute Tests: `frontend/sql_generator/helpers/main_helpers/main_generation_phases.py:170`
  - Evaluation: `frontend/sql_generator/helpers/main_helpers/main_evaluation.py:140`

Behavior
- Preserves order (first occurrence kept).
- If a later duplicate contains `[EVIDENCE-CRITICAL]` and the kept one does not, the kept text is upgraded to the tagged version.
- Logs reductions (and emits `THOTHLOG` during precompute phase).

Configuration (Env Vars)
- `TEST_SEMANTIC_DEDUP_ENABLED` (default `true`)
- `TEST_SEMANTIC_DEDUP_SEQ` (default `0.92`)
- `TEST_SEMANTIC_DEDUP_JACCARD` (default `0.88`)
- `TEST_SEMANTIC_DEDUP_LENRATIO` (default `0.90`)

Notes
- This reducer runs before any optional LLM-based TestReducer. You can disable LLM reduction by setting `TEST_REDUCER_USE_LLM=false` (if supported by your env) or by not configuring multiple test generators.
