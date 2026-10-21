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
  const cleanName = (plugin.name || plugin.plugin_id).replace(/\s*\([^)]*\)/g, '').trim()

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

      {/* 1. 专属控制视窗直通卡片 (真实由 plugin.gui 配置驱动) */}
      {plugin.gui?.dashboard_route && plugin.gui.dashboard_route !== '/plugins' ? (
        <div className="rounded-md border border-border/60 bg-muted/20 p-3 text-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-foreground flex items-center gap-1.5">
              <SlidersIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
              {cleanName} 专属交互视窗
            </span>
            <a
              href={plugin.gui.dashboard_route.startsWith('http') ? plugin.gui.dashboard_route : plugin.gui.dashboard_route}
              target={plugin.gui.dashboard_route.startsWith('http') ? '_blank' : undefined}
              rel="noreferrer"
              className="flex items-center gap-1 text-xs font-mono text-cyan-700 dark:text-cyan-400 hover:underline"
            >
              前往专属控制台
              <ExternalLinkIcon className="size-3" />
            </a>
          </div>
          <p className="text-muted-foreground leading-relaxed">
            {plugin.description}
          </p>
        </div>
      ) : (
        <div className="rounded-md border border-border/50 bg-muted/10 p-3 text-xs space-y-1">
          <div className="font-semibold text-foreground flex items-center gap-1.5">
            <SlidersIcon className="size-3.5 text-muted-foreground" />
            开箱即用配置托管
          </div>
          <p className="text-muted-foreground leading-relaxed">
            本插件遵循零侵入标准规范，运行参数由宿主与智能体生命周期钩子自动化接管。
          </p>
        </div>
      )}

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
              let displayVal = ''
              if (value == null) {
                displayVal = '未配置 (默认)'
              } else if (typeof value === 'object') {
                displayVal = value.value || value.description || value.label || JSON.stringify(value)
              } else {
                displayVal = String(value)
              }

              return (
                <div
                  key={key}
                  className="flex items-center justify-between rounded-md border border-border/50 bg-card/40 p-2.5 text-xs font-mono"
                >
                  <div className="min-w-0 pr-2">
                    <div className="text-muted-foreground text-xs font-sans">{key}</div>
                    <div className="truncate text-foreground font-medium text-xs mt-0.5" title={displayVal}>
                      {displayVal}
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 px-2 text-xs shrink-0"
                    onClick={() => handleCopy(displayVal, key)}
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

      {/* 3. 架构解耦与通信契约自解释说明 (真实契约与 SOP) */}
      <div className="rounded-md border border-border/40 bg-muted/10 p-3 text-xs leading-relaxed text-muted-foreground space-y-1">
        <div className="font-semibold text-foreground flex items-center gap-1.5">
          <span>💡 架构与治理契约：</span>
          <Badge variant="outline" className="text-xs font-mono border-border/60">
            {plugin.category === 'platform' ? '系统核心组件' : '独立解耦生态'}
          </Badge>
        </div>
        <p className="text-foreground/90">
          {plugin.skill?.sop_summary
            ? `标准作业程序：${plugin.skill.sop_summary}`
            : plugin.description}
        </p>
        <p className="text-muted-foreground/80 font-mono text-xs">
          插件标识: {plugin.plugin_id} · 契约版本: v{plugin.version} · 工具数: {plugin.tools?.length || 0} 项
        </p>
      </div>
    </div>
  )
}
