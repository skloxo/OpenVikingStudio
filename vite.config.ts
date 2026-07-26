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
          'x-api-key': '[REDACTED_API_KEY]'
        }
      },
      '/health': {
        target: 'http://127.0.0.1:1933',
        changeOrigin: true
      }
    }
  }
});
