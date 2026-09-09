import * as React from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { ActivityIcon, FileSearchIcon, SearchIcon, CopyIcon, CheckIcon, ChevronLeftIcon, ChevronRightIcon } from 'lucide-react'

import { Card } from '#/components/ui/card'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { ovClient } from '#/lib/ov-client'
import { cn } from '#/lib/utils'
import { GatekeeperDecisionDrawer } from './gatekeeper-decision-drawer'
import type { GatekeeperDecisionRecord } from './gatekeeper-decision-drawer'

interface GatekeeperApiResponse {
  status: string
  result: {
    stats: unknown
    history: GatekeeperDecisionRecord[]
  }
}

export function GatekeeperAuditStream() {
  const { t } = useTranslation('tasksPage')
  const [selectedDecision, setSelectedDecision] = React.useState<GatekeeperDecisionRecord | null>(null)
  const [actionFilter, setActionFilter] = React.useState<string>('all')
  const [searchKeyword, setSearchKeyword] = React.useState<string>('')
  const [copiedId, setCopiedId] = React.useState<string | null>(null)

  const { data, isLoading } = useQuery<GatekeeperApiResponse>({
    queryKey: ['entropy-gatekeeper-stats'],
    queryFn: async () => {
      const resp = await ovClient.instance.get('/api/v1/system/entropy/gatekeeper')
      return resp.data
    },
    refetchInterval: 10000,
    refetchIntervalInBackground: false,
  })

  const history = data?.result.history || []

  const handleCopyId = (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    void navigator.clipboard.writeText(id)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const [currentPage, setCurrentPage] = React.useState(1)
  const PAGE_SIZE = 10

  const filteredHistory = React.useMemo(() => {
    const kw = searchKeyword.trim().toLowerCase()
    return history.slice().reverse().filter((rec) => {
      if (actionFilter !== 'all' && rec.action !== actionFilter) {
        return false
      }
      if (kw) {
        const idMatch = rec.id?.toLowerCase().includes(kw)
        const uriMatch = rec.uri?.toLowerCase().includes(kw)
        const matchedUriMatch = rec.matched_uri?.toLowerCase().includes(kw)
        const reasonMatch = rec.reason.toLowerCase().includes(kw)
        if (!idMatch && !uriMatch && !matchedUriMatch && !reasonMatch) {
          return false
        }
      }
      return true
    })
  }, [history, actionFilter, searchKeyword])

  React.useEffect(() => {
    setCurrentPage(1)
  }, [actionFilter, searchKeyword])

  const totalPages = Math.max(1, Math.ceil(filteredHistory.length / PAGE_SIZE))
  const paginatedHistory = React.useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE
    return filteredHistory.slice(start, start + PAGE_SIZE)
  }, [filteredHistory, currentPage])

  const formatTime = (timestamp?: number) => {
    if (!timestamp) return '--:--:--'
    const date = new Date(timestamp > 1e11 ? timestamp : timestamp * 1000)
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
  }

  const getActionBadge = (action: string) => {
    switch (action) {
      case 'noop':
        return (
          <Badge variant="outline" className="border-border/60 bg-muted/40 text-muted-foreground text-[11px] font-mono px-1.5 py-0">
            {t('gatekeeper.noop')}
          </Badge>
        )
      case 'update':
        return (
          <Badge variant="outline" className="border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400 text-[11px] font-mono px-1.5 py-0">
            {t('gatekeeper.update')}
          </Badge>
        )
      case 'delete':
        return (
          <Badge variant="outline" className="border-rose-500/40 bg-rose-500/10 text-rose-600 dark:text-rose-400 text-[11px] font-mono px-1.5 py-0">
            {t('gatekeeper.delete')}
          </Badge>
        )
      default:
        return (
          <Badge variant="outline" className="border-primary/40 bg-primary/10 text-primary text-[11px] font-mono px-1.5 py-0">
            {t('gatekeeper.add')}
          </Badge>
        )
    }
  }

  const filterOptions = [
    { key: 'all', label: t('gatekeeper.filterAll') },
    { key: 'add', label: t('gatekeeper.add') },
    { key: 'update', label: t('gatekeeper.update') },
    { key: 'delete', label: t('gatekeeper.delete') },
    { key: 'noop', label: t('gatekeeper.noop') },
  ]

  return (
    <>
      <Card className="flex flex-col gap-2.5 p-3.5 shadow-none border-border/70">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/40 pb-2.5">
          <div className="flex items-center gap-2">
            <ActivityIcon className="size-4 text-primary shrink-0" />
            <span className="text-sm font-semibold tracking-tight text-foreground">
              {t('gatekeeper.streamTitle')}
            </span>
            <span className="hidden text-xs text-muted-foreground sm:inline">
              — {t('gatekeeper.streamSubtitle')}
            </span>
          </div>
          <div className="flex items-center gap-2.5 text-xs text-muted-foreground">
            <span className="inline-block size-1.5 rounded-full bg-primary animate-pulse" />
            <span className="font-mono text-[11px]">
              {history.length > 0
                ? t('gatekeeper.showingCount', { count: filteredHistory.length, total: history.length })
                : t('gatekeeper.emptyDecisions')}
            </span>
          </div>
        </div>

        {/* 筛选与搜索工具条 */}
        <div className="flex flex-wrap items-center justify-between gap-2 bg-muted/20 p-1.5 rounded-md border border-border/40">
          {/* 动作类型 Pills */}
          <div className="flex items-center gap-1">
            {filterOptions.map((opt) => (
              <button
                key={opt.key}
                type="button"
                onClick={() => setActionFilter(opt.key)}
                className={cn(
                  'rounded px-2 py-0.5 text-[11px] font-medium transition-colors cursor-pointer',
                  actionFilter === opt.key
                    ? 'bg-background text-foreground shadow-xs font-semibold'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/40'
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>

          {/* 搜索过滤框 */}
          <div className="relative flex items-center min-w-50 max-w-xs">
            <SearchIcon className="absolute left-2 size-3 text-muted-foreground pointer-events-none" />
            <Input
              type="text"
              value={searchKeyword}
              onChange={(e) => setSearchKeyword(e.target.value)}
              placeholder={t('gatekeeper.searchPlaceholder')}
              className="h-6 pl-6 text-[11px] font-mono bg-background/80"
            />
          </div>
        </div>

        {/* 流水列表区域 */}
        {isLoading ? (
          <div className="py-8 text-center text-xs text-muted-foreground">
            {t('loading')}
          </div>
        ) : filteredHistory.length === 0 ? (
          <div className="py-6 text-center text-[11px] text-muted-foreground rounded-md border border-dashed border-border/50">
            {history.length === 0 ? t('gatekeeper.emptyDecisions') : t('gatekeeper.noFilterMatch')}
          </div>
        ) : (
          <div className="flex flex-col overflow-hidden rounded-md border border-border/50 bg-background">
            {/* 表头 */}
            <div className="flex items-center gap-3 border-b border-border/50 bg-muted/20 px-3 py-1.5 text-[11px] font-medium text-muted-foreground">
              <span className="w-24 shrink-0">{t('gatekeeper.colId')}</span>
              <span className="w-16 shrink-0">{t('gatekeeper.colTime')}</span>
              <span className="w-20 shrink-0">{t('gatekeeper.colAction')}</span>
              <span className="w-48 shrink-0">{t('gatekeeper.colTarget')}</span>
              <span className="w-16 shrink-0">{t('gatekeeper.colSim')}</span>
              <span className="min-w-0 flex-1">{t('gatekeeper.colReason')}</span>
              <span className="w-12 shrink-0 text-right">{t('gatekeeper.colInspect')}</span>
            </div>

            {/* 数据体 */}
            <div className="flex flex-col divide-y divide-border/40 max-h-85 overflow-y-auto">
              {paginatedHistory.map((rec: GatekeeperDecisionRecord, idx: number) => {
                const targetUri = rec.uri || rec.matched_uri || '--'
                const recId = rec.id || `dec_${(rec.timestamp ? Math.floor(rec.timestamp * 1000) : idx).toString(16).slice(-6)}`
                return (
                  <div
                    key={`${rec.id || rec.timestamp || idx}-${idx}`}
                    onClick={() => setSelectedDecision({ ...rec, id: recId })}
                    className="flex items-center gap-3 px-3 py-2 text-left transition-colors hover:bg-muted/40 cursor-pointer"
                  >
                    {/* 流水号 ID */}
                    <button
                      type="button"
                      onClick={(e) => handleCopyId(e, recId)}
                      className="w-24 shrink-0 flex items-center gap-1 font-mono text-[11px] text-muted-foreground hover:text-foreground group cursor-pointer"
                      title={t('gatekeeper.copySuccess')}
                    >
                      <span className="truncate">#{recId}</span>
                      {copiedId === recId ? (
                        <CheckIcon className="size-3 text-primary shrink-0" />
                      ) : (
                        <CopyIcon className="size-2.5 opacity-0 group-hover:opacity-70 shrink-0" />
                      )}
                    </button>

                    {/* 时间戳 */}
                    <span className="w-16 shrink-0 font-mono text-[11px] tabular-nums text-muted-foreground">
                      {formatTime(rec.timestamp)}
                    </span>

                    {/* 裁决动作 */}
                    <div className="w-20 shrink-0">
                      {getActionBadge(rec.action)}
                    </div>

                    {/* 目标 URI */}
                    <span
                      className="w-48 shrink-0 truncate font-mono text-[11px] text-foreground/90"
                      title={targetUri}
                    >
                      {targetUri}
                    </span>

                    {/* 相似度 */}
                    <span
                      className={cn(
                        'w-16 shrink-0 font-mono text-[11px] tabular-nums font-semibold',
                        rec.similarity >= 0.95
                          ? 'text-primary'
                          : rec.similarity >= 0.9
                            ? 'text-amber-500 dark:text-amber-400'
                            : 'text-muted-foreground'
                      )}
                    >
                      {rec.similarity > 0 ? (rec.similarity * 100).toFixed(1) + '%' : '--'}
                    </span>

                    {/* 裁决依据 (直接阅读) */}
                    <span
                      className="min-w-0 flex-1 truncate text-[11px] text-muted-foreground"
                      title={rec.reason}
                    >
                      {rec.reason || '--'}
                    </span>

                    {/* 溯源按钮 */}
                    <div className="w-12 shrink-0 text-right">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation()
                          setSelectedDecision({ ...rec, id: recId })
                        }}
                        className="h-6 px-1.5 text-[11px] text-muted-foreground hover:text-foreground"
                      >
                        <FileSearchIcon className="size-3" />
                        <span className="sr-only sm:not-sr-only sm:inline-block sm:ml-1 text-[11px]">
                          {t('gatekeeper.colInspect')}
                        </span>
                      </Button>
                    </div>
                  </div>
                )
              })}
            </div>

            {/* 分页控制栏 */}
            {filteredHistory.length > 0 && (
              <div className="flex items-center justify-between border-t border-border/50 bg-muted/20 px-3 py-1.5 text-[11px] text-muted-foreground">
                <span className="font-mono">
                  {t('gatekeeper.paginationSummary', {
                    count: filteredHistory.length,
                    current: currentPage,
                    total: totalPages,
                    defaultValue: `共 ${filteredHistory.length} 条 · 第 ${currentPage}/${totalPages} 页`,
                  })}
                </span>
                <div className="flex items-center gap-1.5">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={currentPage <= 1}
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    className="h-6 px-2 text-[11px] cursor-pointer"
                  >
                    <ChevronLeftIcon className="size-3 mr-0.5" />
                    {t('gatekeeper.prevPage', { defaultValue: '上一页' })}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={currentPage >= totalPages}
                    onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                    className="h-6 px-2 text-[11px] cursor-pointer"
                  >
                    {t('gatekeeper.nextPage', { defaultValue: '下一页' })}
                    <ChevronRightIcon className="size-3 ml-0.5" />
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </Card>

      <GatekeeperDecisionDrawer
        open={Boolean(selectedDecision)}
        onOpenChange={(open) => {
          if (!open) setSelectedDecision(null)
        }}
        decision={selectedDecision}
      />
    </>
  )
}

