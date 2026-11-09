/**
 * Tududi Task Manager Cordis RPC Bridge for DeepSeek Harness (DSH).
 * Pure Node.js ESM - Compliant with official DSH Schemastery & Cordis specs.
 *
 * First Principles:
 * 1. Dual-Link Failover: Tries public HTTPS URL (todo.tide.red), seamlessly falls back to LAN IP (10.128.226.5).
 * 2. 65 FastMCP Tools: Full spectrum OKR+GTD capability for DSH agents.
 * 3. Zero-Crash Output: output.render strictly returns array of ContentBlock objects.
 * 4. SystemPrompt Context Injection: Automatically injects OKR+GTD 5-layer & parameter contract guardrails.
 */

import { readFileSync, existsSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { homedir } from 'node:os'
import Schema from './schema.js'

export const name = 'dsh-plugin-tududi'
export const inject = ['agents', 'tools', 'systemPrompt']

const PKG_NAME = 'dsh-plugin-tududi'
const SHORT_NAME = 'tududi'
const __dir = dirname(fileURLToPath(import.meta.url))
const TOOLS_JSON_PATH = resolve(__dir, 'tools.json')

function v(s) {
  return typeof s?.volatile === 'function' ? s.volatile() : s
}

export const Config = Schema ? Schema.object({
  endpointUrl: v(Schema.string().default('https://todo.tide.red/api/mcp')).description('Tududi 公网 MCP 服务端点'),
  internalUrl: v(Schema.string().default('http://10.128.226.5:3002/api/mcp')).description('Tududi 局域网备用端点'),
  apiToken: v(Schema.string().role('secret').default('')).description('Tududi API Token (Bearer)'),
  enableMcp: v(Schema.boolean().default(true)).description('是否挂载 65 项 Tududi MCP 工具箱')
}).description('Tududi 全域任务管理与 OKR+GTD 生产力中枢配置') : undefined

if (Config && !Config['~standard']) {
  Config['~standard'] = {
    version: 1,
    vendor: 'schemastery-fallback',
    validate: (val) => ({ value: val })
  }
}

function getDshDir() {
  const home = process.env.USERPROFILE || process.env.HOME || homedir()
  return resolve(home, '.dsh')
}

function readUiSavedConfig() {
  try {
    const p = resolve(getDshDir(), 'openviking-plugins-config.json')
    if (existsSync(p)) {
      const all = JSON.parse(readFileSync(p, 'utf8'))
      return all[PKG_NAME] || all[SHORT_NAME] || {}
    }
  } catch (_) {}
  return {}
}

function getVal(val, fallback = '') {
  if (val === undefined || val === null) return fallback
  if (typeof val?.get === 'function') {
    const vRes = val.get()
    return (vRes !== undefined && vRes !== null && vRes !== '') ? String(vRes).trim() : fallback
  }
  return String(val).trim() || fallback
}

function resolveToken(cfg) {
  const ui = readUiSavedConfig()
  const direct = getVal(cfg?.apiToken, '') || getVal(cfg?.userKey, '') || ui.apiToken || ui.userKey || ''
  if (direct) return direct
  if (process.env.TUDUDI_API_TOKEN) return process.env.TUDUDI_API_TOKEN
  const localCfgPath = resolve(homedir(), '.gemini/config/plugins/tududi/config.json')
  if (existsSync(localCfgPath)) {
    try {
      const data = JSON.parse(readFileSync(localCfgPath, 'utf8'))
      return data.api_token || ''
    } catch (_) {}
  }
  return ''
}

function resolveUrls(cfg) {
  const ui = readUiSavedConfig()
  const pub = getVal(cfg?.endpointUrl, '') || ui.endpointUrl || 'https://todo.tide.red/api/mcp'
  const lan = getVal(cfg?.internalUrl, '') || ui.internalUrl || 'http://10.128.226.5:3002/api/mcp'
  return [pub, lan]
}

async function callTududiMcp(targetUrls, token, toolName, args, timeoutMs = 15000) {
  let lastErr = null
  for (const url of targetUrls) {
    if (!url) continue
    try {
      const controller = new AbortController()
      const timer = setTimeout(() => controller.abort(), timeoutMs)
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Accept': 'application/json, text/event-stream'
        },
        body: JSON.stringify({
          jsonrpc: '2.0',
          id: Date.now(),
          method: 'tools/call',
          params: {
            name: toolName,
            arguments: args || {}
          }
        }),
        signal: controller.signal
      })
      clearTimeout(timer)

      if (!res.ok) {
        lastErr = new Error(`HTTP ${res.status}: ${res.statusText}`)
        continue
      }

      const text = await res.text()
      for (const line of text.trim().split('\n')) {
        if (line.startsWith('data: ')) {
          const parsed = JSON.parse(line.slice(6))
          if (parsed.result?.content?.[0]?.text) {
            return parsed.result.content[0].text
          }
          return JSON.stringify(parsed.result || parsed, null, 2)
        }
      }
      if (text.startsWith('{')) return text
    } catch (err) {
      lastErr = err
    }
  }
  return JSON.stringify({ error: `Tududi call failed across all endpoints: ${lastErr?.message || lastErr}` })
}

const OUT_SPEC = {
  schema: { type: 'string' },
  render: (_args, value) => [{
    type: 'text',
    text: typeof value === 'string' ? value : JSON.stringify(value ?? '', null, 2)
  }]
}

export function apply(ctx, config = {}) {
  if (ctx.systemPrompt) {
    try {
      ctx.systemPrompt.context({
        name: 'tududi-okr-gtd-guide',
        order: 15,
        text: () => [
          '【Tududi (todo) 全域任务管理与 OKR+GTD 生产力中枢导轨】',
          '1. 五层标准映射：L1 Area (工作 id=6 / 个人 id=7) ➔ L2 Goal (O1~O4) ➔ L3 Project (承接核心KR载体) ➔ L4 Tag (规划/开发/运维/汇报/缺陷) ➔ L5 Task/Subtask。',
          '2. 主键与枚举契约：Task 主键参数名为 id (priority 为 "none"|"low"|"medium"|"high")；其余实体 (Project/Goal/Area/Habit/Inbox/Note/Tag) 主键参数名一律为 uid (Project priority 为 0|1|2)；status 禁传 "todo"。',
          '3. 完工双行汇报锚点：调用 complete_task 前必须先在 note 写入 【达成成果】 与 【解决挑战】。'
        ].join('\n')
      })
    } catch (_) {}
  }

  let toolsList = []
  if (existsSync(TOOLS_JSON_PATH)) {
    try {
      toolsList = JSON.parse(readFileSync(TOOLS_JSON_PATH, 'utf8'))
    } catch (_) {}
  }

  const toDshParameterSpec = (rawParams) => {
    if (!rawParams || typeof rawParams !== 'object') return {}
    const rawProps = (rawParams.type === 'object' && rawParams.properties) ? rawParams.properties : rawParams
    const reqSet = new Set(Array.isArray(rawParams.required) ? rawParams.required : [])
    const spec = {}
    for (const [k, v] of Object.entries(rawProps)) {
      if (!v || typeof v !== 'object') continue
      const prop = { ...v }
      if (Array.isArray(prop.type)) {
        const nonNull = prop.type.filter((x) => x !== 'null')
        prop.type = nonNull.includes('string') ? 'string' : (nonNull[0] || 'string')
      }
      if (reqSet.has(k) || prop.required === true) {
        prop.required = true
      } else {
        delete prop.required
      }
      spec[k] = prop
    }
    return spec
  }

  const toStandardJsonSchema = (params) => {
    const spec = toDshParameterSpec(params)
    const properties = {}
    const required = []
    for (const [k, v] of Object.entries(spec)) {
      properties[k] = { ...v }
      if (properties[k].required === true) {
        required.push(k)
        delete properties[k].required
      }
    }
    return { type: 'object', properties, ...(required.length > 0 ? { required } : {}) }
  }

  const wrapTool = (def, defineToolFn) => {
    const presentCall = (args) => ({
      card: 'generic',
      kind: def.name.startsWith('list_') || def.name.startsWith('get_') || def.name === 'search' ? 'read' : 'other',
      title: def.description || def.name,
      rawInput: args
    })
    if (typeof defineToolFn === 'function') {
      return defineToolFn({
        ...def,
        parameters: toDshParameterSpec(def.parameters),
        output: OUT_SPEC,
        presentCall
      })
    }
    return {
      ...def,
      parameters: toStandardJsonSchema(def.parameters),
      output: OUT_SPEC,
      presentCall
    }
  }

  if (ctx.tools && typeof ctx.tools.register === 'function') {
    const registerAll = (defineToolFn) => {
      for (const toolDef of toolsList) {
        const toolName = toolDef.name
        ctx.tools.register(wrapTool({
          name: toolName,
          description: toolDef.description || toolName,
          parameters: toolDef.parameters || {},
          async execute(args) {
            return await callTududiMcp(resolveUrls(config), resolveToken(config), toolName, args)
          }
        }, defineToolFn))
      }
    }

    try {
      import('@deepseek-ai/dsh-tools').then((mod) => {
        const fn = mod?.defineTool || mod?.default?.defineTool
        registerAll(fn)
      }).catch(() => {
        registerAll(null)
      })
    } catch (_) {
      registerAll(null)
    }
  }
}

apply.inject = ['systemPrompt', 'tools']
