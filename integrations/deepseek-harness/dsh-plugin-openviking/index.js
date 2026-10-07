/**
 * OpenViking Native Cordis Hook & MCP Unified Plugin for DeepSeek Harness (DSH).
 * Pure Node.js ESM - Compliant with official DSH Schemastery & Cordis specs.
 * 
 * Capabilities:
 * 1. GUI Settings Form: Exposes Schemastery Config schema rendered directly in DSH settings.
 * 2. Pre-Invocation Memory Injection: Intercepts user prompt assembly and injects OpenViking memories into ctx.systemPrompt.
 * 3. Dynamic Streamable-HTTP MCP Mounting: Dynamically mounts @deepseek-ai/dsh-mcp-client with Authorization Header.
 */

import { appendFileSync, statSync, renameSync, existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

export const name = 'dsh-plugin-openviking'
export const inject = ['systemPrompt']

import Schema from './schema.js'

// 🛡️ 防御性 volatile 修饰包装器
function v(s) {
  return typeof s?.volatile === 'function' ? s.volatile() : s
}

// 遵循 DSH 官方规范：只有标记为 .volatile() 的字段才会被 SettingsForm 投影到 GUI 表单中
export const Config = Schema ? Schema.object({
  apiUrl: v(Schema.string().default('http://127.0.0.1:1933')).description('OpenViking 服务端端点 (如 http://127.0.0.1:1933 或 https://vk.tide.red)'),
  userId: v(Schema.string().default('default')).description('租户 / 账户身份标识 (默认 default)'),
  agentId: v(Schema.string().default('deepseek-harness@2080ti')).description('智能体工兵 ID (如 deepseek-harness@2080ti 或 ag_cd3c029d7ea4)'),
  apiKey: v(Schema.string().role('secret').default('')).description('用户的 API Key / User Key (在请求头中传递鉴权，带密码遮罩)'),
  apiKeyEnv: v(Schema.string().default('OPENVIKING_API_KEY')).description('从 DSH 凭据库 (.credentials.yaml) 或环境变量中引用的 Key 名称 (默认 OPENVIKING_API_KEY)'),
  enableMcp: v(Schema.boolean().default(true)).description('是否挂载体外 MCP 工具箱 (开启后自动向模型提供 47 项体外大脑工具)'),
  enableHook: v(Schema.boolean().default(true)).description('是否启用前置记忆感知 Hook (自动在 Prompt 组装时感知并注入上下文)'),
  peer: v(Schema.string().default('deepseek-harness@2080ti')).description('调用方节点名称标识 (用于审计日志与调用链追踪)')
}).description('OpenViking 体外大脑一体化套件配置') : undefined

const STEP_WORDS = new Set([
  'continue', 'ok', 'g', 'go', 'y', 'n', 'yes', 'no',
  '好的', '继续', '收到', '?', '？', '.', '。', ',', '，', '!', '！'
])

let lastQuery = ''
let lastInjectedMemory = ''
let lastFetchTime = 0
const CACHE_TTL_MS = 60_000

// 🛡️ 生产级日志防爆与轻量滚动保护 (2MB 硬上限，双文件滚动)
const MAX_LOG_BYTES = 2 * 1024 * 1024
let writeCount = 0

function log(msg) {
  try {
    const home = process.env.USERPROFILE || process.env.HOME || 'C:\\Users\\Skl'
    const logPath = resolve(home, '.dsh', 'openviking-hook.log')

    if (++writeCount % 50 === 0 && existsSync(logPath)) {
      if (statSync(logPath).size > MAX_LOG_BYTES) {
        const oldPath = resolve(home, '.dsh', 'openviking-hook.log.old')
        renameSync(logPath, oldPath)
      }
    }

    const line = `[${new Date().toISOString()}] ${msg}\n`
    appendFileSync(logPath, line, 'utf8')
  } catch (_) {}
}

async function fetchMemory(api, key, peer, query) {
  try {
    const now = Date.now()
    if (query === lastQuery && (now - lastFetchTime) < CACHE_TTL_MS && lastInjectedMemory) {
      log(`[CACHE_HIT] reusing prefetch for "${query.slice(0, 30)}..."`)
      return lastInjectedMemory
    }

    const url = `${api.replace(/\/+$/, '')}/api/v1/search/find`
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 4000)

    const headers = {
      'Content-Type': 'application/json',
      'X-OpenViking-Actor-Peer': peer,
      'X-Caller': peer
    }
    if (key) {
      headers['Authorization'] = `Bearer ${key}`
    }

    log(`[FETCH] querying ${url} for "${query.slice(0, 40)}..."`)
    const res = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        query: query.slice(0, 300),
        limit: 2,
        mode: 'fast'
      }),
      signal: controller.signal
    })
    clearTimeout(timer)

    if (!res.ok) {
      log(`[FETCH_FAIL] HTTP ${res.status}`)
      return ''
    }

    const json = await res.json()
    const result = json?.result
    const items = [
      ...(result?.memories || []),
      ...(result?.resources || []),
      ...(result?.skills || [])
    ]
    if (!items.length) {
      log('[FETCH_EMPTY] no memories found')
      return ''
    }

    const lines = [`【OpenViking 核心记忆预取 (${peer})】`]
    const topItems = items.slice(0, 2)

    // 并发读取 L2 完整正文
    const readPromises = topItems.map(async (item) => {
      const uri = item?.uri || ''
      if (!uri) return ''
      try {
        const readUrl = `${api.replace(/\/+$/, '')}/api/v1/content/read?uri=${encodeURIComponent(uri)}`
        const r = await fetch(readUrl, { headers, signal: AbortSignal.timeout(2000) })
        if (r.ok) {
          const j = await r.json()
          const raw = typeof j.result === 'string' ? j.result : (j.result?.content || j.result?.text || '')
          if (raw && raw.trim()) {
            return `- [${uri}]:\n${raw.trim().slice(0, 1500)}`
          }
        }
      } catch (_) {}
      const fallback = (item.abstract || item.content || '').trim().slice(0, 600)
      return `- [${uri}]: ${fallback}`
    })

    const readResults = await Promise.all(readPromises)
    for (const text of readResults) {
      if (text) lines.push(text)
    }

    lines.push('💡 协同契约：以上为体外大脑预取的先验记忆，请直接吸收并融入回答，无需机械复述。')
    const finalMemory = lines.join('\n\n')

    lastQuery = query
    lastInjectedMemory = finalMemory
    lastFetchTime = Date.now()

    log(`[PREFETCH_SUCCESS] retrieved ${readResults.length} items for "${query.slice(0, 30)}..."`)
    return finalMemory
  } catch (err) {
    log(`[FETCH_ERROR] ${err?.message || err}`)
    return ''
  }
}

function getVal(v, fallback = '') {
  if (v === undefined || v === null) return fallback
  if (typeof v?.get === 'function') {
    const val = v.get()
    return (val !== undefined && val !== null && val !== '') ? String(val).trim() : fallback
  }
  if (typeof v === 'string') {
    const trimmed = v.trim()
    return trimmed !== '' ? trimmed : fallback
  }
  return v
}

export function apply(ctx, config = {}) {
  const getApi = () => getVal(config.apiUrl || config.api, process.env.OPENVIKING_API || 'http://127.0.0.1:1933')
  const getKey = () => {
    const raw = getVal(config.apiKey || config.key)
    if (raw) return raw
    const envKeyName = getVal(config.apiKeyEnv, 'OPENVIKING_API_KEY')
    if (process.env[envKeyName]) return process.env[envKeyName]
    // 🛡️ 官方 DSH 标准：从 ~/.dsh/.credentials.yaml 自动读取 refs 凭据
    try {
      const home = process.env.USERPROFILE || process.env.HOME || 'C:\\Users\\Skl'
      const credPath = resolve(home, '.dsh', '.credentials.yaml')
      if (existsSync(credPath)) {
        const text = readFileSync(credPath, 'utf8')
        const regex = new RegExp(`^\\s*${envKeyName}:\\s*([^\\s\\r\\n]+)`, 'm')
        const m = text.match(regex)
        if (m) return m[1]
      }
    } catch (_) {}
    return ''
  }
  const getPeer = () => getVal(config.peer, process.env.OPENVIKING_ACTOR_PEER || 'deepseek-harness@2080ti')
  const getUserId = () => getVal(config.userId, 'default')
  const getAgentId = () => getVal(config.agentId, process.env.OPENVIKING_AGENT_ID || 'deepseek-harness@2080ti')
  const getEnableHook = () => getVal(config.enableHook, true) !== false
  const getEnableMcp = () => getVal(config.enableMcp, true) !== false

  log(`[INIT] OpenViking DSH Plugin activated (peer=${getPeer()}, api=${getApi()}, agentId=${getAgentId() || 'none'}, hook=${getEnableHook()}, mcp=${getEnableMcp()})`)

  let currentMcpFork = null
  let lastMcpSignature = ''

  function mountMcpIfNeeded() {
    const agentId = getAgentId()
    const enableMcp = getEnableMcp()

    if (!enableMcp || !agentId) {
      if (currentMcpFork) {
        log('[MCP_UNMOUNT] MCP disabled or agentId empty, disposing previous MCP fork')
        try { currentMcpFork.dispose() } catch (_) {}
        currentMcpFork = null
        lastMcpSignature = ''
      }
      return
    }

    try {
      const api = getApi()
      const userId = getUserId()
      const key = getKey()
      const mcpUrl = `${api.replace(/\/+$/, '')}/mcp?agent_id=${encodeURIComponent(agentId)}&user_id=${encodeURIComponent(userId)}`
      const signature = `${mcpUrl}#${key || 'nokey'}`

      if (currentMcpFork && signature === lastMcpSignature) {
        log(`[MCP_SKIP] MCP client already mounted with identical signature (${signature})`)
        return
      }

      if (currentMcpFork) {
        log(`[MCP_RELOAD] config changed, disposing previous MCP fork before remounting`)
        try { currentMcpFork.dispose() } catch (_) {}
        currentMcpFork = null
      }

      log(`[MCP_MOUNT] mounting @deepseek-ai/dsh-mcp-client at ${mcpUrl}`)
      
      const mcpHeaders = {
        'Accept': 'application/json, text/event-stream'
      }
      if (key) {
        mcpHeaders['Authorization'] = `Bearer ${key}`
      }
      
      currentMcpFork = ctx.plugin('@deepseek-ai/dsh-mcp-client', {
        serverName: 'openviking',
        transport: 'streamable-http',
        url: mcpUrl,
        headers: mcpHeaders,
        reconnect: {
          enabled: true,
          initialDelayMs: 500,
          maxDelayMs: 15000,
          maxAttempts: 10
        }
      })
      lastMcpSignature = signature
      log('[MCP_MOUNT_SUCCESS] @deepseek-ai/dsh-mcp-client mounted successfully')
    } catch (err) {
      log(`[MCP_MOUNT_WARN] failed to mount mcp client dynamically: ${err?.stack || err?.message || err}`)
    }
  }

  // 1. 尝试初始挂载 MCP
  mountMcpIfNeeded()

  // 2. 监听 volatile 配置动态热更新（用户在 DSH GUI 点击【保存】时触发，零重启热生效）
  ctx.on('loader/volatile-update', () => {
    log(`[VOLATILE_UPDATE] GUI settings saved, reloading dynamic config (agentId=${getAgentId() || 'none'})`)
    mountMcpIfNeeded()
  })

  // 3. 被动先验 Hook：动态感知用户输入事件
  if (getEnableHook()) {
    ctx.on('session/event', (event) => {
      try {
        if (!getEnableHook()) return
        if (event?.type === 'user/message') {
          const raw = event?.content || event?.text || ''
          const text = typeof raw === 'string' ? raw.trim() : (raw?.[0]?.text || '').trim()
          if (text && text.length >= 2 && !STEP_WORDS.has(text.toLowerCase())) {
            log(`[USER_MSG_DETECTED] "${text.slice(0, 50)}..."`)
            // 异步触发预热
            fetchMemory(getApi(), getKey(), getPeer(), text).catch(() => {})
          }
        }
      } catch (_) {}
    })

    // 3. 注入 System Prompt 动态上下文（在模型组装 Prompt 阶段无感注入）
    if (ctx.systemPrompt) {
      try {
        ctx.systemPrompt.context({
          name: 'openviking-memory-prefetch',
          order: 90,
          text: () => {
            if (lastInjectedMemory) {
              log(`[PROMPT_INJECT] injecting ${lastInjectedMemory.length} chars into SystemPrompt context`)
              return lastInjectedMemory
            }
            return ''
          }
        })
        log('[INJECTOR_READY] ctx.systemPrompt.context registered successfully')
      } catch (e) {
        log(`[INJECTOR_WARN] could not register systemPrompt context: ${e.message}`)
      }
    }
  }
}

apply.inject = ['systemPrompt']
