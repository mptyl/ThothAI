# First Workspace

This walkthrough assumes the stack is already running through the supported Docker Compose flow.

## 1. Sign In To The Admin

Open `http://localhost:8040/admin` and log in with the bootstrap superuser defined in `.env.docker`.

## 2. Configure Core Records

Populate the minimum entities required by the runtime:

1. AI models
2. Agents
3. Vector database connection
4. SQL database metadata
5. Workspace
6. Settings

ThothAI stores the SQL generation configuration in backend-managed records rather than in static files alone.

## 3. Prepare The Target Database Metadata

For the first usable workspace you need:

- SQL database connection details
- tables, columns, and relationships metadata
- enough comments and descriptions to make retrieval meaningful
- a linked vector database target

## 4. Link A Workspace

A workspace ties together:

- users or groups
- a SQL database
- a vector database collection
- a configured agent set
- a settings profile

The frontend and SQL Generator both resolve their runtime behavior from this workspace context.

## 5. Run Preprocessing

Before asking production-style questions, prepare the retrieval assets:

- evidence
- Gold SQL examples
- comments and column descriptions
- LSH or similar preprocessing artifacts where applicable

## 6. Use The Frontend

Open `http://localhost:8040` and:

- select the workspace
- submit a natural-language question
- inspect the SQL, explanation, and execution result
- use feedback actions to improve future retrieval quality
