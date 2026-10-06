import React from 'react'
import {
  ShieldCheckIcon,
  CheckIcon,
  CheckSquareIcon,
  SquareIcon,
  SparklesIcon,
  RotateCcwIcon,
  Trash2Icon,
  RadioIcon,
  CpuIcon,
  LockIcon,
  ChevronDownIcon,
  ChevronUpIcon,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import {
  TOOL_CATEGORIES,
  ALL_TOOL_IDS,
  DEFAULT_TOOL_IDS,
  SATELLITE_CONSUMER_TOOL_IDS,
  MASTER_MAINTAINER_TOOL_IDS,
  OFFICIAL_TOOL_BUNDLES,
  isToolDisabledByRole,
} from '../-constants/agent-tools'
import type { ToolItem, ToolBundle } from '../-constants/agent-tools'

export type ToolACLMatrixProps = {
  selectedTools: string[]
  onChange: (tools: string[]) => void
  disabled?: boolean
  userRole?: string
}

export function ToolACLMatrix({
  selectedTools,
  onChange,
  disabled = false,
  userRole = 'user',
}: ToolACLMatrixProps) {
  const [isDetailedOpen, setIsDetailedOpen] = React.useState(false)

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

  // 有效的已选工具列表（严格对齐合法工具字典，彻底切除历史废弃脏ID）
  const validSelectedIds = React.useMemo(() => {
    return selectedTools.filter((id) => allToolMap.has(id))
  }, [selectedTools, allToolMap])

  // 当前激活的工具包检测
  const activeBundleId = React.useMemo(() => {
    const selectedSet = new Set(validSelectedIds)
    const satAllowed = SATELLITE_CONSUMER_TOOL_IDS.filter((id) => allowedToolIds.includes(id))
    const masterAllowed = MASTER_MAINTAINER_TOOL_IDS.filter((id) => allowedToolIds.includes(id))

    // 检查是否全选 (中枢总控包)
    if (masterAllowed.length > 0 && masterAllowed.every((id) => selectedSet.has(id))) {
      return 'master_maintainer'
    }

    // 检查是否刚好为卫星工兵包
    if (
      satAllowed.length > 0 &&
      satAllowed.every((id) => selectedSet.has(id)) &&
      selectedSet.size === satAllowed.length
    ) {
      return 'satellite_consumer'
    }

    return null
  }, [validSelectedIds, allowedToolIds])

  // 1. 点选官方工具包
  const handleSelectBundle = React.useCallback(
    (bundle: ToolBundle) => {
      if (disabled) return
      const targetTools = bundle.toolIds.filter((id) => allowedToolIds.includes(id))
      onChange(targetTools)
    },
    [disabled, allowedToolIds, onChange],
  )

  // 2. 全选所有可用项
  const handleSelectAll = React.useCallback(() => {
    onChange([...allowedToolIds])
  }, [onChange, allowedToolIds])

  // 3. 恢复默认推荐
  const handleSelectDefaults = React.useCallback(() => {
    const valid = DEFAULT_TOOL_IDS.filter((id) => allowedToolIds.includes(id))
    onChange(valid)
  }, [onChange, allowedToolIds])

  // 4. 全部清空
  const handleClearAll = React.useCallback(() => {
    onChange([])
  }, [onChange])

  // 5. 单项切换
  const handleToggleTool = React.useCallback(
    (tool: ToolItem) => {
      if (disabled) return
      if (isToolDisabledByRole(tool, userRole)) return

      if (selectedTools.includes(tool.id)) {
        onChange(selectedTools.filter((id) => id !== tool.id))
      } else {
        onChange([...selectedTools, tool.id])
      }
    },
    [selectedTools, onChange, disabled, userRole],
  )

  // 6. 场景分类一键全选 / 取消全选 (自动跳过无权置灰项)
  const handleToggleCategory = React.useCallback(
    (catTools: ToolItem[]) => {
      if (disabled) return
      const availableCatIds = catTools
        .filter((t) => !isToolDisabledByRole(t, userRole))
        .map((t) => t.id)
      if (availableCatIds.length === 0) return

      const isAllCatSelected = availableCatIds.every((id) => selectedTools.includes(id))
      if (isAllCatSelected) {
        onChange(selectedTools.filter((id) => !availableCatIds.includes(id)))
      } else {
        const next = Array.from(new Set([...selectedTools, ...availableCatIds]))
        onChange(next)
      }
    },
    [selectedTools, onChange, disabled, userRole],
  )

  return (
    <div className="space-y-3 pt-2 border-t border-border/40 font-sans text-xs">
      {/* 头部标题与权限说明 */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <ShieldCheckIcon className="size-4 text-cyan-500 shrink-0" />
          <span className="font-semibold text-foreground text-xs">智能体角色工具包 (Tool Bundles)</span>
          <Badge variant="outline" className="text-xs font-mono font-normal">
            已选 {validSelectedIds.length} / {allowedToolIds.length} 项可用 (全域 {ALL_TOOL_IDS.length})
          </Badge>
          {!activeBundleId && validSelectedIds.length > 0 && (
            <Badge variant="secondary" className="text-xs font-normal text-cyan-600 dark:text-cyan-400">
              ✨ 自定义微调组合
            </Badge>
          )}
        </div>

        {userRole === 'user' && allowedToolIds.length < ALL_TOOL_IDS.length && (
          <Badge variant="secondary" className="text-xs font-normal text-muted-foreground shrink-0">
            <LockIcon className="size-2.5 mr-1" />
            已置灰 {ALL_TOOL_IDS.length - allowedToolIds.length} 项非普通用户特权工具
          </Badge>
        )}
      </div>

      {/* 核心亮点：两大官方工具包卡片一键点选 (消灭逐一勾选痛点) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {OFFICIAL_TOOL_BUNDLES.map((bundle) => {
          const isSelected = activeBundleId === bundle.id
          const isSatellite = bundle.id === 'satellite_consumer'

          return (
            <div
              key={bundle.id}
              onClick={() => !disabled && handleSelectBundle(bundle)}
              className={`p-3 rounded-lg border transition-all cursor-pointer select-none flex flex-col justify-between ${
                isSelected
                  ? 'border-cyan-500 bg-cyan-500/10 shadow-xs ring-1 ring-cyan-500/30'
                  : 'border-border/60 bg-muted/15 hover:border-border hover:bg-muted/30'
              } ${disabled ? 'opacity-60 cursor-not-allowed' : ''}`}
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-1.5">
                    {isSatellite ? (
                      <RadioIcon className="size-4 text-cyan-500 shrink-0" />
                    ) : (
                      <CpuIcon className="size-4 text-cyan-500 shrink-0" />
                    )}
                    <span className="font-semibold text-foreground text-xs">{bundle.name}</span>
                  </div>

                  <Badge
                    variant={isSelected ? 'default' : 'outline'}
                    className={`text-xs font-mono font-normal h-5 px-1.5 ${
                      isSelected
                        ? 'bg-cyan-500 text-white border-transparent'
                        : 'text-muted-foreground border-border/60'
                    }`}
                  >
                    {isSelected ? '✓ 已选中生效' : bundle.highlightBadge}
                  </Badge>
                </div>

                <div className="text-xs text-foreground/90 font-medium mb-1">
                  角色定位：{bundle.roleTitle}
                </div>
                <div className="text-xs text-muted-foreground leading-relaxed">
                  {bundle.description}
                </div>
              </div>

              <div className="pt-2 mt-2 border-t border-border/30 text-xs text-muted-foreground/80 flex items-center justify-between">
                <span>{bundle.recommendedFor}</span>
                <span className="font-mono shrink-0 ml-1 font-medium">
                  {isSelected ? (
                    <span className="text-cyan-600 dark:text-cyan-400">✓ 当前角色已装配</span>
                  ) : (
                    <span className="text-muted-foreground group-hover:text-foreground">点击装配此角色 →</span>
                  )}
                </span>
              </div>
            </div>
          )
        })}
      </div>

      {/* 快捷微调操作栏与折叠开关 */}
      <div className="flex flex-wrap items-center justify-between gap-2 p-2 rounded-md bg-muted/20 border border-border/40">
        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={() => setIsDetailedOpen(!isDetailedOpen)}
          className="h-6 px-2 text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
        >
          {isDetailedOpen ? <ChevronUpIcon className="size-3.5" /> : <ChevronDownIcon className="size-3.5" />}
          <span>{isDetailedOpen ? '收起细粒度工具清单' : '🛠️ 展开自定义工具细粒度微调清单 (47项)'}</span>
        </Button>

        <div className="flex items-center gap-1.5 shrink-0">
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-6 px-2 text-xs text-foreground border-border hover:bg-muted"
            onClick={handleSelectAll}
            disabled={disabled || selectedTools.length === allowedToolIds.length}
            title="全选当前角色允许的所有工具"
          >
            <SparklesIcon className="size-3 mr-1 text-cyan-500" />
            全选
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-6 px-2 text-xs text-muted-foreground hover:text-foreground"
            onClick={handleSelectDefaults}
            disabled={disabled}
          >
            <RotateCcwIcon className="size-3 mr-1" />
            推荐
          </Button>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="h-6 px-2 text-xs text-rose-500 hover:bg-rose-500/10 hover:text-rose-600"
            onClick={handleClearAll}
            disabled={disabled || selectedTools.length === 0}
          >
            <Trash2Icon className="size-3 mr-1" />
            清空
          </Button>
        </div>
      </div>

      {/* 折叠区：细粒度工具单项勾选 (默认收起，高级微调时展开) */}
      {isDetailedOpen && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
          {TOOL_CATEGORIES.map((cat) => {
            const availableToolsInCat = cat.tools.filter((t) => !isToolDisabledByRole(t, userRole))
            const selectedInCat = cat.tools.filter((t) => selectedTools.includes(t.id))
            const isAllSelected =
              availableToolsInCat.length > 0 && selectedInCat.length >= availableToolsInCat.length
            const isPartial = selectedInCat.length > 0 && !isAllSelected

            return (
              <div
                key={cat.id}
                className={`rounded-lg border transition-all flex flex-col ${
                  isAllSelected
                    ? 'border-cyan-500/30 bg-muted/20'
                    : isPartial
                      ? 'border-border/80 bg-background/90'
                      : 'border-border/50 bg-background/50'
                }`}
              >
                {/* 分类头部：点击即可快捷切换该分类全选/全不选 */}
                <div
                  className="flex items-center justify-between p-2.5 border-b border-border/40 bg-muted/30 hover:bg-muted/50 cursor-pointer select-none transition-colors"
                  onClick={() => handleToggleCategory(cat.tools)}
                  title={isAllSelected ? '点击取消该组所有可用工具' : '点击全选该组所有可用工具'}
                >
                  <div className="flex items-center gap-1.5 min-w-0 pr-1">
                    <span className="font-semibold text-foreground text-xs truncate">
                      {cat.name}
                    </span>
                    <span
                      className={`font-mono text-xs px-1.5 py-0.2 rounded border ${
                        isAllSelected
                          ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-600 dark:text-cyan-400'
                          : isPartial
                            ? 'bg-muted border-border text-foreground'
                            : 'bg-muted/40 border-border/40 text-muted-foreground'
                      }`}
                    >
                      {selectedInCat.length}/{availableToolsInCat.length}
                    </span>
                  </div>

                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-6 px-1.5 text-xs text-cyan-600 dark:text-cyan-400 hover:bg-cyan-500/10 shrink-0"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleToggleCategory(cat.tools)
                    }}
                    disabled={disabled || availableToolsInCat.length === 0}
                  >
                    {isAllSelected ? (
                      <>
                        <CheckSquareIcon className="size-3.5 mr-1 text-cyan-500" />
                        取消全选
                      </>
                    ) : (
                      <>
                        <SquareIcon className="size-3.5 mr-1 text-muted-foreground" />
                        全选本组
                      </>
                    )}
                  </Button>
                </div>

                {/* 场景说明 */}
                <div className="px-2.5 py-1.5 text-xs text-muted-foreground border-b border-border/20 bg-background/40 leading-snug">
                  {cat.description}
                </div>

                {/* 工具卡片列表 */}
                <div className="p-2 space-y-1.5 flex-1">
                  {cat.tools.map((tool) => {
                    const isChecked = selectedTools.includes(tool.id)
                    const isDisabled = disabled || isToolDisabledByRole(tool, userRole)

                    const cardContent = (
                      <div
                        key={tool.id}
                        onClick={() => !isDisabled && handleToggleTool(tool)}
                        className={`group flex items-start justify-between p-2 rounded-md border transition-all ${
                          isDisabled
                            ? 'border-border/30 bg-muted/10 opacity-55 cursor-not-allowed select-none'
                            : isChecked
                              ? 'border-cyan-500/40 bg-cyan-500/8 text-foreground cursor-pointer'
                              : 'border-border/40 bg-background/80 hover:border-border hover:bg-muted/40 text-muted-foreground cursor-pointer'
                        }`}
                      >
                        <div className="min-w-0 pr-2 flex-1">
                          <div className="flex items-center gap-1.5 font-mono text-xs font-medium flex-wrap">
                            <span className={isChecked && !isDisabled ? 'text-cyan-600 dark:text-cyan-400' : 'text-foreground'}>
                              {tool.id}
                            </span>
                            <span className="font-sans text-xs text-muted-foreground font-normal">
                              {tool.name.includes('(')
                                ? tool.name.substring(tool.name.indexOf('('))
                                : ''}
                            </span>
                            {/* 技术属性标签 */}
                            <Badge
                              variant="secondary"
                              className="text-xs h-4.5 px-1.5 py-0 font-normal font-sans border border-border/40 bg-muted/60"
                            >
                              {tool.categoryBadge}
                            </Badge>
                            {/* 角色门禁徽标 */}
                            {tool.requiredRole && (
                              <Badge
                                variant="outline"
                                className={`text-xs h-4.5 px-1.5 py-0 font-normal font-sans ${
                                  isDisabled
                                    ? 'border-rose-500/30 text-rose-500 bg-rose-500/5'
                                    : 'border-border/60 text-muted-foreground'
                                }`}
                              >
                                <LockIcon className="size-2.5 mr-0.5" />
                                需 {tool.requiredRole} 权限
                              </Badge>
                            )}
                          </div>
                          <div className="text-xs text-muted-foreground/80 leading-relaxed mt-0.5">
                            {tool.description}
                          </div>
                        </div>

                        {/* 复选框 */}
                        <div
                          className={`mt-0.5 size-4 rounded flex items-center justify-center border shrink-0 transition-colors ${
                            isDisabled
                              ? 'border-border/40 bg-muted/30 text-transparent'
                              : isChecked
                                ? 'bg-cyan-500 border-cyan-500 text-white'
                                : 'border-border bg-background group-hover:border-foreground/50'
                          }`}
                        >
                          {isChecked && !isDisabled && <CheckIcon className="size-3 stroke-3" />}
                          {isDisabled && <LockIcon className="size-2.5 text-muted-foreground/50" />}
                        </div>
                      </div>
                    )

                    if (isDisabled && tool.requiredRole) {
                      return (
                        <Tooltip key={tool.id}>
                          <TooltipTrigger render={cardContent} />
                          <TooltipContent className="text-xs max-w-xs">
                            当前所属用户角色为 <strong>{userRole}</strong>，其账号凭证权限未包含此系统特权工具。智能体权限不得超越所属用户，若需开启，请在用户管理中将该用户提升为 <strong>{tool.requiredRole}</strong> 或 <strong>root</strong> 权限。
                          </TooltipContent>
                        </Tooltip>
                      )
                    }

                    return cardContent
                  })}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
