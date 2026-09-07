import * as React from 'react'
import {
  DownloadIcon,
  FileArchiveIcon,
  Loader2Icon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { Button } from '#/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '#/components/ui/card'
import { Checkbox } from '#/components/ui/checkbox'
import {
  Field,
  FieldContent,
  FieldLabel,
} from '#/components/ui/field'
import { Input } from '#/components/ui/input'
import { ovClient } from '#/lib/ov-client'

export function ExportBackupCard() {
  const { t } = useTranslation('settings')

  const [exportUri, setExportUri] = React.useState('viking://resources/')
  const [exportIncludeVectors, setExportIncludeVectors] = React.useState(false)
  const [isExporting, setIsExporting] = React.useState(false)
  const [isBackingUp, setIsBackingUp] = React.useState(false)

  const handleExport = async () => {
    setIsExporting(true)
    try {
      const response = await ovClient.instance.post(
        '/api/v1/pack/export',
        {
          uri: exportUri.trim() || 'viking://',
          include_vectors: exportIncludeVectors,
        },
        { responseType: 'blob' },
      )
      const blob = new Blob([response.data as BlobPart], {
        type: 'application/zip',
      })
      const downloadUrl = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = downloadUrl
      const baseName =
        exportUri
          .trim()
          .replace(/^viking:\/\/?/, '')
          .replace(/\//g, '_') || 'export'
      a.download = `${baseName}.ovpack`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(downloadUrl)
      toast.success(t('hub.dataOps.successExport'))
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Export failed'
      toast.error(msg)
    } finally {
      setIsExporting(false)
    }
  }

  const handleBackup = async () => {
    setIsBackingUp(true)
    try {
      const response = await ovClient.instance.post(
        '/api/v1/pack/backup',
        { include_vectors: false },
        { responseType: 'blob' },
      )
      const blob = new Blob([response.data as BlobPart], {
        type: 'application/zip',
      })
      const downloadUrl = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = downloadUrl
      a.download = 'openviking-backup.ovpack'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(downloadUrl)
      toast.success(t('hub.dataOps.successBackup'))
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Backup failed'
      toast.error(msg)
    } finally {
      setIsBackingUp(false)
    }
  }

  return (
    <>
      {/* Section 1: Export OVPack Card */}
      <Card className="gap-0 overflow-hidden border-border/80 bg-card py-0 shadow-sm">
        <CardHeader className="gap-2 border-b border-border/60 bg-muted/20 px-5 py-3.5">
          <div className="flex items-center gap-2">
            <div className="flex size-7 items-center justify-center rounded-md bg-cyan-500/10 text-cyan-500 border border-cyan-500/30">
              <DownloadIcon className="size-4" />
            </div>
            <div>
              <CardTitle className="text-sm font-semibold">
                {t('hub.dataOps.exportTitle')}
              </CardTitle>
              <p className="text-[11px] text-muted-foreground">
                {t('hub.dataOps.exportDesc')}
              </p>
            </div>
          </div>
        </CardHeader>
        <CardContent className="grid gap-3 px-5 py-4">
          <Field>
            <div className="flex items-center justify-between">
              <FieldLabel htmlFor="export-target-uri" className="text-xs">
                {t('hub.dataOps.targetUriLabel')}
              </FieldLabel>
              <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                <span>{t('hub.dataOps.quickScopes')}</span>
                <button
                  type="button"
                  onClick={() => setExportUri('viking://resources/')}
                  className="text-cyan-500 hover:underline cursor-pointer font-mono"
                >
                  viking://resources/
                </button>
                <span>·</span>
                <button
                  type="button"
                  onClick={() =>
                    setExportUri('viking://resources/master_memory/')
                  }
                  className="text-cyan-500 hover:underline cursor-pointer font-mono"
                >
                  master_memory
                </button>
              </div>
            </div>
            <FieldContent>
              <Input
                id="export-target-uri"
                value={exportUri}
                onChange={(e) => setExportUri(e.target.value)}
                placeholder={t('hub.dataOps.targetUriPlaceholder')}
                className="h-8 text-xs font-mono"
              />
            </FieldContent>
          </Field>

          <div className="flex items-center gap-2 pt-1">
            <Checkbox
              id="include-vectors-checkbox"
              checked={exportIncludeVectors}
              onCheckedChange={(val) => setExportIncludeVectors(Boolean(val))}
            />
            <label
              htmlFor="include-vectors-checkbox"
              className="text-xs text-foreground cursor-pointer select-none"
            >
              {t('hub.dataOps.includeVectors')}
            </label>
            <span className="text-[11px] text-muted-foreground">
              ({t('hub.dataOps.includeVectorsHint')})
            </span>
          </div>

          <div className="pt-2">
            <Button
              onClick={handleExport}
              disabled={isExporting || !exportUri.trim()}
              size="sm"
              className="h-8 gap-1.5 text-xs font-medium bg-cyan-600 hover:bg-cyan-700 text-white cursor-pointer"
            >
              {isExporting ? (
                <>
                  <Loader2Icon className="size-3.5 animate-spin" />
                  <span>{t('hub.dataOps.exporting')}</span>
                </>
              ) : (
                <>
                  <DownloadIcon className="size-3.5" />
                  <span>{t('hub.dataOps.exportBtn')}</span>
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Section 2: Full System Backup Card */}
      <Card className="gap-0 overflow-hidden border-border/80 bg-card py-0 shadow-sm">
        <CardHeader className="gap-2 border-b border-border/60 bg-muted/20 px-5 py-3.5">
          <div className="flex items-center gap-2">
            <div className="flex size-7 items-center justify-center rounded-md bg-cyan-500/10 text-cyan-500 border border-cyan-500/30">
              <FileArchiveIcon className="size-4" />
            </div>
            <div>
              <CardTitle className="text-sm font-semibold">
                {t('hub.dataOps.backupTitle')}
              </CardTitle>
              <p className="text-[11px] text-muted-foreground">
                {t('hub.dataOps.backupDesc')}
              </p>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
          <div className="text-xs text-muted-foreground max-w-lg">
            一键对全域公开作用域执行快照打包，输出标准全量容灾归档{' '}
            <span className="font-mono text-foreground">
              openviking-backup.ovpack
            </span>
            ，供灾备冷存或跨宿主机完整还原。
          </div>
          <Button
            onClick={handleBackup}
            disabled={isBackingUp}
            size="sm"
            variant="outline"
            className="h-8 gap-1.5 text-xs font-medium border-border/80 hover:border-cyan-500/50 hover:bg-cyan-500/5 cursor-pointer"
          >
            {isBackingUp ? (
              <>
                <Loader2Icon className="size-3.5 animate-spin" />
                <span>{t('hub.dataOps.backingUp')}</span>
              </>
            ) : (
              <>
                <DownloadIcon className="size-3.5 text-cyan-500" />
                <span>{t('hub.dataOps.backupBtn')}</span>
              </>
            )}
          </Button>
        </CardContent>
      </Card>
    </>
  )
}
