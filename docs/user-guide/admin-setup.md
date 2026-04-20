# Admin Setup

ThothAI is configured primarily through the Django admin.

## Core Administrative Areas

The current runtime depends on the admin for:

- AI model definitions
- agent definitions
- SQL database metadata
- vector database metadata
- workspaces
- users, groups, and group profiles
- settings and prompt-adjacent records

## What Must Exist Before Querying

The SQL Generator expects a workspace to resolve into:

- a queryable SQL database
- a vector database connection
- an agent pool
- enough schema metadata to build context

If one of those elements is missing, the request may stop early during request initialization or context retrieval.

## Agent Configuration Principle

The runtime does not infer a complete agent pool from a single model.
You configure specific agent records, and the SQL Generator binds them into the active workspace through the agent manager.

The public docs describe only the current runtime roles. Legacy agent labels or deprecated escalation modes are intentionally excluded.
