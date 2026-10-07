import React from 'react'
import {
  ShieldCheckIcon,
  CheckIcon,
  RadioIcon,
  CpuIcon,
  LockIcon,
  ChevronDownIcon,
  ChevronUpIcon,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  TOOL_CATEGORIES,
  ALL_TOOL_IDS,
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

    // 检查是否刚好为业务使用者包
    if (
      satAllowed.length > 0 &&
      satAllowed.every((id) => selectedSet.has(id)) &&
      selectedSet.size === satAllowed.length
    ) {
      return 'satellite_consumer'
    }

    return null
  }, [validSelectedIds, allowedToolIds])

  // 点选官方工具包 (整包赋权，切除微操勾选)
  const handleSelectBundle = React.useCallback(
    (bundle: ToolBundle) => {
      if (disabled) return
      const targetTools = bundle.toolIds.filter((id) => allowedToolIds.includes(id))
      onChange(targetTools)
    },
    [disabled, allowedToolIds, onChange],
  )

  return (
    <div className="space-y-3 pt-2 border-t border-border/40 font-sans text-xs">
      {/* 头部标题与权限说明 */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <ShieldCheckIcon className="size-4 text-cyan-500 shrink-0" />
          <span className="font-semibold text-foreground text-xs">智能体角色工具包 (Tool Bundles)</span>
          <Badge variant="outline" className="text-xs font-mono font-normal">
            已装配 {validSelectedIds.length} / {allowedToolIds.length} 项可用 (全域 {ALL_TOOL_IDS.length})
          </Badge>
        </div>

        {userRole === 'user' && allowedToolIds.length < ALL_TOOL_IDS.length && (
          <Badge variant="secondary" className="text-xs font-normal text-muted-foreground shrink-0">
            <LockIcon className="size-2.5 mr-1" />
            已置灰 {ALL_TOOL_IDS.length - allowedToolIds.length} 项系统特权工具
          </Badge>
        )}
      </div>

      {/* 核心卡片：两大官方角色工具包一键整包赋权 (切除多余啰嗦文案与重复装配状态) */}
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
                    variant="outline"
                    className={`text-xs font-mono font-normal h-5 px-1.5 ${
                      isSelected
                        ? 'border-cyan-500/40 text-cyan-600 dark:text-cyan-400 bg-cyan-500/5'
                        : 'text-muted-foreground border-border/60'
                    }`}
                  >
                    {bundle.highlightBadge}
                  </Badge>
                </div>

                <div className="text-xs text-foreground/90 font-medium mb-1">
                  角色定位：{bundle.roleTitle}
                </div>
                <div className="text-xs text-muted-foreground leading-relaxed">
                  {bundle.description}
                </div>
              </div>

              {/* 卡片底栏：合并删减重复啰嗦的“已选中生效”与“当前角色已装配”，只保留单一明确指示 */}
              <div className="pt-2 mt-2 border-t border-border/30 text-xs text-muted-foreground/80 flex items-center justify-between">
                <span className="truncate pr-2">{bundle.recommendedFor}</span>
                <span className="shrink-0 font-medium font-sans">
                  {isSelected ? (
                    <span className="text-cyan-600 dark:text-cyan-400 flex items-center gap-1">
                      <CheckIcon className="size-3 stroke-2.5" />
                      当前已装配
                    </span>
                  ) : (
                    <span className="text-muted-foreground group-hover:text-foreground">
                      点击选用此角色 →
                    </span>
                  )}
                </span>
              </div>
            </div>
          )
        })}
      </div>

      {/* 折叠开关：只读查看工具清单 (切除全选/清空/推荐等微调按钮) */}
      <div className="flex items-center justify-between p-2 rounded-md bg-muted/20 border border-border/40">
        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={() => setIsDetailedOpen(!isDetailedOpen)}
          className="h-6 px-2 text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 cursor-pointer"
        >
          {isDetailedOpen ? <ChevronUpIcon className="size-3.5" /> : <ChevronDownIcon className="size-3.5" />}
          <span>{isDetailedOpen ? '收起工具清单' : `📋 查看当前已装配工具清单 (${validSelectedIds.length} 项)`}</span>
        </Button>

        <span className="text-xs text-muted-foreground font-mono">
          按角色整包赋权，不支持单独勾选微操
        </span>
      </div>

      {/* 展开区：纯只读工具清单审阅面板 (切除所有 Checkbox 勾选框) */}
      {isDetailedOpen && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
          {TOOL_CATEGORIES.map((cat) => {
            const availableToolsInCat = cat.tools.filter((t) => !isToolDisabledByRole(t, userRole))
            const selectedInCat = cat.tools.filter((t) => selectedTools.includes(t.id))
            const isAllIncluded =
              availableToolsInCat.length > 0 && selectedInCat.length >= availableToolsInCat.length

            return (
              <div
                key={cat.id}
                className="rounded-lg border border-border/40 bg-background/50 flex flex-col"
              >
                {/* 分类头部 (纯信息展示，无全选按钮) */}
                <div className="flex items-center justify-between p-2.5 border-b border-border/30 bg-muted/25">
                  <div className="flex items-center gap-1.5 min-w-0 pr-1">
                    <span className="font-semibold text-foreground text-xs truncate">
                      {cat.name}
                    </span>
                    <span
                      className={`font-mono text-xs px-1.5 py-0.2 rounded border ${
                        isAllIncluded
                          ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-600 dark:text-cyan-400'
                          : selectedInCat.length > 0
                            ? 'bg-muted border-border text-foreground'
                            : 'bg-muted/40 border-border/40 text-muted-foreground'
                      }`}
                    >
                      已包含 {selectedInCat.length}/{availableToolsInCat.length}
                    </span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {isAllIncluded ? '全量装配' : selectedInCat.length === 0 ? '未包含' : '部分装配'}
                  </span>
                </div>

                {/* 场景说明 */}
                <div className="px-2.5 py-1.5 text-xs text-muted-foreground border-b border-border/20 bg-background/40 leading-snug">
                  {cat.description}
                </div>

                {/* 工具卡片列表 (纯只读审阅，彻底切除 Checkbox) */}
                <div className="p-2 space-y-1.5 flex-1">
                  {cat.tools.map((tool) => {
                    const isIncluded = selectedTools.includes(tool.id)
                    const isDisabled = isToolDisabledByRole(tool, userRole)

                    return (
                      <div
                        key={tool.id}
                        className={`flex items-start justify-between p-2 rounded-md border transition-all ${
                          isDisabled
                            ? 'border-border/30 bg-muted/10 opacity-50'
                            : isIncluded
                              ? 'border-cyan-500/30 bg-cyan-500/5 text-foreground'
                              : 'border-border/30 bg-muted/5 opacity-60 text-muted-foreground'
                        }`}
                      >
                        <div className="min-w-0 pr-2 flex-1">
                          <div className="flex items-center gap-1.5 font-mono text-xs font-medium flex-wrap">
                            <span className={isIncluded && !isDisabled ? 'text-cyan-600 dark:text-cyan-400 font-semibold' : 'text-muted-foreground'}>
                              {tool.id}
                            </span>
                            <span className="font-sans text-xs text-muted-foreground font-normal">
                              {tool.name.includes('(') ? tool.name.substring(tool.name.indexOf('(')) : ''}
                            </span>
                            <Badge
                              variant="secondary"
                              className="text-xs h-4.5 px-1.5 py-0 font-normal font-sans border border-border/40 bg-muted/60"
                            >
                              {tool.categoryBadge}
                            </Badge>
                            {tool.requiredRole && (
                              <Badge
                                variant="outline"
                                className="text-xs h-4.5 px-1.5 py-0 font-normal font-sans border-border/60 text-muted-foreground"
                              >
                                <LockIcon className="size-2.5 mr-0.5" />
                                需 {tool.requiredRole} 权限
                              </Badge>
                            )}
                          </div>
                          <div className="text-xs text-muted-foreground leading-relaxed mt-0.5">
                            {tool.description}
                          </div>
                        </div>

                        <div className="shrink-0 mt-0.5">
                          {isDisabled ? (
                            <span className="text-xs text-muted-foreground/60">角色受限</span>
                          ) : isIncluded ? (
                            <Badge variant="outline" className="text-xs h-4.5 px-1.5 border-cyan-500/40 text-cyan-600 dark:text-cyan-400 bg-cyan-500/10">
                              已装配
                            </Badge>
                          ) : (
                            <span className="text-xs text-muted-foreground/50">未包含</span>
                          )}
                        </div>
                      </div>
                    )
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
