/**
 * plugin-tiles.tsx
 * 智能体插件高密状态瓦片卡片组组件 (Cockpit UI 规范)。
 *
 * 核心架构哲学：
 * 1. 彻底切除过度工程化的批量开启按钮与啰嗦标题；
 * 2. 各插件完全解耦，右上角平等展示实际装配比例 (X/Y 工具 · A/B Hook)；
 * 3. 卡片紧凑高密，点击整卡或点击配置直接滑出专属抽屉；
 * 4. 遵行 Cockpit UI 视觉规范：NO GREEN EVER 🚫，字号物理硬下限 >= 12px (text-xs)。
 */

import * as React from 'react'
import {
  BotIcon,
  GlobeIcon,
  KeyIcon,
  PackageIcon,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import type { PluginCapability } from '../-lib/capability-bundles'
import { PLUGIN_CAPABILITIES } from '../-lib/capability-bundles'

export type PluginTilesProps = {
  selectedTools: string[]
  hooksState: Record<string, boolean>
  onSelectPlugin: (plugin: PluginCapability) => void
}

export function PluginTiles({
  selectedTools,
  hooksState,
  onSelectPlugin,
}: PluginTilesProps) {
  const getPluginIcon = (id: string) => {
    switch (id) {
      case 'openviking-memory':
        return <BotIcon className="size-4 text-cyan-600 dark:text-cyan-400" />
      case 'network-search':
        return <GlobeIcon className="size-4 text-cyan-600 dark:text-cyan-400" />
      case 'keepass-vault':
        return <KeyIcon className="size-4 text-cyan-600 dark:text-cyan-400" />
      default:
        return <PackageIcon className="size-4 text-cyan-600 dark:text-cyan-400" />
    }
  }

  return (
    <div className="space-y-2 font-sans text-xs">
      {/* 极简标题栏 */}
      <div className="flex items-center justify-between border-b border-border/40 pb-1">
        <div className="flex items-center gap-1.5 font-semibold text-foreground text-xs">
          <PackageIcon className="size-3.5 text-cyan-500" />
          <span>插件</span>
        </div>
      </div>

      {/* 三大插件并排高密瓦片网格 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
        {PLUGIN_CAPABILITIES.map((plugin) => {
          const allToolIds = plugin.bundles.flatMap((b) => b.toolIds)
          const equippedCount = allToolIds.filter((id) => selectedTools.includes(id)).length
          const isAll = equippedCount === allToolIds.length
          const isPart = equippedCount > 0 && !isAll
          const activeHooksCount = plugin.hooks.filter((h) => hooksState[h.id] ?? true).length

          return (
            <div
              key={plugin.pluginId}
              onClick={() => onSelectPlugin(plugin)}
              className={`group cursor-pointer rounded-md border p-2.5 transition-all relative flex flex-col justify-between ${
                isAll
                  ? 'border-cyan-500/50 bg-cyan-500/5 hover:border-cyan-500/80 hover:bg-cyan-500/10'
                  : isPart
                    ? 'border-amber-500/40 bg-amber-500/5 hover:border-amber-500/70 hover:bg-amber-500/10'
                    : 'border-border/60 bg-muted/20 hover:border-border hover:bg-muted/30 text-muted-foreground'
              }`}
            >
              {/* 卡片头部：名称、版本与平等工具/Hook统计 */}
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <div className="p-1 rounded bg-background/80 border border-border/40 shrink-0">
                      {getPluginIcon(plugin.pluginId)}
                    </div>
                    <div className="min-w-0">
                      <div className="font-semibold text-foreground text-xs truncate">
                        {plugin.name}
                      </div>
                      <div className="font-mono text-muted-foreground text-xs">
                        v{plugin.version}
                      </div>
                    </div>
                  </div>

                  {/* 右上角：真实平等的装配比例徽标 (替代全开/半开) */}
                  <Badge
                    variant="outline"
                    className="shrink-0 font-mono text-xs px-1.5 py-0 border-border/60 text-muted-foreground group-hover:border-cyan-500/40 group-hover:text-foreground transition-colors"
                  >
                    {equippedCount}/{allToolIds.length} 工具 · {activeHooksCount}/{plugin.hooks.length} Hook
                  </Badge>
                </div>

                <p className="mt-1.5 text-xs text-muted-foreground leading-relaxed line-clamp-2">
                  {plugin.description}
                </p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
