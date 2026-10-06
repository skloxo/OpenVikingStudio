/**
 * OpenViking Native Cordis Hook Plugin for DeepSeek Harness (DSH).
 * Pure Node.js ESM - Zero external dependencies.
 * 
 * Capabilities:
 * 1. Pre-Invocation Memory Injection: Intercepts user prompt assembly and injects OpenViking memories directly into ctx.systemPrompt.
 * 2. Post-Turn Harvesting: Observes completed assistant messages via session events.
 */

import { appendFileSync } from 'node:fs'
import { resolve } from 'node:path'

export const name = 'dsh-plugin-openviking'
export const inject = ['systemPrompt']

const STEP_WORDS = new Set([
  'continue', 'ok', 'g', 'go', 'y', 'n', 'yes', 'no',
  '好的', '继续', '收到', '?', '？', '.', '。', ',', '，', '!', '！'
])

let lastQuery = ''
let lastInjectedMemory = ''
let lastFetchTime = 0
const CACHE_TTL_MS = 60_000

function log(msg) {
  try {
    const home = process.env.USERPROFILE || process.env.HOME || 'C:\\Users\\Skl'
    const logPath = resolve(home, '.dsh', 'openviking-hook.log')
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

export function apply(ctx, config = {}) {
  const api = config.api || process.env.OPENVIKING_API || 'http://127.0.0.1:1933'
  const key = config.key || process.env.OPENVIKING_API_KEY || ''
  const peer = config.peer || process.env.OPENVIKING_ACTOR_PEER || 'deepseek-harness@2080ti'

  log(`[INIT] OpenViking DSH Native Hook plugin activated (peer=${peer}, api=${api})`)

  // 1. 动态感知用户输入事件
  ctx.on('session/event', (event) => {
    try {
      if (event?.type === 'user/message') {
        const raw = event?.content || event?.text || ''
        const text = typeof raw === 'string' ? raw.trim() : (raw?.[0]?.text || '').trim()
        if (text && text.length >= 2 && !STEP_WORDS.has(text.toLowerCase())) {
          log(`[USER_MSG_DETECTED] "${text.slice(0, 50)}..."`)
          // 异步触发预热
          fetchMemory(api, key, peer, text).catch(() => {})
        }
      }
    } catch (_) {}
  })

  // 2. 注入 System Prompt 动态上下文（在模型组装 Prompt 阶段无感注入）
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

apply.inject = ['systemPrompt']
