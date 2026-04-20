# SQL Testing And Selection

ThothAI does not stop at generating candidate SQL. It precomputes tests, validates candidate output, and then selects the best query.

For the detailed developer view of `main_test_generation.py`, `main_evaluation.py`, `sql_selection.py`, and the escalation logic in `main_generation_phases.py`, see [Evaluation And Selection](../technical-architecture/developer-pipeline/evaluation-and-selection.md).

## Precomputed Tests

The current pipeline runs `_precompute_tests_phase()` before candidate generation.

That phase:

- generates tests from schema and evidence
- deduplicates them
- stores them on the request state
- marks evidence-critical tests when special grounding is required

This is important because the selection stage is not purely stylistic. It is evidence-aware.

## How Tests Are Actually Generated

The implementation in `main_test_generation.py` uses `test_gen_agent_1` as the fixed generator and runs multiple generations in parallel with a temperature range between `0.5` and `1.0`.

For each batch it:

- regenerates a dynamic `mschema`
- injects directives, evidence, and the SQL candidate list into the test template
- gathers structured outputs from the test generation agent

The outputs are then deduplicated and stored so later phases evaluate against a consolidated set of tests rather than isolated one-off answers.

## Candidate Generation

`_generate_sql_candidates_phase()` runs SQL generation agents in parallel and records timing and status metrics in the execution state.

The agent manager typically builds:

- one Basic SQL generator
- one Advanced SQL generator
- one Expert SQL generator
- multiple test generators
- one evaluator

## How Candidate Diversity Is Produced

The runtime does not depend on one static prompt.

`generate_sql_units(...)` produces diversity through:

- three different generation methods:
  - `query_plan`
  - `step_by_step`
  - `divide_and_conquer`
- a spread of temperature values
- repeated parallel generations with the agent selected by `functionality_level`

That means quality comes from controlled prompt and temperature variation within the current `BASIC` / `ADVANCED` / `EXPERT` tiers.

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

## How Evaluation Works In Code

`evaluate_sql_candidates(...)`:

1. collects all generated test answers
2. deduplicates them
3. optionally runs semantic filtering through `TestReducer`
4. evaluates each SQL candidate against the resulting test basis

The evaluation stage therefore operates on a merged and cleaned set of requirements, not on whichever test batch happened to be generated first.

## How Final Selection Works

`select_best_sql(...)` parses evaluator output per SQL candidate, computes pass rates, records failure reasons, and compares the outcome to the workspace threshold.

The selector does not rely on vague model confidence.
It uses structured pass/fail evidence from the evaluation output.

The execution state uses status values such as:

- `GOLD`
- `SILVER`
- `FAILED`

## Escalation Rules

If no candidate satisfies the current threshold, the runtime can escalate:

- `BASIC -> ADVANCED`
- `ADVANCED -> EXPERT`

The code mutates `request.functionality_level`, clears previous generation artefacts, and re-runs generation plus evaluation.

Once `EXPERT` is exhausted, the request stops with failure.

## Feedback Loop

The SQL Generator also exposes `save_sql_feedback`, which stores successful SQL back into the vector database as reusable retrieval material.

That closes the loop between:

- user requests
- generated SQL
- validated outcomes
- future retrieval quality
