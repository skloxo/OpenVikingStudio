import { defineConfig } from 'vite'
import pkg from './package.json' with { type: 'json' }
import { devtools } from '@tanstack/devtools-vite'
import tsconfigPaths from 'vite-tsconfig-paths'

import { tanstackRouter } from '@tanstack/router-plugin/vite'

import viteReact from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// All OpenViking backend API paths (none under /studio/) are proxied to 1933.
// 1936 is the Vite dev server; 1933 is the production OpenViking backend.
const OV_BACKEND = 'http://127.0.0.1:1933'
const ovProxyEntry = {
  target: OV_BACKEND,
  changeOrigin: true,
}

const config = defineConfig({
  base: '/studio/',
  server: {
    port: 1936,
    host: '0.0.0.0',
    allowedHosts: true,
    watch: {
      ignored: ['**/public/all_skills.json', '**/all_skills.json'],
    },
    proxy: {
      // Root-level OpenViking API paths (no /api prefix)
      '/health':    ovProxyEntry,
      '/ready':     ovProxyEntry,
      '/metrics':   ovProxyEntry,
      // Standard /api paths
      '/api':       ovProxyEntry,
      // Bot API
      '/bot':       ovProxyEntry,
      // Admin API
      '/admin':     ovProxyEntry,
      // Console API
      '/console':   ovProxyEntry,
      // File system
      '/fs':        ovProxyEntry,
      '/webdav':    ovProxyEntry,
      // Search
      '/search':    ovProxyEntry,
      // Sessions, tasks, system
      '/sessions':  ovProxyEntry,
      '/tasks':     ovProxyEntry,
      '/system':    ovProxyEntry,
      // Resources, skills, pack
      '/skills':    ovProxyEntry,
      '/resources': ovProxyEntry,
      '/pack':      ovProxyEntry,
      // Relations, privacy, content
      '/relations': ovProxyEntry,
      '/privacy':   ovProxyEntry,
      '/content':   ovProxyEntry,
    }
  },
  plugins: [
    devtools(),
    tsconfigPaths({ projects: ['./tsconfig.json'] }),
    tailwindcss(),
    tanstackRouter({ target: 'react', autoCodeSplitting: true }),
    viteReact(),
  ],
  // 实时从 package.json 读取并注入版本号 — 组件中使用 __APP_VERSION__ 常量即可
  define: {
    __APP_VERSION__: JSON.stringify(pkg.version),
  },
})

export default config
