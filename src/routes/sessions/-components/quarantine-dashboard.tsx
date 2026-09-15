import * as React from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  ArchiveIcon,
  CheckCircle2Icon,
  FileBoxIcon,
  FolderArchiveIcon,
  HardDriveIcon,
  RotateCcwIcon,
  SearchIcon,
  ShieldCheckIcon,
  XCircleIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { ovClient } from '#/lib/ov-client'

export interface QuarantineItem {
  name: string
  source: string
  destination: string
  size_bytes: number
  file_count: number
  batch_id: string
  category: string
  created_at: string
  uri?: string
}

export interface QuarantineBatch {
  batch_id: string
  category: string
  created_at: string
  total_targets: number
  total_files: number
  total_bytes: number
  archive_dir: string
}

export interface QuarantineManifestSnapshot {
  total_quarantined_targets: number
  total_quarantined_files: number
  total_quarantined_bytes: number
  total_quarantined_mb: number
  total_batches: number
  batches: QuarantineBatch[]
  items: QuarantineItem[]
  filtered_count: number
  cache_timestamp: number
}

export interface RestoreDryRunResult {
  success: boolean
  item_name: string
  batch_id: string
  destination_exists: boolean
  destination_files_count: number
  destination_size_bytes: number
  target_restore_path: string
  target_already_exists: boolean
  safe_to_restore: boolean
  message: string
  integrity_checked_at: number
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

export function QuarantineDashboard({ onBackToActive }: { onBackToActive?: () => void }) {
  const { t } = useTranslation('sessions')
  const [searchTerm, setSearchTerm] = React.useState('')
  const [selectedCategory, setSelectedCategory] = React.useState<string>('all')
  const [activeItem, setActiveItem] = React.useState<QuarantineItem | null>(null)
  const [dryRunResult, setDryRunResult] = React.useState<RestoreDryRunResult | null>(null)

  const manifestQuery = useQuery({
    queryKey: ['quarantine-manifest', searchTerm, selectedCategory],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (searchTerm.trim()) params.append('search', searchTerm.trim())
      if (selectedCategory !== 'all') params.append('category', selectedCategory)
      params.append('limit', '100')
      const res = await ovClient.instance.get<QuarantineManifestSnapshot>(
        `/api/v1/memory/quarantine_manifest?${params.toString()}`
      )
      return res.data
    },
    staleTime: 15_000,
  })

  const dryRunMutation = useMutation({
    mutationFn: async (payload: { batch_id: string; item_name: string }) => {
      const res = await ovClient.instance.post<RestoreDryRunResult>(
        '/api/v1/memory/quarantine_restore_dry_run',
        payload
      )
      return res.data
    },
    onSuccess: (data) => {
      setDryRunResult(data)
    },
  })

  const snapshot = manifestQuery.data

  const handleTestDryRun = (item: QuarantineItem) => {
    setActiveItem(item)
    setDryRunResult(null)
    dryRunMutation.mutate({ batch_id: item.batch_id, item_name: item.name })
  }

  return (
    <div className="flex h-full flex-col overflow-hidden bg-background text-foreground">
      {/* Top Header */}
      <div className="flex items-center justify-between border-b border-border/40 px-4 py-3">
        <div className="flex items-center gap-2.5">
          <div className="flex size-7 items-center justify-center rounded-md border border-amber-500/30 bg-amber-500/10 text-amber-400">
            <ArchiveIcon className="size-3.5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-foreground">
                {t('quarantine.title')}
              </h2>
              <Badge variant="outline" className="h-4 border-amber-500/30 bg-amber-500/10 px-1 font-mono text-[11px] text-amber-400">
                {t('quarantine.badge')}
              </Badge>
            </div>
            <p className="font-mono text-[11px] text-muted-foreground">
              {t('quarantine.desc')}
            </p>
          </div>
        </div>

        {onBackToActive && (
          <Button
            size="sm"
            variant="outline"
            onClick={onBackToActive}
            className="h-7 gap-1.5 border-border/60 text-[11px]"
          >
            {t('quarantine.backToActive')}
          </Button>
        )}
      </div>

      {/* Main Content Area */}
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {/* Metric Cards Grid */}
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <div className="flex flex-col justify-between rounded-md border border-border/40 bg-card/60 p-3.5 shadow-2xs">
            <div className="flex items-center justify-between text-muted-foreground">
              <span className="text-[11px] font-medium uppercase tracking-wider">{t('quarantine.metricTargets')}</span>
              <FileBoxIcon className="size-3.5 text-cyan-400" />
            </div>
            <div className="mt-2 flex items-baseline justify-between">
              <span className="font-mono text-xl font-bold tabular-nums text-cyan-400">
                {snapshot ? snapshot.total_quarantined_targets.toLocaleString() : '--'}
              </span>
              <span className="font-mono text-[11px] text-muted-foreground">{t('quarantine.targetsUnit')}</span>
            </div>
            <div className="mt-1 font-mono text-[11px] text-muted-foreground/80">
              {t('quarantine.metricTargetsSub')}
            </div>
          </div>

          <div className="flex flex-col justify-between rounded-md border border-border/40 bg-card/60 p-3.5 shadow-2xs">
            <div className="flex items-center justify-between text-muted-foreground">
              <span className="text-[11px] font-medium uppercase tracking-wider">{t('quarantine.metricFiles')}</span>
              <FolderArchiveIcon className="size-3.5 text-cyan-400" />
            </div>
            <div className="mt-2 flex items-baseline justify-between">
              <span className="font-mono text-xl font-bold tabular-nums text-cyan-400">
                {snapshot ? snapshot.total_quarantined_files.toLocaleString() : '--'}
              </span>
              <span className="font-mono text-[11px] text-muted-foreground">{t('quarantine.filesUnit')}</span>
            </div>
            <div className="mt-1 font-mono text-[11px] text-muted-foreground/80">
              {t('quarantine.metricFilesSub')}
            </div>
          </div>

          <div className="flex flex-col justify-between rounded-md border border-border/40 bg-card/60 p-3.5 shadow-2xs">
            <div className="flex items-center justify-between text-muted-foreground">
              <span className="text-[11px] font-medium uppercase tracking-wider">{t('quarantine.metricBytes')}</span>
              <HardDriveIcon className="size-3.5 text-cyan-400" />
            </div>
            <div className="mt-2 flex items-baseline justify-between">
              <span className="font-mono text-xl font-bold tabular-nums text-cyan-400">
                {snapshot ? snapshot.total_quarantined_mb.toFixed(2) : '--'}
              </span>
              <span className="font-mono text-[11px] text-muted-foreground">{t('quarantine.bytesUnit')}</span>
            </div>
            <div className="mt-1 font-mono text-[11px] text-muted-foreground/80">
              {t('quarantine.metricBytesSub')}
            </div>
          </div>

          <div className="flex flex-col justify-between rounded-md border border-border/40 bg-card/60 p-3.5 shadow-2xs">
            <div className="flex items-center justify-between text-muted-foreground">
              <span className="text-[11px] font-medium uppercase tracking-wider">{t('quarantine.metricBatches')}</span>
              <ShieldCheckIcon className="size-3.5 text-amber-400" />
            </div>
            <div className="mt-2 flex items-baseline justify-between">
              <span className="font-mono text-xl font-bold tabular-nums text-amber-400">
                {snapshot ? `${snapshot.total_batches} ${t('quarantine.batchUnit')}` : '--'}
              </span>
              <span className="font-mono text-[11px] text-amber-400">{t('quarantine.integrityOk')}</span>
            </div>
            <div className="mt-1 font-mono text-[11px] text-muted-foreground/80">
              {t('quarantine.metricBatchesSub')}
            </div>
          </div>
        </div>

        {/* Filter and Search Bar */}
        <div className="flex items-center justify-between gap-3 rounded-md border border-border/40 bg-card/40 p-2.5">
          <div className="flex flex-1 items-center gap-2">
            <div className="relative flex-1 max-w-sm">
              <SearchIcon className="absolute left-2.5 top-2 size-3 text-muted-foreground" />
              <Input
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder={t('quarantine.searchPlaceholder')}
                className="h-7 pl-8 text-xs font-mono"
              />
            </div>

            <div className="flex items-center gap-1.5">
              <Button
                size="sm"
                variant={selectedCategory === 'all' ? 'secondary' : 'ghost'}
                onClick={() => setSelectedCategory('all')}
                className="h-6 px-2 text-[11px]"
              >
                {t('quarantine.filterAll')} ({snapshot ? snapshot.total_quarantined_targets : 0})
              </Button>
              <Button
                size="sm"
                variant={selectedCategory === 'zombie_sessions' ? 'secondary' : 'ghost'}
                onClick={() => setSelectedCategory('zombie_sessions')}
                className="h-6 px-2 text-[11px]"
              >
                {t('quarantine.filterZombies')}
              </Button>
              <Button
                size="sm"
                variant={selectedCategory === 'cold_staging_sessions' ? 'secondary' : 'ghost'}
                onClick={() => setSelectedCategory('cold_staging_sessions')}
                className="h-6 px-2 text-[11px]"
              >
                {t('quarantine.filterStaging')}
              </Button>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] text-muted-foreground">
              {t('quarantine.matchedCount', { count: snapshot ? snapshot.filtered_count : 0 })}
            </span>
            <Button
              size="icon"
              variant="outline"
              onClick={() => manifestQuery.refetch()}
              className="size-7 border-border/60"
              title={t('quarantine.rescanTooltip')}
            >
              <RotateCcwIcon className="size-3 text-muted-foreground" />
            </Button>
          </div>
        </div>

        {/* Dry-Run Result Banner if active */}
        {dryRunResult && activeItem && (
          <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {dryRunResult.safe_to_restore ? (
                  <CheckCircle2Icon className="size-4 text-cyan-400" />
                ) : (
                  <XCircleIcon className="size-4 text-rose-400" />
                )}
                <span className="font-mono text-xs font-bold text-foreground">
                  {t('quarantine.dryRunReportTitle')}: {dryRunResult.item_name}
                </span>
                <Badge
                  variant="outline"
                  className={`h-4 text-[11px] ${
                    dryRunResult.safe_to_restore
                      ? 'border-cyan-500/30 bg-cyan-500/10 text-cyan-400'
                      : 'border-rose-500/30 bg-rose-500/10 text-rose-400'
                  }`}
                >
                  {dryRunResult.safe_to_restore ? t('quarantine.verifiedPass') : t('quarantine.verifiedFail')}
                </Badge>
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setDryRunResult(null)}
                className="h-5 px-1.5 text-[11px] text-muted-foreground"
              >
                {t('quarantine.closeReport')}
              </Button>
            </div>
            <div className="mt-2 grid grid-cols-2 gap-2 font-mono text-[11px] text-muted-foreground md:grid-cols-4">
              <div>{t('quarantine.archivedFiles')}: <span className="text-foreground">{dryRunResult.destination_files_count}</span></div>
              <div>{t('quarantine.archivedSize')}: <span className="text-foreground">{formatBytes(dryRunResult.destination_size_bytes)}</span></div>
              <div>{t('quarantine.targetExists')}: <span className={dryRunResult.target_already_exists ? 'text-amber-400' : 'text-cyan-400'}>{dryRunResult.target_already_exists ? t('quarantine.targetExistsYes') : t('quarantine.targetExistsNo')}</span></div>
              <div>{t('quarantine.batchIdLabel')}: <span className="text-foreground">{dryRunResult.batch_id}</span></div>
            </div>
            <div className="mt-1 font-mono text-[11px] text-foreground/90">
              {dryRunResult.message}
            </div>
          </div>
        )}

        {/* High-Density Manifest Table */}
        <div className="rounded-md border border-border/40 bg-card/60">
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead className="border-b border-border/40 bg-muted/40 text-[11px] uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-3 py-2 font-medium">{t('quarantine.colTarget')}</th>
                  <th className="px-3 py-2 font-medium">{t('quarantine.colCategory')}</th>
                  <th className="px-3 py-2 font-medium text-right">{t('quarantine.colFiles')}</th>
                  <th className="px-3 py-2 font-medium text-right">{t('quarantine.colSize')}</th>
                  <th className="px-3 py-2 font-medium">{t('quarantine.colBatch')}</th>
                  <th className="px-3 py-2 font-medium text-right">{t('quarantine.colAction')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/20">
                {manifestQuery.isLoading ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-muted-foreground">
                      {t('quarantine.loading')}
                    </td>
                  </tr>
                ) : !snapshot || snapshot.items.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-muted-foreground">
                      {t('quarantine.emptyList')}
                    </td>
                  </tr>
                ) : (
                  snapshot.items.map((item) => (
                    <tr
                      key={`${item.batch_id}-${item.name}`}
                      className="hover:bg-muted/30 transition-colors"
                    >
                      <td className="px-3 py-2">
                        <div className="font-semibold text-foreground">{item.name}</div>
                        <div className="text-[11px] text-muted-foreground truncate max-w-md">
                          {item.source}
                        </div>
                      </td>
                      <td className="px-3 py-2">
                        <Badge
                          variant="outline"
                          className="border-border/60 bg-muted/30 text-[11px] text-muted-foreground"
                        >
                          {item.category}
                        </Badge>
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums text-foreground">
                        {item.file_count}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums text-foreground">
                        {formatBytes(item.size_bytes)}
                      </td>
                      <td className="px-3 py-2 text-muted-foreground text-[11px]">
                        {item.batch_id}
                      </td>
                      <td className="px-3 py-2 text-right">
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={dryRunMutation.isPending && activeItem?.name === item.name}
                          onClick={() => handleTestDryRun(item)}
                          className="h-6 border-amber-500/30 px-2 text-[11px] text-amber-400 hover:bg-amber-500/10"
                        >
                          {dryRunMutation.isPending && activeItem?.name === item.name ? (
                            t('quarantine.dryRunTesting')
                          ) : (
                            t('quarantine.dryRunBtn')
                          )}
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
