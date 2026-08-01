import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
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
      '/resources': ovProxyEntry,
      '/skills':    ovProxyEntry,
      '/pack':      ovProxyEntry,
      // Relations, privacy, content
      '/relations': ovProxyEntry,
      '/privacy':   ovProxyEntry,
      '/content':   ovProxyEntry,
      // Metrics endpoint override
      '/api/v1/system/harness_metrics': {
        target: 'http://127.0.0.1:1936',
        selfHandleResponse: true,
      },
    }
  },
  plugins: [
    devtools(),
    {
      name: 'harness-metrics-plugin',
      configureServer(server) {
        server.middlewares.use('/api/v1/system/skill_content', (req, res) => {
          const urlParams = new URL(req.url || '', 'http://localhost')
          const skillPath = urlParams.searchParams.get('path') || ''
          const skillName = urlParams.searchParams.get('name') || ''

          let content = ''
          let skillMdPath = ''

          if (skillPath) {
            skillMdPath = path.join(skillPath, 'SKILL.md')
            if (!fs.existsSync(skillMdPath) && fs.existsSync(skillPath)) {
              skillMdPath = skillPath
            }
          }

          if ((!skillMdPath || !fs.existsSync(skillMdPath)) && skillName) {
            const candidates = [
              path.join('/home/skloxo/aho/openclaw/project/OpenVikingStudio/.agents/skills', skillName, 'SKILL.md'),
              path.join('/home/skloxo/.gemini/config/skills', skillName, 'SKILL.md'),
              path.join('/home/skloxo/.openclaw/skills', skillName, 'SKILL.md'),
            ]
            for (const cand of candidates) {
              if (fs.existsSync(cand)) {
                skillMdPath = cand
                break
              }
            }
          }

          let files: Array<{ name: string; path: string; is_dir: boolean }> = []
          if (skillMdPath && fs.existsSync(skillMdPath)) {
            try {
              content = fs.readFileSync(skillMdPath, 'utf-8')
              const skillDir = path.dirname(skillMdPath)
              if (fs.existsSync(skillDir) && fs.statSync(skillDir).isDirectory()) {
                const entries = fs.readdirSync(skillDir, { withFileTypes: true })
                files = entries.map((entry) => ({
                  is_dir: entry.isDirectory(),
                  name: entry.name,
                  path: entry.name,
                }))
              }
            } catch {
              // fallback
            }
          }

          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify({ content, files, name: skillName, path: skillMdPath }))
        })

        server.middlewares.use('/api/v1/system/harness_metrics', (_req, res) => {
          const metricsPath = path.join(os.homedir(), '.openviking', 'harness_metrics.json')
          let metrics: Record<string, any> = {
            actor_peers: { antigravity: 2, openclaw: 2 },
            find_calls: 2,
            lessons_count: 2,
            most_evolved_skill: 'openviking-studio-dev',
            store_calls: 2,
            total_calls: 4,
          }
          try {
            if (fs.existsSync(metricsPath)) {
              metrics = JSON.parse(fs.readFileSync(metricsPath, 'utf-8'))
            }

            const skillMdPath = '/home/skloxo/aho/openclaw/project/OpenVikingStudio/.agents/skills/openviking-studio-dev/SKILL.md'
            if (fs.existsSync(skillMdPath)) {
              const content = fs.readFileSync(skillMdPath, 'utf-8')
              const chunks = content.split('#### 📌 Lesson ')
              const lessons_detail: Array<{ id: number; title: string; context: string; reflection: string; lesson: string }> = []
              
              chunks.slice(1).forEach((chunk) => {
                const lines = chunk.split('\n')
                const headerLine = lines[0] || ''
                const titleMatch = headerLine.match(/#(\d+)：(.+)/)
                const id = titleMatch ? Number(titleMatch[1]) : lessons_detail.length + 1
                const title = titleMatch ? titleMatch[2].trim() : headerLine.trim()

                let context = ''
                let reflection = ''
                let lesson = ''

                lines.forEach((line) => {
                  if (line.includes('**CONTEXT**：')) context = line.split('**CONTEXT**：')[1].trim()
                  if (line.includes('**REFLECTION**：')) reflection = line.split('**REFLECTION**：')[1].trim()
                  if (line.includes('**LESSON**：')) lesson = line.split('**LESSON**：')[1].trim()
                })

                if (title) {
                  lessons_detail.push({ id, title, context, reflection, lesson })
                }
              })
              metrics.lessons_detail = lessons_detail
            }
          } catch {
            // fallback
          }
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify(metrics))
        })
      },
    },
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
