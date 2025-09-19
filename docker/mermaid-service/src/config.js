export const DEFAULT_MERMAID_CONFIG = {
  startOnLoad: false,
  deterministicIds: true,
  deterministicIDSeed: 'thoth-mermaid-service',
  securityLevel: 'strict',
  theme: 'neutral',
  fontFamily: 'Inter, "Helvetica Neue", Arial, sans-serif',
  logLevel: 'fatal'
};

export const BODY_SIZE_LIMIT = process.env.MERMAID_MAX_BODY_SIZE || '1mb';
export const PORT = parseInt(process.env.PORT || process.env.MERMAID_SERVICE_PORT || '8001', 10);

export const ENABLE_PNG = process.env.MERMAID_ENABLE_PNG !== 'false';
