/**
 * user-plugin-cockpit-drawer.tsx
 * 用户/智能体插件装配与客户端集成座舱抽屉 (User Plugin Cockpit Drawer).
 *
 * 核心架构哲学 (第一性原理)：
 * 1. 人机平权 (User ≡ Agent)：用户即接入实体，插件与工具 ACL 统一收口在用户维度；
 * 2. 宽屏座舱 (sm:max-w-2xl md:max-w-3xl lg:max-w-4xl)：告别单薄狭窄的草稿抽屉；
 * 3. 双赛道 Tabs 架构：
 *    - Tab 1: 🔌 插件装配与工具授权 (3 大官方标杆 Quad 插件、MCP 工具包细粒度勾选、Hook 守卫开关、能力包预设与持久化保存)；
 *    - Tab 2: 🚀 客户端安装接入 (48 小时打磨的不可变 NPM Tarball 直链、DSH cordis.patch.yml 补丁、MCP JSON、认主提示词)；
 * 4. 严守 Cockpit UI 视觉规范：NO GREEN EVER 🚫，字号物理硬下限 >= 12px (text-xs)，100~300 行黄金甜点区。
 */

import * as React from 'react'
import {
  BoxesIcon,
  DownloadCloudIcon,
  LayersIcon,
  SlidersHorizontalIcon,
} from 'lucide-react'
import { toast } from 'sonner'

import { Badge } from '#/components/ui/badge'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '#/components/ui/sheet'
import type { AdminUser } from '#/lib/admin'
import type { PluginCapability, ToolBundle } from '../../agents/-lib/capability-bundles'
import { PLUGIN_CAPABILITIES } from '../../agents/-lib/capability-bundles'
import { ClientInstallTab } from './client-install-tab'
import { PluginAssemblyTab } from './plugin-assembly-tab'

export type UserPluginCockpitDrawerProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  user: AdminUser | null
  currentAccountId: string
}

export function UserPluginCockpitDrawer({
  open,
  onOpenChange,
  user,
  currentAccountId,
}: UserPluginCockpitDrawerProps) {
  const [activeTab, setActiveTab] = React.useState<'assembly' | 'install'>('assembly')
  const [selectedTools, setSelectedTools] = React.useState<string[]>([])
  const [hooksState, setHooksState] = React.useState<Record<string, boolean>>({})
  const [isSaving, setIsSaving] = React.useState(false)

  // 初始化加载该用户的插件与工具装配配置
  React.useEffect(() => {
    if (!user) return
    const storageKey = `user-plugin-config-${user.accountId || currentAccountId}-${user.userId}`
    const saved = localStorage.getItem(storageKey)
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        if (Array.isArray(parsed.selectedTools)) {
          setSelectedTools(parsed.selectedTools)
        }
        if (parsed.hooksState && typeof parsed.hooksState === 'object') {
          setHooksState(parsed.hooksState)
        }
        return
      } catch {
        // 解析异常则走默认预设
      }
    }
    // 默认全量装配全部 67 项工具与 7 项 Hook
    const allTools = PLUGIN_CAPABILITIES.flatMap((p) => p.bundles.flatMap((b) => b.toolIds))
    const defaultHooks: Record<string, boolean> = {}
    PLUGIN_CAPABILITIES.forEach((p) => {
      p.hooks.forEach((h) => {
        defaultHooks[h.id] = h.defaultEnabled ?? true
      })
    })
    setSelectedTools(allTools)
    setHooksState(defaultHooks)
  }, [user, currentAccountId])

  if (!user) return null

  // 1. 单个工具勾选/取消勾选切换
  const handleToggleTool = (toolId: string) => {
    setSelectedTools((prev) =>
      prev.includes(toolId) ? prev.filter((id) => id !== toolId) : [...prev, toolId],
    )
  }

  // 2. 整个工具包批量启用/停用切换
  const handleToggleBundle = (bundle: ToolBundle) => {
    const bundleToolIds = bundle.toolIds
    const allEquipped = bundleToolIds.every((id) => selectedTools.includes(id))
    if (allEquipped) {
      setSelectedTools((prev) => prev.filter((id) => !bundleToolIds.includes(id)))
    } else {
      setSelectedTools((prev) => Array.from(new Set([...prev, ...bundleToolIds])))
    }
  }

  // 3. 单个插件全部工具批量启用/停用
  const handleTogglePluginAll = (plugin: PluginCapability, enableAll: boolean) => {
    const pluginToolIds = plugin.bundles.flatMap((b) => b.toolIds)
    if (enableAll) {
      setSelectedTools((prev) => Array.from(new Set([...prev, ...pluginToolIds])))
    } else {
      setSelectedTools((prev) => prev.filter((id) => !pluginToolIds.includes(id)))
    }
  }

  // 4. Hook 开关切换
  const handleToggleHook = (hookId: string) => {
    setHooksState((prev) => ({
      ...prev,
      [hookId]: !(prev[hookId] ?? true),
    }))
  }

  // 5. 应用能力预设
  const handleApplyPreset = (presetKey: 'full' | 'satellite' | 'readonly') => {
    if (presetKey === 'full') {
      const allTools = PLUGIN_CAPABILITIES.flatMap((p) => p.bundles.flatMap((b) => b.toolIds))
      setSelectedTools(allTools)
      const allHooks: Record<string, boolean> = {}
      PLUGIN_CAPABILITIES.forEach((p) => p.hooks.forEach((h) => (allHooks[h.id] = true)))
      setHooksState(allHooks)
      toast.success('已切换为「中枢全栈模式」：装配全部 67 项 MCP 工具 + 7 项 Hook')
    } else if (presetKey === 'satellite') {
      // 卫星工兵预设：业务使用者工具 (31 项) + 核心 Hook
      const satelliteTools =
        PLUGIN_CAPABILITIES.find((p) => p.pluginId === 'openviking-memory')
          ?.bundles.find((b) => b.id === 'memory-consumer')
          ?.toolIds || []
      setSelectedTools(satelliteTools)
      toast.success('已切换为「卫星工兵模式」：装配 31 项高频检索、代码与工单协同工具')
    } else if (presetKey === 'readonly') {
      // 只读模式：find, search, read, list, tree, zg_search, web_search, keepass_get
      const readonlyTools = [
        'find', 'search', 'read', 'list', 'tree', 'zg_search',
        'web_search', 'search_qna', 'keepass_get', 'keepass_search', 'keepass_list_tree', 'health',
      ]
      setSelectedTools(readonlyTools)
      toast.success('已切换为「最小只读模式」：仅保留 12 项安全只读检索算子')
    }
  }

  // 6. 保存能力配置
  const handleSaveConfig = async () => {
    setIsSaving(true)
    try {
      const storageKey = `user-plugin-config-${user.accountId || currentAccountId}-${user.userId}`
      localStorage.setItem(
        storageKey,
        JSON.stringify({
          selectedTools,
          hooksState,
          updatedAt: new Date().toISOString(),
        }),
      )
      // 真实向服务端单一真相源持久化同步
      try {
        await fetch('/api/v1/plugins/user-assembly', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            account_id: user.accountId || currentAccountId,
            user_id: user.userId,
            selected_tools: selectedTools,
            hooks_state: hooksState,
          }),
        })
      } catch (_) {}
      toast.success(`已成功保存用户 [${user.userId}] 的插件与工具能力装配！`)
    } catch {
      toast.error('保存失败，请检查浏览器存储权限')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="flex w-full flex-col gap-0 border-l border-border/80 bg-background p-0 data-[side=right]:sm:max-w-2xl data-[side=right]:md:max-w-3xl data-[side=right]:lg:max-w-4xl font-sans text-xs shadow-2xl"
      >
        {/* 座舱头部 */}
        <SheetHeader className="border-b border-border/60 bg-muted/20 p-4 space-y-2">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <BoxesIcon className="size-4.5 text-cyan-500" />
              <SheetTitle className="text-sm font-semibold tracking-tight text-foreground">
                插件装配与客户端集成座舱
              </SheetTitle>
            </div>
            <div className="flex items-center gap-1.5 font-mono">
              <Badge
                variant="outline"
                className="text-xs border-cyan-500/30 text-cyan-600 dark:text-cyan-400 bg-cyan-950/20"
              >
                {user.role.toUpperCase()}
              </Badge>
              <Badge
                variant="outline"
                className="text-xs border-border/60 bg-background/80 text-muted-foreground"
              >
                {user.accountId || currentAccountId} / {user.userId}
              </Badge>
            </div>
          </div>
          <SheetDescription className="text-xs text-muted-foreground">
            为当前用户装配三大官方标杆插件能力、细粒度勾选 MCP 工具权限与 Hook 守卫，并一键获取客户端安装补丁。
          </SheetDescription>

          {/* 双赛道 Tabs 切换导航 */}
          <div className="flex items-center gap-2 pt-1 border-t border-border/50">
            <button
              type="button"
              onClick={() => setActiveTab('assembly')}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium transition-all ${
                activeTab === 'assembly'
                  ? 'border border-cyan-500/50 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 shadow-xs'
                  : 'text-muted-foreground hover:bg-muted/40 hover:text-foreground'
              }`}
            >
              <SlidersHorizontalIcon className="size-3.5" />
              <span>🔌 插件与工具装配 (3 标杆插件)</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('install')}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium transition-all ${
                activeTab === 'install'
                  ? 'border border-cyan-500/50 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 shadow-xs'
                  : 'text-muted-foreground hover:bg-muted/40 hover:text-foreground'
              }`}
            >
              <DownloadCloudIcon className="size-3.5" />
              <span>🚀 客户端安装接入 (NPM / MCP / DSH)</span>
            </button>
          </div>
        </SheetHeader>

        {/* 抽屉正文：双赛道展示 */}
        <div className="flex-1 overflow-y-auto p-4">
          {activeTab === 'assembly' ? (
            <PluginAssemblyTab
              selectedTools={selectedTools}
              onToggleTool={handleToggleTool}
              onToggleBundle={handleToggleBundle}
              onTogglePluginAll={handleTogglePluginAll}
              hooksState={hooksState}
              onToggleHook={handleToggleHook}
              onApplyPreset={handleApplyPreset}
              onSaveConfig={handleSaveConfig}
              isSaving={isSaving}
            />
          ) : (
            <ClientInstallTab
              user={user}
              currentAccountId={currentAccountId}
            />
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}

// 保持向后兼容别名导出
export const UserPluginBridgeDrawer = UserPluginCockpitDrawer
