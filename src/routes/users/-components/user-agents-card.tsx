/**
 * user-agents-card.tsx
 * 用户作用域在籍智能体标识管理卡片 (Card-113 / Card-116).
 * 遵循 Agent 编码规范与黄金甜点区 (<= 300 行)，严守 NO GREEN EVER 🚫、字号 >= 12px 与主题自适应规范。
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
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '#/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '#/components/ui/dialog'
import { Input } from '#/components/ui/input'
import { Label } from '#/components/ui/label'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '#/components/ui/table'
import type {
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
import { AgentOnboardingModal } from './agent-onboarding-modal'

export type UserAgentsCardProps = {
  userId?: string
}

export function UserAgentsCard({ userId = 'default' }: UserAgentsCardProps) {
  const queryClient = useQueryClient()
  const [addDialogOpen, setAddDialogOpen] = React.useState(false)
  const [newAgentId, setNewAgentId] = React.useState('')
  const [newRoleDesc, setNewRoleDesc] = React.useState('')
  const [newConnectionMode, setNewConnectionMode] = React.useState<'realtimeApi' | 'apiClient'>('apiClient')
  const [pendingPurgeAgent, setPendingPurgeAgent] = React.useState<UserAgentItem | null>(null)

  const [onboardingData, setOnboardingData] = React.useState<CreateAgentResponse | null>(null)
  const [onboardingOpen, setOnboardingOpen] = React.useState(false)

  // 1. 获取当前用户下的在籍 Agent 列表
  const { data: agents = [], isLoading, refetch, isFetching } = useQuery({
    queryKey: ['user-agents', userId],
    queryFn: () => fetchUserAgents(userId),
    staleTime: 5000,
  })

  // 2. 创建 Agent 突变
  const createMutation = useMutation({
    mutationFn: (input: CreateAgentInput) => createUserAgent(userId, input),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['user-agents', userId] })
      queryClient.invalidateQueries({ queryKey: ['console-peers'] })
      toast.success(`智能体 ${data.agent.agent_id} 授权成功`)
      setAddDialogOpen(false)
      setNewAgentId('')
      setNewRoleDesc('')
      setNewConnectionMode('apiClient')
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

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newAgentId.trim()) {
      toast.error('请输入智能体标识')
      return
    }
    createMutation.mutate({
      agent_id: newAgentId.trim(),
      role_desc: newRoleDesc.trim() || (newConnectionMode === 'realtimeApi' ? '本地主控开发助手' : '远程卫星智能体'),
      connection_mode: newConnectionMode,
    })
  }

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
    <Card className="bg-card text-card-foreground border-border mt-6 shadow-xs">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div>
          <div className="flex items-center gap-2">
            <BotIcon className="size-4 text-cyan-500" />
            <CardTitle className="text-sm font-semibold tracking-wide">
              用户专属智能体标识与授权矩阵 (Authorized Agents)
            </CardTitle>
          </div>
          <CardDescription className="text-xs text-muted-foreground mt-1">
            当前租户用户 <span className="font-mono text-foreground font-medium">{userId}</span> 下属在籍智能体。携带用户密钥与专属 Agent 标识即可免猜谜直连接入。
          </CardDescription>
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
            添加智能体标识
          </Button>
        </div>
      </CardHeader>

      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8 text-xs text-muted-foreground">
            <LoaderCircleIcon className="size-4 animate-spin mr-2 text-cyan-500" />
            正在加载智能体授权列表...
          </div>
        ) : agents.length === 0 ? (
          <div className="text-center py-8 border border-dashed border-border rounded-md text-xs text-muted-foreground">
            暂无在籍智能体。点击右上角【添加智能体标识】签发专属接入身份牌。
          </div>
        ) : (
          <div className="rounded-md border border-border overflow-hidden">
            <Table>
              <TableHeader className="bg-muted/50 text-muted-foreground">
                <TableRow className="border-border hover:bg-transparent">
                  <TableHead className="text-xs h-8">Agent 身份标识</TableHead>
                  <TableHead className="text-xs h-8">角色定位</TableHead>
                  <TableHead className="text-xs h-8">连接方式</TableHead>
                  <TableHead className="text-xs h-8 text-right">沉淀消息数</TableHead>
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
                          className={`text-[12px] h-5 px-1.5 ${
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
      </CardContent>

      {/* 添加智能体 Dialog */}
      <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
        <DialogContent className="max-w-md bg-card border-border text-card-foreground">
          <form onSubmit={handleCreate}>
            <DialogHeader>
              <DialogTitle className="text-sm font-semibold">签发新智能体身份牌</DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground">
                为用户 <span className="font-mono text-foreground font-medium">{userId}</span> 分配新的在籍 Agent 标识。
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-3.5 py-3">
              <div className="space-y-1.5">
                <Label htmlFor="agent-id" className="text-xs text-foreground">
                  智能体标识 (Agent ID) <span className="text-rose-500">*</span>
                </Label>
                <Input
                  id="agent-id"
                  placeholder="例如 cursor@macbook 或 deepseek-harness@2080ti"
                  className="h-8 text-xs font-mono"
                  value={newAgentId}
                  onChange={(e) => setNewAgentId(e.target.value)}
                  autoFocus
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="role-desc" className="text-xs text-foreground">
                  角色定位 / 职能描述
                </Label>
                <Input
                  id="role-desc"
                  placeholder="例如 远程开发哨兵、IDE 结对编程伙伴"
                  className="h-8 text-xs"
                  value={newRoleDesc}
                  onChange={(e) => setNewRoleDesc(e.target.value)}
                />
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs text-foreground">接入拓扑方式</Label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setNewConnectionMode('realtimeApi')}
                    className={`flex flex-col items-start p-2.5 rounded-md border text-left transition-colors ${
                      newConnectionMode === 'realtimeApi'
                        ? 'border-cyan-500 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400'
                        : 'border-border bg-background text-muted-foreground hover:bg-muted'
                    }`}
                  >
                    <div className="flex items-center gap-1.5 font-medium text-xs">
                      <LaptopIcon className="size-3.5" />
                      <span>本地宿主直连</span>
                    </div>
                    <span className="text-xs text-muted-foreground mt-0.5">同一主机 / WSL 本地进程直连</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setNewConnectionMode('apiClient')}
                    className={`flex flex-col items-start p-2.5 rounded-md border text-left transition-colors ${
                      newConnectionMode === 'apiClient'
                        ? 'border-cyan-500 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400'
                        : 'border-border bg-background text-muted-foreground hover:bg-muted'
                    }`}
                  >
                    <div className="flex items-center gap-1.5 font-medium text-xs">
                      <GlobeIcon className="size-3.5" />
                      <span>网络远程卫星</span>
                    </div>
                    <span className="text-xs text-muted-foreground mt-0.5">跨机器 / 远程节点反代网关</span>
                  </button>
                </div>
              </div>
            </div>

            <DialogFooter className="gap-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="text-xs h-8"
                onClick={() => setAddDialogOpen(false)}
              >
                取消
              </Button>
              <Button
                type="submit"
                size="sm"
                className="text-xs h-8"
                disabled={createMutation.isPending}
              >
                {createMutation.isPending ? '正在签发...' : '确认签发并获取接入令'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* 彻底删除确认 Dialog */}
      <Dialog open={Boolean(pendingPurgeAgent)} onOpenChange={(open) => !open && setPendingPurgeAgent(null)}>
        <DialogContent className="max-w-sm bg-card border-border text-card-foreground">
          <DialogHeader>
            <DialogTitle className="text-sm font-semibold text-rose-500">确认彻底删除智能体？</DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground mt-1">
              将从数据库中物理抹除 <span className="font-mono text-foreground font-semibold">{pendingPurgeAgent?.agent_id}</span> 的授权凭牌记录。此操作不可撤销。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 mt-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="text-xs h-8"
              onClick={() => setPendingPurgeAgent(null)}
            >
              取消
            </Button>
            <Button
              type="button"
              variant="destructive"
              size="sm"
              className="text-xs h-8"
              disabled={purgeMutation.isPending}
              onClick={() => pendingPurgeAgent && purgeMutation.mutate(pendingPurgeAgent.agent_id)}
            >
              {purgeMutation.isPending ? '正在删除...' : '彻底物理删除'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 专属接入引导抽屉 (Sheet) */}
      <AgentOnboardingModal
        data={onboardingData}
        open={onboardingOpen}
        onOpenChange={setOnboardingOpen}
      />
    </Card>
  )
}
