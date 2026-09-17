import * as React from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Card } from '#/components/ui/card'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { ovClient } from '#/lib/ov-client'
import {
  CompassIcon,
  LayersIcon,
  ChevronUpIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  ChevronLeftIcon,
  Share2Icon,
  SparklesIcon,
  FolderTreeIcon,
  CheckCircle2Icon,
} from 'lucide-react'

export interface CompassStats {
  active_version: number
  total_nodes: number
  total_roots: number
  max_depth: number
  last_swap_ts: number
  serving_desk_ready: boolean
}

export interface CompassNodeData {
  node_id: string
  title: string
  content_snippet: string
  depth: number
  breadcrumbs: string[]
  parent_id: string | null
  children_ids: string[]
  sibling_prev_id: string | null
  sibling_next_id: string | null
  metadata: Record<string, string>
}

export interface CompassNodeResponse {
  node: CompassNodeData
  available_directions: string[]
}

export interface NavigationResult {
  anchor_id: string
  direction: string
  target_node: CompassNodeData | null
  available_directions: string[]
  lineage_path: string
  status: string
}

const PRESET_ANCHORS = [
  { id: 'root_openviking', label: '根架构 (Root)' },
  { id: 'ch_invariants', label: '不可变式 (Invariants)' },
  { id: 'ch_retrieval', label: '检索引擎 (Retrieval)' },
  { id: 'sec_bm25', label: 'BM25 FTS5' },
  { id: 'sec_zg', label: 'zg 语义搜索' },
  { id: 'sec_abstention', label: 'RAG 主动弃答' },
]

export function HGRAGCompassCockpit() {
  const [currentAnchorId, setCurrentAnchorId] = React.useState<string>('root_openviking')

  // 1. Operational stats query
  const statsQuery = useQuery({
    queryKey: ['hg_compass_stats'],
    queryFn: async () => {
      const res = await ovClient.instance.get<CompassStats>('/api/v1/rag/compass/stats')
      return res.data
    },
    refetchInterval: 15_000,
    refetchIntervalInBackground: false,
    staleTime: 15_000,
  })

  // 2. Current node query
  const nodeQuery = useQuery({
    queryKey: ['hg_compass_node', currentAnchorId],
    queryFn: async () => {
      const res = await ovClient.instance.get<CompassNodeResponse>(`/api/v1/rag/compass/node/${currentAnchorId}`)
      return res.data
    },
  })

  // 3. Navigation mutation
  const navMutation = useMutation({
    mutationFn: async ({ direction, childIndex = 0 }: { direction: string; childIndex?: number }) => {
      const res = await ovClient.instance.post<NavigationResult>('/api/v1/rag/compass/navigate', {
        anchor_id: currentAnchorId,
        direction,
        child_index: childIndex,
      })
      return res.data
    },
    onSuccess: (data) => {
      if (data.target_node) {
        setCurrentAnchorId(data.target_node.node_id)
      }
    },
  })

  const stats = statsQuery.data
  const nodeData = nodeQuery.data?.node
  const availableDirs = new Set(nodeQuery.data?.available_directions || [])

  return (
    <Card className="border-border bg-card p-3.5 space-y-3.5">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border/60 pb-2.5">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-md bg-cyan-50 border border-cyan-200 text-cyan-700 dark:bg-cyan-950/40 dark:border-cyan-800/50 dark:text-cyan-400">
            <CompassIcon className="size-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-semibold tracking-wide text-foreground">
                HG-RAG 分层指南针拓扑与读写分离知识工程
              </h3>
              <Badge variant="outline" className="border-cyan-200 bg-cyan-50 text-cyan-800 dark:border-cyan-800/60 dark:bg-cyan-950/30 dark:text-cyan-400 font-mono text-[12px]">
                v1.5.19
              </Badge>
            </div>
            <p className="text-[12px] text-muted-foreground mt-0.5">
              四向罗盘拓扑漫游 · 结构化叶子自洽全路径回填 · 生产服务台与重计算编辑台物理分离
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="outline" className="border-border/60 bg-muted/40 text-muted-foreground font-mono text-[12px]">
            Serving Desk: 只读零锁
          </Badge>
          <Badge variant="outline" className="border-cyan-200 bg-cyan-50 text-cyan-800 dark:border-cyan-800/50 dark:bg-cyan-950/20 dark:text-cyan-400 font-mono text-[12px]">
            <CheckCircle2Icon className="size-3 mr-1 inline text-cyan-600 dark:text-cyan-400" />
            Active V{stats?.active_version ?? 1}
          </Badge>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        <div className="p-2.5 rounded-md bg-muted/30 border border-border/50">
          <div className="flex items-center justify-between text-muted-foreground mb-1">
            <span className="text-[12px]">拓扑节点总数</span>
            <LayersIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
          </div>
          <div className="text-sm font-semibold font-mono tabular-nums text-foreground">
            {stats?.total_nodes ?? '--'}
          </div>
        </div>

        <div className="p-2.5 rounded-md bg-muted/30 border border-border/50">
          <div className="flex items-center justify-between text-muted-foreground mb-1">
            <span className="text-[12px]">根大类体系数</span>
            <FolderTreeIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
          </div>
          <div className="text-sm font-semibold font-mono tabular-nums text-foreground">
            {stats?.total_roots ?? '--'}
          </div>
        </div>

        <div className="p-2.5 rounded-md bg-muted/30 border border-border/50">
          <div className="flex items-center justify-between text-muted-foreground mb-1">
            <span className="text-[12px]">最大拓扑深度</span>
            <Share2Icon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
          </div>
          <div className="text-sm font-semibold font-mono tabular-nums text-foreground">
            Level {stats?.max_depth ?? '--'}
          </div>
        </div>

        <div className="p-2.5 rounded-md bg-muted/30 border border-border/50">
          <div className="flex items-center justify-between text-muted-foreground mb-1">
            <span className="text-[12px]">读写分离状态</span>
            <SparklesIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
          </div>
          <div className="text-sm font-semibold font-mono tabular-nums text-cyan-700 dark:text-cyan-400">
            {stats?.serving_desk_ready ? 'Immutable Ready' : 'Syncing'}
          </div>
        </div>
      </div>

      {/* Preset Quick Anchor Bar */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="text-[12px] text-muted-foreground mr-1">快速漫游定位:</span>
        {PRESET_ANCHORS.map((anchor) => (
          <Button
            key={anchor.id}
            variant={currentAnchorId === anchor.id ? 'secondary' : 'outline'}
            size="sm"
            className="h-6 text-[12px] px-2 font-mono"
            onClick={() => setCurrentAnchorId(anchor.id)}
          >
            {anchor.label}
          </Button>
        ))}
      </div>

      {/* Main Interactive Stage: 4-Way Compass Navigation & Anchor Details */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
        {/* Left Column: 4-Way Compass Console */}
        <div className="md:col-span-4 p-3 rounded-md bg-muted/20 border border-border/60 flex flex-col items-center justify-center space-y-2">
          <span className="text-[12px] font-medium text-muted-foreground mb-1">HG-RAG 四向指南针</span>

          {/* North (Upwards - Parent) */}
          <Button
            variant="outline"
            size="sm"
            disabled={!availableDirs.has('north') || navMutation.isPending}
            onClick={() => navMutation.mutate({ direction: 'north' })}
            className={`w-28 h-7 text-[12px] flex items-center justify-center gap-1 ${
              availableDirs.has('north') ? 'border-cyan-200 text-cyan-800 hover:bg-cyan-50 dark:border-cyan-800/60 dark:text-cyan-300 dark:hover:bg-cyan-950/30' : 'opacity-40'
            }`}
          >
            <ChevronUpIcon className="size-3.5" />
            <span>North (父类)</span>
          </Button>

          {/* Middle Row: West & East (Lateral - Siblings) */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={!availableDirs.has('west') || navMutation.isPending}
              onClick={() => navMutation.mutate({ direction: 'west' })}
              className={`w-24 h-7 text-[12px] flex items-center justify-center gap-1 ${
                availableDirs.has('west') ? 'border-cyan-200 text-cyan-800 hover:bg-cyan-50 dark:border-cyan-800/60 dark:text-cyan-300 dark:hover:bg-cyan-950/30' : 'opacity-40'
              }`}
            >
              <ChevronLeftIcon className="size-3.5" />
              <span>West (前驱)</span>
            </Button>

            <div className="size-8 rounded-full border border-cyan-200 bg-cyan-50 dark:border-cyan-800/50 dark:bg-cyan-950/40 flex items-center justify-center">
              <CompassIcon className="size-4 text-cyan-600 dark:text-cyan-400 animate-spin-slow" />
            </div>

            <Button
              variant="outline"
              size="sm"
              disabled={!availableDirs.has('east') || navMutation.isPending}
              onClick={() => navMutation.mutate({ direction: 'east' })}
              className={`w-24 h-7 text-[12px] flex items-center justify-center gap-1 ${
                availableDirs.has('east') ? 'border-cyan-200 text-cyan-800 hover:bg-cyan-50 dark:border-cyan-800/60 dark:text-cyan-300 dark:hover:bg-cyan-950/30' : 'opacity-40'
              }`}
            >
              <span>East (后继)</span>
              <ChevronRightIcon className="size-3.5" />
            </Button>
          </div>

          {/* South (Downwards - Children) */}
          <Button
            variant="outline"
            size="sm"
            disabled={!availableDirs.has('south') || navMutation.isPending}
            onClick={() => navMutation.mutate({ direction: 'south', childIndex: 0 })}
            className={`w-28 h-7 text-[12px] flex items-center justify-center gap-1 ${
              availableDirs.has('south') ? 'border-cyan-200 text-cyan-800 hover:bg-cyan-50 dark:border-cyan-800/60 dark:text-cyan-300 dark:hover:bg-cyan-950/30' : 'opacity-40'
            }`}
          >
            <ChevronDownIcon className="size-3.5" />
            <span>South (下钻)</span>
          </Button>

          <p className="text-[11px] text-muted-foreground/80 text-center mt-1">
            点击罗盘方向漫游，实体全路径大类 100% 自洽挂载
          </p>
        </div>

        {/* Right Column: Active Node Details & Full Lineage */}
        <div className="md:col-span-8 p-3 rounded-md bg-muted/20 border border-border/60 space-y-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="border-border text-foreground font-mono text-[12px]">
                Depth {nodeData?.depth ?? 0}
              </Badge>
              <h4 className="text-xs font-semibold text-foreground">{nodeData?.title ?? '加载中...'}</h4>
            </div>
            <span className="font-mono text-[11px] text-muted-foreground">{nodeData?.node_id}</span>
          </div>

          {/* Self-contained Breadcrumb Lineage */}
          <div className="p-2 rounded bg-muted/40 border border-border/50 text-[12px]">
            <span className="text-muted-foreground mr-1">自洽祖先血缘路径:</span>
            <span className="font-mono text-cyan-400 font-medium">
              {nodeData ? nodeData.breadcrumbs.join(' > ') : '--'}
            </span>
          </div>

          {/* Content Snippet */}
          <div className="p-2 rounded bg-muted/30 border border-border/40 text-[12px] leading-relaxed text-foreground">
            {nodeData?.content_snippet ?? '暂无内容摘录'}
          </div>

          {/* Directional Pointers Summary */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 pt-1 text-[11px] font-mono text-muted-foreground">
            <div>Parent: {nodeData?.parent_id ? <span className="text-foreground">{nodeData.parent_id}</span> : 'Root'}</div>
            <div>Children: <span className="text-foreground">{nodeData ? `${nodeData.children_ids.length} 项` : '0 项'}</span></div>
            <div>Prev: {nodeData?.sibling_prev_id ? <span className="text-foreground">{nodeData.sibling_prev_id}</span> : 'None'}</div>
            <div>Next: {nodeData?.sibling_next_id ? <span className="text-foreground">{nodeData.sibling_next_id}</span> : 'None'}</div>
          </div>
        </div>
      </div>
    </Card>
  )
}
