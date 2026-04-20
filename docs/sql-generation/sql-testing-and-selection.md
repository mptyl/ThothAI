# SQL Testing And Selection

ThothAI does not stop at generating candidate SQL. It precomputes tests, validates candidate output, and then selects the best query.

## Precomputed Tests

The current pipeline runs `_precompute_tests_phase()` before candidate generation.

That phase:

- generates tests from schema and evidence
- deduplicates them
- stores them on the request state
- marks evidence-critical tests when special grounding is required

This is important because the selection stage is not purely stylistic. It is evidence-aware.

## Candidate Generation

`_generate_sql_candidates_phase()` runs SQL generation agents in parallel and records timing and status metrics in the execution state.

The agent manager typically builds:

- one Basic SQL generator
- one Advanced SQL generator
- one Expert SQL generator
- multiple test generators
- one evaluator

## Validators

The validation layer includes:

- SQL validators in `agents/validators/sql_validators.py`
- test validators in `agents/validators/test_validators.py`
- explanation validators for SQL explanation outputs

The SQL validators are responsible for safe execution checks and compatibility cleanup before final selection.

## Evaluation And Final Selection

`_evaluate_and_select_phase()` scores the candidates and updates:

- final SQL status
- evaluation case
- selected SQL complexity
- failure metadata when no acceptable query survives

The execution state uses status values such as:

- `GOLD`
- `SILVER`
- `FAILED`

## Feedback Loop

The SQL Generator also exposes `save_sql_feedback`, which stores successful SQL back into the vector database as reusable retrieval material.

That closes the loop between:

- user requests
- generated SQL
- validated outcomes
- future retrieval quality
