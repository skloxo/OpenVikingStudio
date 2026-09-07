import * as React from 'react'
import {
  Loader2Icon,
  RotateCcwIcon,
  UploadIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '#/components/ui/card'
import {
  Field,
  FieldContent,
  FieldLabel,
} from '#/components/ui/field'
import { Input } from '#/components/ui/input'
import { ovClient } from '#/lib/ov-client'

export function ImportRestoreCard() {
  const { i18n, t } = useTranslation('settings')
  const isZh = i18n.resolvedLanguage?.startsWith('zh')

  const [selectedPackFile, setSelectedPackFile] = React.useState<File | null>(null)
  const [importParentUri, setImportParentUri] = React.useState('viking://')
  const [onConflict, setOnConflict] = React.useState<'fail' | 'overwrite' | 'skip'>('overwrite')
  const [vectorMode, setVectorMode] = React.useState<'auto' | 'recompute' | 'require'>('auto')
  const [isImporting, setIsImporting] = React.useState(false)
  const [isRestoring, setIsRestoring] = React.useState(false)

  const uploadTempPackFile = async (file: File): Promise<string> => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('telemetry', 'true')
    const uploadRes = await ovClient.instance.post<{
      status: string
      result: { temp_file_id: string }
    }>('/api/v1/resources/temp_upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return uploadRes.data.result.temp_file_id
  }

  const handleImport = async () => {
    if (!selectedPackFile) {
      toast.error(
        isZh ? '请先选择 .ovpack 归档文件' : 'Please select an .ovpack file first',
      )
      return
    }
    setIsImporting(true)
    try {
      const tempFileId = await uploadTempPackFile(selectedPackFile)
      const importRes = await ovClient.instance.post<{
        status: string
        result: { uri: string }
      }>('/api/v1/pack/import', {
        temp_file_id: tempFileId,
        parent: importParentUri.trim() || 'viking://',
        on_conflict: onConflict,
        vector_mode: vectorMode,
      })
      toast.success(
        t('hub.dataOps.successImport', {
          uri: importRes.data.result?.uri || importParentUri,
        }),
      )
      setSelectedPackFile(null)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Import failed'
      toast.error(msg)
    } finally {
      setIsImporting(false)
    }
  }

  const handleRestore = async () => {
    if (!selectedPackFile) {
      toast.error(
        isZh ? '请先选择备份归档文件' : 'Please select a backup file first',
      )
      return
    }
    if (!window.confirm(t('hub.dataOps.restoreConfirm'))) {
      return
    }
    setIsRestoring(true)
    try {
      const tempFileId = await uploadTempPackFile(selectedPackFile)
      await ovClient.instance.post('/api/v1/pack/restore', {
        temp_file_id: tempFileId,
        on_conflict: onConflict,
        vector_mode: vectorMode,
      })
      toast.success(t('hub.dataOps.successRestore'))
      setSelectedPackFile(null)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Restore failed'
      toast.error(msg)
    } finally {
      setIsRestoring(false)
    }
  }

  return (
    <Card className="gap-0 overflow-hidden border-border/80 bg-card py-0 shadow-sm">
      <CardHeader className="gap-2 border-b border-border/60 bg-muted/20 px-5 py-3.5">
        <div className="flex items-center gap-2">
          <div className="flex size-7 items-center justify-center rounded-md bg-cyan-500/10 text-cyan-500 border border-cyan-500/30">
            <UploadIcon className="size-4" />
          </div>
          <div>
            <CardTitle className="text-sm font-semibold">
              {t('hub.dataOps.importTitle')}
            </CardTitle>
            <p className="text-[11px] text-muted-foreground">
              {t('hub.dataOps.importDesc')}
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="grid gap-3 px-5 py-4">
        {/* File Selector */}
        <div className="space-y-1">
          <span className="text-xs font-medium text-foreground">
            {t('hub.dataOps.selectPackLabel')}
          </span>
          <div className="flex items-center gap-2">
            <Input
              type="file"
              accept=".ovpack,.zip"
              onChange={(e) => {
                const file = e.target.files?.[0] || null
                setSelectedPackFile(file)
              }}
              className="h-8 text-xs cursor-pointer file:text-xs file:font-medium"
            />
            {selectedPackFile && (
              <Badge
                variant="outline"
                className="text-[11px] font-mono shrink-0 border-cyan-500/30 bg-cyan-500/10 text-cyan-500"
              >
                {(selectedPackFile.size / 1024).toFixed(1)} KB
              </Badge>
            )}
          </div>
        </div>

        {/* Mount Parent URI */}
        <Field>
          <FieldLabel htmlFor="import-parent-uri" className="text-xs">
            {t('hub.dataOps.parentUriLabel')}
          </FieldLabel>
          <FieldContent>
            <Input
              id="import-parent-uri"
              value={importParentUri}
              onChange={(e) => setImportParentUri(e.target.value)}
              placeholder="viking://"
              className="h-8 text-xs font-mono"
            />
          </FieldContent>
        </Field>

        {/* Strategy Selectors */}
        <div className="grid gap-3 sm:grid-cols-2 pt-1">
          <div className="space-y-1">
            <span className="text-xs font-medium text-foreground">
              {t('hub.dataOps.conflictPolicy')}
            </span>
            <select
              value={onConflict}
              onChange={(e) =>
                setOnConflict(e.target.value as 'fail' | 'overwrite' | 'skip')
              }
              className="h-8 w-full rounded-md border border-input bg-transparent px-2 text-xs font-medium outline-none focus:border-ring"
            >
              <option value="overwrite" className="bg-background text-foreground">
                {t('hub.dataOps.conflictOverwrite')}
              </option>
              <option value="skip" className="bg-background text-foreground">
                {t('hub.dataOps.conflictSkip')}
              </option>
              <option value="fail" className="bg-background text-foreground">
                {t('hub.dataOps.conflictFail')}
              </option>
            </select>
          </div>

          <div className="space-y-1">
            <span className="text-xs font-medium text-foreground">
              {t('hub.dataOps.vectorMode')}
            </span>
            <select
              value={vectorMode}
              onChange={(e) =>
                setVectorMode(
                  e.target.value as 'auto' | 'recompute' | 'require',
                )
              }
              className="h-8 w-full rounded-md border border-input bg-transparent px-2 text-xs font-medium outline-none focus:border-ring"
            >
              <option value="auto" className="bg-background text-foreground">
                {t('hub.dataOps.vectorAuto')}
              </option>
              <option value="recompute" className="bg-background text-foreground">
                {t('hub.dataOps.vectorRecompute')}
              </option>
              <option value="require" className="bg-background text-foreground">
                {t('hub.dataOps.vectorRequire')}
              </option>
            </select>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-3 pt-3">
          <Button
            onClick={handleImport}
            disabled={isImporting || isRestoring || !selectedPackFile}
            size="sm"
            className="h-8 gap-1.5 text-xs font-medium bg-cyan-600 hover:bg-cyan-700 text-white cursor-pointer"
          >
            {isImporting ? (
              <>
                <Loader2Icon className="size-3.5 animate-spin" />
                <span>{t('hub.dataOps.importing')}</span>
              </>
            ) : (
              <>
                <UploadIcon className="size-3.5" />
                <span>{t('hub.dataOps.importBtn')}</span>
              </>
            )}
          </Button>

          <Button
            onClick={handleRestore}
            disabled={isImporting || isRestoring || !selectedPackFile}
            size="sm"
            variant="outline"
            className="h-8 gap-1.5 text-xs font-medium border-rose-500/40 text-rose-500 hover:bg-rose-500/10 cursor-pointer"
          >
            {isRestoring ? (
              <>
                <Loader2Icon className="size-3.5 animate-spin" />
                <span>{t('hub.dataOps.restoring')}</span>
              </>
            ) : (
              <>
                <RotateCcwIcon className="size-3.5" />
                <span>{t('hub.dataOps.restoreBtn')}</span>
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
