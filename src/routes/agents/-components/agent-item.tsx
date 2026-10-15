/**
 * agent-item.tsx
 * 智能体中心单个智能体资产卡片主容器组件 (Cockpit UI 规范)。
 *
 * 核心架构哲学：
 * 1. 极致单行座舱：折叠态仅占一行，高密集成名称、描述、状态、统计、ID与快捷操作；
 * 2. 就地内联编辑：点击「编辑」直接在第一行内就地修改名称与描述，彻底切除冗余大输入框；
 * 3. 展开即插件：展开后直接呈现插件瓦片网格，零多余表单底栏；
 * 4. 真实物理状态机：待接入 / 活跃 / 休眠 / 已停用，杜绝硬编码假正常；
 * 5. 遵行 Cockpit UI 视觉规范：NO GREEN EVER 🚫，字号硬下限 >= 12px (text-xs)。
 */

import * as React from 'react'
import {
  ChevronDownIcon,
  ChevronRightIcon,
  Edit3Icon,
  LoaderCircleIcon,
  RotateCcwIcon,
  SaveIcon,
  TerminalIcon,
  Trash2Icon,
  XIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import type { UpdateAgentInput, UserAgentItem } from '#/lib/admin'
import type { PluginCapability, ToolBundle } from '../-lib/capability-bundles'
import { PLUGIN_CAPABILITIES } from '../-lib/capability-bundles'
import { AgentBridgeDrawer } from './agent-bridge-drawer'
import { PluginConfigDrawer } from './plugin-config-drawer'
import { PluginTiles } from './plugin-tiles'

export type AgentItemProps = {
  agent: UserAgentItem
  userId: string
  userRole?: string
  isExpanded: boolean
  onToggleExpand: () => void
  onUpdate: (agentId: string, input: UpdateAgentInput) => Promise<any> | void
  onDelete: (agent: UserAgentItem) => void
  onActivate: (agentId: string) => void
  isUpdating: boolean
}

function formatLastSeen(lastSeen?: number): string {
  if (!lastSeen || lastSeen <= 0) return '尚未接入'
  const diffSec = Math.floor(Date.now() / 1000 - lastSeen)
  if (diffSec < 60) return '刚刚'
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)} 分钟前`
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} 小时前`
  return `${Math.floor(diffSec / 86400)} 天前`
}

function getAgentLiveStatus(agent: UserAgentItem): {
  label: string
  dotColor: string
  detail: string
} {
  if (agent.status !== 'active') {
    return { label: '已停用', dotColor: 'bg-muted-foreground/40', detail: '' }
  }
  // 如果从未接入过或无交互记录
  if (!agent.last_seen || agent.last_seen <= 0 || !agent.total_messages || agent.total_messages === 0) {
    return { label: '待接入', dotColor: 'bg-muted-foreground/40', detail: '' }
  }
  const diffSec = Math.floor(Date.now() / 1000 - agent.last_seen)
  const timeStr = formatLastSeen(agent.last_seen)
  if (diffSec < 3600) {
    return { label: '活跃', dotColor: 'bg-cyan-500', detail: `最后交互: ${timeStr}` }
  }
  return { label: '休眠', dotColor: 'bg-muted-foreground/40', detail: `最后交互: ${timeStr}` }
}

export function AgentItem({
  agent,
  userId,
  isExpanded,
  onToggleExpand,
  onUpdate,
  onDelete,
  onActivate,
  isUpdating,
}: AgentItemProps) {
  const [name, setName] = React.useState(agent.agent_name || '')
  const [roleDesc, setRoleDesc] = React.useState(agent.role_desc || '')
  const [isEditing, setIsEditing] = React.useState(false)
  const [selectedTools, setSelectedTools] = React.useState<string[]>(agent.allowed_tools)
  const [activeBundleIds, setActiveBundleIds] = React.useState<Set<string>>(new Set())
  const [drawerPlugin, setDrawerPlugin] = React.useState<PluginCapability | null>(null)
  const [showBridgeDrawer, setShowBridgeDrawer] = React.useState(false)

  // Hook 状态
  const [hooksState, setHooksState] = React.useState<Record<string, boolean>>({
    ov_pre_invocation: true,
    ov_lesson_crystallizer: true,
    ov_sandbox_guard: true,
    key_rotator_hook: true,
    vault_guard_hook: true,
  })

  React.useEffect(() => {
    setName(agent.agent_name || '')
    setRoleDesc(agent.role_desc || '')
    const tools = agent.allowed_tools
    setSelectedTools(tools)

    const bundles = new Set<string>()
    for (const plugin of PLUGIN_CAPABILITIES) {
      for (const b of plugin.bundles) {
        if (tools.includes('*') || b.toolIds.every((t) => tools.includes(t))) {
          bundles.add(b.id)
        }
      }
    }
    setActiveBundleIds(bundles)
  }, [agent])

  const [isSavingTools, setIsSavingTools] = React.useState(false)

  // 核心：工具权限与插件授权真正持久化落盘至服务端数据库 (SSOT)
  const persistToolGrants = React.useCallback(
    async (toolsToSave?: string[], silent?: boolean) => {
      const targetTools = toolsToSave ?? selectedTools
      setIsSavingTools(true)
      const pluginGrants: Record<string, string[]> = {}
      for (const p of PLUGIN_CAPABILITIES) {
        const pTools = p.bundles.flatMap((b) => b.toolIds).filter((t) => targetTools.includes(t))
        if (pTools.length > 0) {
          pluginGrants[p.pluginId] = pTools
        }
      }

      try {
        await onUpdate(agent.agent_id, {
          allowed_tools: targetTools,
          plugin_grants: pluginGrants,
        })
        if (!silent) {
          toast.success('工具配置已成功保存')
        }
      } catch (err) {
        toast.error('保存工具授权失败')
      } finally {
        setIsSavingTools(false)
      }
    },
    [agent.agent_id, onUpdate, selectedTools]
  )

  // 保存内联修改 (名称与描述)
  const handleSaveInline = async (e?: React.MouseEvent) => {
    e?.stopPropagation()
    const pluginGrants: Record<string, string[]> = {}
    for (const p of PLUGIN_CAPABILITIES) {
      const pTools = p.bundles.flatMap((b) => b.toolIds).filter((t) => selectedTools.includes(t))
      if (pTools.length > 0) {
        pluginGrants[p.pluginId] = pTools
      }
    }

    await onUpdate(agent.agent_id, {
      agent_name: name.trim() || undefined,
      role_desc: roleDesc.trim() || undefined,
      allowed_tools: selectedTools,
      plugin_grants: pluginGrants,
    })
    setIsEditing(false)
  }

  const handleCancelEdit = (e?: React.MouseEvent) => {
    e?.stopPropagation()
    setName(agent.agent_name || '')
    setRoleDesc(agent.role_desc || '')
    setIsEditing(false)
  }

  // 切换工具包：就地实时自动持久化
  const handleToggleBundle = async (bundle: ToolBundle) => {
    const isEquipped = activeBundleIds.has(bundle.id)
    const nextBundles = new Set(activeBundleIds)
    let nextTools = [...selectedTools]

    if (isEquipped) {
      nextBundles.delete(bundle.id)
      const removeSet = new Set(bundle.toolIds)
      nextTools = nextTools.filter((t) => !removeSet.has(t))
    } else {
      nextBundles.add(bundle.id)
      nextTools = Array.from(new Set([...nextTools, ...bundle.toolIds]))
    }

    setActiveBundleIds(nextBundles)
    setSelectedTools(nextTools)
    await persistToolGrants(nextTools)
  }

  const handleToggleHook = (hookId: string, enabled: boolean) => {
    setHooksState((prev) => ({ ...prev, [hookId]: enabled }))
  }

  // 抽屉内一键全开/全关单个插件：就地实时自动持久化
  const handleTogglePluginAll = async (plugin: PluginCapability, enableAll: boolean) => {
    const pToolIds = new Set(plugin.bundles.flatMap((b) => b.toolIds))
    const pBundleIds = new Set(plugin.bundles.map((b) => b.id))

    const nextBundles = new Set(activeBundleIds)
    let nextTools = [...selectedTools]

    if (enableAll) {
      pBundleIds.forEach((id) => nextBundles.add(id))
      nextTools = Array.from(new Set([...nextTools, ...Array.from(pToolIds)]))
      toast.success(`已开启「${plugin.name}」全部工具`)
    } else {
      pBundleIds.forEach((id) => nextBundles.delete(id))
      nextTools = nextTools.filter((t) => !pToolIds.has(t))
      toast.info(`已关闭「${plugin.name}」全部工具`)
    }

    setActiveBundleIds(nextBundles)
    setSelectedTools(nextTools)
    await persistToolGrants(nextTools)
  }

  const isActive = agent.status === 'active'
  const liveStatus = getAgentLiveStatus(agent)
  const activeHooksCount = Object.values(hooksState).filter(Boolean).length

  return (
    <div
      className={`rounded-md border text-xs font-sans transition-all ${
        isExpanded
          ? 'border-cyan-500/50 bg-card shadow-xs'
          : 'border-border/60 bg-muted/10 hover:bg-muted/30'
      }`}
    >
      {/* ⭐ 极致高密单行头部：ID(第1位)、名称与描述(第2位)、状态(第3位)、资产统计(第4位)、操作(第5位) */}
      <div
        className="cursor-pointer select-none px-3 py-2 flex items-center gap-3 transition-colors"
        onClick={() => {
          if (!isEditing) onToggleExpand()
        }}
      >
        {/* 列 0: 展开折叠指示 */}
        <button
          type="button"
          className="w-5 shrink-0 flex items-center justify-center p-0.5 text-muted-foreground hover:text-foreground transition-colors"
          onClick={(e) => {
            e.stopPropagation()
            onToggleExpand()
          }}
          title={isExpanded ? '收起插件' : '展开插件'}
        >
          {isExpanded ? (
            <ChevronDownIcon className="size-4 text-cyan-500" />
          ) : (
            <ChevronRightIcon className="size-4" />
          )}
        </button>

        {/* 列 1: Agent ID (纯文本等宽，无多余边框与复制图标，原生鼠标可选) */}
        <div
          className="w-44 sm:w-48 shrink-0 font-mono text-xs text-foreground/90 truncate select-text"
          title={agent.agent_id}
          onClick={(e) => e.stopPropagation()}
        >
          {agent.agent_id}
        </div>

        {/* 列 2: 智能体名称与备注 */}
        {isEditing ? (
          /* 行内就地编辑态：输入名称与描述 + 确认/取消 */
          <div
            className="flex items-center gap-1.5 flex-1 min-w-0"
            onClick={(e) => e.stopPropagation()}
          >
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="智能体名称"
              className="h-6.5 text-xs font-mono w-36 bg-background shrink-0"
              autoFocus
            />
            <Input
              value={roleDesc}
              onChange={(e) => setRoleDesc(e.target.value)}
              placeholder="备注"
              className="h-6.5 text-xs font-sans flex-1 min-w-28 bg-background"
            />
            <Button
              type="button"
              size="sm"
              onClick={handleSaveInline}
              disabled={isUpdating}
              className="h-6.5 text-xs font-mono border border-cyan-500/50 bg-cyan-500/15 text-cyan-700 hover:bg-cyan-500/25 dark:text-cyan-300 shrink-0 px-2"
            >
              {isUpdating ? (
                <LoaderCircleIcon className="size-3 animate-spin mr-1" />
              ) : (
                <SaveIcon className="size-3 mr-1" />
              )}
              保存
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleCancelEdit}
              disabled={isUpdating}
              className="h-6.5 text-xs font-mono text-muted-foreground hover:text-foreground shrink-0 px-2"
            >
              <XIcon className="size-3 mr-0.5" />
              取消
            </Button>
          </div>
        ) : (
          /* 正常显示态：名称 + 备注 */
          <div className="flex items-center gap-2 min-w-0 flex-1 truncate">
            <span className="font-semibold text-foreground text-xs truncate shrink-0 max-w-44">
              {agent.agent_name || '未命名'}
            </span>

            {agent.role_desc && (
              <span
                className="text-muted-foreground text-xs truncate flex-1 min-w-0"
                title={agent.role_desc}
              >
                · {agent.role_desc}
              </span>
            )}
          </div>
        )}

        {/* 非编辑态下展示状态与授权 */}
        {!isEditing && (
          <>
            {/* 列 3: 状态 (纯文字 + 状态微圆点，彻底切除 Badge 边框) */}
            <div className="w-36 shrink-0 hidden sm:flex items-center gap-1.5 font-mono text-xs text-muted-foreground">
              <span className={`size-1.5 rounded-full ${liveStatus.dotColor} shrink-0`} />
              <span className="shrink-0">{liveStatus.label}</span>
              {liveStatus.detail && (
                <span className="truncate opacity-75">· {liveStatus.detail}</span>
              )}
            </div>

            {/* 列 4: 授权 (纯文字，彻底切除 Badge 边框) */}
            <div className="w-32 shrink-0 hidden md:flex items-center font-mono text-xs text-muted-foreground">
              <span>{selectedTools.length} 工具 · {activeHooksCount} Hook</span>
            </div>
          </>
        )}

        {/* 列 5: 快捷操作 (无静态边框的幽灵按钮，悬停高亮) */}
        <div
          className="w-40 shrink-0 flex items-center justify-end gap-1 ml-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {!isEditing && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setIsEditing(true)}
              className="h-6.5 gap-1 text-xs text-muted-foreground hover:text-foreground font-mono px-2"
              title="编辑名称与备注"
            >
              <Edit3Icon className="size-3" />
              <span>编辑</span>
            </Button>
          )}

          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setShowBridgeDrawer(true)}
            className="h-6.5 gap-1 text-xs text-muted-foreground hover:text-cyan-600 dark:hover:text-cyan-400 font-mono px-2"
          >
            <TerminalIcon className="size-3" />
            <span>接入指引</span>
          </Button>

          {isActive ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => onDelete(agent)}
              disabled={isUpdating}
              className="h-6.5 gap-1 text-xs text-muted-foreground hover:text-rose-600 dark:hover:text-rose-400 font-mono px-2"
            >
              <Trash2Icon className="size-3" />
              <span>删除</span>
            </Button>
          ) : (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => onActivate(agent.agent_id)}
              disabled={isUpdating}
              className="h-6.5 gap-1 text-xs text-cyan-600 hover:bg-cyan-500/10 font-mono px-2"
            >
              <RotateCcwIcon className="size-3" />
              <span>恢复</span>
            </Button>
          )}
        </div>
      </div>

      {/* 原位展开配置区：直接呈现插件瓦片网格，切除多余大表单 */}
      {isExpanded && (
        <div className="border-t border-border/50 bg-background/50 p-2.5">
          <PluginTiles
            selectedTools={selectedTools}
            hooksState={hooksState}
            onSelectPlugin={(p) => setDrawerPlugin(p)}
          />

          {/* 高密状态与落盘保障底栏 */}
          <div className="mt-2.5 pt-2 border-t border-border/40 flex items-center justify-between text-xs font-mono">
            <div className="flex items-center gap-2 text-muted-foreground">
              <span className="size-1.5 rounded-full bg-cyan-500" />
              <span>当前装配：{selectedTools.length} 工具 · {activeHooksCount} Hook</span>
              {isSavingTools && (
                <span className="flex items-center gap-1 text-cyan-600 dark:text-cyan-400">
                  <LoaderCircleIcon className="size-3 animate-spin" />
                  保存中...
                </span>
              )}
            </div>
            <Button
              type="button"
              size="sm"
              onClick={() => persistToolGrants(selectedTools, false)}
              disabled={isSavingTools}
              className="h-6.5 text-xs font-mono border border-cyan-500/40 bg-cyan-500/10 text-cyan-700 hover:bg-cyan-500/20 dark:text-cyan-300 px-2.5"
            >
              {isSavingTools ? (
                <LoaderCircleIcon className="size-3 animate-spin mr-1" />
              ) : (
                <SaveIcon className="size-3 mr-1" />
              )}
              保存工具配置
            </Button>
          </div>

          {/* 客户端接入指引专属抽屉 */}
          <AgentBridgeDrawer
            agentId={agent.agent_id}
            userId={agent.user_id || userId}
            open={showBridgeDrawer}
            onClose={() => setShowBridgeDrawer(false)}
          />

          {/* 插件专属按需配置抽屉 */}
          <PluginConfigDrawer
            plugin={drawerPlugin}
            open={drawerPlugin !== null}
            onClose={() => setDrawerPlugin(null)}
            selectedTools={selectedTools}
            activeBundleIds={activeBundleIds}
            onToggleBundle={handleToggleBundle}
            onTogglePluginAll={handleTogglePluginAll}
            hooksState={hooksState}
            onToggleHook={handleToggleHook}
            onSave={() => persistToolGrants(selectedTools, false)}
            isSaving={isSavingTools}
          />
        </div>
      )}
    </div>
  )
}
