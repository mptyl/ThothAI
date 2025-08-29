# SQL Generator Module

This module provides the FastAPI-based SQL generation service for Thoth. It handles question validation and SQL generation using AI agents.

## Features

- ✅ Question validation using AI agents
- ✅ FastAPI-based REST API
- ✅ Integration with Django backend for workspace information
- ✅ Docker containerization
- 🚧 Full SQL generation pipeline (planned for next steps)

## API Endpoints

### Health Check
- **GET** `/health`
- Returns the service health status

### Question Validation
- **POST** `/validate-question`
- Validates a user question for SQL generation feasibility
- Request body:
  ```json
  {
    "question": "What is the average salary?",
    "workspace_id": "default"
  }
  ```
- Response:
  ```json
  {
    "outcome": "OK",
    "reasons": "Question passed validation..."
  }
  ```

## Quick Start

### Development Mode

1. Install dependencies:
   ```bash
   cd sql_generator
   uv sync
   ```

2. Set environment variables:
   ```bash
   export OPENAI_API_KEY=your-api-key-here
   export DJANGO_BACKEND_URL=http://localhost:8040
   ```

3. Run the service:
   ```bash
   uv run python main.py
   ```

The service will be available at `http://localhost:8001`.

### Docker Mode

1. Build and run with docker-compose:
   ```bash
   cd ..  # Back to thoth_ui directory
   docker-compose -f docker-compose.dev.yml up sql-generator-dev
   ```

## Testing

Run the test script to verify the API:

```bash
cd sql_generator
uv run python test_api.py
```

## Architecture

```
sql_generator/
├── main.py                 # FastAPI application
├── agents/
│   ├── agent_manager.py    # Agent management
│   └── validation_agent.py # Question validation agent
├── templates/
│   ├── template_preparation.py    # Template utilities
│   ├── template_check_question.txt # Question validation template
│   └── system_template_check_question.txt # System prompt
├── requirements.txt        # Python dependencies
├── Dockerfile             # Container configuration
└── test_api.py            # API test suite
```

## Integration with Frontend

The Next.js frontend communicates with this service through the `sql-generator-api.ts` client:

1. User submits question in chat interface
2. Frontend calls `/validate-question` endpoint
3. Service validates question using AI agent
4. Response displayed in conversation area

## Next Steps

The next implementation phases will add:

1. **Full SQL Generation**: Complete SQL generation pipeline
2. **Advanced Agents**: Keyword extraction, column selection, SQL generation agents
3. **Vector Database Integration**: Similarity search for context
4. **Streaming Responses**: Real-time response streaming
5. **Caching**: Response caching for improved performance

## Environment Variables

- `OPENAI_API_KEY`: OpenAI API key for AI agents
- `DJANGO_BACKEND_URL`: URL of Django backend service (default: http://localhost:8040)

## Error Handling

The service includes comprehensive error handling:

- **Network errors**: Graceful fallback when Django backend is unavailable
- **AI agent errors**: Fallback to basic validation logic
- **Validation errors**: Proper error responses with details
- **Timeout handling**: 30-second timeout for AI processing