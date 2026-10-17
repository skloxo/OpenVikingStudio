/**
 * search-integration-guide.tsx
 * 搜索网关双模态集成指引组件 (Cockpit UI 规范)。
 *
 * 核心设计哲学 (第一性原理)：
 * 1. 双模态单一真相源：底层由 services/search-gateway 26-Key 轮询矩阵驱动；
 * 2. 客户按需自选：
 *    - 形态 A (标准 API 模式)：零安装插件，直接在支持第三方搜索的客户端填入接口地址 + UserKey；
 *    - 形态 B (定制插件模式)：无原生配置或需要 12 项高级原子工具，一键安装 dsh-plugin-search-gateway；
 * 3. 严守 Cockpit UI 视觉规范：NO GREEN EVER 🚫，字号 >= 12px (text-xs)，极客高密。
 */

import * as React from 'react'
import {
  CheckIcon,
  CopyIcon,
  GlobeIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { copyTextToClipboard } from '#/lib/clipboard'

export type SearchIntegrationGuideProps = {
  userApiKey?: string
}

export function SearchIntegrationGuide({ userApiKey = '' }: SearchIntegrationGuideProps) {
  const [mode, setMode] = React.useState<'api' | 'plugin'>('api')
  const [network, setNetwork] = React.useState<'public' | 'local'>('public')
  const [copiedKey, setCopiedKey] = React.useState<string | null>(null)

  const isPublic = network === 'public'
  const apiEndpoint = isPublic
    ? 'https://sear.tide.red/v1'
    : 'http://127.0.0.1:18888/v1'
  const mcpEndpoint = isPublic
    ? 'https://sear.tide.red/mcp'
    : 'http://127.0.0.1:18888/mcp'

  const effectiveApiKey = userApiKey || 'sear-matrix-key-2026'
  const installCmd = 'npm install https://vk.tide.red/studio/dsh-plugin-search-gateway.tgz'

  const universalMcpSnippet = JSON.stringify(
    {
      mcpServers: {
        'search-gateway': {
          url: mcpEndpoint,
          headers: {
            'x-api-key': effectiveApiKey,
          },
        },
      },
    },
    null,
    2,
  )

  const handleCopy = async (text: string, label: string) => {
    try {
      await copyTextToClipboard(text)
      setCopiedKey(label)
      toast.success(`${label} 已复制到剪贴板`)
      setTimeout(() => setCopiedKey(null), 2000)
    } catch {
      toast.error('复制失败，请手动选择复制')
    }
  }

  return (
    <div className="space-y-3 rounded-md border border-border/70 bg-card/40 p-3 font-sans text-xs">
      <div className="flex items-center justify-between border-b border-border/40 pb-2">
        <div className="flex items-center gap-2">
          <GlobeIcon className="size-4 text-cyan-500" />
          <span className="font-semibold text-foreground text-xs">
            联网搜索接入指南 (双模态单一真相源)
          </span>
        </div>
        <div className="inline-flex rounded-md border border-border/60 bg-muted/20 p-0.5 text-xs font-mono">
          <button
            type="button"
            onClick={() => setNetwork('public')}
            className={`px-2 py-0.5 rounded transition-all ${
              isPublic
                ? 'bg-background text-cyan-600 dark:text-cyan-400 shadow-xs font-medium'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            公网中继 (sear.tide.red)
          </button>
          <button
            type="button"
            onClick={() => setNetwork('local')}
            className={`px-2 py-0.5 rounded transition-all ${
              !isPublic
                ? 'bg-background text-cyan-600 dark:text-cyan-400 shadow-xs font-medium'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            本地局域网 (18888)
          </button>
        </div>
      </div>

      {/* 独立服务凭据声明 */}
      <div className="rounded border border-border/60 bg-muted/20 p-2.5 text-xs text-muted-foreground leading-relaxed">
        🛡️ <strong>独立后端凭据声明</strong>：联网搜索网关为解耦运行的独立服务，其鉴权 Key 由搜索网关服务独立签发与管控。OpenViking 不托管该 Key，亦不当下位系统的消耗账本。请在客户端安装或接入时，直接配置搜索服务对应的接口地址与专用 Key。
      </div>

      {/* 模态双选切换器 */}
      <div className="flex items-center gap-1 rounded-md border border-border/60 bg-muted/30 p-1 text-xs">
        <button
          type="button"
          onClick={() => setMode('api')}
          className={`flex-1 rounded px-2.5 py-1.5 text-left font-medium transition-all ${
            mode === 'api'
              ? 'border border-cyan-500/40 bg-background text-cyan-700 dark:text-cyan-300 shadow-xs'
              : 'text-muted-foreground hover:text-foreground hover:bg-muted/40'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="font-semibold">形态 A · 原生标准 API (免装插件)</span>
            <Badge variant="outline" className="text-xs border-cyan-500/30 text-cyan-600 dark:text-cyan-400">
              推荐 DSH 原生
            </Badge>
          </div>
          <div className="mt-0.5 text-xs text-muted-foreground font-normal">
            DSH 官方原生支持：一条接口地址加一个密钥直接对接，免装任何客户端插件
          </div>
        </button>

        <button
          type="button"
          onClick={() => setMode('plugin')}
          className={`flex-1 rounded px-2.5 py-1.5 text-left font-medium transition-all ${
            mode === 'plugin'
              ? 'border border-cyan-500/40 bg-background text-cyan-700 dark:text-cyan-300 shadow-xs'
              : 'text-muted-foreground hover:text-foreground hover:bg-muted/40'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="font-semibold">形态 B · 通用 MCP 与高级插件</span>
            <Badge variant="outline" className="text-xs border-border/60 text-muted-foreground">
              12 大高级工具
            </Badge>
          </div>
          <div className="mt-0.5 text-xs text-muted-foreground font-normal">
            Cursor / Claude / Windsurf 通用 MCP 挂载，或 DSH 定制插件包
          </div>
        </button>
      </div>

      {/* 模式 A：原生标准 API 配置引导 */}
      {mode === 'api' && (
        <div className="space-y-2.5 pt-1">
          <div className="rounded border border-border/60 bg-muted/20 p-2.5 text-xs text-muted-foreground leading-relaxed">
            💡 <strong>极简免装插件对接：</strong>DeepSeek Harness (DSH) 原生网页搜索设置完全支持标准 API 接口。<strong>无需安装额外插件包</strong>，直接在设置中填入以下两项：
          </div>

          {/* 1. 接口地址 */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium text-muted-foreground">搜索接口 Base URL (Search API Endpoint)</span>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground gap-1"
                onClick={() => handleCopy(apiEndpoint, '搜索接口端点')}
              >
                {copiedKey === '搜索接口端点' ? (
                  <CheckIcon className="size-3 text-cyan-400" />
                ) : (
                  <CopyIcon className="size-3" />
                )}
                复制
              </Button>
            </div>
            <div className="rounded border border-border/60 bg-background/80 p-2 font-mono text-xs text-foreground select-all">
              {apiEndpoint}
            </div>
          </div>

          {/* 2. 鉴权密钥 */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium text-muted-foreground">搜索接口 API Key</span>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground gap-1"
                onClick={() => handleCopy(effectiveApiKey, '搜索密钥')}
              >
                {copiedKey === '搜索密钥' ? (
                  <CheckIcon className="size-3 text-cyan-400" />
                ) : (
                  <CopyIcon className="size-3" />
                )}
                复制
              </Button>
            </div>
            <div className="rounded border border-border/60 bg-background/80 p-2 font-mono text-xs text-foreground break-all select-all">
              {effectiveApiKey}
            </div>
          </div>

          {/* 3. 规范说明 */}
          <div className="rounded border border-border/40 bg-muted/10 p-2 font-mono text-xs text-muted-foreground space-y-1">
            <div>• DSH 设置：在 DSH 网页搜索设置中填写 BaseURL ({apiEndpoint}) 与 API Key 即可原生激活。</div>
            <div>• REST 协议：支持 POST /v1/search (query, limit) 与 GET /v1/search?q=关键词。</div>
            <div>• 底层保障：26-Key 轮询矩阵 (Keenable 80万次池 + Tavily + Crawl4AI 无头爬虫 + SearXNG 保底)。</div>
          </div>
        </div>
      )}

      {/* 模式 B：定制插件包与 通用 MCP 引导 */}
      {mode === 'plugin' && (
        <div className="space-y-2.5 pt-1">
          <div className="rounded border border-border/60 bg-muted/20 p-2.5 text-xs text-muted-foreground leading-relaxed">
            💡 <strong>适用场景：</strong>通用智能体 (Cursor / Claude Desktop / Windsurf / Cline) 通过 Streamable HTTP 协议接入 12 项原子级高级工具 (代码反查、学术、无头网页渲染脱水)。
          </div>

          {/* 1. 通用 MCP JSON 配置 */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium text-muted-foreground">通用 MCP 配置文件 (mcp.json / claude_desktop_config.json)</span>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground gap-1"
                onClick={() => handleCopy(universalMcpSnippet, '通用MCP配置')}
              >
                {copiedKey === '通用MCP配置' ? (
                  <CheckIcon className="size-3 text-cyan-400" />
                ) : (
                  <CopyIcon className="size-3" />
                )}
                复制 MCP 配置
              </Button>
            </div>
            <pre className="rounded border border-border/60 bg-background/80 p-2 font-mono text-xs text-foreground overflow-x-auto leading-relaxed">
              {universalMcpSnippet}
            </pre>
          </div>

          {/* 2. DSH 定制插件包一键安装 */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium text-muted-foreground">DSH 独立插件 NPM 安装命令 (可选高级工具包)</span>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground gap-1"
                onClick={() => handleCopy(installCmd, 'NPM安装命令')}
              >
                {copiedKey === 'NPM安装命令' ? (
                  <CheckIcon className="size-3 text-cyan-400" />
                ) : (
                  <CopyIcon className="size-3" />
                )}
                复制命令
              </Button>
            </div>
            <div className="rounded border border-border/60 bg-background/80 p-2 font-mono text-xs text-foreground select-all">
              {installCmd}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
