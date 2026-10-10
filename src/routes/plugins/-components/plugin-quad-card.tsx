/**
 * plugin-quad-card.tsx
 * 四位一体插件高密卡片组件 (Cockpit UI 规范)。
 * 严禁绿色 🚫，字号 >= 12px，奥卡姆剃刀整卡可点，极致高密无多余留白。
 */

import {
  BrainIcon,
  LayersIcon,
  SlidersIcon,
  ZapIcon,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import type { QuadPluginItem } from '../-lib/plugin-types'

export type PluginQuadCardProps = {
  plugin: QuadPluginItem
  onSelect: (plugin: QuadPluginItem) => void
}

export function PluginQuadCard({ plugin, onSelect }: PluginQuadCardProps) {
  const isHealthy = plugin.health.status === 'healthy'
  const toolCount = plugin.tools.length
  const hookCount = plugin.hooks.length
  const settingsCount = Object.keys(plugin.gui.settings_fields).length
  // 清洗任何多余括号英文，如 "OpenViking 核心记忆插件 (openviking-memory)" -> "OpenViking 核心记忆"
  const cleanName = plugin.name.replace(/\s*\([^)]*\)/g, '').trim()

  return (
    <div
      onClick={() => onSelect(plugin)}
      className="group flex flex-col justify-between rounded-md border border-border/70 bg-card/60 p-3 transition-all hover:border-cyan-500/50 hover:bg-card/90 hover:shadow-xs cursor-pointer active:scale-[0.995]"
    >
      {/* 头部与信息区：紧凑贴合，彻底消灭 gap 冗余留白 */}
      <div>
        {/* 1. 标题行：名称、版本与运行态状态胶囊 (物理水平严格对齐) */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <h3 className="text-sm font-semibold text-foreground tracking-tight truncate group-hover:text-cyan-600 dark:group-hover:text-cyan-400 transition-colors">
              {cleanName}
            </h3>
            <Badge
              variant="outline"
              className="text-xs font-mono border-border/60 bg-muted/30 px-1.5 py-0 text-muted-foreground shrink-0"
            >
              v{plugin.version}
            </Badge>
          </div>

          {/* 运行态状态胶囊 (性冷淡高密风格，NO GREEN EVER) */}
          <div className="flex shrink-0 items-center gap-1.5 rounded border border-border/60 bg-muted/30 px-2 py-0.5 text-xs font-mono">
            <span
              className={`size-1.5 rounded-full shrink-0 ${
                isHealthy ? 'bg-cyan-500' : 'bg-amber-500'
              }`}
            />
            <span className={isHealthy ? 'text-cyan-700 dark:text-cyan-400 font-medium' : 'text-amber-700 dark:text-amber-400 font-medium'}>
              {isHealthy ? '服务就绪' : '部分降级'}
            </span>
          </div>
        </div>

        {/* 2. 插件身份标识 (紧贴标题，零留白) */}
        <div className="mt-0.5 font-mono text-xs text-muted-foreground/60 leading-tight">
          {plugin.plugin_id}
        </div>

        {/* 3. 紧凑自解释概述 (紧贴 ID，单行截断) */}
        <p className="mt-1 text-xs text-muted-foreground line-clamp-1 leading-snug" title={plugin.description}>
          {plugin.description}
        </p>
      </div>

      {/* 四位一体高密四维矩阵 (2x2 紧凑格) */}
      <div className="mt-2.5 grid grid-cols-2 gap-1.5 border-t border-border/40 pt-2 font-mono text-xs">
        {/* 1. 认知导轨 */}
        <div className="flex items-center gap-1.5 rounded border border-border/40 bg-muted/20 p-1.5">
          <BrainIcon className="size-3 shrink-0 text-muted-foreground" />
          <div className="min-w-0">
            <div className="text-xs text-muted-foreground/70 font-sans leading-none">认知导轨</div>
            <div className="mt-0.5 truncate text-xs font-medium text-foreground" title={plugin.skill.name || '随包装配'}>
              {plugin.skill.name ? plugin.skill.name.replace(/\s*\([^)]*\)/g, '') : '随包装配'}
            </div>
          </div>
        </div>

        {/* 2. Hook 反射 */}
        <div className="flex items-center gap-1.5 rounded border border-border/40 bg-muted/20 p-1.5">
          <ZapIcon className="size-3 shrink-0 text-cyan-600 dark:text-cyan-400" />
          <div className="min-w-0">
            <div className="text-xs text-muted-foreground/70 font-sans leading-none">Hook 反射</div>
            <div className="mt-0.5 truncate text-xs font-medium text-foreground">
              {hookCount} 项物理反射
            </div>
          </div>
        </div>

        {/* 3. 标准工具 */}
        <div className="flex items-center gap-1.5 rounded border border-border/40 bg-muted/20 p-1.5">
          <LayersIcon className="size-3 shrink-0 text-cyan-600 dark:text-cyan-400" />
          <div className="min-w-0">
            <div className="text-xs text-muted-foreground/70 font-sans leading-none">标准工具</div>
            <div className="mt-0.5 truncate text-xs font-medium text-foreground tabular-nums">
              {toolCount} 项标准工具
            </div>
          </div>
        </div>

        {/* 4. 交互配置 */}
        <div className="flex items-center gap-1.5 rounded border border-border/40 bg-muted/20 p-1.5">
          <SlidersIcon className="size-3 shrink-0 text-muted-foreground" />
          <div className="min-w-0">
            <div className="text-xs text-muted-foreground/70 font-sans leading-none">交互配置</div>
            <div className="mt-0.5 truncate text-xs font-medium text-foreground">
              {settingsCount > 0 ? `${settingsCount} 项动态参数` : '免配就绪'}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
