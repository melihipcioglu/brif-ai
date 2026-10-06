import { defineConfig } from 'vitest/config';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [tailwindcss()],
  build: {
    outDir: 'dist-yokdil',
    lib: { entry: 'src/index.ts', formats: ['es'], fileName: 'yokdil-phase-one' },
    rollupOptions: { external: ['react', 'react-dom', 'react/jsx-runtime', 'dexie', 'zod', 'lucide-react'] },
  },
  test: {
    environment: 'jsdom',
    include: ['tests/yokdil/**/*.test.{ts,tsx}'],
    setupFiles: ['tests/yokdil/setup.ts'],
    restoreMocks: true,
  },
});
