import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { defineConfig, type Plugin } from 'vite';
import tailwindcss from '@tailwindcss/vite';

/** Emits the service worker stamped with a per-build id so old caches are dropped on update. */
function emitServiceWorker(): Plugin {
  let root = process.cwd();
  return {
    name: 'emit-service-worker',
    apply: 'build',
    configResolved(config) {
      root = config.root;
    },
    generateBundle() {
      const template = readFileSync(resolve(root, 'pwa/sw.template.js'), 'utf8');
      this.emitFile({
        type: 'asset',
        fileName: 'sw.js',
        source: template.split('__BUILD_ID__').join(Date.now().toString(36)),
      });
    },
  };
}

export default defineConfig(({ command }) => ({
  // Relative base: the build works from any path (GitHub Pages sub-path, LAN server, file share).
  base: './',
  plugins: [tailwindcss(), emitServiceWorker()],
  define: {
    __PWA_ENABLED__: JSON.stringify(command === 'build'),
  },
  server: {
    host: true, // reachable from the phone on the same Wi-Fi
    port: 5173,
  },
  preview: {
    host: true,
    port: 4173,
  },
  build: {
    outDir: 'dist',
  },
}));
