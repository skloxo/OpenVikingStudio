/* eslint-disable i18next/no-literal-string */
import * as React from 'react'
import { useQuery } from '@tanstack/react-query'
import { ovClient } from '#/lib/ov-client'
import {
  ListFilterIcon,
  RefreshCwIcon,
  SparklesIcon,
  ShieldCheckIcon,
  LayersIcon,
  ArrowRightIcon,
  ExternalLinkIcon,
} from 'lucide-react'
import { FactCrystalDrawer, type FactCrystal } from './fact-crystal-drawer'

interface GovernanceStreamEvent {
  event_id: string
  type: string
  action: string
  uri: string
  matched_uri?: string | null
  similarity?: number | null
  reason: string
  timestamp: number
  net_entropy_reduced: number
}

export function MemoryGovernanceStreamCard() {
  const [filterType, setFilterType] = React.useState<string>('all')
  const [selectedCrystal, setSelectedCrystal] = React.useState<FactCrystal | null>(null)
  const [drawerOpen, setDrawerOpen] = React.useState(false)

  const { data: events, isLoading, refetch } = useQuery<GovernanceStreamEvent[]>({
    queryKey: ['memory-governance-stream', filterType],
    queryFn: async () => {
      const typeParam = filterType !== 'all' ? `&event_type=${filterType}` : ''
      const res = await ovClient.instance.get<{ status: string; result: GovernanceStreamEvent[] }>(
        `/api/v1/memory/governance/stream?limit=30${typeParam}`
      )
      return res.data.result
    },
    staleTime: 15_000,
    refetchIntervalInBackground: false,
  })

  const handleRowClick = async (evt: GovernanceStreamEvent) => {
    if (evt.type === 'DREAM_CONSOLIDATION' || evt.event_id.startsWith('#cry')) {
      try {
        const res = await ovClient.instance.get<{ status: string; result: FactCrystal }>(
          `/api/v1/memory/crystallize/detail?uri=${encodeURIComponent(evt.uri)}`
        )
        if (res.data?.result) {
          setSelectedCrystal(res.data.result)
          setDrawerOpen(true)
          return
        }
      } catch {
        // Fallback to synthetic crystal if detail endpoint hasn't indexed it yet
      }

      // Synthetic crystal representation fallback
      setSelectedCrystal({
        uri: evt.uri,
        axiom: evt.reason,
        context_bounds: {
          version_range: '>= v1.6.0',
          source_uris: evt.matched_uri ? [evt.matched_uri] : [],
          evidence_hashes: [],
          distilled_at: evt.timestamp,
          distiller_id: 'dream_recipe_distiller',
        },
        negative_boundary: {
          deprecated_patterns: [],
          forbidden_keywords: [],
        },
        status: 'active',
        created_at: evt.timestamp,
      })
      setDrawerOpen(true)
    }
  }

  return (
    <div className="rounded-md border border-neutral-800 bg-neutral-900/80 p-3.5 text-xs text-neutral-200">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-800 pb-3">
        <div className="flex items-center gap-2">
          <ListFilterIcon className="size-4 text-cyan-400" />
          <span className="font-semibold text-neutral-100">
            全生命周期记忆治理总账流水 (Unified Memory Governance Stream)
          </span>
          <span className="rounded border border-neutral-800 bg-neutral-800/60 px-1.5 py-0.5 text-xs text-neutral-400">
            前门准入 ⊕ 存量做梦
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Filter Pills */}
          <div className="flex items-center rounded-md border border-neutral-800 bg-neutral-950/60 p-0.5">
            <button
              onClick={() => setFilterType('all')}
              className={`rounded px-2 py-0.5 text-xs transition-colors ${
                filterType === 'all'
                  ? 'bg-neutral-800 text-cyan-300 font-medium'
                  : 'text-neutral-400 hover:text-neutral-200'
              }`}
            >
              全部总账
            </button>
            <button
              onClick={() => setFilterType('INGRESS_ADMISSION')}
              className={`rounded px-2 py-0.5 text-xs transition-colors ${
                filterType === 'INGRESS_ADMISSION'
                  ? 'bg-neutral-800 text-cyan-300 font-medium'
                  : 'text-neutral-400 hover:text-neutral-200'
              }`}
            >
              前门准入 (#dec)
            </button>
            <button
              onClick={() => setFilterType('DREAM_CONSOLIDATION')}
              className={`rounded px-2 py-0.5 text-xs transition-colors ${
                filterType === 'DREAM_CONSOLIDATION'
                  ? 'bg-neutral-800 text-cyan-300 font-medium'
                  : 'text-neutral-400 hover:text-neutral-200'
              }`}
            >
              做梦提纯 (#cry)
            </button>
          </div>

          <button
            onClick={() => refetch()}
            disabled={isLoading}
            className="rounded p-1 text-neutral-400 transition-colors hover:text-neutral-200 disabled:opacity-50"
            title="刷新流水"
          >
            <RefreshCwIcon className={`size-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Stream List */}
      <div className="mt-3 divide-y divide-neutral-800/60 overflow-hidden rounded border border-neutral-800/80 bg-neutral-950/40">
        {isLoading ? (
          <div className="p-4 text-center text-xs text-neutral-400">加载治理总账流水中...</div>
        ) : !events || events.length === 0 ? (
          <div className="p-4 text-center text-xs text-neutral-500">暂无治理流水记录</div>
        ) : (
          events.map((evt, idx) => {
            const isDream = evt.type === 'DREAM_CONSOLIDATION'
            const isNoop = evt.action === 'noop'
            const isUpdate = evt.action === 'update'
            const timeStr = new Date(evt.timestamp * 1000).toLocaleTimeString()

            const actionBadge = isDream ? (
              <span className="flex items-center gap-1 rounded border border-cyan-500/30 bg-cyan-950/40 px-1.5 py-0.5 text-xs text-cyan-300">
                <SparklesIcon className="size-3" />
                <span>做梦提纯</span>
              </span>
            ) : isNoop ? (
              <span className="flex items-center gap-1 rounded border border-cyan-500/30 bg-cyan-950/40 px-1.5 py-0.5 text-xs text-cyan-300">
                <ShieldCheckIcon className="size-3" />
                <span>印证去重</span>
              </span>
            ) : isUpdate ? (
              <span className="flex items-center gap-1 rounded border border-amber-500/30 bg-amber-950/40 px-1.5 py-0.5 text-xs text-amber-300">
                <LayersIcon className="size-3" />
                <span>特例演化</span>
              </span>
            ) : (
              <span className="rounded border border-neutral-800 bg-neutral-800/60 px-1.5 py-0.5 text-xs text-neutral-400">
                新增写入
              </span>
            )

            return (
              <div
                key={`${evt.event_id}-${idx}`}
                onClick={() => void handleRowClick(evt)}
                className={`flex flex-col gap-1.5 p-2.5 transition-colors sm:flex-row sm:items-center sm:justify-between ${
                  isDream ? 'cursor-pointer hover:bg-neutral-800/50' : 'hover:bg-neutral-900/40'
                }`}
                title={isDream ? '点击查看不可变晶体详情 (Fact Crystal Drawer)' : undefined}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs text-neutral-400">{evt.event_id}</span>
                  {actionBadge}
                  <span className="font-mono text-xs text-neutral-300 flex items-center gap-1" title={evt.uri}>
                    {evt.uri.replace('viking://resources/', '')}
                    {isDream && <ExternalLinkIcon className="size-3 text-cyan-400/70" />}
                  </span>
                  {evt.matched_uri && (
                    <div className="flex items-center gap-1 text-xs text-neutral-400">
                      <ArrowRightIcon className="size-3" />
                      <span className="font-mono" title={evt.matched_uri}>
                        {evt.matched_uri.replace('viking://resources/', '')}
                      </span>
                      {evt.similarity !== null && evt.similarity !== undefined && (
                        <span className="font-mono text-cyan-400 font-semibold">
                          ({(evt.similarity * 100).toFixed(1)}%)
                        </span>
                      )}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-3 text-xs text-neutral-400">
                  <span className="line-clamp-1 max-w-70" title={evt.reason}>
                    {evt.reason}
                  </span>
                  {evt.net_entropy_reduced > 0 && (
                    <span className="font-mono text-cyan-400 font-semibold">
                      减熵 -{evt.net_entropy_reduced}
                    </span>
                  )}
                  <span className="font-mono text-neutral-400">{timeStr}</span>
                </div>
              </div>
            )
          })
        )}
      </div>

      {/* Fact Crystal Drawer */}
      <FactCrystalDrawer
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        crystal={selectedCrystal}
      />
    </div>
  )
}

