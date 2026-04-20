# Preprocessing Assets

ThothAI relies on retrieval assets that are prepared before normal querying.

## Main Asset Types

- schema metadata
- comments and column descriptions
- evidence
- Gold SQL examples
- vector embeddings
- LSH-derived similarity artifacts

## Why They Matter

These assets shape the context passed to the SQL generation agents.

They help the runtime:

- map business language to tables and columns
- recover relevant examples from the vector store
- reduce the schema for smaller generation models
- enforce evidence-aware testing before selecting a final query

## Operational Consequence

If preprocessing is skipped or incomplete, the system can still run, but:

- context retrieval becomes weaker
- schema reduction becomes noisier
- SQL evaluation has less grounded evidence
- final selection quality drops
