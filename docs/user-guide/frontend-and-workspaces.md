# Frontend And Workspaces

The frontend is the operator-facing surface of ThothAI.

## What The Frontend Depends On

At runtime the frontend talks to:

- the Django backend for configuration and admin-managed data
- the SQL Generator service for request execution
- the proxy for the public entrypoint

## Workspace-Driven Behavior

Most execution behavior is selected by the active workspace:

- database target
- agent pool
- vector database source
- settings profile

That is why two users in the same deployment can get different SQL generation behavior when they switch workspace context.

## Main User Actions

- select a workspace
- submit a question
- inspect generated SQL
- request SQL explanation
- execute and page through results
- send feedback for successful SQL

The current request model in `frontend/sql_generator/main.py` is centered on `question`, `workspace_id`, `functionality_level`, and UI `flags`.
