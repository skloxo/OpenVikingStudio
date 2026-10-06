/**
 * new-agent-card.tsx
 * 新智能体就地签发卡片 (New Agent Inline Form Card).
 * 嵌入在抽屉面板顶部，点击展开就地签发，完成即收起，彻底杜绝 Dialog 模态跳层与跳页！
 */
import * as React from 'react'
import { CheckIcon, PlusIcon, ShieldCheckIcon, SparklesIcon, XIcon } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { Label } from '#/components/ui/label'
import type { CreateAgentInput } from '#/lib/admin'
import { DEFAULT_TOOL_IDS, TOOL_CATEGORIES } from '../-constants/agent-tools'

export type NewAgentCardProps = {
  open: boolean
  onClose: () => void
  onSubmit: (input: CreateAgentInput) => void
  isPending?: boolean
}

export function NewAgentCard({
  open,
  onClose,
  onSubmit,
  isPending,
}: NewAgentCardProps) {
  const [name, setName] = React.useState('')
  const [roleDesc, setRoleDesc] = React.useState('')
  const [connectionMode, setConnectionMode] = React.useState<'realtimeApi' | 'apiClient'>('apiClient')
  const [selectedTools, setSelectedTools] = React.useState<string[]>(DEFAULT_TOOL_IDS)

  if (!open) return null

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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) {
      toast.error('请输入智能体自定义名称')
      return
    }
    onSubmit({
      agent_name: name.trim(),
      role_desc: roleDesc.trim() || (connectionMode === 'realtimeApi' ? '本地宿主助手' : '远程卫星助手'),
      connection_mode: connectionMode,
      allowed_tools: selectedTools,
    })
    // 重置
    setName('')
    setRoleDesc('')
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-md border border-cyan-500/50 bg-card p-3.5 space-y-3 shadow-xs text-xs font-sans animate-in fade-in-50 duration-150"
    >
      <div className="flex items-center justify-between pb-1.5 border-b border-border/50">
        <span className="font-semibold text-foreground flex items-center gap-1.5">
          <SparklesIcon className="size-3.5 text-cyan-500" />
          签发新智能体身份牌
        </span>
        <button
          type="button"
          onClick={onClose}
          className="text-muted-foreground hover:text-foreground p-0.5"
          title="关闭"
        >
          <XIcon className="size-3.5" />
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="space-y-1">
          <Label className="text-xs font-medium text-foreground">
            智能体名称 (自定义可改) <span className="text-rose-500">*</span>
          </Label>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="例如 前端结对助手、3070 巡检小助手"
            className="h-7 text-xs bg-background"
            autoFocus
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

        <div className="sm:col-span-2 space-y-1">
          <Label className="text-xs font-medium text-foreground">接入拓扑方式</Label>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setConnectionMode('realtimeApi')}
              className={`p-2 rounded border text-left transition-colors ${
                connectionMode === 'realtimeApi'
                  ? 'border-cyan-500 bg-cyan-500/10 text-foreground font-medium'
                  : 'border-border/60 bg-background text-muted-foreground hover:bg-muted/30'
              }`}
            >
              <div>本地宿主直连</div>
              <div className="text-muted-foreground mt-0.5">同一主机直连 (1933)</div>
            </button>
            <button
              type="button"
              onClick={() => setConnectionMode('apiClient')}
              className={`p-2 rounded border text-left transition-colors ${
                connectionMode === 'apiClient'
                  ? 'border-cyan-500 bg-cyan-500/10 text-foreground font-medium'
                  : 'border-border/60 bg-background text-muted-foreground hover:bg-muted/30'
              }`}
            >
              <div>网络远程卫星</div>
              <div className="text-muted-foreground mt-0.5">跨机器 / 远程节点网关</div>
            </button>
          </div>
        </div>

        <div className="sm:col-span-2 rounded border border-border/40 bg-muted/20 px-2.5 py-1.5 flex items-center justify-between text-muted-foreground">
          <span>系统唯一身份证 (ID):</span>
          <span className="font-mono text-foreground">签发时自动生成不可重复 ag_xxxx（永久锁定不可篡改）</span>
        </div>
      </div>

      {/* 工具授权矩阵 */}
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

      <div className="flex items-center justify-end gap-2 pt-2 border-t border-border/40">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 text-xs"
          onClick={onClose}
        >
          取消
        </Button>
        <Button
          type="submit"
          size="sm"
          className="h-7 text-xs"
          disabled={isPending}
        >
          <PlusIcon className="size-3 mr-1" />
          {isPending ? '正在签发...' : '确认签发并注册入籍'}
        </Button>
      </div>
    </form>
  )
}
