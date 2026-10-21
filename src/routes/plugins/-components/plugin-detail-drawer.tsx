/**
 * plugin-detail-drawer.tsx
 * 四位一体插件全景规格与详情抽屉组件 (Cockpit UI 规范)。
 * 
 * 核心设计哲学 (与 Google Antigravity 插件介绍页互通 SSOT):
 * 1. 【一源两端】：默认以 Markdown 渲染插件根目录下的原生 README.md，两端展现完全一致；
 * 2. 【脱水聚焦】：主 Tab 为详情介绍，辅 Tab 仅保留 MCP 工具池、Hook 守卫与参数配置；
 * 3. 【真实权限拦截】：严格执行权限拦截门禁；
 * 4. 【严守黄金甜点区】：单文件 <= 300 行，NO GREEN EVER 🚫，字体硬下限 >= 12px (text-xs)。
 */

import * as React from 'react'
import {
  BrainIcon,
  FileTextIcon,
  LayersIcon,
  SearchIcon,
  Settings2Icon,
  ShieldAlertIcon,
  XIcon,
  ZapIcon,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { useAppConnection } from '#/hooks/use-app-connection'
import {
  getPluginPrivilegeStatus,
  isPrivilegedTool,
  notifyPlugin403,
} from '../-lib/plugin-auth-guard'
import type { QuadPluginItem, ToolItem } from '../-lib/plugin-types'
import { PluginConfigSection } from './plugin-config-section'
import { PluginReadmeViewer } from './plugin-readme-viewer'

export type PluginDetailDrawerProps = {
  plugin: QuadPluginItem | null
  onClose: () => void
}

type TabKey = 'readme' | 'tools' | 'skills' | 'hooks' | 'config'

export function PluginDetailDrawer({ plugin, onClose }: PluginDetailDrawerProps) {
  const { connectionRole } = useAppConnection()
  const [activeTab, setActiveTab] = React.useState<TabKey>('readme')
  const [toolSearch, setToolSearch] = React.useState('')

  React.useEffect(() => {
    setActiveTab('readme')
    setToolSearch('')
  }, [plugin?.plugin_id])

  if (!plugin) return null

  const privilege = getPluginPrivilegeStatus(connectionRole, plugin.plugin_id)
  const tools = plugin.tools || []
  const hooks = plugin.hooks || []
  const skills = plugin.skills?.length ? plugin.skills : plugin.skill ? [plugin.skill] : []
  const cleanName = plugin.name.replace(/\s*\([^)]*\)/g, '').trim()

  const filteredTools = tools.filter((t) => {
    if (!toolSearch.trim()) return true
    const q = toolSearch.toLowerCase()
    return t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q)
  })


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

  const tabs: { key: TabKey; label: string; icon: React.ReactNode }[] = [
    { key: 'readme', label: '详情介绍 (README)', icon: <FileTextIcon className="size-3.5" /> },
    { key: 'tools', label: `MCP 工具 (${tools.length})`, icon: <LayersIcon className="size-3.5" /> },
    ...(skills.length > 0
      ? [{ key: 'skills' as TabKey, label: `认知导轨 (${skills.length})`, icon: <BrainIcon className="size-3.5" /> }]
      : []),
    ...(hooks.length > 0
      ? [{ key: 'hooks' as TabKey, label: `Hook 守卫 (${hooks.length})`, icon: <ZapIcon className="size-3.5" /> }]
      : []),
    { key: 'config', label: '参数配置', icon: <Settings2Icon className="size-3.5" /> },
  ]


  return (
    <div
      role="dialog"
      aria-label={`${plugin.name} 详情抽屉`}
      className="fixed inset-y-0 right-0 z-50 flex w-full max-w-2xl flex-col border-l border-border/60 bg-background/95 backdrop-blur-md shadow-2xl transition-transform animate-in slide-in-from-right duration-200"
    >
      {/* 头部导航区 */}
      <div className="border-b border-border/60 p-4 space-y-2.5">
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
            <Badge variant="outline" className="text-xs font-mono border-border/70 shrink-0">
              v{plugin.version}
            </Badge>
            {plugin.author && (
              <span className="text-xs text-muted-foreground truncate">
                by {plugin.author}
              </span>
            )}
          </div>
        </div>

        {/* 权限提示 */}
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

        {/* Tab 导航栏 */}
        <div className="flex items-center gap-1 rounded-md border border-border/60 bg-muted/30 p-1 text-xs font-mono">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.key
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={`flex-1 flex items-center justify-center gap-1.5 rounded px-2 py-1 text-center font-medium transition-all ${
                  isActive
                    ? 'border border-cyan-500/40 bg-background text-cyan-700 dark:text-cyan-300 shadow-xs'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/40'
                }`}
              >
                {tab.icon}
                <span>{tab.label}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* 滚动正文 */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4">
        {/* Tab 1: 详情介绍 (README 渲染 - 标杆互通) */}
        {activeTab === 'readme' && (
          <PluginReadmeViewer
            content={plugin.readme_content}
            fallbackDescription={plugin.description}
          />
        )}

        {/* Tab 2: MCP 工具 */}
        {activeTab === 'tools' && (
          <div className="space-y-3 font-sans text-xs">
            <div className="flex items-center justify-between gap-2 border-b border-border/40 pb-2">
              <h4 className="flex items-center gap-1.5 font-semibold text-foreground">
                <LayersIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
                MCP 原子工具全景 ({filteredTools.length}/{tools.length})
              </h4>
              <div className="relative w-48">
                <SearchIcon className="absolute left-2 top-1/2 size-3 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={toolSearch}
                  onChange={(e) => setToolSearch(e.target.value)}
                  placeholder="过滤工具名称或描述..."
                  className="h-6.5 pl-6 text-xs font-mono"
                />
              </div>
            </div>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {filteredTools.map(renderToolCard)}
            </div>
          </div>
        )}

        {/* Tab 3: 认知导轨 (专属 Skill 认知层) */}
        {activeTab === 'skills' && (
          <div className="space-y-3 font-sans text-xs">
            <div className="flex items-center justify-between border-b border-border/40 pb-2">
              <h4 className="flex items-center gap-1.5 font-semibold text-foreground">
                <BrainIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
                配套专家操作手册与认知导轨 ({skills.length})
              </h4>
              <Badge variant="outline" className="text-xs font-mono border-border/60">
                认知层规约
              </Badge>
            </div>
            <div className="space-y-2.5">
              {skills.map((skill) => (
                <div
                  key={skill.skill_id}
                  className="rounded-md border border-border/50 bg-card/40 p-3 space-y-2"
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
                      <span className="text-cyan-600 dark:text-cyan-400 shrink-0">SOP:</span>
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
              ))}
            </div>
          </div>
        )}

        {/* Tab 4: Hook 守卫 */}
        {activeTab === 'hooks' && (

          <div className="space-y-2.5 font-sans text-xs">
            <h4 className="flex items-center gap-1.5 font-semibold text-foreground border-b border-border/40 pb-2">
              <ZapIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
              Hook 拦截事件与生命周期神经反射 ({hooks.length})
            </h4>
            <div className="space-y-2">
              {hooks.map((hook) => (
                <div
                  key={hook.hook_id}
                  className="rounded-md border border-border/50 bg-card/40 p-3 space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-foreground">{hook.name}</span>
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
              ))}
            </div>
          </div>
        )}

        {/* Tab 4: 参数配置 */}
        {activeTab === 'config' && (
          <PluginConfigSection
            plugin={plugin}
            connectionRole={connectionRole}
            privilegeAllowed={privilege.isAllowed}
          />
        )}
      </div>
    </div>
  )
}
