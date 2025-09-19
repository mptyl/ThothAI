import express from 'express';
import bodyParser from 'body-parser';
import { pathToFileURL } from 'node:url';

import {
  BODY_SIZE_LIMIT,
  DEFAULT_MERMAID_CONFIG,
  ENABLE_PNG,
  PORT
} from './config.js';
import { MermaidRenderer, MermaidRenderError } from './renderer.js';

const app = express();
const renderer = new MermaidRenderer(DEFAULT_MERMAID_CONFIG);

app.use(bodyParser.json({ limit: BODY_SIZE_LIMIT }));
app.use(bodyParser.urlencoded({ extended: true, limit: BODY_SIZE_LIMIT }));
app.use(
  bodyParser.text({
    limit: BODY_SIZE_LIMIT,
    type: ['text/plain', 'text/mermaid', 'application/mermaid', 'application/text']
  })
);

const extractDefinition = (payload) => {
  if (payload == null) {
    return '';
  }

  if (typeof payload === 'string') {
    return payload;
  }

  if (Buffer.isBuffer(payload)) {
    return payload.toString('utf-8');
  }

  if (typeof payload === 'object') {
    const candidates = [
      'definition',
      'diagram',
      'code',
      'mermaid',
      'content',
      'data'
    ];

    for (const key of candidates) {
      if (typeof payload[key] === 'string') {
        return payload[key];
      }
    }
  }

  return '';
};

const sendSvgResponse = (res, svg) => {
  res.status(200);
  res.setHeader('Content-Type', 'image/svg+xml; charset=utf-8');
  res.send(svg);
};

const sendPngResponse = (res, buffer) => {
  res.status(200);
  res.setHeader('Content-Type', 'image/png');
  res.send(buffer);
};

const handleRender = (format) => async (req, res) => {
  const definition = extractDefinition(req.body).trim();

  if (!definition) {
    return res.status(400).json({ error: 'No Mermaid diagram provided', type: 'validation' });
  }

  try {
    const result = await renderer.render(definition, {
      format,
      scale: Number.parseFloat(req.query.scale) || 1
    });

    if (format === 'png') {
      return sendPngResponse(res, result.png);
    }

    return sendSvgResponse(res, result.svg);
  } catch (error) {
    const isRenderError = error instanceof MermaidRenderError;
    const status = isRenderError
      ? error.type === 'syntax' || error.type === 'validation'
        ? 400
        : 500
      : 500;

    res.status(status).json({
      error: error.message || 'Failed to render diagram',
      type: isRenderError ? error.type : 'unknown'
    });
  }
};

app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'thoth-mermaid-service', pngEnabled: ENABLE_PNG });
});

app.post('/svg', handleRender('svg'));

if (ENABLE_PNG) {
  app.post('/png', handleRender('png'));
} else {
  app.post('/png', (req, res) => {
    res.status(405).json({ error: 'PNG rendering disabled', type: 'disabled' });
  });
}

const startServer = () =>
  app.listen(PORT, () => {
    console.log(`Mermaid service listening on port ${PORT}`);
  });

const entryUrl = process.argv[1] ? pathToFileURL(process.argv[1]).href : null;
if (entryUrl && import.meta.url === entryUrl) {
  startServer();
}

export { app, renderer, startServer };
