/**
 * plugin-detail-drawer.tsx
 * 四位一体插件完整规格抽屉组件 (Cockpit UI 规范)。
 * 严禁绿色 🚫，字号 >= 12px，font-mono 代码与标签。
 */

import * as React from 'react'
import {
  BrainIcon,
  CheckCircle2Icon,
  CodeIcon,
  LayersIcon,
  SlidersIcon,
  XIcon,
  ZapIcon,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { ScrollArea } from '#/components/ui/scroll-area'
import type { QuadPluginItem } from '../-lib/plugin-types'

export type PluginDetailDrawerProps = {
  plugin: QuadPluginItem | null
  onClose: () => void
}

export function PluginDetailDrawer({ plugin, onClose }: PluginDetailDrawerProps) {
  if (!plugin) return null

  const isHealthy = plugin.health?.status === 'healthy'

  return (
    <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-xl flex-col border-l border-border bg-background shadow-2xl transition-all animate-in slide-in-from-right duration-200">
      {/* 抽屉头部 */}
      <div className="flex items-center justify-between border-b border-border p-4">
        <div className="grid gap-1">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold tracking-tight text-foreground">
              {plugin.name}
            </h2>
            <Badge variant="outline" className="text-xs font-mono">
              v{plugin.version}
            </Badge>
          </div>
          <p className="font-mono text-xs text-muted-foreground">{plugin.plugin_id}</p>
        </div>
        <Button variant="ghost" size="icon" className="size-8" onClick={onClose}>
          <XIcon className="size-4" />
        </Button>
      </div>

      <ScrollArea className="flex-1 p-4">
        <div className="space-y-5">
          {/* 1. 运行态健康摘要 */}
          <div className="rounded-md border border-border/60 bg-muted/20 p-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-foreground">运行态健康状态</span>
              <Badge
                variant="outline"
                className={`text-xs font-mono ${
                  isHealthy
                    ? 'border-cyan-800/40 bg-cyan-950/30 text-cyan-400'
                    : 'border-amber-800/40 bg-amber-950/30 text-amber-400'
                }`}
              >
                {plugin.health?.message || '正常'} ({plugin.health?.latency_ms?.toFixed(1) || 1.0}ms)
              </Badge>
            </div>
            <p className="mt-1.5 text-xs text-muted-foreground leading-relaxed">
              {plugin.description}
            </p>
          </div>

          {/* 2. MCP 物理工具池 (Dimension 1) */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h4 className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                <LayersIcon className="size-3.5 text-cyan-400" />
                MCP 物理工具清单 ({plugin.tools?.length || 0})
              </h4>
            </div>
            <div className="grid gap-1.5 max-h-56 overflow-y-auto pr-1">
              {(plugin.tools || []).map((tool) => (
                <div
                  key={tool.name}
                  className="rounded border border-border/50 bg-card/40 p-2 text-xs hover:bg-card/80"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-medium text-cyan-400">{tool.name}</span>
                    {tool.is_dangerous && (
                      <Badge variant="outline" className="text-xs font-mono border-rose-800/40 bg-rose-950/30 text-rose-400 px-1 py-0">
                        危险操作
                      </Badge>
                    )}
                  </div>
                  <p className="mt-1 text-muted-foreground text-xs leading-normal">
                    {tool.description}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* 3. Hook 神经反射拦截 (Dimension 2) */}
          <div className="space-y-2">
            <h4 className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
              <ZapIcon className="size-3.5 text-cyan-400" />
              Hook 神经反射拦截 ({plugin.hooks?.length || 0})
            </h4>
            <div className="space-y-2">
              {(plugin.hooks || []).map((hook) => (
                <div
                  key={hook.hook_id}
                  className="rounded border border-border/50 bg-card/40 p-2.5 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-foreground">{hook.name}</span>
                    <Badge variant="outline" className="text-xs font-mono border-cyan-800/40 bg-cyan-950/30 text-cyan-400 px-1.5 py-0">
                      {hook.trigger_event}
                    </Badge>
                  </div>
                  <p className="mt-1 text-muted-foreground text-xs leading-relaxed">
                    {hook.description}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* 4. Skill 认知导轨 (Dimension 3) */}
          {plugin.skill && (
            <div className="space-y-2">
              <h4 className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                <BrainIcon className="size-3.5 text-muted-foreground" />
                Skill 认知导轨规约
              </h4>
              <div className="rounded border border-border/50 bg-card/40 p-2.5 text-xs space-y-2">
                <div className="font-medium text-foreground">{plugin.skill.name}</div>
                <div className="text-xs text-muted-foreground font-mono bg-muted/30 p-2 rounded">
                  💡 {plugin.skill.sop_summary}
                </div>
                {plugin.skill.rules && plugin.skill.rules.length > 0 && (
                  <div className="space-y-1 pt-1">
                    <div className="text-xs font-medium text-muted-foreground">执行红线门禁:</div>
                    {plugin.skill.rules.map((rule, idx) => (
                      <div key={idx} className="flex items-center gap-1.5 text-xs text-foreground">
                        <CheckCircle2Icon className="size-3 text-cyan-400 shrink-0" />
                        <span>{rule}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 5. GUI 交互表单 (Dimension 4) */}
          <div className="space-y-2">
            <h4 className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
              <SlidersIcon className="size-3.5 text-muted-foreground" />
              GUI 配置模式 (DSH SettingsForm)
            </h4>
            <div className="rounded border border-border/50 bg-card/40 p-2.5 text-xs">
              <pre className="font-mono text-xs text-muted-foreground bg-muted/40 p-2 rounded overflow-x-auto">
                {JSON.stringify(plugin.gui?.settings_fields || {}, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      </ScrollArea>
    </div>
  )
}
