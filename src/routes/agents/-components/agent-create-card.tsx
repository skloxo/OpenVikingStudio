/**
 * agent-create-card.tsx
 * 智能体中心新智能体就地签发卡片组件 (Cockpit UI 规范)。
 *
 * 核心架构哲学：
 * 1. 默认三大插件全开 (记忆 58 + 搜索 12 + 凭据 8，共 78 项全量就绪)；
 * 2. 界面极致清爽，按需拉起专属抽屉配置细节；
 * 3. 遵行 Cockpit UI 视觉规范：NO GREEN EVER 🚫，字号物理硬下限 >= 12px (text-xs)；
 * 4. 严守单文件 100~300 行黄金甜点区规范。
 */

import * as React from 'react'
import {
  PlusIcon,
  SparklesIcon,
  XIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { Label } from '#/components/ui/label'
import type { CreateAgentInput } from '#/lib/admin'
import type { PluginCapability, ToolBundle } from '../-lib/capability-bundles'
import { PLUGIN_CAPABILITIES } from '../-lib/capability-bundles'
import { PluginConfigDrawer } from './plugin-config-drawer'
import { PluginTiles } from './plugin-tiles'

export type AgentCreateCardProps = {
  open: boolean
  onClose: () => void
  onSubmit: (input: CreateAgentInput) => void
  isPending?: boolean
}

export function AgentCreateCard({
  open,
  onClose,
  onSubmit,
  isPending = false,
}: AgentCreateCardProps) {
  const [name, setName] = React.useState('')
  const [roleDesc, setRoleDesc] = React.useState('')

  // 抽屉状态：当前正在配置细节的插件对象
  const [drawerPlugin, setDrawerPlugin] = React.useState<PluginCapability | null>(null)

  // 1. 默认三大插件全开 (67项 MCP 工具全部包含)
  const [selectedTools, setSelectedTools] = React.useState<string[]>(() => {
    return Array.from(new Set(PLUGIN_CAPABILITIES.flatMap((p) => p.bundles.flatMap((b) => b.toolIds))))
  })

  // 2. 默认所有工具包全开
  const [activeBundleIds, setActiveBundleIds] = React.useState<Set<string>>(() => {
    return new Set(PLUGIN_CAPABILITIES.flatMap((p) => p.bundles.map((b) => b.id)))
  })

  // 3. 默认所有 Hook 守卫全开
  const [hooksState, setHooksState] = React.useState<Record<string, boolean>>({
    ov_pre_invocation: true,
    ov_lesson_crystallizer: true,
    ov_sandbox_guard: true,
    key_rotator_hook: true,
    search_guard_hook: true,
    credit_audit_hook: true,
    vault_guard_hook: true,
  })

  if (!open) return null

  const handleCopy = async (text: string, label: string, e?: React.MouseEvent) => {
    e?.stopPropagation()
    try {
      await navigator.clipboard.writeText(text)
      toast.success(`已复制 ${label}`)
    } catch {
      toast.error('复制失败')
    }
  }

  // 切换单个工具包
  const handleToggleBundle = (bundle: ToolBundle) => {
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
  }

  // 抽屉内一键全开/全关单个插件
  const handleTogglePluginAll = (plugin: PluginCapability, enableAll: boolean) => {
    const pToolIds = new Set(plugin.bundles.flatMap((b) => b.toolIds))
    const pBundleIds = new Set(plugin.bundles.map((b) => b.id))

    const nextBundles = new Set(activeBundleIds)
    let nextTools = [...selectedTools]

    if (enableAll) {
      pBundleIds.forEach((id) => nextBundles.add(id))
      nextTools = Array.from(new Set([...nextTools, ...Array.from(pToolIds)]))
      toast.success(`已全量开启「${plugin.name}」`)
    } else {
      pBundleIds.forEach((id) => nextBundles.delete(id))
      nextTools = nextTools.filter((t) => !pToolIds.has(t))
      toast.info(`已停用「${plugin.name}」全部工具`)
    }

    setActiveBundleIds(nextBundles)
    setSelectedTools(nextTools)
  }



  const handleToggleHook = (hookId: string, enabled: boolean) => {
    setHooksState((prev) => ({ ...prev, [hookId]: enabled }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const cleanName = name.trim()
    if (!cleanName) {
      toast.error('请输入智能体自定义名称')
      return
    }

    // 按插件切分 plugin_grants
    const pluginGrants: Record<string, string[]> = {}
    for (const p of PLUGIN_CAPABILITIES) {
      const pTools = p.bundles.flatMap((b) => b.toolIds).filter((t) => selectedTools.includes(t))
      if (pTools.length > 0) {
        pluginGrants[p.pluginId] = pTools
      }
    }

    onSubmit({
      agent_name: cleanName,
      role_desc: roleDesc.trim() || '业务研发与跨宿主知识协作智能体',
      connection_mode: 'apiClient',
      allowed_tools: selectedTools,
      plugin_grants: pluginGrants,
    })

    // 重置输入
    setName('')
    setRoleDesc('')
  }

  return (
    <>
      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-md border border-cyan-500/40 bg-card p-4 text-xs font-sans shadow-xs"
      >
        {/* 头部标题与关闭 */}
        <div className="flex items-center justify-between border-b border-border/40 pb-2.5">
          <div className="flex items-center gap-2">
            <SparklesIcon className="size-4 text-cyan-600 dark:text-cyan-400" />
            <span className="text-sm font-semibold text-foreground">
              新建智能体
            </span>
            <span className="font-mono text-muted-foreground text-xs hidden sm:inline">
              (三大插件默认全开，点击任意卡片拉起抽屉按需微调)
            </span>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon-xs"
            onClick={onClose}
            className="size-6 text-muted-foreground hover:text-foreground"
            title="关闭"
          >
            <XIcon className="size-3.5" />
          </Button>
        </div>

        {/* 基础身份与网络拓扑 */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="space-y-1">
            <Label className="text-xs font-medium text-foreground">
              智能体名称 (自定义可改) <span className="text-rose-500">*</span>
            </Label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="例如 前端结对助手、3070 巡检小助手、量化风控专家"
              className="h-7 text-xs bg-background font-sans"
              autoFocus
            />
          </div>

          <div className="space-y-1">
            <Label className="text-xs font-medium text-foreground">角色定位 / 职能描述</Label>
            <Input
              value={roleDesc}
              onChange={(e) => setRoleDesc(e.target.value)}
              placeholder="例如 自动化编译巡检、代码审查、全网情报调研"
              className="h-7 text-xs bg-background font-sans"
            />
          </div>
        </div>

        {/* 核心插件瓦片列表 (并排3列，默认全开，点击拉起抽屉) */}
        <PluginTiles
          selectedTools={selectedTools}
          hooksState={hooksState}
          onSelectPlugin={(p) => setDrawerPlugin(p)}
        />

        {/* 底部按钮栏 */}
        <div className="flex items-center justify-between border-t border-border/40 pt-3">
          <span className="font-mono text-muted-foreground text-xs">
            智能体 ID 将自动生成
          </span>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 text-xs font-mono"
              onClick={onClose}
            >
              取消
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={isPending}
              className="h-7 gap-1 border border-cyan-500/40 bg-cyan-500/10 font-mono text-xs text-cyan-700 hover:bg-cyan-500/20 active:bg-cyan-500/30 dark:border-cyan-500/50 dark:bg-cyan-950/40 dark:text-cyan-300 dark:hover:bg-cyan-900/50"
            >
              <PlusIcon className="size-3" />
              {isPending ? '正在创建...' : `确认创建智能体 (${selectedTools.length} 项工具)`}
            </Button>
          </div>
        </div>
      </form>

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
        onCopy={handleCopy}
      />
    </>
  )
}
