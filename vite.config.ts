import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const engineOrigin = process.env.CLINIC_ENGINE_ORIGIN ?? 'http://127.0.0.1:8765';

export default defineConfig({
  plugins: [react(), {
    name: 'local-motion-review-evidence',
    apply: 'serve',
    configureServer(server) {
      server.middlewares.use(async (request, response, next) => {
        const match = /^\/__review-evidence\/([1-6])$/.exec(request.url ?? '');
        const uiMatch = /^\/__ui-evidence\/(patient|doctor)$/.exec(request.url ?? '');
        if (!match && !uiMatch) {
          next();
          return;
        }
        const contentType = uiMatch ? 'image/jpeg' : 'image/png';
        if (request.method !== 'POST' || request.headers.origin !== `http://${request.headers.host}` || request.headers['content-type'] !== contentType) {
          response.writeHead(403).end();
          return;
        }
        try {
          const chunks: Buffer[] = [];
          let length = 0;
          for await (const chunk of request) {
            length += chunk.length;
            if (length > 10_000_000) {
              response.writeHead(413).end();
              return;
            }
            chunks.push(chunk);
          }
          const bytes = Buffer.concat(chunks);
          const signature = uiMatch ? [255, 216, 255] : [137, 80, 78, 71, 13, 10, 26, 10];
          if (!bytes.subarray(0, signature.length).equals(Buffer.from(signature))) {
            response.writeHead(400).end();
            return;
          }
          const folder = path.resolve('docs/evidence');
          await mkdir(folder, { recursive: true });
          const filename = uiMatch ? `ui-${uiMatch[1]}-v0.2.1.jpg` : `motion-review-v0.2.1-${match![1]}.png`;
          await writeFile(path.join(folder, filename), bytes);
          response.writeHead(201).end();
        } catch {
          response.writeHead(500).end();
        }
      });
    },
  }],
  base: '/',
  build: {
    assetsDir: 'ui-assets',
    sourcemap: true,
    chunkSizeWarningLimit: 1800,
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': engineOrigin,
      '/ws': { target: engineOrigin.replace('http:', 'ws:'), ws: true },
      '/assets': engineOrigin,
    },
  },
});
