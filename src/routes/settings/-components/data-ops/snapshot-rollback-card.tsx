import * as React from 'react'
import {
  ClockIcon,
  GitCommitIcon,
  HistoryIcon,
  Loader2Icon,
  RotateCcwIcon,
  RotateCwIcon,
  ShieldCheckIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '#/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '#/components/ui/dialog'
import { Input } from '#/components/ui/input'
import { ovClient } from '#/lib/ov-client'

interface SnapshotEntry {
  oid: string
  message: string
  author_name?: string
  author_email?: string
  timestamp?: string | number
  created_at?: string
}

export function SnapshotRollbackCard() {
  const { t } = useTranslation('settings')
  const [snapshots, setSnapshots] = React.useState<SnapshotEntry[]>([])
  const [loading, setLoading] = React.useState(false)
  const [commitMessage, setCommitMessage] = React.useState('')
  const [committing, setCommitting] = React.useState(false)

  // Rollback dialog state
  const [rollbackTarget, setRollbackTarget] = React.useState<SnapshotEntry | null>(null)
  const [restoring, setRestoring] = React.useState(false)

  const fetchSnapshots = React.useCallback(async () => {
    setLoading(true)
    try {
      const response = await ovClient.instance.get('/api/v1/snapshot/log', {
        params: { branch: 'main', limit: 10 },
      })
      const list = response.data?.result || []
      setSnapshots(Array.isArray(list) ? list : [])
    } catch {
      // Branch may be fresh or without snapshots yet
      setSnapshots([])
    } finally {
      setLoading(false)
    }
  }, [])

  React.useEffect(() => {
    fetchSnapshots()
  }, [fetchSnapshots])

  const handleCreateSnapshot = async (e: React.FormEvent) => {
    e.preventDefault()
    const msg = commitMessage.trim() || `Manual Snapshot ${new Date().toLocaleTimeString()}`
    setCommitting(true)
    try {
      const response = await ovClient.instance.post('/api/v1/snapshot/commit', {
        message: msg,
        branch: 'main',
      })
      const oid = response.data?.result?.commit_oid || ''
      const shortOid = oid ? oid.slice(0, 8) : 'HEAD'
      toast.success(`[${shortOid}] ${msg}`)
      setCommitMessage('')
      await fetchSnapshots()
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Create snapshot failed'
      toast.error(errorMsg)
    } finally {
      setCommitting(false)
    }
  }

  const handleExecuteRestore = async () => {
    if (!rollbackTarget) return
    setRestoring(true)
    try {
      await ovClient.instance.post('/api/v1/snapshot/restore', {
        source_commit: rollbackTarget.oid,
        branch: 'main',
        message: `Restore to [${rollbackTarget.oid.slice(0, 8)}]`,
      })
      toast.success(`Restored to ${rollbackTarget.oid.slice(0, 8)}`)
      setRollbackTarget(null)
      await fetchSnapshots()
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Restore failed'
      toast.error(errorMsg)
    } finally {
      setRestoring(false)
    }
  }

  const latestOid = snapshots[0]?.oid ? snapshots[0].oid.slice(0, 8) : '--'
  const totalSnapshots = snapshots.length

  return (
    <>
      <Card className="border-border/60 bg-card/60">
        <CardHeader className="p-3.5 pb-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex size-7 items-center justify-center rounded-md border border-cyan-500/20 bg-cyan-950/20 text-cyan-400">
                <HistoryIcon className="size-4" />
              </div>
              <div>
                <CardTitle className="text-sm font-semibold tracking-tight text-foreground">
                  {t('hub.dataOps.snapshotTitle')}
                </CardTitle>
                <p className="text-xs text-muted-foreground">
                  {t('hub.dataOps.snapshotDesc')}
                </p>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchSnapshots}
              disabled={loading}
              className="h-7 text-xs"
            >
              <RotateCwIcon className={`size-3.5 mr-1 ${loading ? 'animate-spin' : ''}`} />
              {t('actions.refresh')}
            </Button>
          </div>
        </CardHeader>

        <CardContent className="space-y-3.5 p-3.5 pt-1">
          {/* Status Indicator Tiles */}
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            <div className="flex items-center justify-between rounded-md border border-border/40 bg-muted/20 p-2.5">
              <span className="text-xs text-muted-foreground">{t('hub.dataOps.currentHead')}</span>
              <span className="font-mono text-xs font-semibold text-cyan-400">{latestOid}</span>
            </div>
            <div className="flex items-center justify-between rounded-md border border-border/40 bg-muted/20 p-2.5">
              <span className="text-xs text-muted-foreground">{t('hub.dataOps.totalSnapshots')}</span>
              <span className="font-mono text-xs font-semibold text-foreground">{totalSnapshots}</span>
            </div>
            <div className="flex items-center justify-between rounded-md border border-border/40 bg-muted/20 p-2.5">
              <span className="text-xs text-muted-foreground">{t('hub.dataOps.integrity')}</span>
              <div className="flex items-center gap-1 text-xs text-cyan-400">
                <ShieldCheckIcon className="size-3.5" />
                <span>{t('hub.dataOps.integrityOk')}</span>
              </div>
            </div>
          </div>

          {/* Quick Create Snapshot Bar */}
          <form onSubmit={handleCreateSnapshot} className="flex gap-2">
            <Input
              value={commitMessage}
              onChange={(e) => setCommitMessage(e.target.value)}
              placeholder={t('hub.dataOps.commitPlaceholder')}
              className="h-8 text-xs"
              disabled={committing}
            />
            <Button
              type="submit"
              size="sm"
              disabled={committing}
              className="h-8 whitespace-nowrap bg-cyan-900/60 text-xs text-cyan-200 hover:bg-cyan-800/80 border border-cyan-500/30"
            >
              {committing ? (
                <Loader2Icon className="size-3.5 mr-1 animate-spin" />
              ) : (
                <GitCommitIcon className="size-3.5 mr-1" />
              )}
              {t('hub.dataOps.createSnapshotBtn')}
            </Button>
          </form>

          {/* Snapshots Timeline List */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
              <span>{t('hub.dataOps.recentRecords')}</span>
              <span>{t('hub.dataOps.actions')}</span>
            </div>

            {loading && snapshots.length === 0 ? (
              <div className="flex items-center justify-center p-6 text-xs text-muted-foreground">
                <Loader2Icon className="size-4 animate-spin mr-2" />
                {t('hub.dataOps.loadingSnapshots')}
              </div>
            ) : snapshots.length === 0 ? (
              <div className="rounded-md border border-dashed border-border/60 p-4 text-center text-xs text-muted-foreground">
                {t('hub.dataOps.noSnapshots')}
              </div>
            ) : (
              <div className="divide-y divide-border/30 rounded-md border border-border/40 bg-muted/10">
                {snapshots.map((item, idx) => {
                  const shortHash = item.oid ? item.oid.slice(0, 8) : 'HEAD'
                  const isHead = idx === 0
                  return (
                    <div
                      key={item.oid || idx}
                      className="flex items-center justify-between p-2.5 text-xs hover:bg-muted/30 transition-colors"
                    >
                      <div className="flex items-center gap-2 min-w-0 pr-2">
                        <Badge
                          variant="outline"
                          className={`font-mono text-xs ${
                            isHead
                              ? 'border-cyan-500/40 bg-cyan-950/30 text-cyan-400'
                              : 'text-muted-foreground border-border/60'
                          }`}
                        >
                          {shortHash}
                        </Badge>
                        <span className="truncate font-medium text-foreground">
                          {item.message}
                        </span>
                        {item.author_name && (
                          <span className="text-muted-foreground hidden sm:inline">
                            · {item.author_name}
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-1.5 shrink-0">
                        {isHead ? (
                          <Badge variant="secondary" className="text-xs text-cyan-400 border border-cyan-500/30">
                            {t('hub.dataOps.currentHeadBadge')}
                          </Badge>
                        ) : (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setRollbackTarget(item)}
                            className="h-6 px-2 text-xs text-amber-400 hover:text-amber-300 hover:bg-amber-950/30 border-amber-500/30"
                          >
                            <RotateCcwIcon className="size-3 mr-1" />
                            {t('hub.dataOps.rollbackToBtn')}
                          </Button>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Rollback Confirmation Modal */}
      <Dialog open={!!rollbackTarget} onOpenChange={(open) => !open && setRollbackTarget(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-sm text-amber-400">
              <ClockIcon className="size-4" />
              {t('hub.dataOps.rollbackModalTitle')}
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              {t('hub.dataOps.rollbackModalDesc')}
              <span className="font-mono text-foreground font-semibold ml-1">
                {rollbackTarget?.oid ? rollbackTarget.oid.slice(0, 8) : ''}
              </span>
              <br />
              {rollbackTarget?.message}
            </DialogDescription>
          </DialogHeader>

          <div className="rounded-md border border-amber-500/20 bg-amber-950/20 p-3 text-xs text-amber-300/90 leading-relaxed">
            {t('hub.dataOps.rollbackModalWarning')}
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setRollbackTarget(null)}
              disabled={restoring}
              className="text-xs"
            >
              {t('hub.dataOps.cancelBtn')}
            </Button>
            <Button
              size="sm"
              onClick={handleExecuteRestore}
              disabled={restoring}
              className="text-xs bg-amber-900/60 text-amber-200 hover:bg-amber-800/80 border border-amber-500/30"
            >
              {restoring ? (
                <Loader2Icon className="size-3.5 mr-1 animate-spin" />
              ) : (
                <RotateCcwIcon className="size-3.5 mr-1" />
              )}
              {t('hub.dataOps.confirmRollbackBtn')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

