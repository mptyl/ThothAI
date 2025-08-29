# AI Provider Configuration for SQL Generator

The SQL Generator service supports multiple AI providers for question validation. You need to configure at least one provider to use the service.

## Supported Providers

### 1. OpenAI (GPT Models)
```bash
# Set in .env.local or environment
OPENAI_API_KEY=your-openai-api-key-here
```
- Models: gpt-3.5-turbo, gpt-4, etc.
- Get API key: https://platform.openai.com/api-keys

### 2. Anthropic (Claude Models)
```bash
# Set in .env.local or environment
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```
- Models: claude-3-haiku-20240307, claude-3-sonnet-20240229, etc.
- Get API key: https://console.anthropic.com/

### 3. Mistral AI
```bash
# Set in .env.local or environment
MISTRAL_API_KEY=your-mistral-api-key-here
```
- Models: mistral-tiny, mistral-small, mistral-medium
- Get API key: https://console.mistral.ai/

### 4. Local Ollama (Free, runs locally)
```bash
# Set in .env.local or environment
OLLAMA_API_BASE=http://localhost:11434
```
- Requires Ollama installed and running locally
- Models: llama3.2, codellama, mistral, etc.
- Install: https://ollama.ai/

## Configuration Priority

The service will automatically detect and use the first available provider in this order:
1. OpenAI (if OPENAI_API_KEY is set)
2. Anthropic (if ANTHROPIC_API_KEY is set)  
3. Mistral (if MISTRAL_API_KEY is set)
4. Ollama (if OLLAMA_API_BASE is set)

## Setup Instructions

1. Copy the environment template:
   ```bash
   cp .env.local.template .env.local
   ```

2. Edit `.env.local` and uncomment/set one of the AI provider keys:
   ```bash
   # Example for OpenAI
   OPENAI_API_KEY=sk-your-actual-key-here
   
   # Example for Anthropic
   ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
   
   # Example for local Ollama
   OLLAMA_API_BASE=http://localhost:11434
   ```

3. Start the service:
   ```bash
   ./start-all.sh
   ```

## Error Messages

- **"No AI provider configured"**: No API keys found in environment
- **"Authentication error"**: Invalid API key for the provider
- **"Model not found"**: The specified model is not available for your account

## Fallback Behavior

If the AI provider fails (network issues, invalid key, etc.), the service will fall back to basic rule-based validation that checks for:
- Empty or too-short questions
- Obviously out-of-scope questions (weather, recipes, etc.)
- Returns "OK" for most database-related questions

This ensures the service remains functional even when AI providers are unavailable.