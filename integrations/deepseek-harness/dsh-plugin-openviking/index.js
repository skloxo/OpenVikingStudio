/**
 * OpenViking Native Cordis Universal RPC Bridge & Hook Plugin for DeepSeek Harness (DSH).
 * Pure Node.js ESM - Compliant with official DSH Schemastery & Cordis specs.
 * 
 * First Principles:
 * - Centralized Quad-Plugins: Memory (47), Search (12), Vault (8) run centrally on OpenViking (1933 / vk.tide.red).
 * - Agent locally installs ONLY this lightweight RPC bridge + Interfacing Hook.
 * - Dynamic Capability Projection: Streamable-HTTP proxy with Auth header & volatile hot-reload.
 */

import { appendFileSync, statSync, renameSync, existsSync, readFileSync, copyFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

export const name = 'dsh-plugin-openviking'
export const inject = ['agents', 'sessions', 'tools', 'systemPrompt']

import Schema from './schema.js'

// 🛡️ 防御性 volatile 修饰包装器
function v(s) {
  return typeof s?.volatile === 'function' ? s.volatile() : s
}

// 遵循 DSH 官方规范：标记为 .volatile() 的字段会被 SettingsForm 投影到 GUI 表单中
export const Config = Schema ? Schema.object({
  endpointUrl: v(Schema.string().default('https://vk.tide.red/mcp')).description('OpenViking 通信端点 URL (公网默认 https://vk.tide.red/mcp，本地开发可填 http://127.0.0.1:1933/mcp)'),
  apiUrl: v(Schema.string().default('')).description('【兼容别名】服务端 HTTP 端点 (建议留空，自动由 endpointUrl 推导)'),
  agentId: v(Schema.string().default('deepseek-harness@satellite')).description('智能体工兵 ID (在 OpenViking 智能体中心复制，如 deepseek-harness@satellite 或 ag_xxx)'),
  userKey: v(Schema.string().role('secret').default('')).description('所属用户 API Key / User Key (在 HTTP Header 中安全传递，带密码遮罩)'),
  apiKey: v(Schema.string().role('secret').default('')).description('【兼容别名】用户 API Key (同 userKey)'),
  userKeyEnv: v(Schema.string().default('OPENVIKING_USER_KEY')).description('从 DSH 凭据库 (.credentials.yaml) 或环境变量中引用的 Key 变量名'),
  apiKeyEnv: v(Schema.string().default('OPENVIKING_API_KEY')).description('【兼容别名】引用的环境变量 Key 名称'),
  userId: v(Schema.string().default('default')).description('租户 / 账户身份标识 (默认 default)'),
  enableMcp: v(Schema.boolean().default(true)).description('是否挂载体外 MCP 工具箱 (开启后通过 RPC 动态投影服务端全部授权工具)'),
  enableHook: v(Schema.boolean().default(true)).description('是否启用前置记忆感知 Hook (自动在 Prompt 组装时感知并注入先验事实)'),
  peer: v(Schema.string().default('deepseek-harness@satellite')).description('调用方节点标识 (用于服务端审计日志与调用链追踪)')
}).description('OpenViking 通用轻量 RPC 桥梁与 Hook 套件配置') : undefined

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


// 🛡️ 智能 Query 轻量脱水：剔除客套前缀与口头禅，保留纯技术词；若脱水后过短则安全回退原句
function dehydrateQuery(query) {
  if (!query) return ''
  let q = query.trim()
  const patterns = [
    /^(请问|请教一下|请详细告诉我|请问一下|请告诉我|麻烦问一下|帮我查一下|查一下|查找|检索)/i,
    /^(在|从)?(体外大脑|知识库|wiki|OpenViking)(中)?(记录的|里)?/i,
    /^(根据|基于)(体外大脑|知识库|wiki|OpenViking)(的)?(记录|内容)?/i
  ]
  let changed = true
  while (changed) {
    changed = false
    for (const p of patterns) {
      if (p.test(q)) {
        q = q.replace(p, '').trim()
        changed = true
      }
    }
  }
  // 剥离句尾常见套话
  q = q.replace(/(是什么[？?]?|有哪些[？?]?|请详细说明[。！!]?|的具体实现[？?]?|的设计与实现是什么[？?]?)$/i, '').trim()
  // 安全兜底：若脱水后长度过短（小于 2 字），回退原输入，绝不丢词
  return q.length >= 2 ? q : query.trim()
}

async function fetchMemory(api, key, peer, agentId, query) {
  try {
    const cleanQuery = dehydrateQuery(query)
    const now = Date.now()
    if (cleanQuery === lastQuery && (now - lastFetchTime) < CACHE_TTL_MS && lastInjectedMemory) {
      log(`[CACHE_HIT] reusing prefetch for "${cleanQuery.slice(0, 30)}..."`)
      return lastInjectedMemory
    }

    const url = `${api.replace(/\/+$/, '')}/api/v1/search/find`
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 4000)

    const headers = {
      'Content-Type': 'application/json',
      'X-Agent-ID': agentId,
      'X-OpenViking-Actor-Peer': peer,
      'X-Caller': peer,
      'X-OpenViking-Account': 'default'
    }
    if (key) {
      headers['Authorization'] = `Bearer ${key}`
    }

    // 判断用户是否明确查询历史会话
    const isArchiveQuery = /(历史|归档|上次|之前|会话|session)/i.test(query)
    const reqBody = {
      query: cleanQuery.slice(0, 300),
      limit: 6,
      mode: 'fast'
    }
    // 保护：日常技术提问显式声明只搜 resource，彻底杜绝 archived_sessions 虚拟省略号假路径
    if (!isArchiveQuery) {
      reqBody.context_type = 'resource'
    }

    log(`[FETCH] querying ${url} for "${cleanQuery.slice(0, 40)}..." (context_type=${reqBody.context_type || 'all'})`)
    const res = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(reqBody),
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

    // 智能去噪：若非明确询问历史会话/归档，过滤掉会话归档噪音与虚拟路径
    let filteredItems = items
    if (!isArchiveQuery) {
      const docItems = items.filter(it => {
        const u = it?.uri || ''
        return !u.includes('archived_sessions') && !u.includes('staging/') && !u.includes('...')
      })
      if (docItems.length > 0) {
        filteredItems = docItems
      }
    }

    const lines = [`【OpenViking 核心记忆预取 (${peer})】`]
    const topItems = filteredItems.slice(0, 2)

    // 并发读取 L2 完整正文，单篇截断不超过 2000 字符（约 100 行），防止 Token 溢出
    const readPromises = topItems.map(async (item) => {
      const uri = item?.uri || ''
      if (!uri || uri.includes('...')) return ''
      try {
        const readUrl = `${api.replace(/\/+$/, '')}/api/v1/content/read?uri=${encodeURIComponent(uri)}`
        const r = await fetch(readUrl, { headers, signal: AbortSignal.timeout(2000) })
        if (r.ok) {
          const j = await r.json()
          const raw = typeof j.result === 'string' ? j.result : (j.result?.content || j.result?.text || '')
          if (raw && raw.trim()) {
            const trimmed = raw.trim()
            const truncated = trimmed.length > 2000 ? trimmed.slice(0, 2000) + '\n...(已安全截断)' : trimmed
            return `- [${uri}]:\n${truncated}`
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

    lines.push('💡 协同契约：体外大脑知识库先验记忆已在上方为您预取完毕！请直接吸收并基于此回答，无需重复发起搜索或检索工具调用；若某条资源读取返回 File not found，说明该资源属于内部归档或已被合并，严禁循环发起超过 2 次工具调用，应立即基于上方已有事实向用户直接作答。')
    const finalMemory = lines.join('\n\n')

    lastQuery = cleanQuery
    lastInjectedMemory = finalMemory
    lastFetchTime = Date.now()

    log(`[PREFETCH_SUCCESS] retrieved ${readResults.length} items for "${cleanQuery.slice(0, 30)}..."`)
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

const MEMORY_KEYWORDS = [
  '体外大脑', 'openviking', 'wiki', '记忆', '知识库', 'paperclip',
  '架构', '方案', '规范', '密码', 'keepass', '凭据', 'token',
  '查一下', '检索', '历史记录', '之前说的', '上次提到', '项目设计'
]

function isMemoryIntent(text) {
  if (!text) return false
  const t = text.trim()
  if (t.length < 3) return false
  if (/^(\d+\s*[\+\-\*\/]\d+|hi|hello|你好|在吗|ok|好的|收到|测试|test)$/i.test(t)) {
    return false
  }
  const lower = t.toLowerCase()
  return MEMORY_KEYWORDS.some(k => lower.includes(k))
}

export function apply(ctx, config = {}) {
  const getEndpoint = () => {
    return getVal(
      config.endpointUrl,
      getVal(config.apiUrl, getVal(config.api, process.env.OPENVIKING_ENDPOINT || process.env.OPENVIKING_API || 'http://127.0.0.1:1933/mcp'))
    )
  }

  // 基础 API 地址 (用于 /api/v1/search/find 记忆预取)
  const getBaseApi = () => {
    let ep = getEndpoint().trim()
    ep = ep.replace(/\/mcp\/?$/i, '')
    ep = ep.replace(/\/+$/, '')
    return ep || 'http://127.0.0.1:1933'
  }

  // MCP 端点 (用于 streamable-http 挂载)
  const getMcpBaseUrl = () => {
    let ep = getEndpoint().trim()
    if (!ep.endsWith('/mcp')) {
      ep = `${ep.replace(/\/+$/, '')}/mcp`
    }
    return ep
  }

  const getKey = () => {
    const raw = getVal(config.userKey, getVal(config.apiKey, getVal(config.key, '')))
    if (raw) return raw
    const envNames = [
      getVal(config.userKeyEnv, 'OPENVIKING_USER_KEY'),
      getVal(config.apiKeyEnv, 'OPENVIKING_API_KEY'),
      'OPENVIKING_USER_KEY',
      'OPENVIKING_API_KEY'
    ]
    for (const name of envNames) {
      if (name && process.env[name]) return process.env[name]
    }
    // 🛡️ 官方 DSH 标准：从 ~/.dsh/.credentials.yaml 自动读取 refs 凭据
    try {
      const home = process.env.USERPROFILE || process.env.HOME || 'C:\\Users\\Skl'
      const credPath = resolve(home, '.dsh', '.credentials.yaml')
      if (existsSync(credPath)) {
        const text = readFileSync(credPath, 'utf8')
        for (const name of envNames) {
          if (!name) continue
          const regex = new RegExp(`^\\s*${name}:\\s*([^\\s\\r\\n]+)`, 'm')
          const m = text.match(regex)
          if (m) return m[1]
        }
      }
    } catch (_) {}
    return ''
  }

  const getPeer = () => getVal(config.peer, process.env.OPENVIKING_ACTOR_PEER || 'deepseek-harness@satellite')
  const getAccountId = () => getVal(config.accountId, getVal(config.account, process.env.OPENVIKING_ACCOUNT || 'default'))
  const getUserId = () => getVal(config.userId, 'default')
  const getAgentId = () => getVal(config.agentId, process.env.OPENVIKING_AGENT_ID || 'deepseek-harness@satellite')
  const getEnableHook = () => getVal(config.enableHook, true) !== false
  const getEnableMcp = () => getVal(config.enableMcp, true) !== false

  log(`[INIT] OpenViking DSH Plugin activated (peer=${getPeer()}, endpoint=${getEndpoint()}, agentId=${getAgentId() || 'none'}, hook=${getEnableHook()}, mcp=${getEnableMcp()})`)

  let currentMcpFork = null
  let lastMcpSignature = ''

  async function mountMcpIfNeeded() {
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
      const mcpBase = getMcpBaseUrl()
      const userId = getUserId()
      const key = getKey()
      const mcpUrl = `${mcpBase}?agent_id=${encodeURIComponent(agentId)}&user_id=${encodeURIComponent(userId)}`
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

      const proxyPath = fileURLToPath(new URL('./servers/mcp-proxy.mjs', import.meta.url))
      log(`[MCP_MOUNT] mounting @deepseek-ai/dsh-mcp-client via stdio proxy (${proxyPath}) targeting ${mcpBase}`)

      let mcpPlugin = null
      try {
        const mod = await import('@deepseek-ai/dsh-mcp-client')
        mcpPlugin = mod?.default || mod
      } catch (_) {
        if (typeof ctx.loader?.resolve === 'function') {
          try { mcpPlugin = ctx.loader.resolve('@deepseek-ai/dsh-mcp-client') } catch (_) {}
        }
      }

      if (mcpPlugin && typeof ctx.plugin === 'function') {
        const homeDir = process.env.USERPROFILE || process.env.HOME || 'C:\\Users\\Skl'
        const childEnv = {
          ...process.env,
          ELECTRON_RUN_AS_NODE: '1',
          OPENVIKING_URL: mcpBase,
          OPENVIKING_MCP_URL: mcpBase,
          OPENVIKING_PEER_ID: getPeer(),
          OV_DEBUG_LOG: resolve(homeDir, '.dsh', 'mcp-proxy-debug.log')
        }
        if (key) childEnv.OPENVIKING_API_KEY = key
        childEnv.OPENVIKING_ACCOUNT = getAccountId()
        childEnv.OPENVIKING_USER = getUserId()

        currentMcpFork = ctx.plugin(mcpPlugin, {
          serverName: 'openviking',
          transport: 'stdio',
          command: process.execPath,
          args: [proxyPath],
          env: childEnv,
          toolCallTimeoutMs: 60000,
          failOnStartupError: false,
          reconnect: {
            enabled: true,
            initialDelayMs: 500,
            maxDelayMs: 15000,
            maxAttempts: 10
          }
        })
        lastMcpSignature = signature
        log(`[MCP_MOUNT_SUCCESS] @deepseek-ai/dsh-mcp-client mounted successfully via stdio proxy`)
      } else {
        log('[MCP_MOUNT_INFO] dynamic import skipped; bundle patch handles mcp client registration')
      }
    } catch (err) {
      log(`[MCP_MOUNT_WARN] failed to mount mcp client dynamically: ${err?.stack || err?.message || err}`)
    }
  }

  // 1. 尝试初始挂载 MCP
  mountMcpIfNeeded().catch(() => {})

  // 2. 监听 volatile 配置动态热更新（用户在 DSH GUI 点击【保存】时触发，零重启热生效）
  ctx.on('loader/volatile-update', () => {
    log(`[VOLATILE_UPDATE] GUI settings saved, reloading dynamic config (agentId=${getAgentId() || 'none'})`)
    mountMcpIfNeeded().catch(() => {})
  })

  // 3. 被动先验 Hook：动态感知用户输入事件
  if (getEnableHook()) {
    ctx.on('session/event', (event) => {
      try {
        if (!getEnableHook()) return
        if (event?.type === 'user/message') {
          const raw = event?.content || event?.text || ''
          const text = typeof raw === 'string' ? raw.trim() : (raw?.[0]?.text || '').trim()
          if (isMemoryIntent(text)) {
            log(`[USER_MSG_DETECTED] memory intent detected: "${text.slice(0, 50)}..."`)
            // 异步触发预热
            fetchMemory(getBaseApi(), getKey(), getPeer(), getAgentId(), text).catch(() => {})
          }
        }
      } catch (_) {}
    })

    // 🛡️ 官方 agent/pre-step 瀑布流拦截器：在当前 step 发起前同步预热记忆并注入 SystemPrompt
    // ⚠️ 铁律：绝对禁止篡改 user messages 数组！用户消息气泡必须 100% 保持人类原始输入！
    ctx.on('agent/pre-step', async ({ agent, messages, signal }, next) => {
      try {
        const msgs = messages || []
        const lastUserMsg = [...msgs].reverse().find(m => {
          if (m.role !== 'user' && m.type !== 'user/message') return false
          const c = m.content
          const t = typeof c === 'string' ? c : (Array.isArray(c) ? c.map(p => p.text || '').join(' ') : '')
          const s = t.trim()
          if (!s || s.startsWith('Current runtime context') || s.startsWith('Time sampled while') || s.startsWith('【OpenViking')) return false
          return true
        })
        const rawContent = lastUserMsg?.content
        const rawText = typeof rawContent === 'string'
          ? rawContent
          : (Array.isArray(rawContent) ? rawContent.map(c => c.text || '').join(' ') : '')
        const query = rawText.trim()

        if (isMemoryIntent(query)) {
          log(`[PRE_STEP_QUERY] fetching memory for intent "${query.slice(0, 40)}..."`)
          const mem = await fetchMemory(getBaseApi(), getKey(), getPeer(), getAgentId(), query)
          if (mem && mem.trim() && !signal?.aborted) {
            log(`[PRE_STEP_INJECT] appending hidden runtime-context snapshot (${mem.length} chars)`)
            lastInjectedMemory = mem

            // 构造合法的 DSH 原生 runtime-context 隐式快照 (UI 界面对人类 100% 隐藏，对模型完全可见)
            const contextMsg = {
              role: 'user',
              content: [
                {
                  type: 'text',
                  text: `Current runtime context. This snapshot supersedes earlier runtime-context snapshots.\n\n${mem}`
                }
              ],
              source: {
                kind: 'runtime-context',
                form: 'snapshot',
                sections: [
                  {
                    name: 'openviking-memory-prefetch',
                    text: mem
                  }
                ]
              }
            }
            return {
              kind: 'enter',
              messages: [...msgs, contextMsg]
            }
          }
        } else {
          // 非记忆意图直接清空上下文，杜绝残留污染后续轮次
          lastInjectedMemory = ''
        }
      } catch (err) {
        log(`[PRE_STEP_WARN] ${err.message}`)
      }
      return next()
    }, { prepend: true })

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
        log('[INJECTOR_READY] ctx.systemPrompt.context (openviking-memory-prefetch) registered successfully')

        // 4. 注入系统级智能工具路由指南 (无论是否有预取记忆，始终引导模型优先使用 OpenViking 核心套件)
        ctx.systemPrompt.context({
          name: 'openviking-routing-guide',
          order: 15,
          text: () => [
            '【OpenViking 体外大脑长程记忆导轨】',
            '1. 核心长程记忆与知识库：【体外大脑 (OpenViking)】运行于服务端，绝非本地磁盘工作区文件！严禁调用 pwsh、cmd 或 glob 在本地翻找体外大脑。当用户询问体外大脑、历史方案或架构设计时，若上方预取不足，第一跳请调用 `mcp__openviking__find` 检索，该工具已默认附带核心文档正文，搜完请直接基于内联正文向用户作答，无需再调用 read 工具。',
            '2. 正交解耦规范：联网搜索已解耦至专用 Search Gateway；凭据管理已解耦至专用 KeePass Vault。OpenViking 专职提供高可靠长程记忆与知识检索支撑。'
          ].join('\n')
        })
        log('[ROUTING_GUIDE_READY] ctx.systemPrompt.context (openviking-routing-guide) registered successfully')
      } catch (e) {
        log(`[INJECTOR_WARN] could not register systemPrompt context: ${e.message}`)
      }
    }
  }

  // 🛡️ 进程内工具执行前置守卫 (In-Process Tool Pre-Execute Guard)
  // 遵循官方规范：零侵入宿主配置，静默拦截并纠偏越界调用
  try {
    ctx.on('tools/pre-execute', async (exec, next) => {
      try {
        // 1. 守卫官方收费/空壳搜索：一旦模型触发官方 web_search，直接纠偏拦截，防止扣费与 403 崩溃
        if (exec.name === 'web_search' || exec.name === 'tool-web') {
          log(`[GUARD_SEARCH] intercepted official search call: "${JSON.stringify(exec.arguments)}"`)
          return {
            kind: 'deny',
            reason: 'DeepSeek Harness 官方 web_search 未配置或需要额外计费。请改用 OpenViking 免费多云聚合搜索工具：mcp__openviking__web_search(query="...") 或 mcp__openviking__search_deep。'
          }
        }

        // 3. 守卫虚拟 URI (移植官方 uri-guard 智慧)：模型试图用本地文件工具读写 viking:// 时拦截纠偏
        const FILE_TOOLS = ['read', 'write', 'edit', 'glob', 'grep', 'str_replace_editor', 'bash']
        if (FILE_TOOLS.includes(exec.name)) {
          const argsStr = JSON.stringify(exec.arguments || {})
          if (argsStr.includes('viking://')) {
            const pathVal = String(exec.arguments?.file_path || exec.arguments?.path || exec.arguments?.command || '')
            if (pathVal.includes('viking://')) {
              const match = pathVal.match(/viking:\/\/[^\s"'`\\)]+/i)
              const uri = match ? match[0] : 'viking://'
              log(`[GUARD_URI] intercepted virtual URI on local tool ${exec.name}: ${uri}`)
              return {
                kind: 'deny',
                reason: `viking:// 属于 OpenViking 体外大脑的虚拟资源路径，非宿主机本地文件系统路径。请改用 mcp__openviking__read(uri="${uri}") 或 mcp__openviking__search 查询。`
              }
            }
          }
        }
      } catch (err) {
        log(`[GUARD_ERROR] guard pre-execute failed: ${err.message}`)
      }
      return next()
    })
    log('[GUARD_READY] tools/pre-execute search & uri guards registered successfully')
  } catch (err) {
    log(`[GUARD_WARN] failed to register tools/pre-execute guard: ${err.message}`)
  }
}

apply.inject = ['systemPrompt', 'tools']
