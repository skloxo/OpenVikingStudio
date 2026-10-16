/**
 * plugin-detail-drawer.tsx
 * 四位一体插件全景规格与控制抽屉组件 (Cockpit UI 规范)。
 * 严守单文件黄金甜点区 (<= 350 行)、NO GREEN EVER 🚫、>= 12px 字体下限、全屏遮罩与零嵌套截断。
 */

import {
  BrainIcon,
  CheckCircle2Icon,
  LayersIcon,
  SearchIcon,
  ShieldAlertIcon,
  XIcon,
  ZapIcon,
} from 'lucide-react'
import * as React from 'react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { useAppConnection } from '#/hooks/use-app-connection'
import {
  getPluginPrivilegeStatus,
  isPrivilegedPlugin,
  isPrivilegedTool,
  notifyPlugin403,
} from '../-lib/plugin-auth-guard'
import type { QuadPluginItem, ToolItem } from '../-lib/plugin-types'
import { NativeBridgeIntegrationGuide } from './native-bridge-integration-guide'
import { PluginConfigSection } from './plugin-config-section'
import { SearchIntegrationGuide } from './search-integration-guide'
import { VaultIntegrationGuide } from './vault-integration-guide'

export type PluginDetailDrawerProps = {
  plugin: QuadPluginItem | null
  onClose: () => void
}

type TabKey = 'all' | 'tools' | 'hooks' | 'skill' | 'install' | 'config'

export function PluginDetailDrawer({ plugin, onClose }: PluginDetailDrawerProps) {
  const { connectionRole } = useAppConnection()
  const [activeTab, setActiveTab] = React.useState<TabKey>('all')
  const [toolSearch, setToolSearch] = React.useState('')

  // 当插件切换时重置 Tab 与搜索词
  React.useEffect(() => {
    setActiveTab('all')
    setToolSearch('')
  }, [plugin?.plugin_id])

  if (!plugin) return null

  const privilege = getPluginPrivilegeStatus(connectionRole, plugin.plugin_id)
  const isHealthy = plugin.health.status === 'healthy'
  const tools = plugin.tools || []
  const hooks = plugin.hooks || []
  const cleanName = plugin.name.replace(/\s*\([^)]*\)/g, '').trim()

  // 工具过滤
  const filteredTools = tools.filter((t) => {
    if (!toolSearch.trim()) return true
    const q = toolSearch.toLowerCase()
    return t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q)
  })

  // 按分类对工具进行角色拆分
  const consumerTools = filteredTools.filter((t) => t.category !== 'ops')
  const opsTools = filteredTools.filter((t) => t.category === 'ops')
  const isMemoryPlugin = plugin.plugin_id === 'openviking-memory'

  // 渲染单个工具卡片 (Card-144 权限拦截门禁)
  const renderToolCard = (tool: ToolItem) => {
    const isOps = isPrivilegedTool(tool)
    const isRestricted = !privilege.isAllowed || (isOps && connectionRole !== 'admin' && connectionRole !== 'root')

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
          <div className="flex items-center gap-1 shrink-0">
            {isRestricted && (
              <Badge
                variant="outline"
                className="text-xs font-mono border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400 px-1.5 py-0 shrink-0"
              >
                需特权
              </Badge>
            )}
            {tool.is_dangerous && (
              <Badge
                variant="outline"
                className="text-xs font-mono border-rose-500/40 bg-rose-500/10 text-rose-700 dark:text-rose-400 px-1.5 py-0 shrink-0"
              >
                危险操作
              </Badge>
            )}
          </div>
        </div>
        <p className="mt-1 text-muted-foreground leading-relaxed text-xs">
          {tool.description}
        </p>
      </div>
    )
  }

  return (
    <>
      {/* 1. 全屏背景遮罩 (点击外部优雅退出) */}
      <div
        className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs transition-opacity animate-in fade-in duration-200"
        onClick={onClose}
      />

      {/* 2. 宽幅座舱级抽屉主视窗 */}
      <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-2xl flex-col border-l border-border/80 bg-background shadow-2xl transition-all animate-in slide-in-from-right duration-200">
        {/* 头部导航区 */}
        <div className="border-b border-border/60 p-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2.5 min-w-0">
              <h2 className="text-base font-semibold tracking-tight text-foreground truncate">
                {cleanName}
              </h2>
              <Badge variant="outline" className="text-xs font-mono border-border/70 shrink-0">
                v{plugin.version}
              </Badge>
              <span className="font-mono text-xs text-muted-foreground/70 truncate">
                {plugin.plugin_id}
              </span>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="size-7 rounded-md text-muted-foreground hover:text-foreground shrink-0"
              onClick={onClose}
            >
              <XIcon className="size-4" />
            </Button>
          </div>

          {/* 权限状态提示条 (Card-144) */}
          {!privilege.isAllowed ? (
            <div className="mt-2.5 flex items-center justify-between gap-2 rounded border border-amber-500/40 bg-amber-500/10 px-2.5 py-1.5 text-xs text-amber-700 dark:text-amber-400">
              <div className="flex items-center gap-1.5 min-w-0">
                <ShieldAlertIcon className="size-3.5 shrink-0" />
                <span className="truncate">{privilege.reason || '当前为普通用户身份，特权运维受限'}</span>
              </div>
              <Badge variant="outline" className="border-amber-500/50 bg-amber-500/20 text-amber-700 dark:text-amber-300 text-xs shrink-0 font-mono">
                受限模式
              </Badge>
            </div>
          ) : isPrivilegedPlugin(plugin.plugin_id) ? (
            <div className="mt-2.5 flex items-center justify-between gap-2 rounded border border-cyan-500/40 bg-cyan-500/10 px-2.5 py-1.5 text-xs text-cyan-700 dark:text-cyan-300">
              <div className="flex items-center gap-1.5 min-w-0">
                <CheckCircle2Icon className="size-3.5 shrink-0 text-cyan-500" />
                <span className="truncate">平台特权已就绪：当前处于管理员模式 ({connectionRole})</span>
              </div>
              <Badge variant="outline" className="border-cyan-500/50 bg-cyan-500/20 text-cyan-700 dark:text-cyan-300 text-xs shrink-0 font-mono">
                Admin 授权
              </Badge>
            </div>
          ) : null}

          {/* 四位一体高密分段导航 Tab 条 */}
          <div className="mt-3 flex items-center gap-1 rounded-md border border-border/60 bg-muted/30 p-1 text-xs font-mono">
            {[
              { key: 'all', label: '全景全貌' },
              { key: 'tools', label: `MCP 工具 (${tools.length})` },
              { key: 'hooks', label: `Hook 拦截 (${hooks.length})` },
              { key: 'skill', label: '技能认知导轨' },
              { key: 'install', label: '客户端接入' },
              { key: 'config', label: 'GUI 视窗与参数' },
            ].map((tab) => {
              const isActive = activeTab === tab.key
              return (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => setActiveTab(tab.key as TabKey)}
                  className={`flex-1 rounded px-2 py-1 text-center font-medium transition-all ${
                    isActive
                      ? 'border border-cyan-500/40 bg-background text-cyan-700 dark:text-cyan-300 shadow-xs'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted/40'
                  }`}
                >
                  {tab.label}
                </button>
              )
            })}
          </div>
        </div>

        {/* 抽屉平滑自然滚动正文 (彻底消灭嵌套截断与 flex 溢出) */}
        <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-5">
          {/* 运行态探针健康条 (全局常驻) */}
          <div className="rounded-md border border-border/60 bg-muted/20 p-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-foreground">底层运行态探针</span>
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
            <p className="mt-1.5 text-xs text-muted-foreground leading-relaxed">
              {plugin.description}
            </p>
            {plugin.health?.message && (
              <p className="mt-1 font-mono text-xs text-muted-foreground/70">
                探活详情：{plugin.health.message}
              </p>
            )}
          </div>

          {/* 接入指南：根据插件类型动态装配 */}
          {(activeTab === 'all' || activeTab === 'install') && (
            <div className="space-y-4">
              {plugin.plugin_id === 'network-search' && <SearchIntegrationGuide />}
              {plugin.plugin_id === 'keepass-vault' && <VaultIntegrationGuide />}
              {plugin.plugin_id !== 'network-search' && plugin.plugin_id !== 'keepass-vault' && (
                <NativeBridgeIntegrationGuide
                  pluginId={plugin.plugin_id}
                  pluginName={cleanName}
                />
              )}
            </div>
          )}

          {/* ================= 维度一：MCP 工具池 ================= */}
          {(activeTab === 'all' || activeTab === 'tools') && (
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-2 border-b border-border/40 pb-2">
                <h4 className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                  <LayersIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
                  MCP 标准工具全景 ({filteredTools.length}/{tools.length})
                </h4>
                {/* 搜索框 */}
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

              {/* 针对核心记忆插件进行角色工具包拆解展示 */}
              {isMemoryPlugin ? (
                <div className="space-y-4">
                  {/* 业务使用者工具包 (31 项) */}
                  {consumerTools.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-foreground flex items-center gap-1.5">
                          <span className="size-1.5 rounded-full bg-cyan-500" />
                          业务使用者工具包 ({consumerTools.length} 项)
                        </span>
                        <span className="text-muted-foreground/70 font-mono">
                          通用智能体 · 检索/记忆/代码/工单
                        </span>
                      </div>
                      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                        {consumerTools.map(renderToolCard)}
                      </div>
                    </div>
                  )}

                  {/* 中枢运维特权工具包 (16 项) */}
                  {opsTools.length > 0 && (
                    <div className="space-y-2 pt-2 border-t border-border/30">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-rose-700 dark:text-rose-400 flex items-center gap-1.5">
                          <ShieldAlertIcon className="size-3 text-rose-500" />
                          中枢运维特权工具包 ({opsTools.length} 项)
                        </span>
                        <span className="text-muted-foreground/70 font-mono">
                          主控特权 · 需管理员权限
                        </span>
                      </div>
                      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                        {opsTools.map(renderToolCard)}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                /* 其他插件直接全平铺网格展示 */
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {filteredTools.map(renderToolCard)}
                </div>
              )}
            </div>
          )}

          {/* ================= 维度二：Hook 神经反射拦截 ================= */}
          {(activeTab === 'all' || activeTab === 'hooks') && (
            <div className="space-y-2.5">
              <h4 className="flex items-center gap-1.5 text-xs font-semibold text-foreground border-b border-border/40 pb-2">
                <ZapIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
                Hook 拦截事件与神经反射 ({hooks.length})
              </h4>
              <div className="space-y-2">
                {hooks.map((hook) => (
                  <div
                    key={hook.hook_id}
                    className="rounded-md border border-border/50 bg-card/40 p-3 text-xs space-y-1.5"
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

          {/* ================= 维度三：技能认知导轨 ================= */}
          {(activeTab === 'all' || activeTab === 'skill') && plugin.skill && (
            <div className="space-y-2.5">
              <h4 className="flex items-center gap-1.5 text-xs font-semibold text-foreground border-b border-border/40 pb-2">
                <BrainIcon className="size-3.5 text-muted-foreground" />
                技能认知导轨规约
              </h4>
              <div className="rounded-md border border-border/50 bg-card/40 p-3.5 text-xs space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-foreground text-xs">{plugin.skill.name}</span>
                  <Badge variant="outline" className="text-xs font-mono text-muted-foreground">
                    {plugin.skill.skill_id}
                  </Badge>
                </div>
                <div className="rounded bg-muted/40 p-2.5 font-mono text-xs text-muted-foreground leading-relaxed">
                  💡 <strong>标准流程 (SOP)：</strong>
                  <div className="mt-1 text-foreground/90">{plugin.skill.sop_summary}</div>
                </div>
                {plugin.skill.rules && plugin.skill.rules.length > 0 && (
                  <div className="space-y-1.5 pt-1">
                    <div className="font-medium text-muted-foreground text-xs">执行红线门禁:</div>
                    <div className="grid gap-1">
                      {plugin.skill.rules.map((rule, idx) => (
                        <div key={idx} className="flex items-center gap-1.5 text-xs text-foreground">
                          <CheckCircle2Icon className="size-3 text-cyan-400 shrink-0" />
                          <span>{rule}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ================= 维度四：GUI 交互视窗与运行配置 ================= */}
          {(activeTab === 'all' || activeTab === 'config') && (
            <PluginConfigSection plugin={plugin} />
          )}
        </div>
      </div>
    </>
  )
}
