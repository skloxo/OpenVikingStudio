/**
 * user-agents-sheet.tsx
 * 用户专属在籍智能体管理右侧抽屉 (Sheet / Drawer).
 * 物理隔离各 User 独立的 Agent 标识与授权凭牌，切除全局混淆，严守 NO GREEN EVER 🚫 与 >= 12px 规范。
 */
import * as React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  BotIcon,
  GlobeIcon,
  HelpCircleIcon,
  LaptopIcon,
  LoaderCircleIcon,
  PlusIcon,
  RotateCcwIcon,
  RotateCwIcon,
  TerminalIcon,
  Trash2Icon,
  XCircleIcon,
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '#/components/ui/table'
import type {
  AdminUser,
  CreateAgentInput,
  CreateAgentResponse,
  UserAgentItem,
} from '#/lib/admin'
import {
  activateUserAgent,
  createUserAgent,
  fetchUserAgents,
  purgeUserAgent,
  revokeUserAgent,
} from '#/lib/admin'
import { AddAgentDialog } from './add-agent-dialog'
import { AgentOnboardingModal } from './agent-onboarding-modal'
import { PurgeAgentDialog } from './purge-agent-dialog'

export type UserAgentsSheetProps = {
  user: AdminUser | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function UserAgentsSheet({
  user,
  open,
  onOpenChange,
}: UserAgentsSheetProps) {
  const queryClient = useQueryClient()
  const userId = user?.userId || 'default'

  const [addDialogOpen, setAddDialogOpen] = React.useState(false)
  const [pendingPurgeAgent, setPendingPurgeAgent] = React.useState<UserAgentItem | null>(null)
  const [onboardingData, setOnboardingData] = React.useState<CreateAgentResponse | null>(null)
  const [onboardingOpen, setOnboardingOpen] = React.useState(false)

  // 1. 获取指定用户下的专属在籍 Agent 列表
  const { data: agents = [], isLoading, refetch, isFetching } = useQuery({
    queryKey: ['user-agents', userId],
    queryFn: () => fetchUserAgents(userId),
    enabled: open && Boolean(userId),
    staleTime: 5000,
  })

  // 2. 创建专属 Agent 突变
  const createMutation = useMutation({
    mutationFn: (input: CreateAgentInput) => createUserAgent(userId, input),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['user-agents', userId] })
      queryClient.invalidateQueries({ queryKey: ['console-peers'] })
      toast.success(`智能体 ${data.agent.agent_id} 已授权至用户 ${userId}`)
      setAddDialogOpen(false)
      setOnboardingData(data)
      setOnboardingOpen(true)
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : '创建智能体失败')
    },
  })

  // 3. 吊销/下线 Agent 突变
  const revokeMutation = useMutation({
    mutationFn: (agentId: string) => revokeUserAgent(userId, agentId),
    onSuccess: (_, agentId) => {
      queryClient.invalidateQueries({ queryKey: ['user-agents', userId] })
      queryClient.invalidateQueries({ queryKey: ['console-peers'] })
      toast.success(`已下线智能体 ${agentId}`)
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : '下线智能体失败')
    },
  })

  // 4. 彻底物理删除 Agent 突变
  const purgeMutation = useMutation({
    mutationFn: (agentId: string) => purgeUserAgent(userId, agentId),
    onSuccess: (_, agentId) => {
      queryClient.invalidateQueries({ queryKey: ['user-agents', userId] })
      queryClient.invalidateQueries({ queryKey: ['console-peers'] })
      toast.success(`已彻底删除智能体 ${agentId}`)
      setPendingPurgeAgent(null)
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : '删除智能体失败')
    },
  })

  // 5. 重新激活 Agent 突变
  const activateMutation = useMutation({
    mutationFn: (agentId: string) => activateUserAgent(userId, agentId),
    onSuccess: (_, agentId) => {
      queryClient.invalidateQueries({ queryKey: ['user-agents', userId] })
      queryClient.invalidateQueries({ queryKey: ['console-peers'] })
      toast.success(`已重新激活智能体 ${agentId}`)
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : '激活智能体失败')
    },
  })

  const handleOpenGuide = (agent: UserAgentItem) => {
    const isLocal = agent.connection_mode === 'realtimeApi'
    const targetServer = isLocal ? 'http://127.0.0.1:1933/mcp' : `${window.location.origin}/mcp`
    const args = [
      '-y',
      'openviking-bridge',
      '--server',
      targetServer,
      '--agent-id',
      agent.agent_id,
    ]
    if (!isLocal) {
      args.push('--key', '${OPENVIKING_API_KEY}')
    }

    setOnboardingData({
      agent,
      bootstrap: {
        topology: isLocal ? 'local' : 'remote',
        target_server: targetServer,
        mcp_config: {
          mcpServers: {
            openviking: {
              command: 'npx',
              args,
            },
          },
        },
        system_prompt: `# OpenViking 体外大脑专属接入指南 (${isLocal ? '本地宿主直连' : '网络远程卫星'})\n- 你的身份牌 (Agent ID): \`${agent.agent_id}\`\n- 归属用户 (User ID): \`${agent.user_id}\`\n- 专属工作空间: viking://user/${agent.user_id}/peers/${agent.agent_id}/memories/\n- 演进公理: 遇到复杂工程疑难时优先调用 openviking_find 召回知识；解决突破后调用 openviking_record_evolution_lesson 沉淀资产。`,
        remote_mcp_url: isLocal
          ? `http://127.0.0.1:1933/mcp?agent_id=${agent.agent_id}`
          : `${window.location.origin}/mcp?agent_id=${agent.agent_id}&key=\${OPENVIKING_API_KEY}`,
      },
    })
    setOnboardingOpen(true)
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-2xl md:max-w-3xl overflow-y-auto flex flex-col gap-4 font-sans p-6"
      >
        <SheetHeader className="pb-3 border-b border-border/70">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-md bg-muted border border-border text-cyan-500">
                <BotIcon className="size-5" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <SheetTitle className="text-base font-semibold tracking-tight">
                    用户专属智能体：{userId}
                  </SheetTitle>
                  <Badge variant="outline" className="text-xs h-5 px-1.5 font-mono">
                    {agents.length} 个在籍
                  </Badge>
                </div>
                <SheetDescription className="text-xs text-muted-foreground mt-1">
                  该列表仅属于租户用户 <span className="font-mono text-foreground font-medium">{userId}</span>，与全系统其他用户严格物理隔离。
                </SheetDescription>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs"
                onClick={() => refetch()}
                disabled={isFetching}
              >
                <RotateCwIcon className={`size-3.5 mr-1 ${isFetching ? 'animate-spin' : ''}`} />
                刷新
              </Button>
              <Button
                size="sm"
                className="h-7 text-xs"
                onClick={() => setAddDialogOpen(true)}
              >
                <PlusIcon className="size-3.5 mr-1" />
                添加智能体
              </Button>
            </div>
          </div>
        </SheetHeader>

        {/* 智能体表格区 */}
        <div className="flex-1 py-1">
          {isLoading ? (
            <div className="flex items-center justify-center py-12 text-xs text-muted-foreground">
              <LoaderCircleIcon className="size-4 animate-spin mr-2 text-cyan-500" />
              正在加载用户专属智能体...
            </div>
          ) : agents.length === 0 ? (
            <div className="text-center py-12 border border-dashed border-border rounded-md text-xs text-muted-foreground">
              用户 {userId} 暂未授权专属智能体。点击右上角【添加智能体】为其签发接入凭牌。
            </div>
          ) : (
            <div className="rounded-md border border-border overflow-hidden">
              <Table>
                <TableHeader className="bg-muted/50 text-muted-foreground">
                  <TableRow className="border-border hover:bg-transparent">
                    <TableHead className="text-xs h-8">Agent 身份标识</TableHead>
                    <TableHead className="text-xs h-8">角色定位</TableHead>
                    <TableHead className="text-xs h-8">连接方式</TableHead>
                    <TableHead className="text-xs h-8 text-right">沉淀消息</TableHead>
                    <TableHead className="text-xs h-8 text-center">状态</TableHead>
                    <TableHead className="text-xs h-8 text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {agents.map((agent) => {
                    const isLocal = agent.connection_mode === 'realtimeApi'
                    const isActive = agent.status === 'active'
                    return (
                      <TableRow key={agent.agent_id} className="border-border text-xs hover:bg-muted/40">
                        <TableCell className="font-mono text-foreground py-2.5">
                          <div className="flex items-center gap-1.5">
                            <TerminalIcon className="size-3.5 text-cyan-500" />
                            <span className="font-medium">{agent.agent_id}</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-muted-foreground py-2.5">{agent.role_desc}</TableCell>
                        <TableCell className="py-2.5">
                          <div className="flex items-center gap-1 text-muted-foreground font-mono">
                            {isLocal ? (
                              <>
                                <LaptopIcon className="size-3 text-cyan-500" />
                                <span>本地直连</span>
                              </>
                            ) : (
                              <>
                                <GlobeIcon className="size-3 text-muted-foreground" />
                                <span>网络远程</span>
                              </>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-right font-mono tabular-nums text-foreground py-2.5">
                          {agent.total_messages.toLocaleString()}
                        </TableCell>
                        <TableCell className="text-center py-2.5">
                          <Badge
                            variant="outline"
                            className={`text-xs h-5 px-1.5 ${
                              isActive
                                ? 'border-cyan-500/30 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400'
                                : 'border-muted-foreground/30 bg-muted text-muted-foreground'
                            }`}
                          >
                            {isActive ? '在籍活跃' : '已吊销'}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right py-2.5 space-x-1">
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 px-2 text-xs hover:text-cyan-600 hover:bg-muted"
                            onClick={() => handleOpenGuide(agent)}
                          >
                            <HelpCircleIcon className="size-3 mr-1" />
                            接入指南
                          </Button>

                          {isActive ? (
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-6 px-2 text-xs text-rose-500 hover:text-rose-600 hover:bg-rose-500/10"
                              onClick={() => revokeMutation.mutate(agent.agent_id)}
                              disabled={revokeMutation.isPending}
                            >
                              <XCircleIcon className="size-3 mr-1" />
                              下线
                            </Button>
                          ) : (
                            <>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-6 px-2 text-xs text-cyan-600 hover:text-cyan-700 hover:bg-cyan-500/10"
                                onClick={() => activateMutation.mutate(agent.agent_id)}
                                disabled={activateMutation.isPending}
                              >
                                <RotateCcwIcon className="size-3 mr-1" />
                                重新激活
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-6 px-2 text-xs text-rose-500 hover:text-rose-600 hover:bg-rose-500/10"
                                onClick={() => setPendingPurgeAgent(agent)}
                              >
                                <Trash2Icon className="size-3 mr-1" />
                                彻底删除
                              </Button>
                            </>
                          )}
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </div>

        {/* 抽屉子组件：添加智能体与彻底删除确认 */}
        <AddAgentDialog
          open={addDialogOpen}
          onOpenChange={setAddDialogOpen}
          userId={userId}
          isPending={createMutation.isPending}
          onSubmit={(input) => createMutation.mutate(input)}
        />

        <PurgeAgentDialog
          agent={pendingPurgeAgent}
          isPending={purgeMutation.isPending}
          onClose={() => setPendingPurgeAgent(null)}
          onConfirm={(agentId) => purgeMutation.mutate(agentId)}
        />

        {/* 专属接入引导抽屉 (Sheet) */}
        <AgentOnboardingModal
          data={onboardingData}
          open={onboardingOpen}
          onOpenChange={setOnboardingOpen}
        />
      </SheetContent>
    </Sheet>
  )
}
