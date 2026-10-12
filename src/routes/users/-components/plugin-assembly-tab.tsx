/**
 * plugin-assembly-tab.tsx
 * 用户插件装配与细粒度能力授权选项卡 (Plugin Assembly & Tool ACL Tab).
 *
 * 核心架构哲学：
 * 1. 严格遵行“四位一体 (Quad)”架构：MCP 工具包、Hook 物理守卫、技能导轨、GUI 说明；
 * 2. 预设快捷胶囊：中枢全栈 (67 工具) vs 卫星工兵 (31 工具) vs 最小只读 (14 工具)；
 * 3. 插件瓦片与展开细粒度勾选联动，支持每个微观工具单独开关；
 * 4. 严守 Cockpit UI 视觉规范：NO GREEN EVER 🚫，字号物理硬下限 >= 12px (text-xs)。
 */

import * as React from 'react'
import {
  BotIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  GlobeIcon,
  KeyIcon,
  PackageIcon,
  SaveIcon,
  SparklesIcon,
  TerminalIcon,
  ZapIcon,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import type { PluginCapability, ToolBundle } from '../../agents/-lib/capability-bundles'
import { PLUGIN_CAPABILITIES } from '../../agents/-lib/capability-bundles'

export type PluginAssemblyTabProps = {
  selectedTools: string[]
  onToggleTool: (toolId: string) => void
  onToggleBundle: (bundle: ToolBundle) => void
  onTogglePluginAll: (plugin: PluginCapability, enableAll: boolean) => void
  hooksState: Record<string, boolean>
  onToggleHook: (hookId: string) => void
  onApplyPreset: (presetKey: 'full' | 'satellite' | 'readonly') => void
  onSaveConfig: () => void
  isSaving?: boolean
}

export function PluginAssemblyTab({
  selectedTools,
  onToggleTool,
  onToggleBundle,
  onTogglePluginAll,
  hooksState,
  onToggleHook,
  onApplyPreset,
  onSaveConfig,
  isSaving = false,
}: PluginAssemblyTabProps) {
  const [activePluginId, setActivePluginId] = React.useState<string>(PLUGIN_CAPABILITIES[0]?.pluginId || 'openviking-memory')
  const [expandedBundleIds, setExpandedBundleIds] = React.useState<Set<string>>(new Set())

  const activePlugin = PLUGIN_CAPABILITIES.find((p) => p.pluginId === activePluginId) || PLUGIN_CAPABILITIES[0]

  const toggleBundleExpand = (bundleId: string) => {
    setExpandedBundleIds((prev) => {
      const next = new Set(prev)
      if (next.has(bundleId)) next.delete(bundleId)
      else next.add(bundleId)
      return next
    })
  }

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

  // 统计总工具与 Hook
  const totalAllToolsCount = PLUGIN_CAPABILITIES.reduce((acc, p) => acc + p.totalTools, 0)
  const totalAllHooksCount = PLUGIN_CAPABILITIES.reduce((acc, p) => acc + p.hooks.length, 0)
  const activeHooksCount = Object.values(hooksState).filter(Boolean).length

  return (
    <div className="space-y-4 font-sans text-xs">
      {/* 预设能力包胶囊切换条 */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border/70 bg-card/40 p-2.5">
        <div className="flex items-center gap-1.5 font-semibold text-foreground text-xs">
          <SparklesIcon className="size-3.5 text-cyan-500" />
          <span>能力预设快捷包:</span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-6.5 text-xs font-mono border-border/60 hover:border-cyan-500/50"
            onClick={() => onApplyPreset('full')}
            title="全部 67 项 MCP 工具 + 7 项 Hook"
          >
            🚀 中枢全栈 (67工具)
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-6.5 text-xs font-mono border-border/60 hover:border-cyan-500/50"
            onClick={() => onApplyPreset('satellite')}
            title="卫星/通用业务 31 项工具"
          >
            🛰️ 卫星工兵 (31工具)
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-6.5 text-xs font-mono border-border/60 hover:border-cyan-500/50"
            onClick={() => onApplyPreset('readonly')}
            title="最小只读检索与拓扑 14 项工具"
          >
            🔒 最小只读 (14工具)
          </Button>
        </div>
      </div>

      {/* 三大插件并排高密选择瓦片 */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <span className="font-semibold text-foreground text-xs flex items-center gap-1.5">
            <PackageIcon className="size-3.5 text-cyan-500" />
            官方标杆 Quad 插件列表 ({PLUGIN_CAPABILITIES.length})
          </span>
          <span className="font-mono text-xs text-muted-foreground">
            点击插件卡片切换下方细粒度配置
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
          {PLUGIN_CAPABILITIES.map((plugin) => {
            const allToolIds = plugin.bundles.flatMap((b) => b.toolIds)
            const equippedCount = allToolIds.filter((id) => selectedTools.includes(id)).length
            const isAll = equippedCount === allToolIds.length
            const isPart = equippedCount > 0 && !isAll
            const isSelected = activePluginId === plugin.pluginId
            const activeHooks = plugin.hooks.filter((h) => hooksState[h.id] ?? true).length

            return (
              <div
                key={plugin.pluginId}
                onClick={() => setActivePluginId(plugin.pluginId)}
                className={`group cursor-pointer rounded-md border p-2.5 transition-all flex flex-col justify-between ${
                  isSelected
                    ? 'border-cyan-500 ring-1 ring-cyan-500/30 bg-cyan-500/10'
                    : isAll
                      ? 'border-cyan-500/40 bg-card/60 hover:border-cyan-500/70 hover:bg-card/90'
                      : isPart
                        ? 'border-amber-500/40 bg-card/60 hover:border-amber-500/70 hover:bg-card/90'
                        : 'border-border/60 bg-muted/20 hover:border-border hover:bg-muted/30'
                }`}
              >
                <div>
                  <div className="flex items-start justify-between gap-1.5">
                    <div className="flex items-center gap-1.5 min-w-0">
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

                    <Badge
                      variant="outline"
                      className="shrink-0 font-mono text-xs px-1.5 py-0 border-border/60 text-muted-foreground"
                    >
                      {equippedCount}/{allToolIds.length} 工具
                    </Badge>
                  </div>

                  <p className="mt-1.5 text-xs text-muted-foreground leading-relaxed line-clamp-2">
                    {plugin.description}
                  </p>
                </div>

                <div className="mt-2 pt-1.5 border-t border-border/40 flex items-center justify-between text-xs font-mono text-muted-foreground">
                  <span>Hook: {activeHooks}/{plugin.hooks.length}</span>
                  <span className={isSelected ? 'text-cyan-500 font-semibold' : 'text-muted-foreground'}>
                    {isSelected ? '● 正在配置' : '点击配置'}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* 选中插件的四位一体微观配置视窗 */}
      {activePlugin && (
        <div className="rounded-md border border-border/80 bg-card/50 p-3 space-y-3">
          {/* 插件头部与一键开关 */}
          <div className="flex items-center justify-between border-b border-border/50 pb-2">
            <div className="flex items-center gap-2 min-w-0">
              {getPluginIcon(activePlugin.pluginId)}
              <span className="font-semibold text-foreground text-xs">
                {activePlugin.name}
              </span>
              <Badge variant="outline" className="font-mono text-xs border-cyan-500/30 text-cyan-500">
                v{activePlugin.version}
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-6.5 text-xs font-mono border-border/60"
                onClick={() => {
                  const allIds = activePlugin.bundles.flatMap((b) => b.toolIds)
                  const allEquipped = allIds.every((id) => selectedTools.includes(id))
                  onTogglePluginAll(activePlugin, !allEquipped)
                }}
              >
                {activePlugin.bundles.flatMap((b) => b.toolIds).every((id) => selectedTools.includes(id))
                  ? '一键卸载全部工具'
                  : '一键装配全部工具'}
              </Button>
            </div>
          </div>

          {/* 支柱 1: MCP 工具包与具体算子细粒度勾选 */}
          <div className="space-y-2">
            <span className="font-semibold text-foreground text-xs flex items-center gap-1.5">
              <TerminalIcon className="size-3.5 text-cyan-500" />
              ① MCP 角色工具包与细粒度算子 ({activePlugin.bundles.length} 个角色包)
            </span>

            <div className="space-y-2">
              {activePlugin.bundles.map((bundle) => {
                const bundleTools = bundle.tools || []
                const selectedInBundle = bundle.toolIds.filter((id) => selectedTools.includes(id)).length
                const isBundleAll = selectedInBundle === bundle.toolIds.length
                const isExpanded = expandedBundleIds.has(bundle.id)

                return (
                  <div
                    key={bundle.id}
                    className="rounded-md border border-border/60 bg-background/60 p-2.5 space-y-2"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <button
                          type="button"
                          onClick={() => toggleBundleExpand(bundle.id)}
                          className="p-0.5 text-muted-foreground hover:text-foreground"
                        >
                          {isExpanded ? (
                            <ChevronUpIcon className="size-3.5" />
                          ) : (
                            <ChevronDownIcon className="size-3.5" />
                          )}
                        </button>
                        <span className="font-semibold text-foreground text-xs truncate">
                          {bundle.name}
                        </span>
                        <Badge
                          variant="outline"
                          className="font-mono text-xs border-border/60 text-muted-foreground"
                        >
                          {selectedInBundle}/{bundle.toolIds.length} 项
                        </Badge>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="h-6 text-xs font-mono px-2 border-border/60"
                          onClick={() => onToggleBundle(bundle)}
                        >
                          {isBundleAll ? '整包停用' : '整包启用'}
                        </Button>
                      </div>
                    </div>

                    <p className="text-xs text-muted-foreground leading-relaxed pl-5">
                      {bundle.description}
                    </p>

                    {/* 展开展示每个微观工具算子 */}
                    {isExpanded && (
                      <div className="mt-2 border-t border-border/40 pt-2 grid grid-cols-1 sm:grid-cols-2 gap-1.5 pl-5">
                        {bundleTools.map((tool) => {
                          const isToolEquipped = selectedTools.includes(tool.id)

                          return (
                            <div
                              key={tool.id}
                              onClick={() => onToggleTool(tool.id)}
                              className={`flex items-start gap-2 rounded border p-1.5 cursor-pointer transition-colors ${
                                isToolEquipped
                                  ? 'border-cyan-500/40 bg-cyan-500/5'
                                  : 'border-border/40 bg-muted/10 opacity-70 hover:opacity-100'
                              }`}
                            >
                              <input
                                type="checkbox"
                                checked={isToolEquipped}
                                onChange={() => onToggleTool(tool.id)}
                                onClick={(e) => e.stopPropagation()}
                                className="mt-0.5 rounded border-border text-cyan-600 focus:ring-cyan-500"
                              />
                              <div className="min-w-0 flex-1">
                                <div className="flex items-center gap-1">
                                  <span className="font-mono text-xs font-semibold text-foreground truncate">
                                    {tool.name}
                                  </span>
                                  {tool.isDangerous && (
                                    <Badge
                                      variant="outline"
                                      className="text-[12px] px-1 py-0 border-rose-500/40 text-rose-500"
                                    >
                                      特权高危
                                    </Badge>
                                  )}
                                </div>
                                <p className="text-xs text-muted-foreground truncate" title={tool.description}>
                                  {tool.description}
                                </p>
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* 支柱 2: Hook 物理守卫 */}
          {activePlugin.hooks.length > 0 && (
            <div className="space-y-1.5 border-t border-border/50 pt-2.5">
              <span className="font-semibold text-foreground text-xs flex items-center gap-1.5">
                <ZapIcon className="size-3.5 text-cyan-500" />
                ② Hook 先验拦截守卫 ({activePlugin.hooks.length} 项)
              </span>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {activePlugin.hooks.map((hook) => {
                  const isEnabled = hooksState[hook.id] ?? true

                  return (
                    <div
                      key={hook.id}
                      onClick={() => onToggleHook(hook.id)}
                      className={`flex items-start justify-between gap-2 rounded-md border p-2 cursor-pointer transition-colors ${
                        isEnabled
                          ? 'border-cyan-500/40 bg-cyan-500/5'
                          : 'border-border/40 bg-muted/10 opacity-60'
                      }`}
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5">
                          <span className="font-semibold text-foreground text-xs truncate">
                            {hook.name}
                          </span>
                          <Badge variant="outline" className="font-mono text-[12px] text-muted-foreground">
                            {hook.triggerEvent}
                          </Badge>
                        </div>
                        <p className="mt-0.5 text-xs text-muted-foreground leading-relaxed line-clamp-2">
                          {hook.description}
                        </p>
                      </div>

                      <input
                        type="checkbox"
                        checked={isEnabled}
                        onChange={() => onToggleHook(hook.id)}
                        onClick={(e) => e.stopPropagation()}
                        className="mt-1 rounded border-border text-cyan-600 focus:ring-cyan-500"
                      />
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* 支柱 3 & 4: 技能导轨与 GUI 视窗说明 */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 border-t border-border/50 pt-2.5">
            {activePlugin.skill && (
              <div className="rounded-md border border-border/50 bg-background/50 p-2 space-y-1">
                <div className="font-semibold text-foreground text-xs flex items-center gap-1">
                  <span>③ 技能导轨:</span>
                  <span className="font-mono text-cyan-500">{activePlugin.skill.name}</span>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {activePlugin.skill.summary}
                </p>
              </div>
            )}
            {activePlugin.gui && (
              <div className="rounded-md border border-border/50 bg-background/50 p-2 space-y-1">
                <div className="font-semibold text-foreground text-xs flex items-center gap-1">
                  <span>④ GUI 视窗形态:</span>
                  <span className="font-mono text-cyan-500">{activePlugin.gui.name}</span>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {activePlugin.gui.cloudConfigSummary}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 底部保存与装配统计操作栏 */}
      <div className="flex items-center justify-between rounded-md border border-cyan-500/30 bg-cyan-500/5 p-3">
        <div className="font-mono text-xs text-foreground flex items-center gap-2">
          <Badge variant="outline" className="border-cyan-500/40 text-cyan-600 dark:text-cyan-400 font-mono">
            {selectedTools.length} / {totalAllToolsCount} 工具已选
          </Badge>
          <Badge variant="outline" className="border-border/60 text-muted-foreground font-mono">
            {activeHooksCount} / {totalAllHooksCount} Hook 守护激活
          </Badge>
        </div>

        <Button
          type="button"
          size="sm"
          className="gap-1.5 bg-cyan-600 text-white hover:bg-cyan-700 font-semibold text-xs h-7 px-3"
          onClick={onSaveConfig}
          disabled={isSaving}
        >
          <SaveIcon className="size-3.5" />
          {isSaving ? '正在保存...' : '保存能力装配'}
        </Button>
      </div>
    </div>
  )
}
