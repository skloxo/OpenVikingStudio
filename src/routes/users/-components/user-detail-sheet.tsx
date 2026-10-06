/**
 * user-detail-sheet.tsx
 * 用户详情与专属资产管理右侧抽屉 (User Detail & Assets Sheet).
 * 一体化融合展示用户基础信息、API 密钥凭据以及下属在册智能体 (Agent) 资产。
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
  CreateAgentResponse,
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
import { AgentFormDialog } from './agent-form-dialog'
import { AgentOnboardingModal } from './agent-onboarding-modal'
import { SoftDeleteAgentDialog } from './soft-delete-agent-dialog'
import { UserAgentsTable } from './user-agents-table'
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

  // 模态弹窗状态
  const [formDialogOpen, setFormDialogOpen] = React.useState(false)
  const [editingAgent, setEditingAgent] = React.useState<UserAgentItem | null>(null)
  const [pendingDeleteAgent, setPendingDeleteAgent] = React.useState<UserAgentItem | null>(null)
  const [onboardingData, setOnboardingData] = React.useState<CreateAgentResponse | null>(null)
  const [onboardingOpen, setOnboardingOpen] = React.useState(false)

  // 1. 获取指定用户的在册智能体
  const { data: agents = [], isLoading, refetch, isFetching } = useQuery({
    queryKey: ['user-agents', userId],
    queryFn: () => fetchUserAgents(userId),
    enabled: open && Boolean(userId),
    staleTime: 5000,
  })

  // 2. 突变：创建或编辑智能体
  const createMutation = useMutation({
    mutationFn: (input: CreateAgentInput) => createUserAgent(userId, input),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['user-agents', userId] })
      queryClient.invalidateQueries({ queryKey: ['user-agent-counts'] })
      queryClient.invalidateQueries({ queryKey: ['console-peers'] })
      toast.success(`智能体「${data.agent.agent_name}」已签发成功`)
      setFormDialogOpen(false)
      setOnboardingData(data)
      setOnboardingOpen(true)
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : '创建智能体失败')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ agentId, input }: { agentId: string; input: UpdateAgentInput }) =>
      updateUserAgent(userId, agentId, input),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['user-agents', userId] })
      toast.success(`智能体「${updated.agent_name}」配置已更新`)
      setFormDialogOpen(false)
      setEditingAgent(null)
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : '更新配置失败')
    },
  })

  // 3. 突变：软删除智能体
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

  // 4. 突变：重新激活智能体
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

  // 打开接入指南
  const handleOpenGuide = (agent: UserAgentItem) => {
    const isLocal = agent.connection_mode === 'realtimeApi'
    const origin = typeof window !== 'undefined' ? window.location.origin : 'http://127.0.0.1:1933'
    const mcpUrl = `${origin}/mcp?user_id=${encodeURIComponent(userId)}&agent_id=${encodeURIComponent(agent.agent_id)}`
    const prompt = `你是已在 OpenViking 注册在籍的智能体 [${agent.agent_name}]。\n你的系统永久身份证为: ${agent.agent_id}，所属用户为: ${userId}。\n请通过 FastMCP 端点接入中枢: ${mcpUrl}`

    setOnboardingData({
      agent,
      bootstrap: {
        topology: isLocal ? 'local_copilot' : 'remote_satellite',
        remote_mcp_url: mcpUrl,
        system_prompt: prompt,
        mcp_config: {
          mcpServers: {
            openviking: {
              url: mcpUrl,
            },
          },
        },
      },
    })
    setOnboardingOpen(true)
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-2xl md:max-w-3xl overflow-y-auto flex flex-col gap-5 font-sans p-6"
      >
        <SheetHeader className="pb-3 border-b border-border/70">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <SheetTitle className="text-base font-semibold tracking-tight">
                  用户详情与资产看板
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
              <SheetDescription className="text-xs text-muted-foreground mt-1">
                管理该用户的基本权限、API 访问密钥与名下在册智能体。
              </SheetDescription>
            </div>
          </div>
        </SheetHeader>

        {/* 上半区：用户基础信息与核心凭据 */}
        <UserOverviewCard
          user={user}
          isCurrentIdentity={isCurrentIdentity}
          onSwitchIdentity={onSwitchIdentity}
          onRegenerateKey={onRegenerateKey}
        />

        {/* 下半区：用户名下在册智能体 (Agent Principals) */}
        <div className="flex-1 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="p-1 rounded bg-muted border text-cyan-500">
                <BotIcon className="size-4" />
              </div>
              <span className="text-xs font-semibold text-foreground">
                在册智能体列表 ({agents.length})
              </span>
            </div>

            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs"
                onClick={() => refetch()}
                disabled={isFetching}
              >
                <RotateCwIcon className={`size-3 mr-1 ${isFetching ? 'animate-spin' : ''}`} />
                刷新
              </Button>
              <Button
                size="sm"
                className="h-7 text-xs"
                onClick={() => {
                  setEditingAgent(null)
                  setFormDialogOpen(true)
                }}
              >
                <PlusIcon className="size-3 mr-1" />
                签发新智能体
              </Button>
            </div>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-12 text-xs text-muted-foreground">
              <LoaderCircleIcon className="size-4 animate-spin mr-2 text-cyan-500" />
              正在加载在册智能体...
            </div>
          ) : agents.length === 0 ? (
            <div className="text-center py-10 border border-dashed rounded-md text-xs text-muted-foreground">
              该用户暂无在册智能体。点击右上角【签发新智能体】为其创建专属 Agent。
            </div>
          ) : (
            <UserAgentsTable
              agents={agents}
              onOpenGuide={handleOpenGuide}
              onEditAgent={(agent) => {
                setEditingAgent(agent)
                setFormDialogOpen(true)
              }}
              onDeleteAgent={(agent) => setPendingDeleteAgent(agent)}
              onActivateAgent={(agentId) => activateMutation.mutate(agentId)}
              isActivating={activateMutation.isPending}
            />
          )}
        </div>

        {/* 智能体表单弹窗 (创建或编辑) */}
        <AgentFormDialog
          open={formDialogOpen}
          onOpenChange={setFormDialogOpen}
          userId={userId}
          initialAgent={editingAgent}
          isPending={createMutation.isPending || updateMutation.isPending}
          onSubmit={(data) => {
            if (data.update && editingAgent) {
              updateMutation.mutate({
                agentId: editingAgent.agent_id,
                input: data.update,
              })
            } else if (data.create) {
              createMutation.mutate(data.create)
            }
          }}
        />

        {/* 软删除确认弹窗 */}
        <SoftDeleteAgentDialog
          agent={pendingDeleteAgent}
          isPending={deleteMutation.isPending}
          onClose={() => setPendingDeleteAgent(null)}
          onConfirm={(agentId) => deleteMutation.mutate(agentId)}
        />

        {/* 接入令指南弹窗 */}
        <AgentOnboardingModal
          open={onboardingOpen}
          onOpenChange={setOnboardingOpen}
          data={onboardingData}
        />
      </SheetContent>
    </Sheet>
  )
}
