/**
 * dsh-plugin-openviking-memory
 * OpenViking 核心长程记忆与代码战地 - DeepSeek Harness (DSH) 独立 Cordis RPC 桥接器与 Hook 套件。
 * 遵循官方 DSH Schemastery & Cordis 规范，用户自主配置 Endpoint 与 UserKey，开箱即用。
 */

import { appendFileSync, existsSync, mkdirSync, readFileSync, writeFileSync, unlinkSync } from 'node:fs'
import { createServer } from 'node:http'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { homedir } from 'node:os'
import { resolveOpenVikingCredentials } from './shared/credentials.mjs'

const PKG_NAME = 'dsh-plugin-openviking-memory'
const TARGET_PLUGIN = 'openviking-memory'

function getDshDir() {
  const home = process.env.USERPROFILE || process.env.HOME || homedir()
  return resolve(home, '.dsh')
}

function getUiConfigStorePath() {
  return resolve(getDshDir(), 'openviking-plugins-config.json')
}

function readUiSavedConfig() {
  try {
    const p = getUiConfigStorePath()
    if (existsSync(p)) {
      const all = JSON.parse(readFileSync(p, 'utf8'))
      return all[PKG_NAME] || all[TARGET_PLUGIN] || {}
    }
  } catch (_) {}
  try {
    const localCfg = fileURLToPath(new URL('./config.json', import.meta.url))
    if (existsSync(localCfg)) {
      const c = JSON.parse(readFileSync(localCfg, 'utf8'))
      return {
        endpointUrl: c.endpointUrl || c.api_url || '',
        userKey: c.userKey || c.api_key || '',
        peer: c.peer || c.actor_peer || ''
      }
    }
  } catch (_) {}
  return {}
}

function ensureLocalConfigBridge(onConfigUpdated) {
  if (!globalThis.__ov_dsh_listeners__) {
    globalThis.__ov_dsh_listeners__ = new Set()
  }
  globalThis.__ov_dsh_listeners__.add(onConfigUpdated)

  if (!globalThis.__ov_dsh_config_server__) {
    try {
      const srv = createServer((req, res) => {
        res.setHeader('Access-Control-Allow-Origin', '*')
        res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS')
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type')
        if (req.method === 'OPTIONS') {
          res.writeHead(204)
          res.end()
          return
        }
        if (req.method === 'POST' && req.url === '/ov-dsh-config') {
          let body = ''
          req.on('data', chunk => { body += chunk })
          req.on('end', () => {
            try {
              const payload = JSON.parse(body || '{}')
              const storePath = getUiConfigStorePath()
              mkdirSync(dirname(storePath), { recursive: true })
              let existing = {}
              if (existsSync(storePath)) {
                try { existing = JSON.parse(readFileSync(storePath, 'utf8')) } catch (_) {}
              }
              if (payload.pluginId) existing[payload.pluginId] = payload.config || {}
              if (payload.shortName) existing[payload.shortName] = payload.config || {}
              writeFileSync(storePath, JSON.stringify(existing, null, 2), 'utf8')
              for (const fn of globalThis.__ov_dsh_listeners__ || []) {
                try { fn(payload) } catch (_) {}
              }
              res.writeHead(200, { 'Content-Type': 'application/json' })
              res.end(JSON.stringify({ ok: true }))
            } catch (err) {
              res.writeHead(400, { 'Content-Type': 'application/json' })
              res.end(JSON.stringify({ ok: false, error: String(err) }))
            }
          })
          return
        }
        res.writeHead(404)
        res.end()
      })
      srv.on('error', () => {})
      srv.listen(19339, '127.0.0.1', () => {
        try { srv.unref() } catch (_) {}
      })
      globalThis.__ov_dsh_config_server__ = srv
    } catch (_) {}
  }

  return () => {
    try {
      globalThis.__ov_dsh_listeners__?.delete(onConfigUpdated)
    } catch (_) {}
  }
}

function selfHealLegacyResidues() {
  try {
    const credPath = resolve(getDshDir(), '.credentials.yaml')
    if (existsSync(credPath)) {
      let content = readFileSync(credPath, 'utf8')
      const revokedPrefix = 'vk-sk-'
      if (content.includes('OPENVIKING_USER_KEY') && content.includes(revokedPrefix)) {
        content = content.replace(new RegExp(`^\\s*OPENVIKING_USER_KEY:.*${revokedPrefix}[a-zA-Z0-9_-]*.*\\r?\\n?`, 'gm'), '')
        content = content.replace(new RegExp(`^\\s*value:.*${revokedPrefix}[a-zA-Z0-9_-]*.*\\r?\\n?`, 'gm'), '')
        writeFileSync(credPath, content, 'utf8')
      }
    }
  } catch (_) {}
}

export const name = 'dsh-plugin-openviking-memory'
export const inject = ['agents', 'sessions', 'tools', 'systemPrompt']

import Schema from './schema.js'

function v(s) {
  return typeof s?.volatile === 'function' ? s.volatile() : s
}

export const Config = Schema ? Schema.object({
  endpointUrl: v(Schema.string().default('')).description('OpenViking 通信端点 URL (由用户自主填写)'),
  userKey: v(Schema.string().role('secret').default('')).description('所属用户 API Key / User Key (由用户自主填写)'),
  userKeyEnv: v(Schema.string().default('OPENVIKING_USER_KEY')).description('从环境变量中引用的 Key 变量名'),
  userId: v(Schema.string().default('')).description('可选显式用户标识 (留空由服务端从 UserKey 自动提取)'),
  enableMcp: v(Schema.boolean().default(true)).description('是否挂载 FastMCP 工具箱'),
  peer: v(Schema.string().default('openviking-memory')).description('调用方节点标识')
}).description('OpenViking 核心长程记忆与代码战地 通信桥梁配置') : undefined

function log(msg) {
  try {
    const logPath = resolve(getDshDir(), `${PKG_NAME}-hook.log`)
    const line = `[${new Date().toISOString()}] ${msg}\n`
    appendFileSync(logPath, line, 'utf8')
  } catch (_) {}
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
  selfHealLegacyResidues()
  const credentials = resolveOpenVikingCredentials()

  const getEndpoint = () => {
    const uiCfg = readUiSavedConfig()
    const explicit = getVal(config.endpointUrl, '') || (uiCfg.endpointUrl || '').trim()
    if (explicit) return explicit
    return credentials.baseUrl || 'http://127.0.0.1:1933'
  }
  const getMcpBaseUrl = () => {
    let ep = getEndpoint().trim()
    if (!ep) return ''
    if (!ep.endsWith('/mcp')) ep = `${ep.replace(/\/+$/, '')}/mcp`
    return ep
  }
  const getKey = () => {
    const uiCfg = readUiSavedConfig()
    const raw = getVal(config.userKey, '') || (uiCfg.userKey || '').trim()
    if (raw) return raw
    const envNames = [getVal(config.userKeyEnv, 'OPENVIKING_USER_KEY'), 'OPENVIKING_USER_KEY', 'OPENVIKING_API_KEY']
    for (const envName of envNames) {
      if (envName && process.env[envName]) return process.env[envName]
    }
    if (credentials.apiKey && !credentials.apiKey.startsWith('vk-sk-')) {
      return credentials.apiKey
    }
    return ''
  }
  const getPeer = () => {
    const uiCfg = readUiSavedConfig()
    return getVal(config.peer, '') || (uiCfg.peer || '').trim() || credentials.peerId || TARGET_PLUGIN
  }
  const getEnableMcp = () => getVal(config.enableMcp, true) !== false

  log(`[INIT] ${PKG_NAME} activated (peer=${getPeer()}, endpoint=${getEndpoint()})`)

  let currentMcpFork = null
  let lastMcpSignature = ''

  async function mountMcpIfNeeded() {
    const enableMcp = getEnableMcp()
    const mcpBase = getMcpBaseUrl()
    if (!enableMcp || !mcpBase) {
      if (currentMcpFork) {
        try { currentMcpFork.dispose() } catch (_) {}
        currentMcpFork = null
        lastMcpSignature = ''
      }
      return
    }

    try {
      const key = getKey()
      const mcpUrl = `${mcpBase}?plugin_id=${TARGET_PLUGIN}`
      const signature = `${mcpUrl}#${key || 'nokey'}`

      if (currentMcpFork && signature === lastMcpSignature) return
      if (currentMcpFork) {
        try { currentMcpFork.dispose() } catch (_) {}
        currentMcpFork = null
      }

      const proxyPath = fileURLToPath(new URL('./servers/mcp-proxy.mjs', import.meta.url))
      log(`[MCP_MOUNT] mounting stdio proxy (${proxyPath}) targeting ${mcpUrl}`)

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
        const childEnv = {
          ...process.env,
          ELECTRON_RUN_AS_NODE: '1',
          OPENVIKING_URL: mcpBase,
          OPENVIKING_MCP_URL: mcpUrl,
          OPENVIKING_PEER_ID: getPeer(),
          OV_TARGET_PLUGIN: TARGET_PLUGIN,
          OV_DEBUG_LOG: resolve(getDshDir(), `${PKG_NAME}-proxy.log`)
        }
        if (key) childEnv.OPENVIKING_API_KEY = key

        currentMcpFork = ctx.plugin(mcpPlugin, {
          serverName: TARGET_PLUGIN,
          transport: 'stdio',
          command: process.execPath,
          args: [proxyPath],
          env: childEnv,
          toolCallTimeoutMs: 60000,
          failOnStartupError: false,
          reconnect: { enabled: true, initialDelayMs: 500, maxDelayMs: 15000, maxAttempts: 10 }
        })
        lastMcpSignature = signature
        log(`[MCP_MOUNT_SUCCESS] ${PKG_NAME} mounted successfully`)
      }
    } catch (err) {
      log(`[MCP_MOUNT_WARN] failed to mount: ${err?.message || err}`)
    }
  }

  const removeBridgeListener = ensureLocalConfigBridge(() => {
    log('[UI_CONFIG_SYNC] received updated credentials from DSH UI panel, reloading MCP')
    mountMcpIfNeeded().catch(() => {})
  })

  mountMcpIfNeeded().catch(() => {})
  ctx.on('loader/volatile-update', () => {
    log('[VOLATILE_UPDATE] reloading dynamic config')
    mountMcpIfNeeded().catch(() => {})
  })

  ctx.on('dispose', () => {
    log('[DISPOSE] releasing child MCP processes and file locks')
    removeBridgeListener()
    if (currentMcpFork) {
      try { currentMcpFork.dispose() } catch (_) {}
      currentMcpFork = null
      lastMcpSignature = ''
    }
  })

  if (ctx.systemPrompt) {
    try {
      ctx.systemPrompt.context({
        name: `${TARGET_PLUGIN}-routing-guide`,
        order: 15,
        text: () => [
          `【OpenViking 核心长程记忆与代码战地 导轨】`,
          `当前已接入 OpenViking 核心长程记忆与代码战地 (${TARGET_PLUGIN})。`,
          `请直接基于授权工具与 Hook 开展工作，开箱即用。`
        ].join('\n')
      })
    } catch (_) {}
  }
}

apply.inject = ['systemPrompt', 'tools']
