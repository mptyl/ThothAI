# Self-Hosted Mermaid Service for ThothAI

## Overview

This document describes the self-hosted Mermaid service that has been integrated into ThothAI to replace the external mermaid.ink service for rendering ERD (Entity Relationship Diagram) diagrams.

## Why a Self-Hosted Service?

The previous implementation relied on the external mermaid.ink service to render Mermaid diagrams. This had several limitations:

1. **Dependency on External Service**: The system was dependent on the availability of mermaid.ink
2. **Privacy Concerns**: Diagram data was sent to an external service
3. **Potential Service Outages**: Any issues with mermaid.ink would affect ERD functionality
4. **Limited Customization**: No control over the rendering service

The self-hosted Mermaid service addresses these issues by:

1. **Self-Contained**: No dependency on external services
2. **Privacy**: All diagram rendering happens within the local network
3. **Reliability**: Full control over service availability
4. **Customization**: Ability to customize themes and rendering options

## Architecture

The Mermaid service is implemented as a Node.js Express server that provides HTTP endpoints for rendering Mermaid diagrams. It uses the following components:

- **Express.js**: Web server framework
- **Mermaid.js**: Diagram parsing/rendering runtime loaded inside a headless Chromium page (via Puppeteer)
- **Puppeteer**: Manages a shared headless Chromium instance that produces accurate Mermaid SVG output and browser-quality PNG screenshots

### Service Endpoints

- `GET /health`: Health check endpoint
- `POST /svg`: Renders Mermaid diagram as SVG
- `POST /png`: Renders Mermaid diagram as PNG

## Integration with ThothAI

### Backend Integration

The `mermaid_utils.py` file has been updated to use the local Mermaid service instead of mermaid.ink:

- `MERMAID_SERVICE_URL`: Environment variable pointing to the local service
- `check_mermaid_service_status()`: Checks if the local service is available
- `generate_mermaid_image()`: Generates images using the local service
- `get_erd_display_image()`: Generates SVG for web display
- `generate_erd_pdf()`: Generates PDF documents with ERD diagrams

### Docker Integration

The Mermaid service is containerized and integrated into the Docker Compose setup:

- **Service Name**: `mermaid-service`
- **Image**: `thoth-mermaid-service:latest`
- **Port**: `8003` (external) / `8001` (internal)
- **Network**: `thoth-network`

### Local Development

For local development, the Mermaid service can be started using the `start-all.sh` script:

- **Port**: `8003`
- **URL**: `http://localhost:8003`
- **Chromium**: `puppeteer` downloads a matching Chromium build automatically during `npm install`. Set `PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true` if you want to point to an existing browser via `PUPPETEER_EXECUTABLE_PATH`.

## Configuration

### Environment Variables

The following environment variables are used to configure the Mermaid service:

- `MERMAID_SERVICE_PORT`: Port for the service (default: `8003`)
- `MERMAID_SERVICE_URL`: URL for the service (default: `http://mermaid-service:8001` for Docker, `http://localhost:8003` for local)

### Docker Configuration

The service is configured in `docker-compose.yml` with the following settings:

```yaml
mermaid-service:
  build:
    context: ./docker/mermaid-service
    dockerfile: Dockerfile
  image: thoth-mermaid-service:latest
  container_name: thoth-mermaid-service
  restart: always
  ports:
    - "${MERMAID_SERVICE_PORT:-8003}:8001"
  networks:
    - thoth-network
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
```

## Testing

A test script (`test_mermaid_service.py`) is provided to verify the integration:

```bash
python test_mermaid_service.py
```

The script tests the following functionality:

1. Service health check
2. SVG generation
3. PNG generation
4. ERD display image generation
5. ERD PDF generation

## Usage

### Starting the Service

#### Docker Compose

```bash
docker-compose up -d mermaid-service
```

#### Local Development

```bash
# Start all services including Mermaid service
./start-all.sh

# Or start only the Mermaid service
cd docker/mermaid-service
npm install
npm start
```

### Checking Service Status

```bash
# Health check
curl http://localhost:8003/health

# Or use the provided test script
python test_mermaid_service.py
```

### Generating Diagrams

#### SVG

```bash
curl -X POST -H "Content-Type: text/plain" \
  -d "graph TD\n    A[Start] --> B[Process]" \
  http://localhost:8003/svg -o diagram.svg
```

#### PNG

```bash
curl -X POST -H "Content-Type: text/plain" \
  -d "graph TD\n    A[Start] --> B[Process]" \
  http://localhost:8003/png -o diagram.png
```

## Troubleshooting

### Service Not Starting

1. **Check Port Availability**: Ensure port `8003` is not in use
2. **Check Node.js Version**: The service requires Node.js 18 or higher
3. **Check Dependencies**: Run `npm install` in the service directory

### Diagram Generation Issues

1. **Check Service Health**: Use the `/health` endpoint to verify the service is running
2. **Check Mermaid Syntax**: Ensure the diagram syntax is valid
3. **Check Logs**: Check the service logs for error messages

### Integration Issues

1. **Check Environment Variables**: Ensure `MERMAID_SERVICE_URL` is set correctly
2. **Check Network Connectivity**: Verify the backend can reach the Mermaid service
3. **Check Backend Configuration**: Ensure `mermaid_utils.py` is using the correct service URL

## Migration from mermaid.ink

The migration from mermaid.ink to the self-hosted service is transparent to the end user. The existing ERD functionality in ThothAI will continue to work as before, but now uses the local service.

### Rollback Plan

If issues arise with the self-hosted service, you can easily revert to mermaid.ink:

1. Stop the Mermaid service:
   ```bash
   docker-compose stop mermaid-service
   ```

2. Update `backend/thoth_ai_backend/mermaid_utils.py`:
   ```python
   # Change this line:
   MERMAID_SERVICE_URL = os.environ.get('MERMAID_SERVICE_URL', 'http://mermaid-service:8001')
   
   # To:
   MERMAID_INK_SERVICE = "https://mermaid.ink"
   ```

3. Update the functions to use the original mermaid.ink API

## Future Enhancements

Potential enhancements for the Mermaid service:

1. **Additional Output Formats**: Support for PDF, JPEG, etc.
2. **Custom Themes**: Ability to specify custom themes
3. **Caching**: Cache frequently requested diagrams
4. **Authentication**: Secure the service with API keys
5. **Metrics**: Add monitoring and metrics collection

## Conclusion

The self-hosted Mermaid service provides a more reliable, private, and customizable solution for rendering ERD diagrams in ThothAI. It eliminates the dependency on external services while maintaining compatibility with the existing ERD functionality.
