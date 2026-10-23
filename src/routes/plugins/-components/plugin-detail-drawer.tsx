/**
 * plugin-detail-drawer.tsx
 * 四位一体插件详情座舱抽屉组件 (1:1 像素级对齐反重力原生 Tab 架构与单一真相源 SSOT)。
 * 
 * 核心架构哲学:
 * 1. 【模块物理解耦 Tab 切换】：概览、技能、MCP、钩子、规则、接入指引 6 大 Tab 独立展示，杜绝长单页内容混淆与堆叠重复；
 * 2. 【README 核心首发与纯净单一真相源】：概览 Tab 仅渲染 suggestedPrompts + 纯净 README，绝不冗余混入安装命令；
 * 3. 【接入指引单轨收敛】：PowerShell、Bash、本地源码自举、DSH 以及运行时配置统一收敛至专门的“接入指引”Tab；
 * 4. 【严守黄金甜点区】：单文件 200~300 行，NO GREEN EVER 🚫，字号硬下限 >= 12px (text-xs)。
 */

import * as React from 'react'
import {
  BookOpenIcon,
  BrainIcon,
  LayersIcon,
  SearchIcon,
  ShieldAlertIcon,
  TerminalIcon,
  XIcon,
  ZapIcon,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { useAppConnection } from '#/hooks/use-app-connection'
import { useServerVersionDetails } from '#/hooks/use-server-version'
import {
  getPluginPrivilegeStatus,
  isPrivilegedTool,
  notifyPlugin403,
} from '../-lib/plugin-auth-guard'
import type { QuadPluginItem, ToolItem } from '../-lib/plugin-types'
import { PluginConfigSection } from './plugin-config-section'
import { PluginPromptsSection } from './plugin-prompts-section'
import { PluginQuickstartSection } from './plugin-quickstart-section'
import { PluginReadmeViewer } from './plugin-readme-viewer'
import { SearchIntegrationGuide } from './search-integration-guide'


export type PluginDetailDrawerProps = {
  plugin: QuadPluginItem | null
  onClose: () => void
}

type PluginTabId = 'overview' | 'skills' | 'mcp' | 'hooks' | 'rules' | 'quickstart'

export function PluginDetailDrawer({ plugin, onClose }: PluginDetailDrawerProps) {
  const { connectionRole } = useAppConnection()
  const versionDetails = useServerVersionDetails()
  const [activeTab, setActiveTab] = React.useState<PluginTabId>('overview')
  const [toolSearch, setToolSearch] = React.useState('')

  React.useEffect(() => {
    setActiveTab('overview')
    setToolSearch('')
  }, [plugin?.plugin_id])

  if (!plugin) return null

  const privilege = getPluginPrivilegeStatus(connectionRole, plugin.plugin_id)
  const tools = plugin.tools || []
  const hooks = plugin.hooks || []
  const skills = plugin.skills?.length ? plugin.skills : plugin.skill ? [plugin.skill] : []
  const rules = plugin.rules || []
  const cleanName = plugin.name.replace(/\s*\([^)]*\)/g, '').trim()

  const filteredTools = tools.filter((t) => {
    if (!toolSearch.trim()) return true
    const q = toolSearch.toLowerCase()
    return t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q)
  })

  const tabs: { id: PluginTabId; label: string; count?: number; icon: React.ComponentType<{ className?: string }> }[] = [
    { id: 'overview', label: '概览', icon: BookOpenIcon },
    { id: 'skills', label: '技能', count: skills.length, icon: BrainIcon },
    { id: 'mcp', label: 'MCP', count: tools.length, icon: LayersIcon },
    { id: 'hooks', label: '钩子', count: hooks.length, icon: ZapIcon },
    { id: 'rules', label: '规则', count: rules.length, icon: ShieldAlertIcon },
    { id: 'quickstart', label: '接入指引', icon: TerminalIcon },
  ]

  const renderToolCard = (tool: ToolItem) => {
    const isOps = isPrivilegedTool(tool)
    const isRestricted =
      !privilege.isAllowed ||
      (isOps && connectionRole !== 'admin' && connectionRole !== 'root')

    return (
      <div
        key={tool.name}
        onClick={() => {
          if (isRestricted) {
            notifyPlugin403(connectionRole, `工具 [${tool.name}]`)
          }
        }}
        className={`flex flex-col justify-between rounded-md border p-2.5 text-xs transition-colors cursor-pointer select-none ${
          isRestricted
            ? 'border-border/40 bg-card/30 hover:border-amber-500/40'
            : 'border-border/50 bg-card/50 hover:border-cyan-500/40 hover:bg-card/90'
        }`}
      >
        <div className="flex items-center justify-between gap-1.5">
          <div className="flex items-center gap-1.5 min-w-0">
            <span
              className={`font-mono font-semibold truncate ${
                isRestricted ? 'text-muted-foreground' : 'text-cyan-700 dark:text-cyan-400'
              }`}
            >
              {tool.name}
            </span>
            {tool.category && (
              <Badge
                variant="outline"
                className="text-xs font-mono px-1.5 py-0 text-muted-foreground/80 border-border/60"
              >
                {tool.category === 'ops' ? '特权运维' : tool.category}
              </Badge>
            )}
          </div>
          {isRestricted && (
            <Badge
              variant="outline"
              className="text-xs font-mono border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400 px-1.5 py-0 shrink-0"
            >
              需特权
            </Badge>
          )}
        </div>
        <p className="mt-1.5 text-xs text-muted-foreground line-clamp-2 leading-relaxed">
          {tool.description || '无详细描述'}
        </p>
      </div>
    )
  }

  return (
    <div
      role="dialog"
      aria-label={`${plugin.name} 详情抽屉`}
      className="fixed inset-y-0 right-0 z-50 flex w-full max-w-2xl flex-col border-l border-border/60 bg-background/95 backdrop-blur-md shadow-2xl transition-transform animate-in slide-in-from-right duration-200"
    >
      {/* 头部导航区 */}
      <div className="border-b border-border/60 p-4 space-y-2">
        <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground font-mono">
          <span>插件中心 / {plugin.plugin_id}</span>
          <Button
            variant="ghost"
            size="icon"
            className="size-7 rounded-md text-muted-foreground hover:text-foreground shrink-0"
            onClick={onClose}
          >
            <XIcon className="size-4" />
          </Button>
        </div>

        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <h2 className="text-base font-semibold tracking-tight text-foreground truncate">
              {cleanName}
            </h2>
            <Badge variant="outline" className="text-xs font-mono border-cyan-500/40 bg-cyan-500/10 text-cyan-700 dark:text-cyan-400 shrink-0">
              包: v{plugin.version}
            </Badge>
            {versionDetails?.version && (
              <Badge variant="outline" className="text-xs font-mono border-border/70 text-muted-foreground shrink-0">
                内核: v{versionDetails.version}
              </Badge>
            )}
            <Badge variant="outline" className="text-xs font-mono border-cyan-500/30 text-cyan-700 dark:text-cyan-400 shrink-0">
              ● {tools.length} 工具热更同频
            </Badge>
            {plugin.author && (
              <span className="text-xs text-muted-foreground truncate">
                by {plugin.author}
              </span>
            )}
          </div>
        </div>

        {/* 插件概述短说明 (1:1 对齐反重力原生头部描述) */}
        {plugin.description && (
          <p className="text-xs text-muted-foreground leading-relaxed pt-0.5">
            {plugin.description}
          </p>
        )}

        {/* 权限受限提示 */}
        {!privilege.isAllowed && (
          <div className="flex items-center justify-between gap-2 rounded border border-amber-500/40 bg-amber-500/10 px-2.5 py-1.5 text-xs text-amber-700 dark:text-amber-400">
            <div className="flex items-center gap-1.5 min-w-0">
              <ShieldAlertIcon className="size-3.5 shrink-0" />
              <span className="truncate">{privilege.reason || '当前为普通用户身份，特权运维受限'}</span>
            </div>
            <Badge
              variant="outline"
              className="border-amber-500/50 bg-amber-500/20 text-amber-700 dark:text-amber-300 text-xs shrink-0 font-mono"
            >
              受限模式
            </Badge>
          </div>
        )}
      </div>

      {/* 反重力原生孪生 Tab 切换条 (对齐图二: 概览 | 技能 | MCP | 钩子 | 规则 | 接入指引) */}
      <div className="flex items-center gap-1 border-b border-border/60 px-4 pt-1 bg-muted/10 overflow-x-auto no-scrollbar">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors whitespace-nowrap ${
                isActive
                  ? 'border-cyan-500 text-cyan-600 dark:text-cyan-400'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border/70'
              }`}
            >
              <Icon className="size-3.5 shrink-0" />
              <span>{tab.label}</span>
              {tab.count != null && (
                <span
                  className={`font-mono text-xs px-1 rounded ${
                    isActive
                      ? 'bg-cyan-500/15 text-cyan-600 dark:text-cyan-400 font-semibold'
                      : 'text-muted-foreground/70 bg-muted/40'
                  }`}
                >
                  {tab.count}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* 选项卡主体容器 */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4">
        {/* Tab 1: 概览 (Overview) */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            {plugin.suggested_prompts && plugin.suggested_prompts.length > 0 && (
              <PluginPromptsSection prompts={plugin.suggested_prompts} />
            )}
            <div className="rounded-md border border-border/40 bg-card/20 p-4">
              <PluginReadmeViewer
                content={plugin.readme_content}
                fallbackDescription={plugin.description}
              />
            </div>
          </div>
        )}

        {/* Tab 2: 技能 (Skills) */}
        {activeTab === 'skills' && (
          <div className="space-y-3">
            {skills.length === 0 ? (
              <div className="text-center py-8 text-xs text-muted-foreground">暂无特定认知导轨</div>
            ) : (
              skills.map((skill) => (
                <div
                  key={skill.skill_id}
                  className="rounded-md border border-border/50 bg-card/50 p-3 space-y-2 text-xs"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-foreground text-xs">{skill.name}</span>
                    <Badge
                      variant="outline"
                      className="text-xs font-mono border-cyan-500/30 bg-cyan-500/10 text-cyan-700 dark:text-cyan-400 px-1.5 py-0 shrink-0"
                    >
                      {skill.skill_id}
                    </Badge>
                  </div>
                  <p className="text-muted-foreground leading-relaxed text-xs">
                    {skill.description}
                  </p>
                  {skill.sop_summary && (
                    <div className="rounded border border-border/40 bg-muted/20 px-2.5 py-1.5 font-mono text-xs text-foreground/80 flex items-center gap-1.5">
                      <span className="text-cyan-600 dark:text-cyan-400 shrink-0 font-semibold">SOP:</span>
                      <span className="truncate">{skill.sop_summary}</span>
                    </div>
                  )}
                  {skill.rules?.length > 0 && (
                    <div className="space-y-1 pt-1">
                      <div className="text-muted-foreground text-xs font-medium">硬性规约与避坑指南:</div>
                      <ul className="space-y-1 pl-1">
                        {skill.rules.map((rule, idx) => (
                          <li key={idx} className="flex items-start gap-1.5 text-xs text-foreground/80 leading-relaxed">
                            <span className="size-1 rounded-full bg-cyan-500 shrink-0 mt-1.5" />
                            <span>{rule}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {/* Tab 3: MCP 物理算子 (MCP Tools) */}
        {activeTab === 'mcp' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-2">
              <div className="relative flex-1">
                <SearchIcon className="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={toolSearch}
                  onChange={(e) => setToolSearch(e.target.value)}
                  placeholder="筛选算子名称或功能描述..."
                  className="h-8 pl-8 text-xs font-mono"
                />
              </div>
              <span className="font-mono text-xs text-muted-foreground shrink-0">
                共 {filteredTools.length} 项算子
              </span>
            </div>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 pt-1">
              {filteredTools.map(renderToolCard)}
            </div>
          </div>
        )}

        {/* Tab 4: 钩子 (Hooks) */}
        {activeTab === 'hooks' && (
          <div className="space-y-3">
            {hooks.length === 0 ? (
              <div className="text-center py-8 text-xs text-muted-foreground">本插件暂未挂载常驻拦截守卫</div>
            ) : (
              hooks.map((hook) => (
                <div
                  key={hook.hook_id}
                  className="rounded-md border border-border/50 bg-card/50 p-3 space-y-1.5 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-foreground">{hook.name}</span>
                    <Badge
                      variant="outline"
                      className="text-xs font-mono border-cyan-500/30 bg-cyan-500/10 text-cyan-700 dark:text-cyan-400 px-1.5 py-0"
                    >
                      {hook.trigger_event}
                    </Badge>
                  </div>
                  <p className="text-muted-foreground leading-relaxed text-xs">
                    {hook.description}
                  </p>
                </div>
              ))
            )}
          </div>
        )}

        {/* Tab 5: 规则 (Rules) */}
        {activeTab === 'rules' && (
          <div className="space-y-3">
            {rules.length > 0 ? (
              rules.map((rule) => (
                <div
                  key={rule.name}
                  className="rounded-md border border-border/50 bg-card/50 p-3.5 space-y-2 text-xs"
                >
                  <div className="flex items-center justify-between gap-2 border-b border-border/40 pb-2">
                    <span className="font-semibold text-foreground text-xs flex items-center gap-1.5 font-mono">
                      <ShieldAlertIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
                      {rule.name}
                    </span>
                    <Badge variant="outline" className="text-xs font-mono border-border/60">
                      规约法则
                    </Badge>
                  </div>
                  {rule.description && rule.description !== rule.name && (
                    <div className="text-xs font-medium text-foreground/90">
                      {rule.description}
                    </div>
                  )}
                  <div className="font-mono text-xs text-foreground/80 whitespace-pre-wrap leading-relaxed rounded bg-muted/20 p-2.5 border border-border/30">
                    {rule.content}
                  </div>
                </div>
              ))
            ) : (
              <div className="rounded-md border border-border/40 bg-card/20 p-6 text-center text-xs text-muted-foreground space-y-1">
                <p className="font-semibold text-foreground">本插件遵循工作区全局法典与统一防线</p>
                <p>未配置独立 `.md` 规约文件，继承统一系统防震法则与奥卡姆剃刀守则。</p>
              </div>
            )}
          </div>
        )}

        {/* Tab 6: 接入指引 (Quickstart & Config) */}
        {activeTab === 'quickstart' && (
          <div className="space-y-4">
            {plugin.plugin_id === 'network-search' ? (
              <SearchIntegrationGuide />
            ) : (
              <PluginQuickstartSection plugin={plugin} />
            )}
            <div className="pt-2 border-t border-border/40">

              <h4 className="text-xs font-semibold text-foreground mb-2 flex items-center gap-1.5">
                <span>运行时核心参数与环境配置</span>
              </h4>
              <PluginConfigSection
                plugin={plugin}
                connectionRole={connectionRole}
                privilegeAllowed={privilege.isAllowed}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
