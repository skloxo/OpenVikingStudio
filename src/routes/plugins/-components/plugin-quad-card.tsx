/**
 * plugin-quad-card.tsx
 * 四位一体插件高密卡片组件 (Cockpit UI 规范)。
 * 严禁绿色 🚫，字号 >= 12px，底边物理平齐 mt-auto，6px 微圆角。
 */

import * as React from 'react'
import {
  BrainIcon,
  ChevronRightIcon,
  LayersIcon,
  SlidersIcon,
  ZapIcon,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import type { QuadPluginItem } from '../-lib/plugin-types'

export type PluginQuadCardProps = {
  plugin: QuadPluginItem
  onSelect: (plugin: QuadPluginItem) => void
}

export function PluginQuadCard({ plugin, onSelect }: PluginQuadCardProps) {
  const isHealthy = plugin.health?.status === 'healthy'
  const toolCount = plugin.tools?.length || 0
  const hookCount = plugin.hooks?.length || 0
  const settingsCount = Object.keys(plugin.gui?.settings_fields || {}).length

  return (
    <Card className="flex flex-col border-border/70 bg-card/60 p-3.5 transition-colors hover:border-border hover:bg-card/90">
      {/* 头部：名称、版本与分类 */}
      <div className="flex items-start justify-between gap-2">
        <div className="grid gap-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-foreground tracking-tight">
              {plugin.name}
            </h3>
            <Badge
              variant="outline"
              className="text-xs font-mono border-border/60 bg-muted/30 px-1 py-0 text-muted-foreground"
            >
              v{plugin.version}
            </Badge>
          </div>
          <p className="font-mono text-xs text-muted-foreground/80">
            {plugin.plugin_id}
          </p>
        </div>

        {/* 运行态健康胶囊 (NO GREEN EVER) */}
        <Badge
          variant="outline"
          className={`flex items-center gap-1 px-1.5 py-0.5 text-xs font-mono ${
            isHealthy
              ? 'border-cyan-800/40 bg-cyan-950/30 text-cyan-400'
              : 'border-amber-800/40 bg-amber-950/30 text-amber-400'
          }`}
        >
          <span
            className={`size-1.5 rounded-full ${
              isHealthy ? 'bg-cyan-400' : 'bg-amber-400'
            }`}
          />
          {plugin.health?.latency_ms ? `${plugin.health.latency_ms.toFixed(1)}ms` : '健康'}
        </Badge>
      </div>

      {/* 概述自解释 */}
      <p className="mt-2 text-xs text-muted-foreground line-clamp-2 leading-relaxed">
        {plugin.description}
      </p>

      {/* 四位一体四维视窗网格 */}
      <div className="mt-3.5 grid grid-cols-2 gap-2 border-y border-border/40 py-2.5">
        {/* 1. Skill 认知导轨 */}
        <div className="flex items-center gap-2 rounded bg-muted/20 px-2 py-1.5">
          <BrainIcon className="size-3.5 shrink-0 text-muted-foreground" />
          <div className="min-w-0">
            <div className="text-xs text-muted-foreground font-mono">Skill 认知</div>
            <div className="truncate text-xs font-medium text-foreground">
              {plugin.skill?.name || '0 随包规约'}
            </div>
          </div>
        </div>

        {/* 2. Hook 神经反射 */}
        <div className="flex items-center gap-2 rounded bg-muted/20 px-2 py-1.5">
          <ZapIcon className="size-3.5 shrink-0 text-cyan-400" />
          <div className="min-w-0">
            <div className="text-xs text-muted-foreground font-mono">Hook 拦截</div>
            <div className="truncate text-xs font-medium text-cyan-400">
              {hookCount} 项物理反射
            </div>
          </div>
        </div>

        {/* 3. MCP 物理工具 */}
        <div className="flex items-center gap-2 rounded bg-muted/20 px-2 py-1.5">
          <LayersIcon className="size-3.5 shrink-0 text-cyan-400" />
          <div className="min-w-0">
            <div className="text-xs text-muted-foreground font-mono">MCP 工具</div>
            <div className="truncate text-xs font-medium text-foreground">
              {toolCount} 个物理算子
            </div>
          </div>
        </div>

        {/* 4. GUI 表单配置 */}
        <div className="flex items-center gap-2 rounded bg-muted/20 px-2 py-1.5">
          <SlidersIcon className="size-3.5 shrink-0 text-muted-foreground" />
          <div className="min-w-0">
            <div className="text-xs text-muted-foreground font-mono">GUI 配置</div>
            <div className="truncate text-xs font-medium text-foreground">
              {settingsCount > 0 ? `${settingsCount} 项动态参数` : '不可变免配'}
            </div>
          </div>
        </div>
      </div>

      {/* 底部按钮栏：底边物理平齐 */}
      <div className="mt-auto pt-3 flex items-center justify-between">
        <Badge
          variant="secondary"
          className="text-xs font-mono bg-muted/50 text-muted-foreground"
        >
          {plugin.category === 'platform' ? '官方原生中枢' : '租户专属'}
        </Badge>
        <Button
          variant="outline"
          size="sm"
          className="h-7 text-xs font-mono"
          onClick={() => onSelect(plugin)}
        >
          查看四位一体详情
          <ChevronRightIcon className="ml-1 size-3" />
        </Button>
      </div>
    </Card>
  )
}
