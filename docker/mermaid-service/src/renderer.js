import { createRequire } from 'node:module';
import os from 'node:os';
import path from 'node:path';
import puppeteer from 'puppeteer';
import { DEFAULT_MERMAID_CONFIG } from './config.js';

const require = createRequire(import.meta.url);
const MERMAID_SCRIPT_PATH = require.resolve('mermaid/dist/mermaid.min.js');

class MermaidRenderError extends Error {
  constructor(message, type = 'generic') {
    super(message);
    this.name = 'MermaidRenderError';
    this.type = type;
  }
}

const HTML_TEMPLATE = `<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <style>
      html,
      body {
        margin: 0;
        padding: 0;
        background: transparent;
        width: 100%;
        height: 100%;
      }

      body {
        font-family: Inter, 'Helvetica Neue', Arial, sans-serif;
        display: flex;
        align-items: flex-start;
        justify-content: flex-start;
      }

      #app {
        display: inline-block;
        padding: 24px;
        background: transparent;
      }
    </style>
  </head>
  <body>
    <div id="app"></div>
  </body>
</html>`;

let browserPromise;
let pagePromise;

const USER_DATA_DIR = path.join(os.tmpdir(), 'thoth-mermaid-puppeteer');

const getBrowser = async () => {
  if (!browserPromise) {
    browserPromise = puppeteer.launch({
      headless: 'new',
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-crash-reporter',
        '--font-render-hinting=none',
        `--user-data-dir=${USER_DATA_DIR}`
      ],
      ignoreDefaultArgs: ['--enable-automation'],
      env: {
        ...process.env,
        PUP_DISABLE_CRASHPAD: '1'
      }
    });
  }
  return browserPromise;
};

const getPage = async () => {
  if (!pagePromise) {
    pagePromise = (async () => {
      const browser = await getBrowser();
      const page = await browser.newPage();
      await page.setContent(HTML_TEMPLATE, { waitUntil: 'domcontentloaded' });
      await page.addScriptTag({ path: MERMAID_SCRIPT_PATH });
      await page.evaluate(() => {
        window.renderMermaidDiagram = async (definition, config) => {
          try {
            const mergedConfig = Object.assign(
              {
                startOnLoad: false,
                deterministicIds: true,
                deterministicIDSeed: 'thoth-mermaid-service',
                securityLevel: 'loose',
                er: {
                  diagramPadding: 20,
                  layoutDirection: 'TB'
                }
              },
              config || {}
            );

            if (typeof mermaid.reset === 'function') {
              mermaid.reset();
            }

            mermaid.initialize(mergedConfig);
            await mermaid.parse(definition);

            const renderId = `mermaid-${Math.random().toString(16).slice(2)}`;
            const { svg } = await mermaid.render(renderId, definition);
            const container = document.getElementById('app');
            container.innerHTML = svg;
            const svgElement = container.querySelector('svg');
            svgElement.style.width = 'auto';
            svgElement.style.height = 'auto';

            const bbox = svgElement.getBBox();
            const rect = svgElement.getBoundingClientRect();

            const width = Math.ceil(Math.max(bbox.width + bbox.x, rect.width));
            const height = Math.ceil(Math.max(bbox.height + bbox.y, rect.height));

            return {
              svg: container.innerHTML,
              width,
              height
            };
          } catch (err) {
            return {
              error: {
                message: err?.message || String(err),
                type: err?.name || 'Error'
              }
            };
          }
        };
      });
      return page;
    })();
  }
  return pagePromise;
};

const closeBrowser = async () => {
  if (pagePromise) {
    try {
      const page = await pagePromise;
      await page.close({ runBeforeUnload: true });
    } catch (error) {
      // ignore
    }
    pagePromise = undefined;
  }

  if (browserPromise) {
    try {
      const browser = await browserPromise;
      await browser.close();
    } catch (error) {
      // ignore
    }
    browserPromise = undefined;
  }
};

process.on('SIGINT', async () => {
  await closeBrowser();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  await closeBrowser();
  process.exit(0);
});

const sanitizeErrorMessage = (error) => {
  if (!error) {
    return 'Unexpected Mermaid error';
  }

  if (typeof error === 'string') {
    return error;
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  if (typeof error === 'object' && 'message' in error) {
    return String(error.message);
  }

  try {
    return JSON.stringify(error);
  } catch (jsonError) {
    return String(error);
  }
};

class MermaidRenderer {
  constructor(config = DEFAULT_MERMAID_CONFIG) {
    this.config = config;
    this._queue = Promise.resolve();
  }

  _enqueue(task) {
    const run = this._queue.then(() => task());
    this._queue = run.catch(() => {});
    return run;
  }

  async renderSvg(definition, options = {}) {
    const diagram = typeof definition === 'string' ? definition.trim() : '';

    if (!diagram) {
      throw new MermaidRenderError('No Mermaid diagram definition provided', 'validation');
    }

    return this._enqueue(async () => {
      const page = await getPage();
      const result = await page.evaluate(
        (definitionString, config) => window.renderMermaidDiagram(definitionString, config),
        diagram,
        { ...this.config, ...(options.config || {}) }
      );

      if (result?.error) {
        const { message, type } = result.error;
        const sanitized = sanitizeErrorMessage(message);
        const errorType = ['ParseError', 'SyntaxError'].includes(type) ? 'syntax' : 'render';
        throw new MermaidRenderError(sanitized, errorType);
      }

      if (!result?.svg) {
        throw new MermaidRenderError('Mermaid produced an empty SVG output', 'render');
      }

      return result;
    });
  }

  async render(definition, { format = 'svg', scale = 1, config = {} } = {}) {
    const renderResult = await this.renderSvg(definition, { config });
    const { svg, width, height } = renderResult;

    if (format === 'svg') {
      return { svg };
    }

    if (format === 'png') {
      const page = await getPage();
      const padding = 48;
      const viewportWidth = Math.max(1, Math.ceil(width + padding));
      const viewportHeight = Math.max(1, Math.ceil(height + padding));
      const deviceScaleFactor = Math.max(1, Math.min(3, scale));

      await page.setViewport({
        width: viewportWidth,
        height: viewportHeight,
        deviceScaleFactor
      });

      const clip = await page.evaluate(() => {
        const container = document.getElementById('app');
        const rect = container.getBoundingClientRect();
        return {
          x: rect.x,
          y: rect.y,
          width: rect.width,
          height: rect.height
        };
      });

      const clipWidth = Math.max(1, Math.ceil(clip.width));
      const clipHeight = Math.max(1, Math.ceil(clip.height));

      const screenshot = await page.screenshot({
        omitBackground: true,
        clip: {
          x: Math.max(0, clip.x - 1),
          y: Math.max(0, clip.y - 1),
          width: Math.min(viewportWidth, clipWidth + 2),
          height: Math.min(viewportHeight, clipHeight + 2)
        }
      });

      return { svg, png: screenshot };
    }

    throw new MermaidRenderError(`Unsupported format: ${format}`, 'validation');
  }
}

export { MermaidRenderer, MermaidRenderError, closeBrowser };
