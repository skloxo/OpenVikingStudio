/**
 * plugin-detail-drawer.tsx
 * 四位一体插件全景规格与控制抽屉组件 (Cockpit UI 规范)。
 * 严守单文件黄金甜点区 (<= 350 行)、NO GREEN EVER 🚫、>= 12px 字体下限、全屏遮罩与零嵌套截断。
 */

import {
  BrainIcon,
  CheckCircle2Icon,
  CopyIcon,
  ExternalLinkIcon,
  LayersIcon,
  SearchIcon,
  ShieldAlertIcon,
  SlidersIcon,
  XIcon,
  ZapIcon,
} from 'lucide-react'
import * as React from 'react'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { copyTextToClipboard } from '#/lib/clipboard'
import type { QuadPluginItem, ToolItem } from '../-lib/plugin-types'
import { NetworkSearchDashboard } from './network-search-dashboard'
import { SearchIntegrationGuide } from './search-integration-guide'
import { VaultIntegrationGuide } from './vault-integration-guide'

export type PluginDetailDrawerProps = {
  plugin: QuadPluginItem | null
  onClose: () => void
}

type TabKey = 'all' | 'tools' | 'hooks' | 'skill' | 'config'

export function PluginDetailDrawer({ plugin, onClose }: PluginDetailDrawerProps) {
  const [activeTab, setActiveTab] = React.useState<TabKey>('all')
  const [toolSearch, setToolSearch] = React.useState('')
  const [copiedKey, setCopiedKey] = React.useState<string | null>(null)

  // 当插件切换时重置 Tab 与搜索词
  React.useEffect(() => {
    setActiveTab('all')
    setToolSearch('')
  }, [plugin?.plugin_id])

  if (!plugin) return null

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

  // 复制辅助函数
  const handleCopy = async (text: string, label: string) => {
    try {
      await copyTextToClipboard(text)
      setCopiedKey(label)
      toast.success(`${label} 已复制到剪贴板`)
      setTimeout(() => setCopiedKey(null), 2000)
    } catch {
      toast.error('复制失败，请手动选择复制')
    }
  }

  // 渲染单个工具卡片
  const renderToolCard = (tool: ToolItem) => (
    <div
      key={tool.name}
      className="flex flex-col justify-between rounded-md border border-border/50 bg-card/50 p-2.5 text-xs transition-colors hover:border-cyan-500/40 hover:bg-card/90"
    >
      <div className="flex items-center justify-between gap-1.5">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="font-mono font-semibold text-cyan-700 dark:text-cyan-400 truncate">
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
        {tool.is_dangerous && (
          <Badge
            variant="outline"
            className="text-xs font-mono border-rose-500/40 bg-rose-500/10 text-rose-700 dark:text-rose-400 px-1.5 py-0 shrink-0"
          >
            危险操作
          </Badge>
        )}
      </div>
      <p className="mt-1 text-muted-foreground leading-relaxed text-xs">
        {tool.description}
      </p>
    </div>
  )

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

          {/* 四位一体高密分段导航 Tab 条 */}
          <div className="mt-3 flex items-center gap-1 rounded-md border border-border/60 bg-muted/30 p-1 text-xs font-mono">
            {[
              { key: 'all', label: '全景全貌' },
              { key: 'tools', label: `MCP 工具 (${tools.length})` },
              { key: 'hooks', label: `Hook 拦截 (${hooks.length})` },
              { key: 'skill', label: '技能认知导轨' },
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

          {/* 专享大盘与接入指南：根据插件类型动态装配 */}
          {plugin.plugin_id === 'network-search' && (
            <div className="space-y-4">
              <SearchIntegrationGuide />
              {(activeTab === 'all' || activeTab === 'config') && <NetworkSearchDashboard />}
            </div>
          )}

          {plugin.plugin_id === 'keepass-vault' && (
            <VaultIntegrationGuide />
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
            <div className="space-y-3">
              <div className="flex items-center justify-between border-b border-border/40 pb-2">
                <h4 className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                  <SlidersIcon className="size-3.5 text-muted-foreground" />
                  GUI 交互视窗与核心参数配置
                </h4>
                {plugin.gui?.dashboard_route && (
                  <Badge variant="outline" className="text-xs font-mono text-cyan-700 dark:text-cyan-400 border-cyan-500/30 bg-cyan-500/10">
                    视窗路由: {plugin.gui.dashboard_route}
                  </Badge>
                )}
              </div>

              {/* 1. 专属控制视窗直通卡片 */}
              <div className="rounded-md border border-border/60 bg-muted/20 p-3 text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-foreground flex items-center gap-1.5">
                    <SlidersIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
                    {plugin.plugin_id === 'openviking-memory'
                      ? '全景记忆库与知识图谱视窗'
                      : plugin.plugin_id === 'network-search'
                        ? '在线搜索试验台与配额大盘'
                        : '凭据分组拓扑与体检视窗'}
                  </span>
                  <a
                    href={plugin.gui?.dashboard_route || '/'}
                    className="flex items-center gap-1 text-xs font-mono text-cyan-700 dark:text-cyan-400 hover:underline"
                  >
                    前往专属控制台
                    <ExternalLinkIcon className="size-3" />
                  </a>
                </div>
                <p className="text-muted-foreground leading-relaxed">
                  {plugin.plugin_id === 'openviking-memory'
                    ? '提供体外大脑长程记忆观测大盘、FTS5 全文索引、知识图谱拓扑与纯度审计。'
                    : plugin.plugin_id === 'network-search'
                      ? '提供多路 Key 轮询健康度观测、Credits 消耗流水账与爬虫渲染测试台。'
                      : '提供 KDBX 凭据分组拓扑树、弱密体检与自动化备份容灾管理。'}
                </p>
              </div>

              {/* 2. 结构化核心参数字典 */}
              <div className="space-y-1.5">
                <div className="text-xs font-medium text-muted-foreground">运行时核心配置参数:</div>
                <div className="grid gap-2">
                  {Object.entries(plugin.gui?.settings_fields || {}).map(([key, value]) => {
                    const valStr = String(value)
                    return (
                      <div
                        key={key}
                        className="flex items-center justify-between rounded-md border border-border/50 bg-card/40 p-2.5 text-xs font-mono"
                      >
                        <div className="min-w-0 pr-2">
                          <div className="text-muted-foreground text-xs font-sans">{key}</div>
                          <div className="truncate text-foreground font-medium text-xs mt-0.5" title={valStr}>
                            {valStr}
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 px-2 text-xs shrink-0"
                          onClick={() => handleCopy(valStr, key)}
                        >
                          <CopyIcon className="mr-1 size-3" />
                          {copiedKey === key ? '已复制' : '复制'}
                        </Button>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* 3. 架构解耦与通信契约自解释说明 */}
              <div className="rounded-md border border-border/40 bg-muted/10 p-3 text-xs leading-relaxed text-muted-foreground">
                <span className="font-semibold text-foreground">💡 架构解耦契约：</span>
                {plugin.plugin_id === 'openviking-memory' && (
                  <>
                    本插件为 OpenViking 服务端中心化核心能力。外部智能体只需接入通用的客户端通信桥梁 (
                    <code className="text-cyan-700 dark:text-cyan-400 font-mono">dsh-plugin-openviking</code>
                    )，即可通过统一通道安全调用全量长程记忆。
                  </>
                )}
                {plugin.plugin_id === 'network-search' && (
                  <>
                    本插件为独立微服务部署。支持<strong className="text-foreground">形态 A【原生标准 API (免装插件)】</strong>与<strong className="text-foreground">形态 B【定制插件 (
                    <code className="text-cyan-700 dark:text-cyan-400 font-mono">dsh-plugin-search-gateway</code>
                    )】</strong>双模态接入，底层共享 26-Key 轮询矩阵。
                  </>
                )}
                {plugin.plugin_id === 'keepass-vault' && (
                  <>
                    本插件与 OpenViking 服务端<strong className="text-foreground">零运行时强依赖</strong>。OpenViking 仅作为官方展示展厅与统一发布托管源，客户端直接通过 (
                    <code className="text-cyan-700 dark:text-cyan-400 font-mono">dsh-plugin-keepass-vault</code>
                    ) 读取智能体本地加密 KDBX。
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
