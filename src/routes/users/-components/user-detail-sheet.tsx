/**
 * user-detail-sheet.tsx
 * 用户详情与专属凭据管理右侧抽屉面板 (User Detail Control Panel).
 *
 * 核心设计哲学 (第一性原理)：
 * 1. 彻底解耦：智能体的全生命周期增删改与工具包配置收口至独立的「智能体中心」(/agents)；
 * 2. 用户抽屉聚焦：用户凭据、安全密钥、角色归属与名下智能体概览；
 * 3. 极速跳转：提供「前往智能体中心管理 ➔」按钮，带参数秒级直达；
 * 4. 严守 NO GREEN EVER 🚫、>= 12px 字体下限与 100~300 行黄金甜点区。
 */

import * as React from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import {
  BotIcon,
  ChevronRightIcon,
  CopyIcon,
  ExternalLinkIcon,
  LoaderCircleIcon,
  RotateCwIcon,
  TerminalIcon,
} from 'lucide-react'
import { toast } from 'sonner'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '#/components/ui/sheet'
import type { AdminUser, UserAgentItem } from '#/lib/admin'
import { fetchUserAgents } from '#/lib/admin'
import { UserOverviewCard } from './user-overview-card'

export type UserDetailSheetProps = {
  user: AdminUser | null
  open: boolean
  onOpenChange: (open: boolean) => void
  currentUserId?: string
  onSwitchIdentity?: (user: AdminUser) => void
  onRegenerateKey?: (user: AdminUser) => void
}

export function UserDetailSheet({
  user,
  open,
  onOpenChange,
  currentUserId,
  onSwitchIdentity,
  onRegenerateKey,
}: UserDetailSheetProps) {
  const navigate = useNavigate()
  const userId = user?.userId || 'default'
  const isCurrentIdentity = currentUserId === userId

  // 获取指定用户的在册智能体概览数据
  const {
    data: rawAgents = [],
    isLoading,
    refetch,
    isFetching,
  } = useQuery<UserAgentItem[]>({
    queryKey: ['user-agents', userId],
    queryFn: () => fetchUserAgents(userId),
    enabled: open && Boolean(userId),
    staleTime: 5000,
  })

  const agents = Array.isArray(rawAgents) ? rawAgents : []

  const handleNavigateToAgents = (agentId?: string) => {
    onOpenChange(false)
    navigate({
      to: '/agents',
      search: agentId ? ({ focus: agentId } as Record<string, unknown>) : undefined,
    })
  }

  const handleCopyAgentId = async (agentId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await navigator.clipboard.writeText(agentId)
      toast.success(`已复制 AgentID: ${agentId}`)
    } catch {
      toast.error('复制失败')
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="flex w-full flex-col gap-4 overflow-y-auto border-l border-border bg-card p-6 font-sans text-xs data-[side=right]:sm:max-w-155 data-[side=right]:lg:max-w-180"
      >
        <SheetHeader className="space-y-1 border-b border-border/70 pb-3">
          <div className="flex items-center gap-2">
            <SheetTitle className="text-base font-semibold tracking-tight text-foreground">
              用户详情与安全座舱
            </SheetTitle>
            <Badge variant="outline" className="font-mono text-xs">
              {userId}
            </Badge>
            {isCurrentIdentity && (
              <Badge className="border-cyan-500/30 bg-cyan-500/10 text-xs text-cyan-600 dark:text-cyan-400">
                当前使用身份
              </Badge>
            )}
          </div>
          <SheetDescription className="text-xs text-muted-foreground">
            管理当前用户的基本权限凭据与安全防线。智能体资产已全面收口至独立的「智能体中心」。
          </SheetDescription>
        </SheetHeader>

        {/* 区域 1：用户基础凭据网格 */}
        <UserOverviewCard
          user={user}
          isCurrentIdentity={isCurrentIdentity}
          onSwitchIdentity={onSwitchIdentity}
          onRegenerateKey={onRegenerateKey}
        />

        {/* 区域 2：用户名下在册智能体汇总与直通跳转 */}
        <div className="flex flex-1 flex-col gap-3 border-t border-border/60 pt-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="rounded border border-border/60 bg-muted/60 p-1 text-cyan-500">
                <BotIcon className="size-3.5" />
              </div>
              <span className="font-semibold text-foreground/90">
                名下在册智能体概览 ({agents.length})
              </span>
            </div>

            <div className="flex items-center gap-2">
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="h-6.5 px-2 font-mono text-xs"
                onClick={() => refetch()}
                disabled={isFetching}
              >
                <RotateCwIcon className={`mr-1 size-3 ${isFetching ? 'animate-spin' : ''}`} />
                刷新
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="h-6.5 gap-1 border-cyan-500/40 bg-cyan-500/10 px-2.5 font-mono text-xs text-cyan-700 hover:bg-cyan-500/20 active:bg-cyan-500/30 dark:border-cyan-500/50 dark:bg-cyan-950/40 dark:text-cyan-300 dark:hover:bg-cyan-900/50"
                onClick={() => handleNavigateToAgents()}
              >
                <ExternalLinkIcon className="size-3" />
                前往智能体中心管理 ➔
              </Button>
            </div>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-8 font-mono text-xs text-muted-foreground">
              <LoaderCircleIcon className="mr-2 size-4 animate-spin text-cyan-500" />
              正在同步智能体资产...
            </div>
          ) : agents.length === 0 ? (
            <div className="rounded-md border border-dashed border-border/80 p-6 text-center font-mono text-xs text-muted-foreground">
              该用户当前暂未签发智能体。点击上方【前往智能体中心管理】创建专属 Agent。
            </div>
          ) : (
            <div className="max-h-72 space-y-2 overflow-y-auto pr-1">
              {agents.map((a) => {
                const isActive = a.status === 'active'
                const toolCount = a.allowed_tools.length

                return (
                  <div
                    key={a.agent_id}
                    onClick={() => handleNavigateToAgents(a.agent_id)}
                    className="group flex cursor-pointer flex-col justify-between gap-2 rounded-md border border-border/70 bg-muted/20 p-2.5 transition-all hover:border-cyan-500/60 hover:bg-muted/40 hover:shadow-xs"
                  >
                    {/* 卡片头部行 */}
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex min-w-0 items-center gap-2">
                        <div className="flex size-6 shrink-0 items-center justify-center rounded border border-cyan-500/30 bg-cyan-500/10 text-cyan-500">
                          <BotIcon className="size-3.5" />
                        </div>
                        <span className="truncate text-xs font-semibold text-foreground group-hover:text-cyan-500 transition-colors">
                          {a.agent_name || a.agent_id}
                        </span>
                      </div>

                      <div className="flex shrink-0 items-center gap-1.5">
                        <div className="inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-xs font-mono border-border/60">
                          <span
                            className={`size-1.5 rounded-full ${
                              isActive ? 'bg-cyan-500 animate-pulse' : 'bg-muted-foreground'
                            }`}
                          />
                          <span className={isActive ? 'text-cyan-600 dark:text-cyan-400 font-medium' : 'text-muted-foreground'}>
                            {isActive ? '在籍' : '已下线'}
                          </span>
                        </div>
                        <ChevronRightIcon className="size-3.5 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-cyan-500" />
                      </div>
                    </div>

                    {/* 卡片芯片属性行 */}
                    <div className="flex flex-wrap items-center gap-2 font-mono text-xs text-muted-foreground border-t border-border/40 pt-1.5">
                      <div className="inline-flex items-center gap-1 rounded border border-border/50 bg-background/80 px-1.5 py-0.5 text-foreground">
                        <span className="text-muted-foreground">ID:</span>
                        <span className="truncate max-w-32">{a.agent_id}</span>
                        <button
                          type="button"
                          className="p-0.5 text-muted-foreground hover:text-cyan-500"
                          onClick={(e) => handleCopyAgentId(a.agent_id, e)}
                          title="复制 AgentID"
                        >
                          <CopyIcon className="size-2.5" />
                        </button>
                      </div>

                      <Badge variant="outline" className="h-5 gap-1 border-border/60 text-xs text-muted-foreground">
                        <TerminalIcon className="size-2.5 text-cyan-500" />
                        <span>{toolCount} 项工具</span>
                      </Badge>

                      {a.role_desc && (
                        <span className="truncate max-w-44 text-muted-foreground font-sans" title={a.role_desc}>
                          {a.role_desc}
                        </span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
