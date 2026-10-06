/**
 * user-agents-card.tsx
 * 用户作用域在籍智能体标识管理卡片 (Card-113 / v1.7.67).
 * 遵循 Agent 编码规范与黄金甜点区 (<= 250 行)，严守 NO GREEN EVER 🚫 与 >= 12px 规范。
 */
import * as React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  BotIcon,
  HelpCircleIcon,
  LoaderCircleIcon,
  PlusIcon,
  RotateCwIcon,
  TerminalIcon,
  Trash2Icon,
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
  createUserAgent,
  fetchUserAgents,
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
      setOnboardingData(data)
      setOnboardingOpen(true)
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : '创建智能体失败')
    },
  })

  // 3. 吊销 Agent 突变
  const revokeMutation = useMutation({
    mutationFn: (agentId: string) => revokeUserAgent(userId, agentId),
    onSuccess: (_, agentId) => {
      queryClient.invalidateQueries({ queryKey: ['user-agents', userId] })
      queryClient.invalidateQueries({ queryKey: ['console-peers'] })
      toast.success(`已吊销并下线智能体 ${agentId}`)
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : '吊销智能体失败')
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
      role_desc: newRoleDesc.trim() || '远程开发助手',
      connection_mode: 'apiClient',
    })
  }

  const handleOpenGuide = (agent: UserAgentItem) => {
    // 组装回显数据
    setOnboardingData({
      agent,
      bootstrap: {
        mcp_config: {
          mcpServers: {
            openviking: {
              command: 'npx',
              args: [
                '-y',
                'openviking-bridge',
                '--server',
                `${window.location.origin}/mcp`,
                '--agent-id',
                agent.agent_id,
                '--key',
                '${OPENVIKING_API_KEY}',
              ],
            },
          },
        },
        system_prompt: `# OpenViking 体外大脑专属接入指南\n- 你的身份牌 (Agent ID): \`${agent.agent_id}\`\n- 归属用户 (User ID): \`${agent.user_id}\`\n- 专属工作空间: viking://user/${agent.user_id}/peers/${agent.agent_id}/memories/\n- 演进公理: 遇到复杂工程疑难时优先调用 openviking_find 召回知识；解决突破后调用 openviking_record_evolution_lesson 沉淀资产。`,
        remote_mcp_url: `${window.location.origin}/mcp?agent_id=${agent.agent_id}&key=\${OPENVIKING_API_KEY}`,
      },
    })
    setOnboardingOpen(true)
  }

  return (
    <Card className="border-zinc-800 bg-zinc-950/80 text-zinc-100 mt-6">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div>
          <div className="flex items-center gap-2">
            <BotIcon className="size-4 text-cyan-400" />
            <CardTitle className="text-sm font-semibold tracking-wide">
              用户专属智能体标识与授权矩阵 (Authorized Agents)
            </CardTitle>
          </div>
          <CardDescription className="text-xs text-zinc-400 mt-1">
            当前租户用户 <span className="font-mono text-zinc-200">{userId}</span> 下属在籍智能体。携带用户密钥与专属 Agent 标识即可免猜谜直连接入。
          </CardDescription>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-xs border-zinc-800 bg-zinc-900 hover:bg-zinc-800 text-zinc-300"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            <RotateCwIcon className={`size-3.5 mr-1 ${isFetching ? 'animate-spin' : ''}`} />
            刷新
          </Button>
          <Button
            size="sm"
            className="h-7 text-xs bg-zinc-100 hover:bg-zinc-200 text-zinc-900 font-medium"
            onClick={() => setAddDialogOpen(true)}
          >
            <PlusIcon className="size-3.5 mr-1" />
            添加智能体标识
          </Button>
        </div>
      </CardHeader>

      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8 text-xs text-zinc-400">
            <LoaderCircleIcon className="size-4 animate-spin mr-2 text-cyan-400" />
            正在加载智能体授权列表...
          </div>
        ) : agents.length === 0 ? (
          <div className="text-center py-8 border border-dashed border-zinc-800 rounded-md text-xs text-zinc-500">
            暂无在籍智能体。点击右上角【添加智能体标识】签发专属接入身份牌。
          </div>
        ) : (
          <div className="rounded-md border border-zinc-800 overflow-hidden">
            <Table>
              <TableHeader className="bg-zinc-900/60 text-zinc-400">
                <TableRow className="border-zinc-800 hover:bg-transparent">
                  <TableHead className="text-xs h-8">Agent 身份标识</TableHead>
                  <TableHead className="text-xs h-8">角色定位</TableHead>
                  <TableHead className="text-xs h-8">连接方式</TableHead>
                  <TableHead className="text-xs h-8 text-right">沉淀消息数</TableHead>
                  <TableHead className="text-xs h-8 text-center">状态</TableHead>
                  <TableHead className="text-xs h-8 text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {agents.map((agent) => (
                  <TableRow key={agent.agent_id} className="border-zinc-800/60 hover:bg-zinc-900/40 text-xs">
                    <TableCell className="font-mono text-zinc-200 py-2">
                      <div className="flex items-center gap-1.5">
                        <TerminalIcon className="size-3.5 text-cyan-400" />
                        <span>{agent.agent_id}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-zinc-300 py-2">{agent.role_desc}</TableCell>
                    <TableCell className="font-mono text-zinc-400 py-2">
                      {agent.connection_mode === 'realtimeApi' ? '本地直连' : '网络远程'}
                    </TableCell>
                    <TableCell className="text-right font-mono tabular-nums text-zinc-200 py-2">
                      {agent.total_messages.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-center py-2">
                      <Badge
                        variant="outline"
                        className={`text-[12px] h-5 px-1.5 border-zinc-800 ${
                          agent.status === 'active'
                            ? 'text-cyan-400 bg-cyan-950/20 border-cyan-800/40'
                            : 'text-zinc-500 bg-zinc-900 border-zinc-800'
                        }`}
                      >
                        {agent.status === 'active' ? '在籍活跃' : '已吊销'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right py-2 space-x-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-6 px-2 text-xs text-zinc-300 hover:text-cyan-300 hover:bg-zinc-800"
                        onClick={() => handleOpenGuide(agent)}
                      >
                        <HelpCircleIcon className="size-3 mr-1" />
                        接入指南
                      </Button>
                      {agent.status === 'active' && (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-6 px-2 text-xs text-rose-400 hover:text-rose-300 hover:bg-rose-950/30"
                          onClick={() => revokeMutation.mutate(agent.agent_id)}
                          disabled={revokeMutation.isPending}
                        >
                          <Trash2Icon className="size-3 mr-1" />
                          下线
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>

      {/* 添加智能体 Dialog */}
      <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
        <DialogContent className="max-w-md bg-zinc-950 border-zinc-800 text-zinc-100">
          <form onSubmit={handleCreate}>
            <DialogHeader>
              <DialogTitle className="text-sm font-semibold">签发新智能体身份牌</DialogTitle>
              <DialogDescription className="text-xs text-zinc-400">
                为用户 <span className="font-mono text-zinc-200">{userId}</span> 分配新的在籍 Agent 标识。
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-3 py-3">
              <div className="space-y-1.5">
                <Label htmlFor="agent-id" className="text-xs text-zinc-300">
                  智能体标识 (Agent ID) <span className="text-rose-400">*</span>
                </Label>
                <Input
                  id="agent-id"
                  placeholder="例如 cursor@macbook 或 deepseek-harness@2080ti"
                  className="h-8 text-xs bg-zinc-900 border-zinc-800 text-zinc-100 font-mono"
                  value={newAgentId}
                  onChange={(e) => setNewAgentId(e.target.value)}
                  autoFocus
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="role-desc" className="text-xs text-zinc-300">
                  角色定位 / 职能描述
                </Label>
                <Input
                  id="role-desc"
                  placeholder="例如 MacBook Cursor 编程助手"
                  className="h-8 text-xs bg-zinc-900 border-zinc-800 text-zinc-100"
                  value={newRoleDesc}
                  onChange={(e) => setNewRoleDesc(e.target.value)}
                />
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
                className="text-xs h-8 bg-zinc-100 text-zinc-900 hover:bg-zinc-200"
                disabled={createMutation.isPending}
              >
                {createMutation.isPending ? '正在签发...' : '确认签发并获取接入令'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* 专属接入引导 Modal */}
      <AgentOnboardingModal
        data={onboardingData}
        open={onboardingOpen}
        onOpenChange={setOnboardingOpen}
      />
    </Card>
  )
}
