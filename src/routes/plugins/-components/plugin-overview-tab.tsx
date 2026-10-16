/**
 * plugin-overview-tab.tsx
 * 插件全景高密概览规格组件 (Cockpit UI 规范)。
 *
 * 核心设计哲学 (奥卡姆剃刀与单一真相源)：
 * 1. 【切除机械平铺】：概览页仅呈现顶层能力指标与架构规格，严禁与子 Tab 重复平铺工具/Hook 列表；
 * 2. 【四维能力矩阵锚点】：以 4 宫格卡片呈现 MCP、Hook、技能与接入渠道，点击一键跳转对应专属 Tab；
 * 3. 视觉契约：NO GREEN EVER 🚫，字号硬下限 >= 12px (text-xs)，严格遵循黄金甜点区 (<= 250 行)。
 */

import * as React from 'react'
import {
  BrainIcon,
  ChevronRightIcon,
  LayersIcon,
  ServerIcon,
  ShieldCheckIcon,
  SparklesIcon,
  ZapIcon,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import type { ConnectionRole } from '#/hooks/app-connection-types'
import type { QuadPluginItem } from '../-lib/plugin-types'

export type PluginOverviewTabProps = {
  plugin: QuadPluginItem
  privilege: { isAllowed: boolean; reason?: string }
  connectionRole: ConnectionRole
  onNavigateTab: (tab: 'tools' | 'hooks' | 'skill' | 'install' | 'config') => void
}

export function PluginOverviewTab({
  plugin,
  privilege,
  connectionRole,
  onNavigateTab,
}: PluginOverviewTabProps) {
  const isHealthy = plugin.health.status === 'healthy'
  const tools = plugin.tools || []
  const hooks = plugin.hooks || []
  const hasSkill = Boolean(plugin.skill)
  const isMemoryPlugin = plugin.plugin_id === 'openviking-memory'

  const opsToolsCount = tools.filter((t) => t.category === 'ops').length
  const consumerToolsCount = tools.length - opsToolsCount

  return (
    <div className="space-y-4 font-sans text-xs">
      {/* 1. 运行态探针与核心定位 */}
      <div className="rounded-md border border-border/60 bg-muted/20 p-3.5 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ServerIcon className="size-4 text-cyan-500" />
            <span className="font-semibold text-foreground text-xs">底层运行态探针与生态归属</span>
          </div>
          <Badge
            variant="outline"
            className={`text-xs font-mono ${
              isHealthy
                ? 'border-cyan-500/30 bg-cyan-500/10 text-cyan-700 dark:text-cyan-400'
                : 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400'
            }`}
          >
            {isHealthy ? '探针存活' : '状态异常'} · 本地响应 {plugin.health?.latency_ms?.toFixed(1) || '0.1'}ms
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">
          {plugin.description}
        </p>
        {plugin.health?.message && (
          <p className="font-mono text-xs text-muted-foreground/70">
            探活详情：{plugin.health.message}
          </p>
        )}
      </div>

      {/* 2. 四维能力矩阵导航卡片 (4-Grid) */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="font-semibold text-foreground text-xs flex items-center gap-1.5">
            <SparklesIcon className="size-3.5 text-cyan-500" />
            四维能力指标矩阵与快速导览
          </span>
          <span className="text-muted-foreground font-mono text-xs">点击卡片直达对应专属详情</span>
        </div>

        <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
          {/* 维度 1: MCP 工具能力 */}
          <button
            type="button"
            onClick={() => onNavigateTab('tools')}
            className="group flex flex-col justify-between rounded-md border border-border/60 bg-card/40 p-3 text-left transition-all hover:border-cyan-500/50 hover:bg-card/80"
          >
            <div className="flex items-center justify-between w-full">
              <div className="flex items-center gap-2">
                <LayersIcon className="size-4 text-cyan-500 transition-transform group-hover:scale-110" />
                <span className="font-semibold text-foreground text-xs">MCP 工具能力池</span>
              </div>
              <Badge variant="outline" className="font-mono text-xs border-cyan-500/30 text-cyan-700 dark:text-cyan-400">
                {tools.length} 项
              </Badge>
            </div>
            <p className="mt-2 text-xs text-muted-foreground line-clamp-2">
              {isMemoryPlugin
                ? `包含 ${consumerToolsCount} 项业务使用者原子工具与 ${opsToolsCount} 项管理运维特权工具。`
                : `向智能体暴露 ${tools.length} 个标准函数调用接口，支撑领域计算与执行。`}
            </p>
            <div className="mt-3 flex items-center gap-1 text-cyan-600 dark:text-cyan-400 font-medium group-hover:underline">
              <span>查阅全部 MCP 工具与参数</span>
              <ChevronRightIcon className="size-3 transition-transform group-hover:translate-x-0.5" />
            </div>
          </button>

          {/* 维度 2: Hook 神经反射 */}
          <button
            type="button"
            onClick={() => onNavigateTab('hooks')}
            className="group flex flex-col justify-between rounded-md border border-border/60 bg-card/40 p-3 text-left transition-all hover:border-cyan-500/50 hover:bg-card/80"
          >
            <div className="flex items-center justify-between w-full">
              <div className="flex items-center gap-2">
                <ZapIcon className="size-4 text-cyan-500 transition-transform group-hover:scale-110" />
                <span className="font-semibold text-foreground text-xs">Hook 拦截神经反射</span>
              </div>
              <Badge variant="outline" className="font-mono text-xs border-cyan-500/30 text-cyan-700 dark:text-cyan-400">
                {hooks.length} 处
              </Badge>
            </div>
            <p className="mt-2 text-xs text-muted-foreground line-clamp-2">
              {hooks.length > 0
                ? `拦截事件点：${hooks.map((h) => h.trigger_event).join(' / ')}。`
                : '暂无生命周期拦截事件。'}
            </p>
            <div className="mt-3 flex items-center gap-1 text-cyan-600 dark:text-cyan-400 font-medium group-hover:underline">
              <span>查看拦截事件流与守卫规则</span>
              <ChevronRightIcon className="size-3 transition-transform group-hover:translate-x-0.5" />
            </div>
          </button>

          {/* 维度 3: 技能认知导轨 */}
          <button
            type="button"
            onClick={() => onNavigateTab('skill')}
            className="group flex flex-col justify-between rounded-md border border-border/60 bg-card/40 p-3 text-left transition-all hover:border-cyan-500/50 hover:bg-card/80"
          >
            <div className="flex items-center justify-between w-full">
              <div className="flex items-center gap-2">
                <BrainIcon className="size-4 text-cyan-500 transition-transform group-hover:scale-110" />
                <span className="font-semibold text-foreground text-xs">技能认知导轨规约</span>
              </div>
              <Badge variant="outline" className="font-mono text-xs border-border/70 text-muted-foreground">
                {hasSkill ? '已绑定 SOP' : '无导轨'}
              </Badge>
            </div>
            <p className="mt-2 text-xs text-muted-foreground line-clamp-2">
              {plugin.skill
                ? `内嵌领域 SOP 规约：${plugin.skill.name}，包含执行红线与红绿循环法门。`
                : '本插件未挂载独立 SKILL.md 导轨，依赖通用 Agent 潜意识。'}
            </p>
            <div className="mt-3 flex items-center gap-1 text-cyan-600 dark:text-cyan-400 font-medium group-hover:underline">
              <span>查阅标准作业程序 (SOP)</span>
              <ChevronRightIcon className="size-3 transition-transform group-hover:translate-x-0.5" />
            </div>
          </button>

          {/* 维度 4: 客户端接入指南 */}
          <button
            type="button"
            onClick={() => onNavigateTab('install')}
            className="group flex flex-col justify-between rounded-md border border-border/60 bg-card/40 p-3 text-left transition-all hover:border-cyan-500/50 hover:bg-card/80"
          >
            <div className="flex items-center justify-between w-full">
              <div className="flex items-center gap-2">
                <SparklesIcon className="size-4 text-cyan-500 transition-transform group-hover:scale-110" />
                <span className="font-semibold text-foreground text-xs">客户端接入指南</span>
              </div>
              <Badge variant="outline" className="font-mono text-xs border-cyan-500/30 text-cyan-700 dark:text-cyan-400">
                一键认主
              </Badge>
            </div>
            <p className="mt-2 text-xs text-muted-foreground line-clamp-2">
              提供 Google 反重力、DeepSeek Harness 与通用 MCP 的一键认主 Prompt 与配置指令。
            </p>
            <div className="mt-3 flex items-center gap-1 text-cyan-600 dark:text-cyan-400 font-medium group-hover:underline">
              <span>获取专属认主提示词与命令</span>
              <ChevronRightIcon className="size-3 transition-transform group-hover:translate-x-0.5" />
            </div>
          </button>
        </div>
      </div>

      {/* 3. 架构与治理合规说明 */}
      <div className="rounded-md border border-border/50 bg-background/60 p-3 space-y-1.5 text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5 text-foreground font-semibold">
          <ShieldCheckIcon className="size-3.5 text-cyan-500" />
          <span>人机平权与治理契约</span>
        </div>
        <p className="leading-relaxed">
          插件通过标准不可变桥梁或本地驱动加载。高危特权与运维接口受 RBAC 严格管控，调用方凭据需具备相应授权。
        </p>
      </div>
    </div>
  )
}
