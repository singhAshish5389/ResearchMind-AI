/**
 * ResearchMind AI – Vite Configuration
 * ======================================
 * Configures Vite for the React frontend.
 * - Sets the dev server port to 5173
 * - Configures the API proxy so /api/* requests go to the FastAPI backend
 */

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Proxy all /api requests to the FastAPI backend during development.
      // This avoids CORS issues in development.
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    // Output directory for production builds
    outDir: 'dist',
    sourcemap: false,
  },
});
