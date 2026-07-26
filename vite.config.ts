import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 1936,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:1933',
        changeOrigin: true,
        headers: {
          'x-api-key': 'sk-fbb21afbe35d09986ac6f66ca91f62f44ee6b2536319be7347759f02de8f6227'
        }
      },
      '/health': {
        target: 'http://127.0.0.1:1933',
        changeOrigin: true
      }
    }
  }
});
