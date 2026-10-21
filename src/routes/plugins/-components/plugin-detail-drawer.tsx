/**
 * plugin-detail-drawer.tsx
 * 四位一体插件详情高密抽屉组件 (参考任务中心抽屉单页连续折叠交互)。
 * 
 * 核心设计哲学 (奥卡姆剃刀与单一真相源):
 * 1. 【切除碎裂 Tab】：废除切来切去的 Tab 条，改用单一自上而下的无缝阅读流；
 * 2. 【README 核心首发】：默认直览与反重力 100% 互通的原生 Markdown 介绍正文；
 * 3. 【可折叠技术附录】：算子全景、认知导轨、Hook 守卫、参数配置按需折叠/展开，绝不产生重复冗余；
 * 4. 【严守黄金甜点区】：单文件 <= 250 行，NO GREEN EVER 🚫，字体硬下限 >= 12px (text-xs)。
 */

import * as React from 'react'
import {
  BrainIcon,
  ChevronDownIcon,
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

function CollapsibleSection({
  title,
  count,
  icon,
  isOpen,
  onToggle,
  children,
}: {
  title: string
  count?: number
  icon: React.ReactNode
  isOpen: boolean
  onToggle: () => void
  children: React.ReactNode
}) {
  return (
    <div className="rounded-md border border-border/60 bg-card/40 overflow-hidden text-xs">
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center justify-between p-3 text-left font-medium text-foreground hover:bg-muted/30 transition-colors"
      >
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-cyan-600 dark:text-cyan-400">{icon}</span>
          <span className="font-semibold text-xs">{title}</span>
          {count != null && (
            <Badge variant="outline" className="text-xs font-mono px-1.5 py-0 border-border/70">
              {count}
            </Badge>
          )}
        </div>
        <ChevronDownIcon
          className={`size-4 text-muted-foreground transition-transform duration-200 ${
            isOpen ? 'rotate-180 text-foreground' : ''
          }`}
        />
      </button>
      {isOpen && <div className="border-t border-border/40 p-3 bg-background/50 space-y-3">{children}</div>}
    </div>
  )
}

export function PluginDetailDrawer({ plugin, onClose }: PluginDetailDrawerProps) {
  const { connectionRole } = useAppConnection()
  const [openTools, setOpenTools] = React.useState(false)
  const [openSkills, setOpenSkills] = React.useState(false)
  const [openHooks, setOpenHooks] = React.useState(false)
  const [openConfig, setOpenConfig] = React.useState(false)
  const [toolSearch, setToolSearch] = React.useState('')

  React.useEffect(() => {
    setOpenTools(false)
    setOpenSkills(false)
    setOpenHooks(false)
    setOpenConfig(false)
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

        {/* 核心能力徽章一行速览 (消灭碎片化 Tab) */}
        <div className="flex flex-wrap items-center gap-2 pt-1 font-mono text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <LayersIcon className="size-3 text-cyan-500" />
            <span>算子: {tools.length}</span>
          </span>
          <span className="text-border">·</span>
          <span className="flex items-center gap-1">
            <BrainIcon className="size-3 text-cyan-500" />
            <span>认知导轨: {skills.length}</span>
          </span>
          {hooks.length > 0 && (
            <>
              <span className="text-border">·</span>
              <span className="flex items-center gap-1">
                <ZapIcon className="size-3 text-cyan-500" />
                <span>守卫: {hooks.length}</span>
              </span>
            </>
          )}
          <span className="text-border">·</span>
          <Badge variant="outline" className="text-xs font-mono px-1.5 py-0 border-border/50">
            {plugin.category === 'platform' ? '系统核心' : '扩展生态'}
          </Badge>
        </div>

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

      {/* 滚动正文 (单页连续流: README 主体 + 技术字典折叠块) */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-5">
        {/* 1. 原生 Markdown 详情说明正文 (默认展示，与反重力完全对齐) */}
        <div className="rounded-md border border-border/40 bg-card/20 p-4">
          <PluginReadmeViewer
            content={plugin.readme_content}
            fallbackDescription={plugin.description}
          />
        </div>

        {/* 2. 技术字典与规约折叠区 (参考任务中心抽屉交互，按需展开查阅) */}
        <div className="space-y-3 pt-2">
          {/* 折叠块 1: MCP 原子算子全景 */}
          <CollapsibleSection
            title="MCP 原子算子全景明细"
            count={tools.length}
            icon={<LayersIcon className="size-3.5" />}
            isOpen={openTools}
            onToggle={() => setOpenTools(!openTools)}
          >
            <div className="relative">
              <SearchIcon className="absolute left-2.5 top-1/2 size-3 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={toolSearch}
                onChange={(e) => setToolSearch(e.target.value)}
                placeholder="筛选算子名称或描述..."
                className="h-7 pl-7 text-xs font-mono"
              />
            </div>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 pt-1">
              {filteredTools.map(renderToolCard)}
            </div>
          </CollapsibleSection>

          {/* 折叠块 2: 配套认知导轨与操作手册 */}
          {skills.length > 0 && (
            <CollapsibleSection
              title="配套专家操作手册与认知导轨"
              count={skills.length}
              icon={<BrainIcon className="size-3.5" />}
              isOpen={openSkills}
              onToggle={() => setOpenSkills(!openSkills)}
            >
              <div className="space-y-2.5">
                {skills.map((skill) => (
                  <div
                    key={skill.skill_id}
                    className="rounded-md border border-border/50 bg-card/50 p-3 space-y-2"
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
            </CollapsibleSection>
          )}

          {/* 折叠块 3: 生命周期 Hook 拦截守卫 */}
          {hooks.length > 0 && (
            <CollapsibleSection
              title="生命周期 Hook 拦截守卫"
              count={hooks.length}
              icon={<ZapIcon className="size-3.5" />}
              isOpen={openHooks}
              onToggle={() => setOpenHooks(!openHooks)}
            >
              <div className="space-y-2">
                {hooks.map((hook) => (
                  <div
                    key={hook.hook_id}
                    className="rounded-md border border-border/50 bg-card/50 p-2.5 space-y-1"
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
            </CollapsibleSection>
          )}

          {/* 折叠块 4: 运行时参数与环境配置 */}
          <CollapsibleSection
            title="运行时核心参数与环境配置"
            icon={<Settings2Icon className="size-3.5" />}
            isOpen={openConfig}
            onToggle={() => setOpenConfig(!openConfig)}
          >
            <PluginConfigSection
              plugin={plugin}
              connectionRole={connectionRole}
              privilegeAllowed={privilege.isAllowed}
            />
          </CollapsibleSection>
        </div>
      </div>
    </div>
  )
}
