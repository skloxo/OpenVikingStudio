import * as React from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Card } from '#/components/ui/card'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { ovClient } from '#/lib/ov-client'
import {
  ShieldAlertIcon,
  ShieldCheckIcon,
  LayersIcon,
  ActivityIcon,
  SearchIcon,
  SparklesIcon,
  CheckCircle2Icon,
  AlertOctagonIcon,
} from 'lucide-react'

export interface RAGMetricsResponse {
  total_verifications: number
  total_abstained: number
  abstention_rate: number
  avg_confidence: number
  avg_latency_ms: number
}

export interface ChunkDedupResult {
  chunk_id: string
  content: string
  is_duplicate: boolean
  duplicate_of: string | null
  similarity_score: number
}

export interface AbstentionDecision {
  should_abstain: boolean
  confidence: number
  abstain_reason: string | null
  matched_evidence_count: number
  grounded_tokens: string[]
  latency_ms: number
}

export interface RAGVerifyResponse {
  decision: AbstentionDecision
  dedup_results: ChunkDedupResult[]
  effective_evidence_count: number
  original_evidence_count: number
}

const PRESET_QUERIES = [
  {
    label: '保真可答 (OpenViking 端口与架构)',
    query: 'OpenViking 服务监听的默认服务端口与 SQLite 架构是什么？',
    evidence: [
      'OpenViking service binds to default port 1933 for HTTP and FastMCP communication.',
      'OpenViking uses SQLite FTS5 for full-text search indexing and WAL mode.',
      'OpenViking service binds to default port 1933 for HTTP and FastMCP communication.', // deliberate duplicate
    ],
  },
  {
    label: '超纲弃答 (无依据烘焙问题)',
    query: '如何用 220 度烤箱烘烤法式巧克力酸种面包？',
    evidence: [
      'OpenViking service binds to default port 1933 for HTTP and FastMCP communication.',
      'System telemetry records memory usage, CPU load, and active sessions.',
    ],
  },
]

export function RAGAbstentionCockpit() {
  const [queryInput, setQueryInput] = React.useState(PRESET_QUERIES[0].query)
  const [evidenceInput, setEvidenceInput] = React.useState(PRESET_QUERIES[0].evidence.join('\n---\n'))
  const [activeProbe, setActiveProbe] = React.useState<RAGVerifyResponse | null>(null)

  // 1. Fetch live metrics
  const { data: metrics, refetch: refetchMetrics } = useQuery<RAGMetricsResponse>({
    queryKey: ['rag-abstention-metrics'],
    queryFn: async () => {
      const res = await ovClient.instance.get<RAGMetricsResponse>('/api/v1/rag/metrics')
      return res.data
    },
    refetchInterval: 15_000,
    refetchIntervalInBackground: false,
    staleTime: 15_000,
  })

  // 2. Run verification probe mutation
  const verifyMutation = useMutation({
    mutationFn: async (payload: { query: string; evidence: string[] }) => {
      const res = await ovClient.instance.post<RAGVerifyResponse>('/api/v1/rag/verify', {
        query: payload.query,
        evidence_chunks: payload.evidence,
        custom_threshold: 0.40,
        enable_dedup: true,
      })
      return res.data
    },
    onSuccess: (data) => {
      setActiveProbe(data)
      refetchMetrics()
    },
  })

  const handleRunVerify = () => {
    if (!queryInput.trim()) return
    const chunks = evidenceInput
      .split('\n---\n')
      .map((s) => s.trim())
      .filter(Boolean)
    verifyMutation.mutate({ query: queryInput, evidence: chunks })
  }

  const handleSelectPreset = (p: (typeof PRESET_QUERIES)[0]) => {
    setQueryInput(p.query)
    setEvidenceInput(p.evidence.join('\n---\n'))
    const chunks = p.evidence.filter(Boolean)
    verifyMutation.mutate({ query: p.query, evidence: chunks })
  }

  return (
    <Card className="p-3.5 border-border/80 bg-card/60 backdrop-blur-sm space-y-3.5">
      {/* Cockpit Header */}
      <div className="flex items-center justify-between border-b border-border/50 pb-2.5">
        <div className="flex items-center gap-2">
          <div className="p-1 rounded bg-cyan-50 text-cyan-700 border border-cyan-200 dark:bg-cyan-500/10 dark:text-cyan-400 dark:border-cyan-500/20">
            <ShieldAlertIcon className="size-3.5" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-semibold text-foreground tracking-wide">
                RAG 约束验证与主动弃答门禁 (Zero-Hallucination Abstention Gate)
              </span>
              <Badge variant="outline" className="text-xs px-1.5 py-0 h-4 border-cyan-200 bg-cyan-50 text-cyan-800 dark:border-cyan-500/30 dark:text-cyan-400 dark:bg-cyan-950/20 font-mono">
                Card-RAG-Abstention-ZeroHallucination
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              MinHash LSH 近重复去重 · NFKC 标准化 · 证据覆盖置信度评定 · 低置信强制拒答
            </p>
          </div>
        </div>
      </div>

      {/* KPI Tiles */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <div className="p-2.5 rounded-md border border-border/70 bg-background/50 space-y-1">
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <AlertOctagonIcon className="size-3 text-rose-400" />
            主动弃答率 (Abstain Rate)
          </span>
          <div className="text-xs font-mono font-semibold text-foreground">
            {metrics ? `${(metrics.abstention_rate * 100).toFixed(1)}%` : '--'}
            <span className="text-xs text-muted-foreground font-normal ml-1">
              ({metrics?.total_abstained ?? 0} / {metrics?.total_verifications ?? 0})
            </span>
          </div>
        </div>

        <div className="p-2.5 rounded-md border border-border/70 bg-background/50 space-y-1">
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <CheckCircle2Icon className="size-3 text-cyan-600 dark:text-cyan-400" />
            平均置信度 (Avg Confidence)
          </span>
          <div className="text-xs font-mono font-semibold text-cyan-700 dark:text-cyan-400">
            {metrics ? metrics.avg_confidence.toFixed(3) : '--'}
            <span className="text-xs text-muted-foreground font-normal ml-1">/ 1.000</span>
          </div>
        </div>

        <div className="p-2.5 rounded-md border border-border/70 bg-background/50 space-y-1">
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <LayersIcon className="size-3 text-cyan-600 dark:text-cyan-400" />
            MinHash 去重引擎 (LSH)
          </span>
          <div className="text-xs font-mono font-semibold text-foreground">
            64-perm <span className="text-xs text-muted-foreground font-normal ml-1">阈值 0.80</span>
          </div>
        </div>

        <div className="p-2.5 rounded-md border border-border/70 bg-background/50 space-y-1">
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <ActivityIcon className="size-3 text-cyan-600 dark:text-cyan-400" />
            门禁验证延迟 (Latency)
          </span>
          <div className="text-xs font-mono font-semibold text-foreground">
            {metrics ? `${metrics.avg_latency_ms.toFixed(2)} ms` : '--'}
          </div>
        </div>
      </div>

      {/* Preset Chips */}
      <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
        <span className="text-xs text-muted-foreground flex items-center gap-1 mr-1">
          <SparklesIcon className="size-3 text-cyan-600 dark:text-cyan-400" />
          预设探针场景:
        </span>
        {PRESET_QUERIES.map((p, idx) => (
          <Button
            key={idx}
            variant="outline"
            size="sm"
            onClick={() => handleSelectPreset(p)}
            className="h-6 text-xs px-2 py-0 border-border/70 hover:border-cyan-500/50 hover:bg-cyan-500/5 transition-colors"
          >
            {p.label}
          </Button>
        ))}
      </div>

      {/* Interactive Testing Bench */}
      <div className="space-y-2 pt-1 border-t border-border/40">
        <div className="flex items-center gap-2">
          <Input
            value={queryInput}
            onChange={(e) => setQueryInput(e.target.value)}
            placeholder="输入待验证查询..."
            className="h-7 text-xs bg-background/70 font-mono border-border/70 flex-1"
            onKeyDown={(e) => e.key === 'Enter' && handleRunVerify()}
          />
          <Button
            size="sm"
            onClick={handleRunVerify}
            disabled={verifyMutation.isPending}
            className="h-7 text-xs px-3 bg-cyan-600 hover:bg-cyan-500 text-white font-mono"
          >
            <SearchIcon className="size-3 mr-1" />
            {verifyMutation.isPending ? '验证中...' : '约束验证'}
          </Button>
        </div>

        {/* Verification Result Display */}
        {activeProbe && (
          <div className="p-2.5 rounded-md border border-border/70 bg-background/40 space-y-2 text-xs">
            <div className="flex items-center justify-between border-b border-border/40 pb-1.5">
              <div className="flex items-center gap-2">
                {activeProbe.decision.should_abstain ? (
                  <Badge variant="outline" className="text-xs px-1.5 py-0.5 border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/40 dark:text-rose-400 dark:bg-rose-950/20 font-semibold flex items-center gap-1">
                    <ShieldAlertIcon className="size-3" />
                    主动弃答 (ABSTAINED)
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-xs px-1.5 py-0.5 border-cyan-200 bg-cyan-50 text-cyan-800 dark:border-cyan-500/40 dark:text-cyan-400 dark:bg-cyan-950/20 font-semibold flex items-center gap-1">
                    <ShieldCheckIcon className="size-3" />
                    准许回答 (GROUNDED)
                  </Badge>
                )}
                <span className="font-mono text-muted-foreground">
                  置信度: <span className="font-semibold text-foreground">{activeProbe.decision.confidence}</span>
                </span>
                <span className="font-mono text-muted-foreground">
                  耗时: <span className="text-foreground">{activeProbe.decision.latency_ms} ms</span>
                </span>
              </div>
              <span className="text-xs text-muted-foreground font-mono">
                去重: {activeProbe.original_evidence_count} ➔ {activeProbe.effective_evidence_count} 块
              </span>
            </div>

            {activeProbe.decision.abstain_reason && (
              <div className="text-xs font-mono text-rose-800 bg-rose-50 p-1.5 rounded border border-rose-200 dark:text-rose-300/90 dark:bg-rose-950/10 dark:border-rose-500/20">
                弃答原因: {activeProbe.decision.abstain_reason}
              </div>
            )}

            {activeProbe.decision.grounded_tokens.length > 0 && (
              <div className="flex items-center gap-1 flex-wrap">
                <span className="text-xs text-muted-foreground">锚定关键词:</span>
                {activeProbe.decision.grounded_tokens.map((token, i) => (
                  <span key={i} className="text-xs font-mono bg-cyan-50 text-cyan-800 border border-cyan-200 dark:bg-cyan-950/30 dark:text-cyan-400 dark:border-cyan-500/20 px-1 py-0.5 rounded">
                    {token}
                  </span>
                ))}
              </div>
            )}

            {/* Deduplicated chunks display */}
            {activeProbe.dedup_results.length > 0 && (
              <div className="space-y-1 pt-1">
                <span className="text-xs text-muted-foreground block">候选证据 MinHash 审计:</span>
                {activeProbe.dedup_results.map((r, i) => (
                  <div key={i} className="flex items-center justify-between text-xs p-1 rounded bg-muted/20 border border-border/40 font-mono">
                    <span className="truncate flex-1 mr-2 text-foreground/80">{r.content}</span>
                    {r.is_duplicate ? (
                      <Badge variant="outline" className="text-xs px-1 py-0 border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-500/30 dark:text-amber-400 dark:bg-amber-950/20">
                        近重复 (相似 {r.similarity_score})
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-xs px-1 py-0 border-border/50 text-muted-foreground">
                        独立证据
                      </Badge>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  )
}
