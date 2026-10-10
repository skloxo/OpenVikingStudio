/**
 * plugin-config-drawer.tsx
 * 智能体单插件专属配置抽屉组件 (Cockpit UI 规范)。
 *
 * 核心架构哲学：
 * 1. 严格遵行“四位一体 (Quad)”固定框架：
 *    ① MCP 工具包 (分组与装配比例)
 *    ② 钩子 (Hook 物理守卫)
 *    ③ 技能 (名称、章节结构与简要摘要)
 *    ④ 插件的 GUI (云端后台配置项与客户端交互形态说明)
 * 2. 实时生效，勾选即保存，零冗余保存流程；
 * 3. 抽屉宽度优化为宽屏舒适座舱 (sm:max-w-2xl md:max-w-3xl)；
 * 4. 遵行 Cockpit UI 视觉规范：NO GREEN EVER 🚫，字号物理硬下限 >= 12px (text-xs)。
 */

import * as React from 'react'
import {
  AppWindowIcon,
  BotIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  FileTextIcon,
  GlobeIcon,
  KeyIcon,
  LoaderCircleIcon,
  PackageIcon,
  SaveIcon,
  XIcon,
  ZapIcon,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '#/components/ui/sheet'
import type { PluginCapability, ToolBundle } from '../-lib/capability-bundles'

export type PluginConfigDrawerProps = {
  plugin: PluginCapability | null
  open: boolean
  onClose: () => void
  selectedTools: string[]
  activeBundleIds: Set<string>
  onToggleBundle: (bundle: ToolBundle) => void
  onTogglePluginAll: (plugin: PluginCapability, enableAll: boolean) => void
  hooksState: Record<string, boolean>
  onToggleHook: (hookId: string, enabled: boolean) => void
  onCopy?: (text: string, title: string, e?: React.MouseEvent) => void
  onSave?: () => Promise<void> | void
  isSaving?: boolean
}

export function PluginConfigDrawer({
  plugin,
  open,
  onClose,
  selectedTools,
  activeBundleIds,
  onToggleBundle,
  onTogglePluginAll,
  hooksState,
  onToggleHook,
  onSave,
  isSaving = false,
}: PluginConfigDrawerProps) {
  const [expandedBundleDetail, setExpandedBundleDetail] = React.useState<string | null>(null)

  if (!plugin) return null

  // 1. MCP 统计
  const allPluginToolIds = plugin.bundles.flatMap((b) => b.toolIds)
  const selectedCount = allPluginToolIds.filter((id) => selectedTools.includes(id)).length
  const isFullyEnabled = selectedCount === allPluginToolIds.length
  const isPartiallyEnabled = selectedCount > 0 && !isFullyEnabled

  // 2. Hook 统计
  const activeHooksCount = plugin.hooks.filter((h) => hooksState[h.id] ?? true).length

  // 图标自适应
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
    <Sheet open={open} onOpenChange={(val) => !val && onClose()}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-2xl md:max-w-3xl border-l border-border/80 bg-background p-0 font-sans text-xs flex flex-col shadow-2xl"
      >
        {/* 抽屉头部 */}
        <SheetHeader className="border-b border-border/60 p-4 space-y-2 bg-muted/10">
          <div className="flex items-center justify-between pr-8">
            <div className="flex items-center gap-2">
              {getPluginIcon(plugin.pluginId)}
              <SheetTitle className="text-sm font-semibold text-foreground">
                {plugin.name}
              </SheetTitle>
              <Badge
                variant="outline"
                className="font-mono text-xs border-cyan-500/30 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400"
              >
                v{plugin.version}
              </Badge>
            </div>
            {/* 快捷一键开关 */}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onTogglePluginAll(plugin, !isFullyEnabled)}
              className="h-6.5 text-xs font-mono border-border/60"
            >
              {isFullyEnabled ? '停用此插件' : '开启全部工具包'}
            </Button>
          </div>
          <SheetDescription className="text-xs text-muted-foreground leading-relaxed">
            {plugin.description}
          </SheetDescription>

          {/* 四位一体装配总览指示条 */}
          <div className="flex flex-wrap items-center gap-2 pt-1 font-mono text-xs">
            <span className="text-muted-foreground">四位一体装配:</span>
            <Badge
              variant="outline"
              className={
                isFullyEnabled
                  ? 'border-cyan-500/40 bg-cyan-500/10 text-cyan-700 dark:text-cyan-300'
                  : isPartiallyEnabled
                    ? 'border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400'
                    : 'border-border/60 text-muted-foreground'
              }
            >
              MCP: {selectedCount} / {allPluginToolIds.length}
            </Badge>
            <Badge variant="outline" className="border-border/60 text-muted-foreground">
              Hook: {activeHooksCount} / {plugin.hooks.length}
            </Badge>
            <Badge variant="outline" className="border-border/60 text-muted-foreground">
              技能: {plugin.skill ? '1 / 1' : '无'}
            </Badge>
            <Badge variant="outline" className="border-border/60 text-muted-foreground">
              GUI: {plugin.gui ? '1 / 1' : '无'}
            </Badge>
          </div>
        </SheetHeader>

        {/* 抽屉主体：四位一体固定框架排布 */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* 1. MCP 角色工具包 */}
          <div className="space-y-2.5 rounded-lg border border-border/60 bg-muted/10 p-3.5">
            <div className="flex items-center justify-between border-b border-border/40 pb-2">
              <span className="font-semibold text-foreground text-xs flex items-center gap-1.5">
                <PackageIcon className="size-3.5 text-cyan-500" />
                1. MCP 工具包 ({plugin.bundles.length} 个角色组 / 共 {plugin.totalTools} 项算子)
              </span>
              <span className="text-muted-foreground text-xs font-mono">
                已装配 {selectedCount}/{allPluginToolIds.length}
              </span>
            </div>

            <div className="space-y-2 pt-1">
              {plugin.bundles.map((bundle) => {
                const isEquipped = activeBundleIds.has(bundle.id)
                const isInspect = expandedBundleDetail === bundle.id

                return (
                  <div
                    key={bundle.id}
                    className={`rounded border p-3 transition-all ${
                      isEquipped
                        ? 'border-cyan-500/60 bg-cyan-500/5 dark:bg-cyan-950/20'
                        : 'border-border/60 bg-muted/20 text-muted-foreground'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-foreground text-xs">{bundle.name}</span>
                        {bundle.roleType === 'ops' ? (
                          <Badge
                            variant="outline"
                            className="border-amber-500/30 bg-amber-500/10 font-mono text-xs text-amber-700 dark:text-amber-400"
                          >
                            特权运维
                          </Badge>
                        ) : (
                          <Badge
                            variant="outline"
                            className="border-cyan-500/30 bg-cyan-500/10 font-mono text-xs text-cyan-700 dark:text-cyan-400"
                          >
                            通用业务
                          </Badge>
                        )}
                        <span className="font-mono text-xs text-muted-foreground">
                          ({bundle.toolIds.length} 项)
                        </span>
                      </div>

                      <label className="flex cursor-pointer items-center gap-1.5 text-xs select-none">
                        <span className={isEquipped ? 'text-cyan-600 dark:text-cyan-400 font-medium' : 'text-muted-foreground'}>
                          {isEquipped ? '已开启' : '未开启'}
                        </span>
                        <input
                          type="checkbox"
                          checked={isEquipped}
                          onChange={() => onToggleBundle(bundle)}
                          className="size-3.5 accent-cyan-500"
                        />
                      </label>
                    </div>

                    <p className="mt-1 leading-relaxed text-xs text-muted-foreground">
                      {bundle.description}
                    </p>

                    <div className="mt-2.5 flex items-center justify-between border-t border-border/40 pt-1.5 font-mono text-xs">
                      <span className="text-muted-foreground">算子包含: {bundle.tools.slice(0, 3).map((t) => t.name).join(', ')}...</span>
                      <button
                        type="button"
                        onClick={() => setExpandedBundleDetail(isInspect ? null : bundle.id)}
                        className="text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-0.5"
                      >
                        {isInspect ? (
                          <>收起算子清单 <ChevronUpIcon className="size-3" /></>
                        ) : (
                          <>展开全部 {bundle.toolIds.length} 项算子 <ChevronDownIcon className="size-3" /></>
                        )}
                      </button>
                    </div>

                    {/* 工具明细列表 */}
                    {isInspect && (
                      <div className="mt-2 max-h-48 space-y-1 overflow-y-auto rounded bg-background/90 p-2 font-mono text-xs border border-border/50">
                        {bundle.tools.map((t) => (
                          <div
                            key={t.id}
                            className="flex items-center justify-between border-b border-border/30 pb-1 pt-0.5 last:border-none"
                          >
                            <div className="flex items-center gap-1.5">
                              <span className="text-cyan-700 dark:text-cyan-400 font-medium">{t.name}</span>
                              {t.isDangerous && (
                                <Badge variant="outline" className="border-rose-500/40 bg-rose-500/10 text-rose-700 dark:text-rose-400 px-1 py-0 text-xs">
                                  高危
                                </Badge>
                              )}
                            </div>
                            <span className="truncate pl-2 text-muted-foreground max-w-sm" title={t.description}>
                              {t.description}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* 2. 钩子 (Hook) */}
          <div className="space-y-2 rounded-lg border border-border/60 bg-muted/10 p-3.5">
            <div className="flex items-center justify-between border-b border-border/40 pb-2">
              <span className="font-semibold text-foreground text-xs flex items-center gap-1.5">
                <ZapIcon className="size-3.5 text-amber-500" />
                2. 钩子 (Hook 守卫 · 共 {plugin.hooks.length} 项)
              </span>
              <span className="text-muted-foreground text-xs font-mono">
                已启用 {activeHooksCount}/{plugin.hooks.length}
              </span>
            </div>

            <div className="space-y-2 pt-1">
              {plugin.hooks.map((h) => {
                const enabled = hooksState[h.id] ?? true
                return (
                  <label
                    key={h.id}
                    className="flex cursor-pointer items-start justify-between gap-2 rounded border border-border/40 bg-background/60 p-2 hover:bg-muted/30 transition-colors"
                  >
                    <div className="flex items-start gap-2 min-w-0">
                      <input
                        type="checkbox"
                        checked={enabled}
                        onChange={(e) => onToggleHook(h.id, e.target.checked)}
                        className="size-3.5 accent-cyan-500 mt-0.5"
                      />
                      <div className="min-w-0">
                        <div className="text-xs font-medium text-foreground">{h.name}</div>
                        <div className="text-xs text-muted-foreground leading-relaxed mt-0.5">
                          {h.description}
                        </div>
                      </div>
                    </div>
                    <Badge variant="outline" className="shrink-0 font-mono text-xs border-border/60 text-muted-foreground">
                      {h.triggerEvent}
                    </Badge>
                  </label>
                )
              })}
            </div>
          </div>

          {/* 3. 技能 (Skill) */}
          <div className="space-y-2 rounded-lg border border-border/60 bg-muted/10 p-3.5">
            <div className="flex items-center justify-between border-b border-border/40 pb-2">
              <span className="font-semibold text-foreground text-xs flex items-center gap-1.5">
                <FileTextIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
                3. 技能 (Skill)
              </span>
              <span className="text-muted-foreground text-xs font-mono">
                {plugin.skill ? `包含 ${plugin.skill.chapters.length} 个核心章节` : '无'}
              </span>
            </div>

            {plugin.skill ? (
              <div className="space-y-2 pt-1">
                <div className="rounded border border-border/50 bg-background/60 p-2.5">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-semibold text-cyan-700 dark:text-cyan-300">
                      {plugin.skill.name}
                    </span>
                    <Badge variant="outline" className="font-mono text-xs border-cyan-500/30 text-cyan-600 dark:text-cyan-400">
                      标准化工程技能
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                    {plugin.skill.summary}
                  </p>
                </div>

                <div className="space-y-1.5 pl-1">
                  <div className="font-mono text-xs text-muted-foreground">章节大纲与执行规约：</div>
                  {plugin.skill.chapters.map((ch, idx) => (
                    <div
                      key={idx}
                      className="rounded border border-border/40 bg-background/40 p-2 text-xs flex items-start gap-2"
                    >
                      <span className="font-mono font-medium text-cyan-600 dark:text-cyan-400 shrink-0">
                        {ch.title}:
                      </span>
                      <span className="text-muted-foreground leading-relaxed">
                        {ch.summary}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="py-2 text-center text-xs text-muted-foreground font-mono">
                此插件暂无独立技能
              </div>
            )}
          </div>

          {/* 4. 插件的 GUI */}
          <div className="space-y-2 rounded-lg border border-border/60 bg-muted/10 p-3.5">
            <div className="flex items-center justify-between border-b border-border/40 pb-2">
              <span className="font-semibold text-foreground text-xs flex items-center gap-1.5">
                <AppWindowIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
                4. 插件的 GUI (图形交互与呈现层)
              </span>
              <span className="text-muted-foreground text-xs font-mono">
                {plugin.gui ? '已就绪' : '无'}
              </span>
            </div>

            {plugin.gui ? (
              <div className="space-y-2.5 pt-1">
                <div className="rounded border border-border/50 bg-background/60 p-2.5">
                  <div className="font-semibold text-foreground text-xs">{plugin.gui.name}</div>
                  <div className="mt-2 space-y-2 text-xs">
                    <div className="rounded border border-border/30 bg-muted/20 p-2">
                      <span className="font-medium text-cyan-700 dark:text-cyan-300">云端控制台呈现与配置：</span>
                      <p className="text-muted-foreground leading-relaxed mt-0.5">
                        {plugin.gui.cloudConfigSummary}
                      </p>
                    </div>
                    <div className="rounded border border-border/30 bg-muted/20 p-2">
                      <span className="font-medium text-cyan-700 dark:text-cyan-300">Agent 客户端对话交互形态：</span>
                      <p className="text-muted-foreground leading-relaxed mt-0.5">
                        {plugin.gui.clientDialogSummary}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-2 text-center text-xs text-muted-foreground font-mono">
                此插件暂无 GUI 交互层
              </div>
            )}
          </div>
        </div>

        {/* 抽屉底部：装配状态指示 + 显式保存授权生效 */}
        <div className="border-t border-border/60 p-3 bg-muted/10 flex items-center justify-between">
          <div className="text-xs font-mono text-muted-foreground flex items-center gap-1.5">
            <span className="size-1.5 rounded-full bg-cyan-500" />
            <span>已配置 {selectedCount}/{allPluginToolIds.length} 项工具</span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onClose}
              className="h-7 text-xs font-mono border-border/60"
            >
              <XIcon className="size-3 mr-1" />
              关闭
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={async () => {
                if (onSave) {
                  await onSave()
                }
                onClose()
              }}
              disabled={isSaving}
              className="h-7 text-xs font-mono bg-cyan-600 hover:bg-cyan-500 text-white font-medium shadow-xs"
            >
              {isSaving ? (
                <LoaderCircleIcon className="size-3 animate-spin mr-1" />
              ) : (
                <SaveIcon className="size-3 mr-1" />
              )}
              保存并完成
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
