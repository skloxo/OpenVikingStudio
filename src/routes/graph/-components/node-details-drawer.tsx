import * as React from 'react'
import { CopyIcon, CheckIcon, CpuIcon, SparklesIcon, FileTextIcon, HistoryIcon, ExternalLinkIcon, XIcon } from 'lucide-react'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '#/components/ui/card'
import { getRouterBasePath } from '#/lib/public-path'
import type { NodeData } from './knowledge-graph-canvas'

interface NodeDetailsDrawerProps {
  node: NodeData | null
  onClose: () => void
}

export function NodeDetailsDrawer({ node, onClose }: NodeDetailsDrawerProps) {
  const [copied, setCopied] = React.useState(false)

  if (!node) return null

  const handleCopyUri = () => {
    navigator.clipboard.writeText(node.id)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleOpenSourcePage = () => {
    const base = getRouterBasePath().replace(/\/$/, '')
    let path = `${base}/resources?uri=${encodeURIComponent(node.id)}`
    if (node.category === 'peers') {
      path = `${base}/skills?search=${encodeURIComponent(node.id.replace('viking://peers/', ''))}`
    } else if (node.category === 'skills') {
      path = `${base}/skills?search=${encodeURIComponent(node.id.replace('viking://skills/', ''))}`
    } else if (node.category === 'sessions') {
      path = `${base}/sessions?s=${encodeURIComponent(node.id.replace('viking://sessions/', ''))}`
    }

    window.open(path, '_blank')
  }

  const getCategoryBadge = () => {
    switch (node.category) {
      case 'peers':
        return (
          <Badge className="bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/30 gap-1 font-mono">
            <CpuIcon className="size-3" />
            <span>Peers 看护代理</span>
          </Badge>
        )
      case 'skills':
        return (
          <Badge className="bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30 gap-1 font-mono">
            <SparklesIcon className="size-3" />
            <span>Skills 技能协议</span>
          </Badge>
        )
      case 'sessions':
        return (
          <Badge className="bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/30 gap-1 font-mono">
            <HistoryIcon className="size-3" />
            <span>Sessions 对话轨迹</span>
          </Badge>
        )
      case 'resources':
        return (
          <Badge className="bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/30 gap-1 font-mono">
            <FileTextIcon className="size-3" />
            <span>Resources 体外大脑文档</span>
          </Badge>
        )
    }
  }

  const getNodeDescription = () => {
    if (node.category === 'peers') {
      return '负责全局任务调配、子代理调度、OpenViking 记忆中枢读写与工程质量闭环控制。'
    }
    if (node.category === 'skills') {
      return '沉淀在 OpenViking 技能矩阵中的工程规则契约，支持自动化诊断与 TDD 测试驱动流程。'
    }
    if (node.category === 'sessions') {
      return '记录跨会话沟通履历与上下文交互快照，保证长周期协作无缝接续。'
    }
    return '持久化于 OpenViking 体外大脑 (viking://resources/master_memory/) 中的 Markdown 架构决策与设计规范。'
  }

  return (
    <Card className="absolute right-4 top-4 z-40 w-80 md:w-96 rounded-md border border-border/80 bg-card/95 backdrop-blur-md shadow-lg transition-all duration-200">
      <CardHeader className="flex flex-row items-start justify-between pb-2 space-y-0">
        <div className="space-y-1 pr-2">
          {getCategoryBadge()}
          <CardTitle className="font-mono text-sm font-bold tracking-tight text-foreground break-all mt-2">
            {node.id}
          </CardTitle>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={onClose}
          className="size-7 rounded hover:bg-muted/60 text-muted-foreground"
        >
          <XIcon className="size-4" />
        </Button>
      </CardHeader>

      <CardContent className="space-y-4 font-mono text-xs pt-2">
        {/* Description Section */}
        <div className="rounded bg-muted/30 p-2.5 border border-border/40 text-muted-foreground leading-relaxed text-[11px]">
          {getNodeDescription()}
        </div>

        {/* Metadata Details Grid */}
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="rounded border border-border/40 bg-background/50 p-2 space-y-0.5">
            <span className="text-[10px] text-muted-foreground block">物理权重 / 关联边</span>
            <span className="font-bold text-foreground tabular-nums">{node.degree} 条拓扑连线</span>
          </div>

          <div className="rounded border border-border/40 bg-background/50 p-2 space-y-0.5">
            <span className="text-[10px] text-muted-foreground block">VikingDB 向量索引</span>
            <span className="font-bold text-cyan-600 dark:text-cyan-400">已建索引 ✅</span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-2 pt-1 border-t border-border/40">
          <Button
            variant="default"
            size="sm"
            onClick={handleOpenSourcePage}
            className="w-full gap-1.5 h-8 text-xs font-mono bg-cyan-600 hover:bg-cyan-700 text-white shadow-none"
          >
            <ExternalLinkIcon className="size-3.5" />
            <span>🔗 在新标签页中查看源文件</span>
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleCopyUri}
            className="w-full gap-1.5 h-8 text-xs font-mono border-border/60 hover:bg-muted/50 shadow-none"
          >
            {copied ? (
              <>
                <CheckIcon className="size-3 text-cyan-500" />
                <span>已复制 URI</span>
              </>
            ) : (
              <>
                <CopyIcon className="size-3" />
                <span>复制 URI 节点地址</span>
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
