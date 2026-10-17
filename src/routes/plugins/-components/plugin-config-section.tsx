/**
 * plugin-config-section.tsx
 * 插件 GUI 交互视窗与核心参数配置分段组件 (Card-144 解耦重塑)。
 * 遵循 Cockpit UI 规范，NO GREEN EVER 🚫，字号 >= 12px，黄金甜点区 <= 150 行。
 */

import * as React from 'react'
import {
  CopyIcon,
  ExternalLinkIcon,
  SlidersIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { copyTextToClipboard } from '#/lib/clipboard'
import type { QuadPluginItem } from '../-lib/plugin-types'

export type PluginConfigSectionProps = {
  plugin: QuadPluginItem
}

export function PluginConfigSection({ plugin }: PluginConfigSectionProps) {
  const [copiedKey, setCopiedKey] = React.useState<string | null>(null)

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

  const settingsEntries = Object.entries(plugin.gui?.settings_fields || {})

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between border-b border-border/40 pb-2">
        <h4 className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
          <SlidersIcon className="size-3.5 text-muted-foreground" />
          GUI 交互视窗与核心参数配置
        </h4>
        {plugin.gui?.dashboard_route && (
          <Badge
            variant="outline"
            className="text-xs font-mono text-cyan-700 dark:text-cyan-400 border-cyan-500/30 bg-cyan-500/10"
          >
            视窗路由: {plugin.gui.dashboard_route}
          </Badge>
        )}
      </div>

      {/* 1. 专属控制视窗直通卡片 */}
      <div className="rounded-md border border-border/60 bg-muted/20 p-3 text-xs space-y-2">
        <div className="flex items-center justify-between">
          <span className="font-semibold text-foreground flex items-center gap-1.5">
            <SlidersIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
            {plugin.plugin_id === 'openviking-memory'
              ? '全景记忆库与知识图谱视窗'
              : plugin.plugin_id === 'network-search'
                ? '在线搜索试验台与配额大盘'
                : plugin.plugin_id === 'dify'
                  ? 'Dify 可视化编排与知识库中枢'
                  : '凭据分组拓扑与体检视窗'}
          </span>
          <a
            href={plugin.plugin_id === 'dify' ? 'http://127.0.0.1:13000' : (plugin.gui?.dashboard_route || '/')}
            target={plugin.plugin_id === 'dify' ? '_blank' : undefined}
            rel="noreferrer"
            className="flex items-center gap-1 text-xs font-mono text-cyan-700 dark:text-cyan-400 hover:underline"
          >
            前往专属控制台
            <ExternalLinkIcon className="size-3" />
          </a>
        </div>
        <p className="text-muted-foreground leading-relaxed">
          {plugin.plugin_id === 'openviking-memory'
            ? '提供体外大脑长程记忆观测大盘、FTS5 全文索引、知识图谱拓扑与纯度审计。'
            : plugin.plugin_id === 'network-search'
              ? '提供多路 Key 轮询健康度观测、Credits 消耗流水账与爬虫渲染测试台。'
              : plugin.plugin_id === 'dify'
                ? '提供可视化工作流编排大盘、DSL 导入导出、知识库检索引擎与模型提供商管理。'
                : '提供 KDBX 凭据分组拓扑树、弱密体检与自动化备份容灾管理。'}
        </p>
      </div>

      {/* 2. 结构化核心参数字典 */}
      <div className="space-y-1.5">
        <div className="text-xs font-medium text-muted-foreground">运行时核心配置参数:</div>
        <div className="grid gap-2">
          {settingsEntries.length === 0 ? (
            <div className="rounded border border-dashed border-border/60 p-2.5 text-center text-xs text-muted-foreground font-mono">
              免配即用（无额外必填环境变量）
            </div>
          ) : (
            settingsEntries.map(([key, value]) => {
              const valStr = String(value)
              return (
                <div
                  key={key}
                  className="flex items-center justify-between rounded-md border border-border/50 bg-card/40 p-2.5 text-xs font-mono"
                >
                  <div className="min-w-0 pr-2">
                    <div className="text-muted-foreground text-xs font-sans">{key}</div>
                    <div className="truncate text-foreground font-medium text-xs mt-0.5" title={valStr}>
                      {valStr}
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 px-2 text-xs shrink-0"
                    onClick={() => handleCopy(valStr, key)}
                  >
                    <CopyIcon className="mr-1 size-3" />
                    {copiedKey === key ? '已复制' : '复制'}
                  </Button>
                </div>
              )
            })
          )}
        </div>
      </div>

      {/* 3. 架构解耦与通信契约自解释说明 */}
      <div className="rounded-md border border-border/40 bg-muted/10 p-3 text-xs leading-relaxed text-muted-foreground">
        <span className="font-semibold text-foreground">💡 架构解耦契约：</span>
        {plugin.plugin_id === 'openviking-memory' && (
          <>
            本插件为 OpenViking 服务端中心化核心能力。外部智能体只需接入通用的客户端通信桥梁 (
            <code className="text-cyan-700 dark:text-cyan-400 font-mono">dsh-plugin-openviking</code>
            )，即可通过统一通道安全调用全量长程记忆。
          </>
        )}
        {plugin.plugin_id === 'network-search' && (
          <>
            本插件为独立微服务部署。支持<strong className="text-foreground">形态 A【原生标准 API (免装插件)】</strong>与<strong className="text-foreground">形态 B【定制插件 (
            <code className="text-cyan-700 dark:text-cyan-400 font-mono">dsh-plugin-search-gateway</code>
            )】</strong>双模态接入，底层共享 26-Key 轮询矩阵。
          </>
        )}
        {plugin.plugin_id === 'keepass-vault' && (
          <>
            本插件与 OpenViking 服务端<strong className="text-foreground">零运行时强依赖</strong>。OpenViking 仅作为官方展示展厅与统一发布托管源，客户端直接通过 (
            <code className="text-cyan-700 dark:text-cyan-400 font-mono">dsh-plugin-keepass-vault</code>
            ) 读取智能体本地加密 KDBX。
          </>
        )}
        {plugin.plugin_id === 'dify' && (
          <>
            本插件为 Dify 独立工作流与知识库生态扩展。支持通过 FastMCP 客户端 (<code className="text-cyan-700 dark:text-cyan-400 font-mono">dify_mcp_server.py</code>) 直接调度本地 Docker 实例 (13000 端口)，实现应用全生命周期纳管、DSL 代码化导入导出与工作流实时触发。
          </>
        )}
      </div>
    </div>
  )
}
