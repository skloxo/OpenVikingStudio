/**
 * Search Gateway Cordis RPC Bridge Plugin for DeepSeek Harness (DSH).
 * Pure Node.js ESM - Compliant with official DSH Schemastery specs.
 */

import Schema from './schema.js'

export const name = 'dsh-plugin-search-gateway'
export const inject = ['agents', 'tools', 'systemPrompt']

function v(s) {
  return typeof s?.volatile === 'function' ? s.volatile() : s
}

export const Config = Schema ? Schema.object({
  endpointUrl: v(Schema.string().default('http://127.0.0.1:18888/mcp')).description('Search Gateway MCP 通信端点 URL (默认 http://127.0.0.1:18888/mcp)'),
  apiKey: v(Schema.string().role('secret').default('')).description('搜索鉴权 API Key (若配置了鉴权保护)'),
  enableMcp: v(Schema.boolean().default(true)).description('是否挂载 12 项原子联网搜索工具箱')
}).description('Search Gateway 独立多引擎联网搜索与采集聚合套件') : undefined

function getVal(v, fallback = '') {
  if (v === undefined || v === null) return fallback
  if (typeof v?.get === 'function') {
    const val = v.get()
    return (val !== undefined && val !== null && val !== '') ? String(val).trim() : fallback
  }
  return String(v).trim() || fallback
}

export function apply(ctx, config = {}) {
  const getEndpoint = () => getVal(config.endpointUrl, 'http://127.0.0.1:18888/mcp')
  const getKey = () => getVal(config.apiKey, '')
  const getEnableMcp = () => getVal(config.enableMcp, true) !== false

  // 1. 注入 System Prompt 搜索工具指引
  if (ctx.systemPrompt) {
    try {
      ctx.systemPrompt.context({
        name: 'search-gateway-routing-guide',
        order: 20,
        text: () => [
          '【Search Gateway 联网搜索与采集聚合导轨】',
          '当用户询问最新时效资讯、外部网页内容、专业学术/金融/代码检索时，模型优先调用 `web_search`、`search_academic`、`search_finance`、`web_fetch` 等工具。',
          '底层由 26-Key 轮询矩阵 (Keenable 80万次池 + Tavily + SearXNG 本地保底) 自动分级调度与熔断保护。'
        ].join('\n')
      })
    } catch (_) {}
  }

  // 2. 进程内工具执行前置守卫：拦截官方失效/计费搜索并引导改用 Search Gateway
  try {
    ctx.on('tools/pre-execute', async (exec, next) => {
      if (exec.name === 'web_search_official' || exec.name === 'tool-web') {
        return {
          kind: 'deny',
          reason: '官方收费搜索未配置。请改用 Search Gateway 聚合搜索工具：web_search(query="...") 或 search_deep。'
        }
      }
      return next()
    })
  } catch (_) {}
}

apply.inject = ['systemPrompt', 'tools']
