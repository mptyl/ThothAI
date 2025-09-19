# Self-Hosted Mermaid Service Implementation Plan

## Overview
This document outlines the implementation plan for replacing the external mermaid.ink service with a self-hosted Mermaid service running in Docker.

## Current Implementation
The current implementation uses the external mermaid.ink service to render ERD diagrams:
- Service URL: `https://mermaid.ink`
- Used in: `backend/thoth_ai_backend/mermaid_utils.py`
- Functions: `generate_mermaid_image()`, `get_erd_display_image()`, `generate_erd_pdf()`

## Selected Solution: Node.js Based Mermaid Service
We'll implement a lightweight Node.js Express server that provides an HTTP API for rendering Mermaid diagrams.

> **Note – September 2025**: the live implementation now renders SVGs with Mermaid + JSDOM and converts them to PNG through `sharp` (no Puppeteer or headless browser required). Key files: `docker/mermaid-service/src/renderer.js` and `docker/mermaid-service/src/server.js`. The step-by-step blueprint below has been kept for historical context, but the final solution follows the updated stack.

### Directory Structure
```
docker/mermaid-service/
├── package.json
├── server.js
├── Dockerfile
└── .dockerignore
```

### Implementation Details

#### 1. Package.json
```json
{
  "name": "thoth-mermaid-service",
  "version": "1.0.0",
  "description": "Self-hosted Mermaid diagram rendering service for ThothAI",
  "main": "server.js",
  "scripts": {
    "start": "node server.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "mermaid": "^10.6.1",
    "puppeteer": "^21.5.2",
    "body-parser": "^1.20.2"
  },
  "engines": {
    "node": ">=18"
  }
}
```

#### 2. Server.js
```javascript
const express = require('express');
const mermaid = require('mermaid');
const puppeteer = require('puppeteer');
const bodyParser = require('body-parser');
const path = require('path');
const fs = require('fs');
const os = require('os');

const app = express();
const PORT = process.env.PORT || 8001;

// Middleware
app.use(bodyParser.json());
app.use(bodyParser.text({ type: 'text/plain' }));

// Initialize Mermaid
mermaid.initialize({
  startOnLoad: true,
  theme: 'default',
  securityLevel: 'loose',
  themeVariables: {
    primaryColor: '#e1f5fe',
    primaryTextColor: '#000',
    primaryBorderColor: '#01579b',
    lineColor: '#01579b',
    secondaryColor: '#fff3e0',
    tertiaryColor: '#fff'
  }
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'ok', service: 'thoth-mermaid-service' });
});

// SVG endpoint (similar to mermaid.ink/svg/)
app.post('/svg', async (req, res) => {
  try {
    const mermaidCode = req.body;
    
    if (!mermaidCode) {
      return res.status(400).json({ error: 'No Mermaid code provided' });
    }

    // Generate SVG
    const { svg } = await mermaid.render('mermaid-diagram', mermaidCode);
    
    res.set('Content-Type', 'image/svg+xml');
    res.send(svg);
  } catch (error) {
    console.error('Error generating SVG:', error);
    res.status(500).json({ error: 'Failed to generate SVG' });
  }
});

// PNG endpoint (similar to mermaid.ink/img/)
app.post('/png', async (req, res) => {
  try {
    const mermaidCode = req.body;
    
    if (!mermaidCode) {
      return res.status(400).json({ error: 'No Mermaid code provided' });
    }

    // Generate SVG first
    const { svg } = await mermaid.render('mermaid-diagram', mermaidCode);
    
    // Convert SVG to PNG using Puppeteer
    const browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    
    // Create HTML with SVG
    const html = `
      <!DOCTYPE html>
      <html>
        <head>
          <style>
            body { margin: 0; padding: 0; }
            svg { width: 100%; height: 100%; }
          </style>
        </head>
        <body>
          ${svg}
        </body>
      </html>
    `;
    
    await page.setContent(html, { waitUntil: 'networkidle0' });
    
    // Get dimensions from SVG
    const dimensions = await page.evaluate(() => {
      const svg = document.querySelector('svg');
      return {
        width: svg.viewBox.baseVal.width || svg.clientWidth,
        height: svg.viewBox.baseVal.height || svg.clientHeight
      };
    });
    
    // Set viewport size
    await page.setViewport({
      width: Math.ceil(dimensions.width),
      height: Math.ceil(dimensions.height)
    });
    
    // Generate PNG
    const pngBuffer = await page.screenshot({
      type: 'png',
      omitBackground: true
    });
    
    await browser.close();
    
    res.set('Content-Type', 'image/png');
    res.send(pngBuffer);
  } catch (error) {
    console.error('Error generating PNG:', error);
    res.status(500).json({ error: 'Failed to generate PNG' });
  }
});

// Start server
app.listen(PORT, () => {
  console.log(`Mermaid service running on port ${PORT}`);
});
```

#### 3. Dockerfile
```dockerfile
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application code
COPY server.js ./

# Create non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S mermaid -u 1001

# Change ownership
RUN chown -R mermaid:nodejs /app
USER mermaid

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:8001/health', (res) => { process.exit(res.statusCode === 200 ? 0 : 1) })"

# Start the application
CMD ["npm", "start"]
```

#### 4. .dockerignore
```
node_modules
npm-debug.log
Dockerfile
.dockerignore
.git
.gitignore
README.md
```

## Docker Compose Integration

### Update docker-compose.yml
Add the following service to the `docker-compose.yml` file:

```yaml
  # === MERMAID SERVICE ===
  mermaid-service:
    build:
      context: ./docker/mermaid-service
      dockerfile: Dockerfile
    image: thoth-mermaid-service:latest
    container_name: thoth-mermaid-service
    restart: always
    ports:
      - "${MERMAID_SERVICE_PORT:-8001}:8001"
    networks:
      - thoth-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Update .env.docker.template
Add the following line to `.env.docker.template`:
```
MERMAID_SERVICE_PORT=8001
```

## Backend Integration

### Update mermaid_utils.py
Modify `backend/thoth_ai_backend/mermaid_utils.py` to use the local service:

1. Replace the `MERMAID_INK_SERVICE` constant:
```python
# Mermaid service configuration
# Using local mermaid service
MERMAID_SERVICE_URL = "http://mermaid-service:8001"
```

2. Update `generate_mermaid_image()` function:
```python
def generate_mermaid_image(
    mermaid_content: str,
    output_format: str = "svg",
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Generate an image from Mermaid diagram content using local mermaid service.
    """
    if not mermaid_content or not mermaid_content.strip():
        return False, None, "Empty Mermaid content provided"

    try:
        # Choose the appropriate endpoint based on format
        if output_format.lower() == "svg":
            url = f"{MERMAID_SERVICE_URL}/svg"
            file_extension = "svg"
            content_type = "image/svg+xml"
        else:  # Default to PNG for other formats
            url = f"{MERMAID_SERVICE_URL}/png"
            file_extension = "png"
            content_type = "image/png"

        # Make HTTP request to local mermaid service
        response = requests.post(url, data=mermaid_content, timeout=20)

        if response.status_code != 200:
            error_msg = f"Mermaid service returned status {response.status_code}"
            if response.text:
                error_msg += f": {response.text}"
            logger.error(error_msg)
            return False, None, error_msg

        # Create temporary file to save the response
        exports_dir = os.path.join(settings.BASE_DIR, "exports")
        os.makedirs(exports_dir, exist_ok=True)

        # Save response to file
        output_filename = f"erd_{int(time.time())}.{file_extension}"
        output_path = os.path.join(exports_dir, output_filename)

        if content_type == "image/svg+xml":
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(response.text)
        else:
            with open(output_path, "wb") as f:
                f.write(response.content)

        logger.info(
            f"Successfully generated Mermaid {file_extension.upper()}: {output_path}"
        )
        return True, output_path, None

    except requests.exceptions.Timeout:
        error_msg = "Diagram generation service is temporarily unavailable. Please try again later."
        logger.warning("Mermaid service timeout")
        return False, None, error_msg
    except requests.exceptions.ConnectionError:
        error_msg = "Diagram generation service is temporarily unavailable. Please try again later."
        logger.warning("Mermaid service connection error")
        return False, None, error_msg
    except requests.exceptions.RequestException as e:
        error_msg = f"HTTP request to Mermaid service failed: {str(e)}"
        logger.error(error_msg)
        return False, None, error_msg
    except Exception as e:
        error_msg = f"Unexpected error during Mermaid generation: {str(e)}"
        logger.error(error_msg)
        return False, None, error_msg
```

3. Update `check_mermaid_service_status()` function:
```python
def check_mermaid_service_status() -> bool:
    """
    Check if local mermaid service is available.
    """
    try:
        # Test with health endpoint
        response = requests.get(f"{MERMAID_SERVICE_URL}/health", timeout=5)
        return response.status_code == 200
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        logger.warning("Local mermaid service temporarily unavailable")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Error checking local mermaid service: {e}")
        return False
```

## Testing Plan

1. Build and start the Mermaid service:
   ```bash
   docker-compose build mermaid-service
   docker-compose up -d mermaid-service
   ```

2. Check service health:
   ```bash
   curl http://localhost:8001/health
   ```

3. Test SVG generation:
   ```bash
   curl -X POST -H "Content-Type: text/plain" -d "graph TD\n    A[Test] --> B[Service]" http://localhost:8001/svg
   ```

4. Test PNG generation:
   ```bash
   curl -X POST -H "Content-Type: text/plain" -d "graph TD\n    A[Test] --> B[Service]" http://localhost:8001/png -o test.png
   ```

5. Test ERD functionality in ThothAI:
   - Generate an ERD for a database
   - View the ERD in the web interface
   - Export ERD as PDF

## Benefits

1. **Self-hosted**: No dependency on external services
2. **Privacy**: Diagram data stays within the local network
3. **Reliability**: No external service outages
4. **Customization**: Can customize themes and styling
5. **Performance**: Local network communication is faster
6. **Control**: Full control over the service configuration

## Rollback Plan

If issues arise, we can easily revert to the external mermaid.ink service by:
1. Commenting out the mermaid-service in docker-compose.yml
2. Reverting the changes in mermaid_utils.py to use the original MERMAID_INK_SERVICE
3. Restarting the services
