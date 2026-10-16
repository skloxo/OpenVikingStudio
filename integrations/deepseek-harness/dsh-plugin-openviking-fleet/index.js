/**
 * dsh-plugin-openviking-fleet
 * 卫星集群同频运维插件 - DeepSeek Harness (DSH) 独立 Cordis RPC 桥接器与 Hook 套件。
 * 遵循官方 DSH Schemastery & Cordis 规范，单包自治，解耦独立。
 */

import { appendFileSync, statSync, renameSync, existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

export const name = 'dsh-plugin-openviking-fleet'
export const inject = ['agents', 'sessions', 'tools', 'systemPrompt']

import Schema from './schema.js'

function v(s) {
  return typeof s?.volatile === 'function' ? s.volatile() : s
}

export const Config = Schema ? Schema.object({
  endpointUrl: v(Schema.string().default('https://vk.tide.red/mcp')).description('OpenViking 通信端点 URL (公网默认 https://vk.tide.red/mcp)'),
  agentId: v(Schema.string().default('fleet-mesh@coordinator')).description('智能体工兵 ID (在 OpenViking 智能体中心复制)'),
  userKey: v(Schema.string().role('secret').default('')).description('所属用户 API Key / User Key (在 HTTP Header 中安全传递，带密码遮罩)'),
  userKeyEnv: v(Schema.string().default('OPENVIKING_USER_KEY')).description('从 DSH 凭据库 (.credentials.yaml) 或环境变量中引用的 Key 变量名'),
  userId: v(Schema.string().default('default')).description('租户 / 账户身份标识 (默认 default)'),
  enableMcp: v(Schema.boolean().default(true)).description('是否挂载 FastMCP 工具箱'),
  peer: v(Schema.string().default('fleet-mesh@coordinator')).description('调用方节点标识 (用于服务端审计日志与调用链追踪)')
}).description('卫星集群同频运维插件 通信桥梁配置') : undefined

function log(msg) {
  try {
    const home = process.env.USERPROFILE || process.env.HOME || 'C:\\Users\\Skl'
    const logPath = resolve(home, '.dsh', 'dsh-plugin-openviking-fleet-hook.log')
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
  const getEndpoint = () => getVal(config.endpointUrl, 'https://vk.tide.red/mcp')
  const getMcpBaseUrl = () => {
    let ep = getEndpoint().trim()
    if (!ep.endsWith('/mcp')) ep = `${ep.replace(/\/+$/, '')}/mcp`
    return ep
  }
  const getKey = () => {
    const raw = getVal(config.userKey, '')
    if (raw) return raw
    const envNames = [getVal(config.userKeyEnv, 'OPENVIKING_USER_KEY'), 'OPENVIKING_USER_KEY', 'OPENVIKING_API_KEY']
    for (const name of envNames) {
      if (name && process.env[name]) return process.env[name]
    }
    return ''
  }
  const getPeer = () => getVal(config.peer, 'fleet-mesh@coordinator')
  const getUserId = () => getVal(config.userId, 'default')
  const getAgentId = () => getVal(config.agentId, 'fleet-mesh@coordinator')
  const getEnableMcp = () => getVal(config.enableMcp, true) !== false

  log(`[INIT] dsh-plugin-openviking-fleet activated (peer=${getPeer()}, endpoint=${getEndpoint()})`)

  let currentMcpFork = null
  let lastMcpSignature = ''

  async function mountMcpIfNeeded() {
    const agentId = getAgentId()
    const enableMcp = getEnableMcp()
    if (!enableMcp || !agentId) {
      if (currentMcpFork) {
        try { currentMcpFork.dispose() } catch (_) {}
        currentMcpFork = null
        lastMcpSignature = ''
      }
      return
    }

    try {
      const mcpBase = getMcpBaseUrl()
      const key = getKey()
      const mcpUrl = `${mcpBase}?agent_id=${encodeURIComponent(agentId)}&plugin_id=fleet-mesh`
      const signature = `${mcpUrl}#${key || 'nokey'}`

      if (currentMcpFork && signature === lastMcpSignature) return
      if (currentMcpFork) {
        try { currentMcpFork.dispose() } catch (_) {}
        currentMcpFork = null
      }

      const proxyPath = fileURLToPath(new URL('./servers/mcp-proxy.mjs', import.meta.url))
      log(`[MCP_MOUNT] mounting stdio proxy (${proxyPath}) targeting ${mcpBase}`)

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
          OV_TARGET_PLUGIN: 'fleet-mesh',
          OV_DEBUG_LOG: resolve(homeDir, '.dsh', 'dsh-plugin-openviking-fleet-proxy.log')
        }
        if (key) childEnv.OPENVIKING_API_KEY = key

        currentMcpFork = ctx.plugin(mcpPlugin, {
          serverName: 'fleet-mesh',
          transport: 'stdio',
          command: process.execPath,
          args: [proxyPath],
          env: childEnv,
          toolCallTimeoutMs: 60000,
          failOnStartupError: false,
          reconnect: { enabled: true, initialDelayMs: 500, maxDelayMs: 15000, maxAttempts: 10 }
        })
        lastMcpSignature = signature
        log(`[MCP_MOUNT_SUCCESS] dsh-plugin-openviking-fleet mounted successfully`)
      }
    } catch (err) {
      log(`[MCP_MOUNT_WARN] failed to mount: ${err?.message || err}`)
    }
  }

  mountMcpIfNeeded().catch(() => {})
  ctx.on('loader/volatile-update', () => {
    log('[VOLATILE_UPDATE] reloading dynamic config')
    mountMcpIfNeeded().catch(() => {})
  })

  // 专属认知导轨上下文注入
  if (ctx.systemPrompt) {
    try {
      ctx.systemPrompt.context({
        name: 'fleet-mesh-routing-guide',
        order: 15,
        text: () => [
          '【卫星集群同频运维插件 导轨】',
          '当前已接入 卫星集群同频运维插件 (fleet-mesh)。',
          '跨物理机节点同频健康体检、代码与配置一键同频同步 (2 项跨机工具 + 1 项 Hook 守卫)',
          '请直接基于授权工具与 Hook 开展工作，开箱即用。'
        ].join('\n')
      })
    } catch (_) {}
  }
}

apply.inject = ['systemPrompt', 'tools']
