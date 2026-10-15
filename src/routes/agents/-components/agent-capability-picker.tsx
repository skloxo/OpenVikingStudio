/**
 * agent-capability-picker.tsx
 * 智能体中心服务端能力包 (Capability Bundles) 装备矩阵组件。
 *
 * 遵循 Cockpit UI 视觉规范：
 * 1. 严格禁止使用绿色 🚫 (NO GREEN EVER)；
 * 2. 字号物理硬下限 >= 12px (text-xs)；
 * 3. 展现 Skill 导轨、Hook 拦截包、角色工具包 (31项业务 vs 58项全栈) 与 GUI 视窗；
 * 4. 提供快速角色预设 (卫星工兵 vs 中枢总控) 一键装配。
 */

import * as React from 'react'
import {
  AppWindowIcon,
  CompassIcon,
  CopyIcon,
  ExternalLinkIcon,
  PackageIcon,
  SparklesIcon,
  ZapIcon,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import type { ToolBundle } from '../-lib/capability-bundles'
import { PLUGIN_CAPABILITIES } from '../-lib/capability-bundles'

export type AgentCapabilityPickerProps = {
  selectedTools: string[]
  activeBundleIds: Set<string>
  onToggleBundle: (bundle: ToolBundle) => void
  onApplyPreset: (preset: 'consumer' | 'ops' | 'clear') => void
  hooksState: Record<string, boolean>
  onToggleHook: (hookId: string, enabled: boolean) => void
  onCopy: (text: string, title: string, e?: React.MouseEvent) => void
}

export function AgentCapabilityPicker({
  selectedTools,
  activeBundleIds,
  onToggleBundle,
  onApplyPreset,
  hooksState,
  onToggleHook,
  onCopy,
}: AgentCapabilityPickerProps) {
  const [expandedBundleDetail, setExpandedBundleDetail] = React.useState<string | null>(null)

  return (
    <div className="space-y-3 pt-2">
      {/* 标题栏与计数回显 */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-1.5">
        <div className="flex items-center gap-1.5">
          <PackageIcon className="size-3.5 text-cyan-500" />
          <span className="font-semibold text-foreground text-xs">
            服务端插件与角色工具包 (Capability Bundles) 装备
          </span>
        </div>
        <span className="font-mono text-muted-foreground text-xs">
          已选 {selectedTools.length} 项工具 / {activeBundleIds.size} 个工具包
        </span>
      </div>

      {/* 快捷角色预设胶囊栏 */}
      <div className="flex flex-wrap items-center gap-2 rounded bg-muted/20 p-2 border border-border/40">
        <div className="flex items-center gap-1 text-muted-foreground text-xs font-medium">
          <SparklesIcon className="size-3 text-cyan-500" />
          <span>快速角色预设:</span>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => onApplyPreset('consumer')}
          className="h-6 gap-1 text-xs border-cyan-500/40 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 hover:bg-cyan-500/20"
        >
          🛰️ 卫星业务工兵预设 (日常免高危)
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => onApplyPreset('ops')}
          className="h-6 gap-1 text-xs border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400 hover:bg-amber-500/20"
        >
          🧠 中枢全栈总控预设 (67项全量)
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => onApplyPreset('clear')}
          className="h-6 gap-1 text-xs text-muted-foreground hover:text-foreground ml-auto"
        >
          清空已选
        </Button>
      </div>

      {/* 真实服务端插件卡片矩阵 */}
      <div className="space-y-4">
        {PLUGIN_CAPABILITIES.map((plugin) => (
          <div
            key={plugin.pluginId}
            className="space-y-3 rounded-md border border-border/80 bg-card/70 p-3.5"
          >
            {/* 插件头部 */}
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/50 pb-2">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-foreground text-xs sm:text-sm">{plugin.name}</span>
                <Badge variant="outline" className="font-mono text-xs border-cyan-500/30 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400">
                  v{plugin.version}
                </Badge>
                <Badge variant="outline" className="font-mono text-xs text-muted-foreground">
                  共 {plugin.totalTools} 项 MCP 工具
                </Badge>
              </div>
              <span className="text-muted-foreground text-xs">{plugin.description}</span>
            </div>

            {/* 四象限网格 */}
            <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
              {/* ① Skill 认知导轨 */}
              <div className="flex flex-col justify-between rounded border border-border/60 bg-muted/20 p-2.5">
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 font-semibold text-foreground text-xs">
                      <CompassIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
                      <span>① 官方技能导轨</span>
                    </div>
                    <Badge variant="outline" className="border-cyan-500/30 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 font-mono text-xs">
                      随包装配
                    </Badge>
                  </div>
                  <div className="mt-1.5 text-xs font-semibold text-foreground">
                    {plugin.skillGuide.name}
                  </div>
                  <p className="mt-0.5 text-xs text-muted-foreground leading-relaxed">
                    {plugin.skillGuide.description}
                  </p>
                </div>
                <div className="mt-2 flex items-center justify-between rounded border border-border/40 bg-background/80 px-2 py-1 font-mono text-xs">
                  <span className="truncate text-muted-foreground" title={plugin.skillGuide.path}>
                    {plugin.skillGuide.path}
                  </span>
                  <button
                    type="button"
                    onClick={(e) => onCopy(plugin.skillGuide.path, 'Skill 导轨路径', e)}
                    className="shrink-0 p-0.5 text-cyan-500 hover:text-cyan-400"
                    title="复制规范文件路径"
                  >
                    <CopyIcon className="size-3" />
                  </button>
                </div>
              </div>

              {/* ② Hook 拦截能力包 */}
              <div className="flex flex-col justify-between rounded border border-border/60 bg-muted/20 p-2.5">
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 font-semibold text-foreground text-xs">
                      <ZapIcon className="size-3.5 text-amber-400" />
                      <span>② Hook 拦截能力包</span>
                    </div>
                    <span className="font-mono text-xs text-muted-foreground">
                      共 {plugin.hooks.length} 项物理反射
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    毫秒级先验拦截、自动上下文预取与执行后经验自动萃取
                  </p>
                </div>

                <div className="mt-2 space-y-1.5 border-t border-border/40 pt-1.5">
                  {plugin.hooks.map((h) => {
                    const enabled = hooksState[h.id] ?? true
                    return (
                      <label
                        key={h.id}
                        className="flex cursor-pointer items-start justify-between gap-2 rounded p-1 hover:bg-muted/40"
                      >
                        <div className="flex items-center gap-1.5 min-w-0">
                          <input
                            type="checkbox"
                            checked={enabled}
                            onChange={(e) => onToggleHook(h.id, e.target.checked)}
                            className="size-3 accent-cyan-500 mt-0.5"
                          />
                          <div className="min-w-0">
                            <div className="truncate text-xs font-medium text-foreground">
                              {h.name}
                            </div>
                            <div className="truncate text-xs text-muted-foreground" title={h.description}>
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
            </div>

            {/* ③ MCP 角色工具包 */}
            <div className="space-y-2 border-t border-border/50 pt-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 font-semibold text-foreground text-xs">
                  <PackageIcon className="size-3.5 text-cyan-500" />
                  <span>③ MCP 角色工具包 (共 {plugin.totalTools} 项工具，按 Agent 角色分组装备)</span>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-2.5 md:grid-cols-2">
                {plugin.bundles.map((bundle) => {
                  const isEquipped = activeBundleIds.has(bundle.id)
                  const isInspect = expandedBundleDetail === bundle.id

                  return (
                    <div
                      key={bundle.id}
                      className={`flex flex-col justify-between rounded border p-3 transition-all ${
                        isEquipped
                          ? 'border-cyan-500/60 bg-cyan-500/5 dark:bg-cyan-950/20 text-foreground'
                          : 'border-border/60 bg-muted/20 text-muted-foreground hover:bg-muted/40'
                      }`}
                    >
                      <div>
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-foreground text-xs">
                              {bundle.name}
                            </span>
                            {bundle.roleType === 'ops' ? (
                              <Badge
                                variant="outline"
                                className="border-amber-500/30 bg-amber-500/10 px-1 py-0 font-mono text-xs text-amber-700 dark:text-amber-400"
                              >
                                特权运维
                              </Badge>
                            ) : (
                              <Badge
                                variant="outline"
                                className="border-cyan-500/30 bg-cyan-500/10 px-1 py-0 font-mono text-xs text-cyan-700 dark:text-cyan-400"
                              >
                                通用业务
                              </Badge>
                            )}
                          </div>

                          <label className="flex cursor-pointer items-center gap-1 text-xs select-none">
                            <span className={isEquipped ? 'text-cyan-600 dark:text-cyan-400 font-medium' : 'text-muted-foreground'}>
                              {isEquipped ? '已装备' : '未装备'}
                            </span>
                            <input
                              type="checkbox"
                              checked={isEquipped}
                              onChange={() => onToggleBundle(bundle)}
                              className="size-3.5 accent-cyan-500"
                            />
                          </label>
                        </div>

                        <p className="mt-1 line-clamp-2 leading-relaxed text-xs text-muted-foreground">
                          {bundle.description}
                        </p>
                      </div>

                      <div className="mt-3 flex items-center justify-between border-t border-border/40 pt-2 font-mono text-xs">
                        <span className="text-muted-foreground">
                          包含 {bundle.toolIds.length} 项工具
                        </span>
                        <button
                          type="button"
                          onClick={() =>
                            setExpandedBundleDetail(isInspect ? null : bundle.id)
                          }
                          className="text-cyan-600 dark:text-cyan-400 hover:underline"
                        >
                          {isInspect ? '收起明细 ▲' : `查看全部 ${bundle.toolIds.length} 项工具明细 ▼`}
                        </button>
                      </div>

                      {/* 展开查看工具明细 */}
                      {isInspect && (
                        <div className="mt-2.5 max-h-48 space-y-1 overflow-y-auto rounded bg-background/90 p-2 font-mono text-xs border border-border/50">
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
                              <span className="truncate pl-2 text-muted-foreground max-w-64" title={t.description}>
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

            {/* ④ GUI 交互视窗 */}
            <div className="flex flex-wrap items-center justify-between gap-2 rounded border border-border/60 bg-muted/20 px-3 py-2 text-xs">
              <div className="flex items-center gap-2">
                <AppWindowIcon className="size-3.5 text-cyan-600 dark:text-cyan-400 shrink-0" />
                <span className="font-semibold text-foreground">④ GUI 交互视窗:</span>
                <span className="text-foreground">{plugin.guiWindow.name}</span>
                <span className="font-mono text-muted-foreground">({plugin.guiWindow.route})</span>
                <span className="text-muted-foreground hidden sm:inline">- {plugin.guiWindow.description}</span>
              </div>
              <a
                href={plugin.guiWindow.route}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-cyan-600 dark:text-cyan-400 hover:text-cyan-500 font-mono text-xs hover:underline"
              >
                <span>打开控制大盘</span>
                <ExternalLinkIcon className="size-3" />
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
