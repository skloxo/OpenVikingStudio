/**
 * agent-collapsible-item.tsx
 * 智能体就地展开/收起面板项 (Agent Collapsible Item).
 * 彻底消除弹窗覆盖与跳页！所有修改与接入令均在抽屉内原位展开收起。
 * 严守 NO GREEN EVER 🚫、>= 12px 字体下限与单文件黄金甜点区。
 */
import * as React from 'react'
import {
  CheckIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  CopyIcon,
  GlobeIcon,
  LaptopIcon,
  RotateCcwIcon,
  SaveIcon,
  ShieldCheckIcon,
  TerminalIcon,
  Trash2Icon,
} from 'lucide-react'
import { toast } from 'sonner'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { Label } from '#/components/ui/label'
import type { UpdateAgentInput, UserAgentItem } from '#/lib/admin'
import { copyTextToClipboard } from '#/lib/clipboard'
import { DEFAULT_TOOL_IDS, TOOL_CATEGORIES } from '../-constants/agent-tools'

export type AgentCollapsibleItemProps = {
  agent: UserAgentItem
  userId: string
  isExpanded: boolean
  onToggleExpand: () => void
  onUpdate: (agentId: string, input: UpdateAgentInput) => void
  onDelete: (agent: UserAgentItem) => void
  onActivate: (agentId: string) => void
  isUpdating?: boolean
}

export function AgentCollapsibleItem({
  agent,
  userId,
  isExpanded,
  onToggleExpand,
  onUpdate,
  onDelete,
  onActivate,
  isUpdating,
}: AgentCollapsibleItemProps) {
  const isLocal = agent.connection_mode === 'realtimeApi'
  const isActive = agent.status === 'active'

  // 本地就地编辑状态
  const [name, setName] = React.useState(agent.agent_name || agent.agent_id)
  const [roleDesc, setRoleDesc] = React.useState(agent.role_desc || '')
  const [selectedTools, setSelectedTools] = React.useState<string[]>(
    agent.allowed_tools.length > 0 ? agent.allowed_tools : DEFAULT_TOOL_IDS,
  )

  // 当外部数据变动时同步
  React.useEffect(() => {
    setName(agent.agent_name || agent.agent_id)
    setRoleDesc(agent.role_desc || '')
    setSelectedTools(agent.allowed_tools.length > 0 ? agent.allowed_tools : DEFAULT_TOOL_IDS)
  }, [agent])

  const handleCopy = async (text: string, label: string, e?: React.MouseEvent) => {
    e?.stopPropagation()
    try {
      await copyTextToClipboard(text)
      toast.success(`已复制 ${label}`)
    } catch {
      toast.error('复制失败')
    }
  }

  const toggleTool = (toolId: string) => {
    setSelectedTools((prev) =>
      prev.includes(toolId) ? prev.filter((id) => id !== toolId) : [...prev, toolId],
    )
  }

  const toggleCategory = (catToolIds: string[]) => {
    const allSelected = catToolIds.every((id) => selectedTools.includes(id))
    if (allSelected) {
      setSelectedTools((prev) => prev.filter((id) => !catToolIds.includes(id)))
    } else {
      setSelectedTools((prev) => Array.from(new Set([...prev, ...catToolIds])))
    }
  }

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) {
      toast.error('请输入智能体名称')
      return
    }
    onUpdate(agent.agent_id, {
      agent_name: name.trim(),
      role_desc: roleDesc.trim(),
      allowed_tools: selectedTools,
    })
  }

  // 生成接入命令与 URL
  const origin = typeof window !== 'undefined' ? window.location.origin : 'http://127.0.0.1:1933'
  const mcpUrl = `${origin}/mcp?user_id=${encodeURIComponent(userId)}&agent_id=${encodeURIComponent(agent.agent_id)}`
  const clientConfigSnippet = JSON.stringify(
    {
      mcpServers: {
        openviking: {
          url: mcpUrl,
        },
      },
    },
    null,
    2,
  )

  return (
    <div
      className={`rounded-md border transition-all text-xs font-sans ${
        isExpanded
          ? 'border-cyan-500/50 bg-card shadow-xs'
          : 'border-border/60 bg-muted/10 hover:bg-muted/30'
      }`}
    >
      {/* 收起态横条 (可点击展开) */}
      <div
        className="flex items-center justify-between p-2.5 cursor-pointer select-none gap-2"
        onClick={onToggleExpand}
      >
        <div className="flex items-center gap-2 min-w-0">
          <button
            type="button"
            className="p-0.5 text-muted-foreground hover:text-foreground shrink-0"
            title={isExpanded ? '收起详情' : '展开就地配置'}
          >
            {isExpanded ? (
              <ChevronDownIcon className="size-3.5 text-cyan-500" />
            ) : (
              <ChevronRightIcon className="size-3.5" />
            )}
          </button>

          <div className="space-y-0.5 min-w-0">
            <div className="flex items-center gap-1.5 font-medium text-foreground">
              <span className="truncate max-w-40 sm:max-w-50 font-semibold">
                {agent.agent_name || agent.agent_id}
              </span>
              <Badge
                variant="outline"
                className={`text-xs h-4.5 px-1 font-normal ${
                  isActive
                    ? 'border-cyan-500/30 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400'
                    : 'border-muted-foreground/30 bg-muted text-muted-foreground'
                }`}
              >
                {isActive ? '在籍' : '已下线'}
              </Badge>
            </div>

            <div className="flex items-center gap-1 font-mono text-muted-foreground">
              <span className="text-muted-foreground/90">{agent.agent_id}</span>
              <button
                type="button"
                className="hover:text-foreground p-0.5"
                onClick={(e) => handleCopy(agent.agent_id, '永久身份证 ID', e)}
                title="复制永久身份证 ID"
              >
                <CopyIcon className="size-3 text-muted-foreground" />
              </button>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <div className="hidden sm:flex items-center gap-1 text-muted-foreground font-mono">
            {isLocal ? (
              <Badge variant="outline" className="text-xs h-5 px-1.5 gap-1 border-border/60">
                <LaptopIcon className="size-2.5 text-cyan-500" />
                本地直连
              </Badge>
            ) : (
              <Badge variant="outline" className="text-xs h-5 px-1.5 gap-1 border-border/60">
                <GlobeIcon className="size-2.5 text-muted-foreground" />
                网络远程
              </Badge>
            )}
          </div>

          <Badge variant="outline" className="text-xs h-5 px-1.5 gap-1 font-mono border-border/60">
            <ShieldCheckIcon className="size-2.5 text-cyan-500" />
            {agent.allowed_tools.length} 项工具
          </Badge>

          <span className="font-mono tabular-nums text-muted-foreground hidden md:inline-block">
            {agent.total_messages} 条消息
          </span>

          <div className="flex items-center gap-1 pl-1 border-l border-border/40" onClick={(e) => e.stopPropagation()}>
            {isActive ? (
              <Button
                type="button"
                size="icon-xs"
                variant="ghost"
                className="size-6 text-muted-foreground hover:text-rose-500 hover:bg-rose-500/10"
                onClick={() => onDelete(agent)}
                title="下线软删除"
              >
                <Trash2Icon className="size-3" />
              </Button>
            ) : (
              <Button
                type="button"
                size="icon-xs"
                variant="ghost"
                className="size-6 text-cyan-600 hover:bg-cyan-500/10"
                onClick={() => onActivate(agent.agent_id)}
                title="重新激活"
              >
                <RotateCcwIcon className="size-3" />
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* 展开态：就地原位编辑与接入配置面板 (Zero Jump, Pure In-place) */}
      {isExpanded && (
        <form onSubmit={handleSave} className="border-t border-border/50 p-3.5 space-y-3.5 bg-background/50">
          {/* 基本属性原位修改 */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs font-medium text-foreground">
                智能体名称 (自定义可改) <span className="text-rose-500">*</span>
              </Label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="例如 前端结对助手"
                className="h-7 text-xs bg-background"
              />
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-medium text-foreground">角色定位 / 职能描述</Label>
              <Input
                value={roleDesc}
                onChange={(e) => setRoleDesc(e.target.value)}
                placeholder="例如 自动化编译巡检、代码审查"
                className="h-7 text-xs bg-background"
              />
            </div>

            <div className="sm:col-span-2 rounded border border-border/40 bg-muted/20 px-2.5 py-1.5 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">系统唯一永久身份证 (ID):</span>
                <code className="font-mono font-semibold text-foreground">{agent.agent_id}</code>
              </div>
              <span className="text-muted-foreground text-xs font-mono">永久锁定，接入唯一凭据</span>
            </div>
          </div>

          {/* 工具授权矩阵 (Tool ACL) */}
          <div className="space-y-2 pt-1 border-t border-border/40">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-foreground flex items-center gap-1.5">
                <ShieldCheckIcon className="size-3.5 text-cyan-500" />
                工具授权矩阵 (Tool ACL)
              </span>
              <span className="font-mono text-muted-foreground">
                已勾选 {selectedTools.length} 项工具
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {TOOL_CATEGORIES.map((cat) => {
                const catToolIds = cat.tools.map((t) => t.id)
                const isAllSelected = catToolIds.every((id) => selectedTools.includes(id))

                return (
                  <div key={cat.id} className="rounded border border-border/50 bg-background/60 p-2 space-y-1.5">
                    <div className="flex items-center justify-between pb-1 border-b border-border/30">
                      <span className="font-medium text-foreground">{cat.name}</span>
                      <button
                        type="button"
                        className="text-xs text-cyan-600 dark:text-cyan-400 hover:underline"
                        onClick={() => toggleCategory(catToolIds)}
                      >
                        {isAllSelected ? '取消该类' : '全选该类'}
                      </button>
                    </div>

                    <div className="space-y-1">
                      {cat.tools.map((tool) => {
                        const checked = selectedTools.includes(tool.id)
                        return (
                          <div
                            key={tool.id}
                            onClick={() => toggleTool(tool.id)}
                            className={`flex items-center justify-between p-1 rounded cursor-pointer transition-colors ${
                              checked ? 'bg-cyan-500/10 text-foreground' : 'text-muted-foreground hover:bg-muted/40'
                            }`}
                          >
                            <span className="font-mono text-xs">{tool.name}</span>
                            <div
                              className={`size-3 rounded flex items-center justify-center border ${
                                checked ? 'bg-cyan-500 border-cyan-500 text-white' : 'border-border'
                              }`}
                            >
                              {checked && <CheckIcon className="size-2 stroke-3" />}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* 接入指令与 URL (就地查看与复制，绝不跳页) */}
          <div className="space-y-1.5 pt-1 border-t border-border/40">
            <span className="font-semibold text-foreground flex items-center gap-1.5">
              <TerminalIcon className="size-3.5 text-cyan-500" />
              中枢接入端点与客户端配置
            </span>

            <div className="flex items-center gap-1.5 rounded border border-border/40 bg-background px-2 py-1">
              <code className="font-mono text-xs flex-1 truncate select-all">{mcpUrl}</code>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                className="h-6 px-1.5 text-xs text-cyan-600 hover:bg-cyan-500/10"
                onClick={(e) => handleCopy(mcpUrl, 'FastMCP 链接', e)}
              >
                <CopyIcon className="size-3 mr-1" />
                复制 URL
              </Button>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground"
                onClick={(e) => handleCopy(clientConfigSnippet, '客户端 JSON 配置', e)}
              >
                <CopyIcon className="size-3 mr-1" />
                复制 JSON
              </Button>
            </div>
          </div>

          {/* 底部就地操作栏 */}
          <div className="flex items-center justify-end gap-2 pt-2 border-t border-border/40">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 text-xs"
              onClick={onToggleExpand}
            >
              收起面板
            </Button>
            <Button
              type="submit"
              size="sm"
              className="h-7 text-xs"
              disabled={isUpdating}
            >
              <SaveIcon className="size-3 mr-1" />
              {isUpdating ? '保存中...' : '保存配置'}
            </Button>
          </div>
        </form>
      )}
    </div>
  )
}
