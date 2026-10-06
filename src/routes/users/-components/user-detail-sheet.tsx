/**
 * user-detail-sheet.tsx
 * 用户详情与专属资产管理右侧抽屉面板 (User Detail & Assets Control Panel).
 * 对标技能中心 / 任务中心高密座舱面板设计：
 * 1. 抽屉内容不整体突变、零多层弹窗遮挡、零跳页！
 * 2. 纯内嵌面板交互：基本操作采用优雅平滑的原位展开与收起 (Collapsible)；
 * 3. 上半区高密用户凭据网格，下半区在册智能体原位就地编辑、权限勾选与接入令查看；
 * 严守 NO GREEN EVER 🚫、>= 12px 字体下限与单文件黄金甜点区。
 */
import * as React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  BotIcon,
  LoaderCircleIcon,
  PlusIcon,
  RotateCwIcon,
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
import type {
  AdminUser,
  CreateAgentInput,
  UpdateAgentInput,
  UserAgentItem,
} from '#/lib/admin'
import {
  activateUserAgent,
  createUserAgent,
  deleteUserAgent,
  fetchUserAgents,
  updateUserAgent,
} from '#/lib/admin'
import { AgentCollapsibleItem } from './agent-collapsible-item'
import { NewAgentCard } from './new-agent-card'
import { SoftDeleteAgentDialog } from './soft-delete-agent-dialog'
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
  const queryClient = useQueryClient()
  const userId = user?.userId || 'default'
  const isCurrentIdentity = currentUserId === userId

  // 抽屉内嵌就地状态：展开的新建卡片、当前展开的智能体 ID
  const [showNewAgentCard, setShowNewAgentCard] = React.useState(false)
  const [expandedAgentId, setExpandedAgentId] = React.useState<string | null>(null)
  const [pendingDeleteAgent, setPendingDeleteAgent] = React.useState<UserAgentItem | null>(null)

  // 1. 获取指定用户的在册智能体
  const { data: agents = [], isLoading, refetch, isFetching } = useQuery({
    queryKey: ['user-agents', userId],
    queryFn: () => fetchUserAgents(userId),
    enabled: open && Boolean(userId),
    staleTime: 5000,
  })

  // 2. 突变：创建新智能体
  const createMutation = useMutation({
    mutationFn: (input: CreateAgentInput) => createUserAgent(userId, input),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['user-agents', userId] })
      queryClient.invalidateQueries({ queryKey: ['user-agent-counts'] })
      queryClient.invalidateQueries({ queryKey: ['console-peers'] })
      toast.success(`智能体「${data.agent.agent_name}」已签发成功`)
      setShowNewAgentCard(false)
      // 自动展开新创建的智能体面板
      setExpandedAgentId(data.agent.agent_id)
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : '创建智能体失败')
    },
  })

  // 3. 突变：就地更新智能体
  const updateMutation = useMutation({
    mutationFn: ({ agentId, input }: { agentId: string; input: UpdateAgentInput }) =>
      updateUserAgent(userId, agentId, input),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['user-agents', userId] })
      toast.success(`智能体「${updated.agent_name}」配置已就地保存`)
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : '保存配置失败')
    },
  })

  // 4. 突变：软删除下线智能体
  const deleteMutation = useMutation({
    mutationFn: (agentId: string) => deleteUserAgent(userId, agentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-agents', userId] })
      queryClient.invalidateQueries({ queryKey: ['user-agent-counts'] })
      queryClient.invalidateQueries({ queryKey: ['console-peers'] })
      toast.success('智能体已下线 (软删除)')
      setPendingDeleteAgent(null)
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : '下线智能体失败')
    },
  })

  // 5. 突变：重新激活智能体
  const activateMutation = useMutation({
    mutationFn: (agentId: string) => activateUserAgent(userId, agentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-agents', userId] })
      queryClient.invalidateQueries({ queryKey: ['user-agent-counts'] })
      queryClient.invalidateQueries({ queryKey: ['console-peers'] })
      toast.success('智能体已重新激活在籍')
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : '激活智能体失败')
    },
  })

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full data-[side=right]:sm:max-w-[780px] data-[side=right]:lg:max-w-[920px] data-[side=right]:xl:max-w-[1060px] overflow-y-auto flex flex-col gap-4 font-sans p-6 text-xs bg-card border-l border-border"
      >
        <SheetHeader className="pb-3 border-b border-border/70 space-y-1">
          <div className="flex items-center gap-2">
            <SheetTitle className="text-base font-semibold tracking-tight text-foreground">
              用户详情与资产座舱
            </SheetTitle>
            <Badge variant="outline" className="text-xs font-mono">
              {userId}
            </Badge>
            {isCurrentIdentity && (
              <Badge className="text-xs bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/30">
                当前使用身份
              </Badge>
            )}
          </div>
          <SheetDescription className="text-xs text-muted-foreground">
            管理当前用户的基本权限凭据与名下在册智能体。支持原位展开收起与就地编辑配置。
          </SheetDescription>
        </SheetHeader>

        {/* 区域 1：用户基础凭据网格 */}
        <UserOverviewCard
          user={user}
          isCurrentIdentity={isCurrentIdentity}
          onSwitchIdentity={onSwitchIdentity}
          onRegenerateKey={onRegenerateKey}
        />

        {/* 区域 2：用户名下在册智能体 (Agent Principals) 纯面板，原位展开收起 */}
        <div className="flex-1 flex flex-col gap-2.5 pt-1">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="p-1 rounded bg-muted/60 border border-border/60 text-cyan-500">
                <BotIcon className="size-3.5" />
              </div>
              <span className="font-semibold text-foreground/90">
                名下在册智能体 ({agents.length})
              </span>
            </div>

            <div className="flex items-center gap-2">
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="h-6.5 px-2 text-xs"
                onClick={() => refetch()}
                disabled={isFetching}
              >
                <RotateCwIcon className={`size-3 mr-1 ${isFetching ? 'animate-spin' : ''}`} />
                刷新
              </Button>
              <Button
                type="button"
                size="sm"
                className="h-6.5 px-2 text-xs"
                onClick={() => setShowNewAgentCard((prev) => !prev)}
              >
                <PlusIcon className="size-3 mr-1" />
                {showNewAgentCard ? '收起签发表单' : '签发新智能体'}
              </Button>
            </div>
          </div>

          {/* 就地展开的新智能体签发表单 (零跳页) */}
          <NewAgentCard
            open={showNewAgentCard}
            onClose={() => setShowNewAgentCard(false)}
            onSubmit={(input) => createMutation.mutate(input)}
            isPending={createMutation.isPending}
            userRole={user?.role ?? 'user'}
          />

          {/* 智能体卡片列表 */}
          {isLoading ? (
            <div className="flex items-center justify-center py-10 text-xs text-muted-foreground">
              <LoaderCircleIcon className="size-4 animate-spin mr-2 text-cyan-500" />
              正在加载智能体资产...
            </div>
          ) : agents.length === 0 && !showNewAgentCard ? (
            <div className="text-center py-8 border border-dashed rounded-md text-xs text-muted-foreground">
              该用户暂无在册智能体。点击右上角【签发新智能体】为其创建专属 Agent。
            </div>
          ) : (
            <div className="space-y-2">
              {agents.map((agent) => (
                <AgentCollapsibleItem
                  key={agent.agent_id}
                  agent={agent}
                  userId={userId}
                  userRole={user?.role ?? 'user'}
                  isExpanded={expandedAgentId === agent.agent_id}
                  onToggleExpand={() =>
                    setExpandedAgentId((prev) => (prev === agent.agent_id ? null : agent.agent_id))
                  }
                  onUpdate={(agentId, input) => updateMutation.mutate({ agentId, input })}
                  onDelete={(a) => setPendingDeleteAgent(a)}
                  onActivate={(id) => activateMutation.mutate(id)}
                  isUpdating={updateMutation.isPending}
                />
              ))}
            </div>
          )}
        </div>

        {/* 软删除下线确认弹窗 */}
        <SoftDeleteAgentDialog
          agent={pendingDeleteAgent}
          isPending={deleteMutation.isPending}
          onClose={() => setPendingDeleteAgent(null)}
          onConfirm={(agentId) => deleteMutation.mutate(agentId)}
        />
      </SheetContent>
    </Sheet>
  )
}
