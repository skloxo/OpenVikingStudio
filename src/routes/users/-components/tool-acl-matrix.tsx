import React from 'react'
import {
  ShieldCheckIcon,
  CheckIcon,
  RadioIcon,
  CpuIcon,
  LockIcon,
  PackageIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  ZapIcon,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  TOOL_CATEGORIES,
  ALL_TOOL_IDS,
  SATELLITE_CONSUMER_TOOL_IDS,
  MASTER_OPS_TOOL_IDS,
  HOOK_CAPABILITIES,
  OFFICIAL_PLUGIN_META,
  isToolDisabledByRole,
} from '../-constants/agent-tools'
import type { ToolItem } from '../-constants/agent-tools'

export type ToolACLMatrixProps = {
  selectedTools: string[]
  onChange: (tools: string[]) => void
  hookEnabled?: boolean
  onToggleHookEnabled?: (enabled: boolean) => void
  pluginSkillsEnabled?: boolean
  onTogglePluginSkillsEnabled?: (enabled: boolean) => void
  disabled?: boolean
  userRole?: string
}

type BundleInspectType = 'satellite' | 'ops' | 'hook' | 'skill' | null

export function ToolACLMatrix({
  selectedTools,
  onChange,
  hookEnabled = true,
  onToggleHookEnabled,
  pluginSkillsEnabled = true,
  onTogglePluginSkillsEnabled,
  disabled = false,
  userRole = 'user',
}: ToolACLMatrixProps) {
  // 当前正在展开审阅的工具/能力包（独立按需展开，杜绝全量铺陈噪音）
  const [inspectingBundle, setInspectingBundle] = React.useState<BundleInspectType>(null)

  // 真实插件包关联技能 (当前标杆插件 dsh-plugin-openviking 真实为 0 项随包技能)
  const pluginSkills = OFFICIAL_PLUGIN_META.skills
  const hasPluginSkills = pluginSkills.length > 0
  const isPluginSkillActive = hasPluginSkills && pluginSkillsEnabled

  // 构建工具字典
  const allToolMap = React.useMemo(() => {
    const map = new Map<string, ToolItem>()
    for (const cat of TOOL_CATEGORIES) {
      for (const tool of cat.tools) {
        map.set(tool.id, tool)
      }
    }
    return map
  }, [])

  // 过滤出当前用户角色有权授权的工具列表
  const allowedToolIds = React.useMemo(() => {
    return ALL_TOOL_IDS.filter((id) => {
      const tool = allToolMap.get(id)
      return !tool || !isToolDisabledByRole(tool, userRole)
    })
  }, [allToolMap, userRole])

  // 有效已选工具集合
  const selectedSet = React.useMemo(() => {
    return new Set(selectedTools.filter((id) => allToolMap.has(id)))
  }, [selectedTools, allToolMap])

  // 1. 业务使用者工具包装配状态 (31项)
  const satAllowed = React.useMemo(
    () => SATELLITE_CONSUMER_TOOL_IDS.filter((id) => allowedToolIds.includes(id)),
    [allowedToolIds],
  )
  const isSatelliteEquipped = React.useMemo(() => {
    return satAllowed.length > 0 && satAllowed.every((id) => selectedSet.has(id))
  }, [satAllowed, selectedSet])
  const satEquippedCount = React.useMemo(() => {
    return satAllowed.filter((id) => selectedSet.has(id)).length
  }, [satAllowed, selectedSet])

  // 2. 中枢运维特权工具包装配状态 (16项)
  const opsAllowed = React.useMemo(
    () => MASTER_OPS_TOOL_IDS.filter((id) => allowedToolIds.includes(id)),
    [allowedToolIds],
  )
  const isOpsEquipped = React.useMemo(() => {
    return opsAllowed.length > 0 && opsAllowed.every((id) => selectedSet.has(id))
  }, [opsAllowed, selectedSet])
  const opsEquippedCount = React.useMemo(() => {
    return opsAllowed.filter((id) => selectedSet.has(id)).length
  }, [opsAllowed, selectedSet])

  // 多选切换：业务使用者工具包 (31项)
  const handleToggleSatellite = React.useCallback(() => {
    if (disabled) return
    if (isSatelliteEquipped) {
      const satSet = new Set(SATELLITE_CONSUMER_TOOL_IDS)
      onChange(selectedTools.filter((id) => !satSet.has(id)))
    } else {
      const combined = Array.from(new Set([...selectedTools, ...satAllowed]))
      onChange(combined)
    }
  }, [disabled, isSatelliteEquipped, selectedTools, satAllowed, onChange])

  // 多选切换：中枢运维特权工具包 (16项)
  const handleToggleOps = React.useCallback(() => {
    if (disabled) return
    if (isOpsEquipped) {
      const opsSet = new Set(MASTER_OPS_TOOL_IDS)
      onChange(selectedTools.filter((id) => !opsSet.has(id)))
    } else {
      const combined = Array.from(new Set([...selectedTools, ...opsAllowed]))
      onChange(combined)
    }
  }, [disabled, isOpsEquipped, selectedTools, opsAllowed, onChange])

  const toggleInspect = (target: BundleInspectType) => {
    setInspectingBundle((prev) => (prev === target ? null : target))
  }

  // 工具分类提取工具
  const satelliteCategory = TOOL_CATEGORIES.find((c) => c.id === 'satellite')
  const opsCategory = TOOL_CATEGORIES.find((c) => c.id === 'master_ops')

  return (
    <div className="space-y-3 pt-2 border-t border-border/40 font-sans text-xs">
      {/* 头部标题与绝对严谨分类统计 (业务 31 / 运维 16 / Hook 3 / 插件技能按真实情况度量) */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <ShieldCheckIcon className="size-4 text-cyan-500 shrink-0" />
          <span className="font-semibold text-foreground text-xs">智能体角色装备与能力包 (Capability Bundles)</span>
          <div className="flex flex-wrap items-center gap-1 text-xs font-mono font-normal">
            <Badge variant="outline" className="text-xs h-5 px-1.5 border-border/60">
              🛰️ 业务: {satEquippedCount}/{satAllowed.length}
            </Badge>
            <Badge variant="outline" className="text-xs h-5 px-1.5 border-border/60">
              🧠 运维: {opsEquippedCount}/{opsAllowed.length}
            </Badge>
            <Badge variant="outline" className="text-xs h-5 px-1.5 border-border/60">
              🛡️ Hook: {hookEnabled ? '3/3' : '0/3'}
            </Badge>
            <Badge
              variant="outline"
              className={`text-xs h-5 px-1.5 border-border/60 ${
                isPluginSkillActive ? 'border-cyan-500/40 text-cyan-600 dark:text-cyan-400' : 'text-muted-foreground'
              }`}
            >
              📦 插件: {hasPluginSkills ? (isPluginSkillActive ? `${pluginSkills.length}/${pluginSkills.length}` : `0/${pluginSkills.length}`) : '0 技能 (未附带)'}
            </Badge>
          </div>
        </div>

        {userRole === 'user' && allowedToolIds.length < ALL_TOOL_IDS.length && (
          <Badge variant="secondary" className="text-xs font-normal text-muted-foreground shrink-0">
            <LockIcon className="size-2.5 mr-1" />
            已置灰 {ALL_TOOL_IDS.length - allowedToolIds.length} 项系统特权
          </Badge>
        )}
      </div>

      {/* 核心能力矩阵卡片：四组平级、支持多选组合装配 (业务 31 + 运维 16 + Hook 3 + 插件技能真实映射) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {/* 卡片 1: 🛰️ 业务使用者工具包 (31 项) */}
        <div
          className={`p-3 rounded-lg border transition-all flex flex-col justify-between ${
            isSatelliteEquipped
              ? 'border-cyan-500 bg-cyan-500/10 shadow-xs ring-1 ring-cyan-500/30'
              : 'border-border/60 bg-muted/15 hover:border-border hover:bg-muted/30'
          }`}
        >
          <div>
            <div className="flex items-center justify-between gap-2 mb-1.5">
              <div className="flex items-center gap-1.5">
                <RadioIcon className="size-4 text-cyan-500 shrink-0" />
                <span className="font-semibold text-foreground text-xs">🛰️ 业务使用者工具包</span>
              </div>
              <Badge variant="outline" className="text-xs font-mono font-normal h-5 px-1.5 border-cyan-500/40 text-cyan-600 dark:text-cyan-400">
                31 项业务工具
              </Badge>
            </div>
            <div className="text-xs text-foreground/90 font-medium mb-1">定位：一线业务工兵 / 研发助手</div>
            <div className="text-xs text-muted-foreground leading-relaxed">
              涵盖知识读写、代码阅读/AST/TDD、工单流转与全球搜索等通用一线全套工具。
            </div>
          </div>

          <div className="pt-2 mt-2 border-t border-border/30 text-xs flex items-center justify-between">
            <button
              type="button"
              onClick={() => toggleInspect('satellite')}
              className="text-muted-foreground hover:text-foreground flex items-center gap-1 cursor-pointer font-sans"
            >
              <span>{inspectingBundle === 'satellite' ? '收起清单' : '📋 查看 31 项工具'}</span>
              {inspectingBundle === 'satellite' ? <ChevronUpIcon className="size-3" /> : <ChevronDownIcon className="size-3" />}
            </button>
            <Button
              type="button"
              size="sm"
              variant={isSatelliteEquipped ? 'default' : 'outline'}
              disabled={disabled}
              onClick={handleToggleSatellite}
              className={`h-6 px-2 text-xs cursor-pointer font-sans ${
                isSatelliteEquipped
                  ? 'bg-cyan-600 hover:bg-cyan-700 text-white dark:bg-cyan-500 dark:hover:bg-cyan-600'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {isSatelliteEquipped ? <><CheckIcon className="size-3 mr-1 stroke-2.5" />已装配业务包</> : '＋ 装配业务包'}
            </Button>
          </div>
        </div>

        {/* 卡片 2: 🧠 中枢运维者工具包 (16 项专属特权) */}
        <div
          className={`p-3 rounded-lg border transition-all flex flex-col justify-between ${
            isOpsEquipped
              ? 'border-cyan-500 bg-cyan-500/10 shadow-xs ring-1 ring-cyan-500/30'
              : 'border-border/60 bg-muted/15 hover:border-border hover:bg-muted/30'
          }`}
        >
          <div>
            <div className="flex items-center justify-between gap-2 mb-1.5">
              <div className="flex items-center gap-1.5">
                <CpuIcon className="size-4 text-cyan-500 shrink-0" />
                <span className="font-semibold text-foreground text-xs">🧠 中枢运维者工具包</span>
              </div>
              <Badge variant="outline" className="text-xs font-mono font-normal h-5 px-1.5 border-cyan-500/40 text-cyan-600 dark:text-cyan-400">
                16 项运维特权
              </Badge>
            </div>
            <div className="text-xs text-foreground/90 font-medium mb-1">定位：自治中枢 / 运维特权</div>
            <div className="text-xs text-muted-foreground leading-relaxed">
              涵盖工作区代码写改、底座探针自愈、隔离舱与集群底座运维专属特权。
            </div>
          </div>

          <div className="pt-2 mt-2 border-t border-border/30 text-xs flex items-center justify-between">
            <button
              type="button"
              onClick={() => toggleInspect('ops')}
              className="text-muted-foreground hover:text-foreground flex items-center gap-1 cursor-pointer font-sans"
            >
              <span>{inspectingBundle === 'ops' ? '收起清单' : '📋 查看 16 项特权'}</span>
              {inspectingBundle === 'ops' ? <ChevronUpIcon className="size-3" /> : <ChevronDownIcon className="size-3" />}
            </button>
            <Button
              type="button"
              size="sm"
              variant={isOpsEquipped ? 'default' : 'outline'}
              disabled={disabled}
              onClick={handleToggleOps}
              className={`h-6 px-2 text-xs cursor-pointer font-sans ${
                isOpsEquipped
                  ? 'bg-cyan-600 hover:bg-cyan-700 text-white dark:bg-cyan-500 dark:hover:bg-cyan-600'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {isOpsEquipped ? <><CheckIcon className="size-3 mr-1 stroke-2.5" />已装配运维包</> : '＋ 装配运维包'}
            </Button>
          </div>
        </div>

        {/* 卡片 3: 🛡️ 生命周期 Hook 守卫包 (3 项被动钩子，平级装配) */}
        <div
          className={`p-3 rounded-lg border transition-all flex flex-col justify-between ${
            hookEnabled
              ? 'border-cyan-500 bg-cyan-500/10 shadow-xs ring-1 ring-cyan-500/30'
              : 'border-border/60 bg-muted/15 hover:border-border hover:bg-muted/30'
          }`}
        >
          <div>
            <div className="flex items-center justify-between gap-2 mb-1.5">
              <div className="flex items-center gap-1.5">
                <ZapIcon className="size-4 text-cyan-500 shrink-0" />
                <span className="font-semibold text-foreground text-xs">🛡️ 生命周期 Hook 守卫包</span>
              </div>
              <Badge variant="outline" className="text-xs font-mono font-normal h-5 px-1.5 border-cyan-500/40 text-cyan-600 dark:text-cyan-400">
                3 项被动钩子
              </Badge>
            </div>
            <div className="text-xs text-foreground/90 font-medium mb-1">定位：神经反射弧 / 被动安全注入</div>
            <div className="text-xs text-muted-foreground leading-relaxed">
              涵盖先验记忆自动预取、轮次经验自动沉淀与工具前置沙箱拦截，整组装配生效。
            </div>
          </div>

          <div className="pt-2 mt-2 border-t border-border/30 text-xs flex items-center justify-between">
            <button
              type="button"
              onClick={() => toggleInspect('hook')}
              className="text-muted-foreground hover:text-foreground flex items-center gap-1 cursor-pointer font-sans"
            >
              <span>{inspectingBundle === 'hook' ? '收起明细' : '📋 查看 3 项钩子'}</span>
              {inspectingBundle === 'hook' ? <ChevronUpIcon className="size-3" /> : <ChevronDownIcon className="size-3" />}
            </button>
            <Button
              type="button"
              size="sm"
              variant={hookEnabled ? 'default' : 'outline'}
              disabled={disabled}
              onClick={() => onToggleHookEnabled?.(!hookEnabled)}
              className={`h-6 px-2 text-xs cursor-pointer font-sans ${
                hookEnabled
                  ? 'bg-cyan-600 hover:bg-cyan-700 text-white dark:bg-cyan-500 dark:hover:bg-cyan-600'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {hookEnabled ? <><CheckIcon className="size-3 mr-1 stroke-2.5" />已启用 Hook 守卫</> : '＋ 启用 Hook 守卫'}
            </Button>
          </div>
        </div>

        {/* 卡片 4: 📦 插件包关联技能 (Plugin Skills - 真实反映当前插件包实际情况) */}
        <div
          className={`p-3 rounded-lg border transition-all flex flex-col justify-between ${
            isPluginSkillActive
              ? 'border-cyan-500 bg-cyan-500/10 shadow-xs ring-1 ring-cyan-500/30'
              : 'border-border/60 bg-muted/15 hover:border-border hover:bg-muted/30'
          }`}
        >
          <div>
            <div className="flex items-center justify-between gap-2 mb-1.5">
              <div className="flex items-center gap-1.5">
                <PackageIcon className="size-4 text-cyan-500 shrink-0" />
                <span className="font-semibold text-foreground text-xs">📦 插件包关联技能</span>
              </div>
              <Badge
                variant="outline"
                className={`text-xs font-mono font-normal h-5 px-1.5 ${
                  isPluginSkillActive
                    ? 'border-cyan-500/40 text-cyan-600 dark:text-cyan-400 bg-cyan-500/5'
                    : 'text-muted-foreground border-border/60'
                }`}
              >
                {hasPluginSkills ? `${pluginSkills.length} 项随包技能` : '0 项随包技能'}
              </Badge>
            </div>
            <div className="text-xs text-foreground/90 font-medium mb-1">定位：插件随包技能 / 扩展规约</div>
            <div className="text-xs text-muted-foreground leading-relaxed">
              {hasPluginSkills
                ? `由当前接入插件包 (${OFFICIAL_PLUGIN_META.pluginName}) 真实捆绑附带的特定领域技能。`
                : `当前官方标杆插件 (${OFFICIAL_PLUGIN_META.pluginName} v${OFFICIAL_PLUGIN_META.version}) 专注于 MCP 工具箱与 Hook 守卫，未内置随包技能。`}
            </div>
          </div>

          <div className="pt-2 mt-2 border-t border-border/30 text-xs flex items-center justify-between">
            <button
              type="button"
              onClick={() => toggleInspect('skill')}
              className="text-muted-foreground hover:text-foreground flex items-center gap-1 cursor-pointer font-sans"
            >
              <span>
                {inspectingBundle === 'skill'
                  ? '收起说明'
                  : hasPluginSkills
                    ? `📋 查看 ${pluginSkills.length} 项技能`
                    : '📋 查看说明'}
              </span>
              {inspectingBundle === 'skill' ? <ChevronUpIcon className="size-3" /> : <ChevronDownIcon className="size-3" />}
            </button>

            {hasPluginSkills ? (
              <Button
                type="button"
                size="sm"
                variant={pluginSkillsEnabled ? 'default' : 'outline'}
                disabled={disabled}
                onClick={() => onTogglePluginSkillsEnabled?.(!pluginSkillsEnabled)}
                className={`h-6 px-2 text-xs cursor-pointer font-sans ${
                  pluginSkillsEnabled
                    ? 'bg-cyan-600 hover:bg-cyan-700 text-white dark:bg-cyan-500 dark:hover:bg-cyan-600'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {pluginSkillsEnabled ? (
                  <>
                    <CheckIcon className="size-3 mr-1 stroke-2.5" />
                    已装配插件技能
                  </>
                ) : (
                  '＋ 装配插件技能'
                )}
              </Button>
            ) : (
              <Badge variant="secondary" className="h-6 px-2 text-xs font-normal border border-border/40 text-muted-foreground">
                当前插件未附带技能
              </Badge>
            )}
          </div>
        </div>
      </div>

      {/* 独立展开抽屉/清单区域：只审阅当前选中的那个能力包，彻底消灭全量杂乱噪音 */}
      {inspectingBundle && (
        <div className="p-3 rounded-lg border border-border/60 bg-background/80 space-y-2 mt-2 transition-all">
          {/* 1. 业务工具包清单 */}
          {inspectingBundle === 'satellite' && satelliteCategory && (
            <div>
              <div className="flex items-center justify-between pb-2 border-b border-border/30 mb-2">
                <div className="flex items-center gap-2">
                  <RadioIcon className="size-4 text-cyan-500" />
                  <span className="font-semibold text-foreground text-xs">🛰️ 业务使用者工具清单 ({satelliteCategory.tools.length} 项)</span>
                  <span className="text-xs text-muted-foreground">整包赋予，用于一线知识、代码与研发辅助</span>
                </div>
                <Button size="sm" variant="ghost" className="h-6 px-1.5 text-xs text-muted-foreground cursor-pointer" onClick={() => setInspectingBundle(null)}>
                  收起清单 ✕
                </Button>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-72 overflow-y-auto pr-1">
                {satelliteCategory.tools.map((t) => (
                  <div key={t.id} className="p-2 rounded border border-border/40 bg-muted/15 space-y-0.5">
                    <div className="flex items-center justify-between gap-1">
                      <span className="font-mono text-xs font-semibold text-foreground">{t.id}</span>
                      <Badge variant="outline" className="text-xs h-4.5 px-1 font-normal font-sans text-muted-foreground">
                        {t.categoryBadge}
                      </Badge>
                    </div>
                    <div className="text-xs text-muted-foreground leading-snug">{t.description}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 2. 运维特权工具包清单 */}
          {inspectingBundle === 'ops' && opsCategory && (
            <div>
              <div className="flex items-center justify-between pb-2 border-b border-border/30 mb-2">
                <div className="flex items-center gap-2">
                  <CpuIcon className="size-4 text-cyan-500" />
                  <span className="font-semibold text-foreground text-xs">🧠 中枢运维特权工具清单 ({opsCategory.tools.length} 项)</span>
                  <span className="text-xs text-muted-foreground">专属特权，涵盖代码修改、自愈重试与系统度量</span>
                </div>
                <Button size="sm" variant="ghost" className="h-6 px-1.5 text-xs text-muted-foreground cursor-pointer" onClick={() => setInspectingBundle(null)}>
                  收起清单 ✕
                </Button>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-72 overflow-y-auto pr-1">
                {opsCategory.tools.map((t) => (
                  <div key={t.id} className="p-2 rounded border border-border/40 bg-muted/15 space-y-0.5">
                    <div className="flex items-center justify-between gap-1">
                      <span className="font-mono text-xs font-semibold text-foreground">{t.id}</span>
                      <div className="flex items-center gap-1">
                        {t.requiredRole && (
                          <Badge variant="outline" className="text-xs h-4.5 px-1 font-normal border-border text-muted-foreground">
                            需 {t.requiredRole}
                          </Badge>
                        )}
                        <Badge variant="outline" className="text-xs h-4.5 px-1 font-normal font-sans text-muted-foreground">
                          {t.categoryBadge}
                        </Badge>
                      </div>
                    </div>
                    <div className="text-xs text-muted-foreground leading-snug">{t.description}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 3. Hook 守卫包明细 */}
          {inspectingBundle === 'hook' && (
            <div>
              <div className="flex items-center justify-between pb-2 border-b border-border/30 mb-2">
                <div className="flex items-center gap-2">
                  <ZapIcon className="size-4 text-cyan-500" />
                  <span className="font-semibold text-foreground text-xs">🛡️ 生命周期 Hook 守卫明细 (3 项)</span>
                  <span className="text-xs text-muted-foreground">被动拦截与自动注入神经反射弧</span>
                </div>
                <Button size="sm" variant="ghost" className="h-6 px-1.5 text-xs text-muted-foreground cursor-pointer" onClick={() => setInspectingBundle(null)}>
                  收起明细 ✕
                </Button>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {HOOK_CAPABILITIES.map((h) => (
                  <div key={h.id} className="p-2.5 rounded border border-border/40 bg-muted/15 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-xs text-foreground">{h.name}</span>
                      <Badge variant="outline" className="text-xs font-mono h-4 px-1 text-cyan-600 dark:text-cyan-400 border-cyan-500/40">
                        {h.timing}
                      </Badge>
                    </div>
                    <div className="text-xs text-muted-foreground leading-relaxed">{h.description}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 4. 插件包关联技能说明与清单 */}
          {inspectingBundle === 'skill' && (
            <div>
              <div className="flex items-center justify-between pb-2 border-b border-border/30 mb-2">
                <div className="flex items-center gap-2">
                  <PackageIcon className="size-4 text-cyan-500" />
                  <span className="font-semibold text-foreground text-xs">
                    📦 插件包关联技能 ({pluginSkills.length} 项)
                  </span>
                  <span className="text-xs text-muted-foreground">
                    基于当前接入插件包 ({OFFICIAL_PLUGIN_META.pluginName}) 的真实随包技能清单
                  </span>
                </div>
                <Button size="sm" variant="ghost" className="h-6 px-1.5 text-xs text-muted-foreground cursor-pointer" onClick={() => setInspectingBundle(null)}>
                  收起说明 ✕
                </Button>
              </div>

              {hasPluginSkills ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                  {pluginSkills.map((s) => (
                    <div key={s.id} className="p-2.5 rounded border border-border/40 bg-muted/15 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-xs text-foreground font-sans">{s.name}</span>
                        <Badge variant="outline" className="text-xs h-4.5 px-1 text-muted-foreground border-border/60">
                          {s.category}
                        </Badge>
                      </div>
                      <div className="text-xs text-muted-foreground leading-relaxed">{s.description}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-2.5 rounded border border-border/40 bg-muted/15 space-y-1.5 text-xs">
                  <div className="text-foreground font-medium flex items-center gap-1.5">
                    <span>💡 当前插件包未内置随包技能</span>
                  </div>
                  <div className="text-muted-foreground leading-relaxed">
                    当前官方标杆插件 <code>{OFFICIAL_PLUGIN_META.pluginName} (v{OFFICIAL_PLUGIN_META.version})</code> 专注于 FastMCP 工具箱桥接与 Prompt 前后置 Hook 拦截生命周期，插件自身未捆绑独立技能。
                  </div>
                  <div className="text-muted-foreground/80 leading-relaxed">
                    智能体在执行任务时，直接由体外大脑 (OpenViking) 自动召回长程经验，或读取工作区本地 <code>.agents/skills/</code> 规约，无需随包技能强依赖。
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
