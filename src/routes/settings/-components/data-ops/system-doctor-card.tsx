import * as React from 'react'
import { useTranslation } from 'react-i18next'
import { StethoscopeIcon, RefreshCwIcon, CheckCircle2Icon, AlertTriangleIcon, DatabaseIcon } from 'lucide-react'
import { Card } from '#/components/ui/card'
import { Button } from '#/components/ui/button'
import { Badge } from '#/components/ui/badge'
import { ovClient } from '#/lib/ov-client'

interface DbResult {
  name: string
  path: string
  exists: boolean
  passed: boolean
  quick_check: string[] | null
  fts5_tables: string[]
  fts5_rebuilt: string[]
  error?: string | null
}

interface DoctorReport {
  status: 'healthy' | 'warning'
  total_databases: number
  passed_databases: number
  fts5_rebuilt_count: number
  duration_ms: number
  databases: DbResult[]
}

export function SystemDoctorCard() {
  const { t } = useTranslation('settings')
  const [report, setReport] = React.useState<DoctorReport | null>(null)
  const [loading, setLoading] = React.useState(false)
  const [running, setRunning] = React.useState(false)

  const fetchHealth = React.useCallback(async () => {
    try {
      setLoading(true)
      const res = await ovClient.instance.get<DoctorReport>('/api/v1/rsi/bootstrap/health')
      if (res.data) setReport(res.data)
    } catch (err) {
      console.error('[SystemDoctorCard] Failed to fetch health report:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  React.useEffect(() => { void fetchHealth() }, [fetchHealth])

  const handleRunDoctor = async () => {
    try {
      setRunning(true)
      const res = await ovClient.instance.post<DoctorReport>('/api/v1/rsi/bootstrap/health/run')
      if (res.data) setReport(res.data)
    } catch (err) {
      console.error('[SystemDoctorCard] Health check failed:', err)
    } finally {
      setRunning(false)
    }
  }

  const isHealthy = report?.status === 'healthy' || (report?.total_databases ?? 0) === (report?.passed_databases ?? 0)
  const totalDbs = report?.total_databases ?? 0
  const passedDbs = report?.passed_databases ?? 0
  const rebuiltCount = report?.fts5_rebuilt_count ?? 0
  const durationMs = report?.duration_ms ?? 0
  const dbs = report?.databases ?? []

  return (
    <Card className="flex flex-col gap-3 p-3.5 shadow-none border border-border/60 transition-colors hover:border-primary/40">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/40 pb-2.5">
        <div className="flex items-center gap-2">
          <DatabaseIcon className="size-4 text-muted-foreground" />
          <span className="text-xs font-semibold tracking-wide text-foreground">
            {t('hub.dataOps.doctorTitle')}
          </span>
          <Badge
            variant="outline"
            className={`h-5 px-1.5 text-xs font-mono tabular-nums rounded-md ${
              isHealthy
                ? 'border-cyan-500/40 text-cyan-500 bg-cyan-500/5'
                : 'border-amber-400/40 text-amber-400 bg-amber-400/5'
            }`}
          >
            {isHealthy ? t('hub.dataOps.healthStatusHealthy') : t('hub.dataOps.healthStatusWarning')}
          </Badge>
        </div>

        <div className="flex items-center gap-1.5">
          <Button
            size="sm"
            variant="outline"
            disabled={running || loading}
            onClick={() => { void fetchHealth() }}
            className="h-6 px-2 text-xs font-mono"
            title={t('actions.refresh')}
          >
            <RefreshCwIcon className={`size-3 ${loading ? 'animate-spin' : ''}`} />
          </Button>

          <Button
            size="sm"
            variant="outline"
            disabled={running || loading}
            onClick={() => { void handleRunDoctor() }}
            className="h-6 px-2 text-xs font-mono text-cyan-500 border-cyan-500/30 hover:bg-cyan-500/10"
          >
            <StethoscopeIcon className={`mr-1 size-3 ${running ? 'animate-spin' : ''}`} />
            {running ? t('hub.dataOps.doctorRunning') : t('hub.dataOps.btnRunDoctor')}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <div className="flex flex-col gap-0.5 rounded-md border border-border/40 bg-muted/10 p-2">
          <span className="text-xs text-muted-foreground">{t('hub.dataOps.passedDbs')}</span>
          <span className={`font-mono text-base font-bold tabular-nums ${isHealthy ? 'text-cyan-500' : 'text-amber-400'}`}>
            {passedDbs} / {totalDbs}
          </span>
          <span className="text-xs text-muted-foreground font-mono">{t('hub.dataOps.dbsCount')}</span>
        </div>

        <div className="flex flex-col gap-0.5 rounded-md border border-border/40 bg-muted/10 p-2">
          <span className="text-xs text-muted-foreground">{t('hub.dataOps.fts5Rebuilt')}</span>
          <span className="font-mono text-base font-bold tabular-nums text-foreground">
            {rebuiltCount}
          </span>
          <span className="text-xs text-muted-foreground">{t('hub.dataOps.timesCount')}</span>
        </div>

        <div className="flex flex-col gap-0.5 rounded-md border border-border/40 bg-muted/10 p-2">
          <span className="text-xs text-muted-foreground">{t('hub.dataOps.durationMs')}</span>
          <span className="font-mono text-base font-bold tabular-nums text-foreground">
            {durationMs.toFixed(1)}ms
          </span>
          <span className="text-xs text-muted-foreground font-mono">SQLite PRAGMA</span>
        </div>

        <div className="flex flex-col gap-0.5 rounded-md border border-border/40 bg-muted/10 p-2">
          <span className="text-xs text-muted-foreground">{t('hub.dataOps.integrity')}</span>
          <span className="font-mono text-base font-bold tabular-nums text-cyan-500">
            {isHealthy ? '100.0%' : `${((passedDbs / Math.max(1, totalDbs)) * 100).toFixed(1)}%`}
          </span>
          <span className="text-xs text-muted-foreground">{t('hub.dataOps.integrityOk')}</span>
        </div>
      </div>

      {dbs.length > 0 && (
        <div className="flex flex-col gap-1.5 border-t border-border/40 pt-2">
          <span className="text-xs font-medium text-muted-foreground">{t('hub.dataOps.dbDetailsTitle')}</span>
          <div className="flex flex-col gap-1 max-h-36 overflow-y-auto pr-0.5">
            {dbs.map((db, idx) => (
              <div
                key={db.path || idx}
                className="flex items-center justify-between text-xs font-mono bg-muted/20 px-2 py-1.5 rounded border border-border/40"
              >
                <div className="flex items-center gap-1.5 truncate max-w-xs">
                  {db.passed ? (
                    <CheckCircle2Icon className="size-3 text-cyan-500 shrink-0" />
                  ) : (
                    <AlertTriangleIcon className="size-3 text-amber-400 shrink-0" />
                  )}
                  <span className="truncate font-medium text-foreground">{db.name}</span>
                </div>
                <div className="flex items-center gap-2 text-muted-foreground">
                  {db.fts5_tables.length > 0 && (
                    <span className="px-1 rounded bg-muted/40 border border-border/40 text-xs">
                      FTS5: {db.fts5_tables.length}
                    </span>
                  )}
                  <span className={db.passed ? 'text-cyan-500' : 'text-amber-400'}>
                    {db.passed ? t('hub.dataOps.statusPassed') : t('hub.dataOps.statusFailed')}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  )
}
