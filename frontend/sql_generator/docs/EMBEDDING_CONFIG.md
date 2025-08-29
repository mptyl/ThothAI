# Embedding Configuration

## Overview

The Thoth system uses external embedding providers for vector similarity search. The embedding configuration is managed at the workspace level through the VectorDb model in the Django backend.

## Configuration Priority

The system checks for API keys in the following order:
1. **Database Configuration**: API key stored in the VectorDb model (via Django admin)
2. **Provider-Specific Environment Variables**: Provider-specific keys from environment
3. **Generic Environment Variable**: EMBEDDING_API_KEY as a fallback

## Environment Variables for Embedding Providers

The backend supports the following environment variables as fallbacks for embedding API keys:

### OpenAI
- `OPENAI_API_KEY`
- `OPENAI_KEY`

### Cohere
- `COHERE_API_KEY`
- `COHERE_KEY`

### Mistral
- `MISTRAL_API_KEY`
- `MISTRAL_KEY`

### HuggingFace
- `HUGGINGFACE_API_KEY`
- `HF_API_KEY`
- `HUGGINGFACE_TOKEN`

### Anthropic
- `ANTHROPIC_API_KEY`
- `CLAUDE_API_KEY`

### Generic (works for any provider)
- `EMBEDDING_API_KEY`

## Configuration Status

The system provides visual feedback about the embedding configuration status:

- **Configured**: Green badge with checkmark - Provider, model, and API key are all properly set
- **Not Configured**: Red badge with X - Missing API key or incomplete configuration
- **API Key Status**: Shows whether an API key is available (from database or environment)

## Setting Environment Variables

### For Development (Django Backend)

Add the environment variables to your Django backend `.env` file:
```bash
# In /Users/mp/Thoth/thoth_be/.env
OPENAI_API_KEY=your-openai-key-here
# OR
COHERE_API_KEY=your-cohere-key-here
# OR
MISTRAL_API_KEY=your-mistral-key-here
# etc.
```

### For Production

Set environment variables in your deployment environment:
- Docker: Add to docker-compose.yml or Dockerfile
- Kubernetes: Use ConfigMaps or Secrets
- Cloud Platforms: Use platform-specific environment configuration

## Troubleshooting

### Embedding Configuration Shows "Not Configured"

1. Check that the VectorDb has an embedding provider selected
2. Check that the VectorDb has an embedding model specified
3. Verify API key is set either in Django admin or environment variables

### API Key Shows "Missing"

1. Check Django admin for the VectorDb configuration
2. Verify environment variables are set in the backend (not frontend)
3. Check the backend logs for any errors loading environment variables

### Wrong Embedding Model Error

If you see errors about using `sentence-transformers/all-MiniLM-L6-v2`:
- This means the system is falling back to a local model
- Check that the VectorDb embedding configuration is complete
- Verify the API key is accessible to the backend

## Security Notes

- API keys are NEVER sent to the frontend
- The frontend only receives boolean status indicators
- All API key checks happen on the backend
- Store production API keys securely using environment variables or secrets management