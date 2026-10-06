/**
 * user-agents-table.tsx
 * 用户名下在册智能体表格组件 (User Agents Table).
 * 展示智能体名称、永久身份证 ID、连接模式、工具权限数、消息计数与操作按钮。
 */
import {
  CopyIcon,
  GlobeIcon,
  HelpCircleIcon,
  LaptopIcon,
  PencilIcon,
  RotateCcwIcon,
  ShieldCheckIcon,
  Trash2Icon,
} from 'lucide-react'
import { toast } from 'sonner'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '#/components/ui/table'
import type { UserAgentItem } from '#/lib/admin'
import { copyTextToClipboard } from '#/lib/clipboard'

export type UserAgentsTableProps = {
  agents: UserAgentItem[]
  onOpenGuide: (agent: UserAgentItem) => void
  onEditAgent: (agent: UserAgentItem) => void
  onDeleteAgent: (agent: UserAgentItem) => void
  onActivateAgent: (agentId: string) => void
  isActivating?: boolean
}

export function UserAgentsTable({
  agents,
  onOpenGuide,
  onEditAgent,
  onDeleteAgent,
  onActivateAgent,
  isActivating,
}: UserAgentsTableProps) {
  const handleCopy = async (text: string, label: string) => {
    try {
      await copyTextToClipboard(text)
      toast.success(`已复制 ${label}`)
    } catch {
      toast.error('复制失败')
    }
  }

  return (
    <div className="rounded-md border overflow-hidden">
      <Table>
        <TableHeader className="bg-muted/50">
          <TableRow className="border-border">
            <TableHead className="text-xs h-8">智能体名称与唯一ID</TableHead>
            <TableHead className="text-xs h-8">连接方式</TableHead>
            <TableHead className="text-xs h-8">工具权限 (ACL)</TableHead>
            <TableHead className="text-xs h-8 text-right">沉淀消息</TableHead>
            <TableHead className="text-xs h-8 text-center">状态</TableHead>
            <TableHead className="text-xs h-8 text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {agents.map((agent) => {
            const isLocal = agent.connection_mode === 'realtimeApi'
            const isActive = agent.status === 'active'
            const toolsCount = agent.allowed_tools.length

            return (
              <TableRow key={agent.agent_id} className="text-xs hover:bg-muted/30">
                <TableCell className="py-2.5">
                  <div className="space-y-0.5">
                    <div className="font-medium text-foreground flex items-center gap-1.5">
                      <span>{agent.agent_name || agent.agent_id}</span>
                    </div>
                    <div className="flex items-center gap-1 text-muted-foreground font-mono">
                      <span>{agent.agent_id}</span>
                      <Button
                        size="icon-xs"
                        variant="ghost"
                        className="size-4 p-0"
                        onClick={() => handleCopy(agent.agent_id, 'Agent ID')}
                        title="复制永久身份证"
                      >
                        <CopyIcon className="size-2.5" />
                      </Button>
                    </div>
                  </div>
                </TableCell>

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

                <TableCell className="py-2.5">
                  <Badge
                    variant="outline"
                    className="text-xs font-mono cursor-pointer hover:border-cyan-500/50"
                    onClick={() => onEditAgent(agent)}
                  >
                    <ShieldCheckIcon className="size-3 mr-1 text-cyan-500" />
                    {toolsCount} 项工具
                  </Badge>
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
                    {isActive ? '在籍' : '已下线'}
                  </Badge>
                </TableCell>

                <TableCell className="text-right py-2.5 space-x-1">
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 px-1.5 text-xs hover:text-cyan-600"
                    onClick={() => onOpenGuide(agent)}
                    title="查看接入指南"
                  >
                    <HelpCircleIcon className="size-3 mr-1" />
                    指南
                  </Button>

                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground"
                    onClick={() => onEditAgent(agent)}
                    title="编辑配置与权限"
                  >
                    <PencilIcon className="size-3 mr-1" />
                    配置
                  </Button>

                  {isActive ? (
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 px-1.5 text-xs text-rose-500 hover:text-rose-600 hover:bg-rose-500/10"
                      onClick={() => onDeleteAgent(agent)}
                      title="软删除下线"
                    >
                      <Trash2Icon className="size-3" />
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 px-1.5 text-xs text-cyan-600 hover:text-cyan-700 hover:bg-cyan-500/10"
                      onClick={() => onActivateAgent(agent.agent_id)}
                      disabled={isActivating}
                      title="重新激活"
                    >
                      <RotateCcwIcon className="size-3" />
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
}
