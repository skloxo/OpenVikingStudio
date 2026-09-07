import * as React from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import {
  CircleAlertIcon,
  CircleDashedIcon,
  CircleHelpIcon,
  CpuIcon,
  DownloadIcon,
  ExternalLinkIcon,
  EyeIcon,
  FileArchiveIcon,
  FolderTreeIcon,
  KeyRoundIcon,
  Loader2Icon,
  PackageIcon,
  PlayIcon,
  RotateCcwIcon,
  ShieldAlertIcon,
  ShieldCheckIcon,
  ShieldIcon,
  SlidersHorizontalIcon,
  TriangleAlertIcon,
  UploadIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { Alert, AlertDescription, AlertTitle } from '#/components/ui/alert'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '#/components/ui/card'
import { Checkbox } from '#/components/ui/checkbox'
import {
  Field,
  FieldContent,
  FieldDescription,
  FieldLabel,
} from '#/components/ui/field'
import { Input } from '#/components/ui/input'
import { Switch } from '#/components/ui/switch'
import { Textarea } from '#/components/ui/textarea'
import { useAppConnection } from '#/hooks/use-app-connection'
import { probeStudioConnection } from '#/lib/admin'
import type { CapabilityProbeResult } from '#/lib/admin'
import { DEFAULT_ACCOUNT_ID, DEFAULT_USER_ID } from '#/lib/admin-options'
import { PLAIN_INPUT_PROPS } from '#/lib/form-input'
import { ovClient } from '#/lib/ov-client'
import { cn } from '#/lib/utils'
import type { ConnectionDraft } from '#/hooks/use-app-connection'

export const Route = createFileRoute('/settings')({
  component: UnifiedSettingsRoute,
})

type SettingsTab = 'general' | 'privacy' | 'dataOps'

function getCapabilityIcon(result: CapabilityProbeResult | undefined) {
  if (!result) {
    return <CircleDashedIcon className="size-4" />
  }
  if (result.state === 'ok') {
    return <ShieldCheckIcon className="size-4" />
  }
  if (result.state === 'error') {
    return <CircleAlertIcon className="size-4" />
  }
  return <CircleDashedIcon className="size-4" />
}

function CapabilityStatus({
  isLoading,
  label,
  result,
}: {
  isLoading: boolean
  label: string
  result: CapabilityProbeResult | undefined
}) {
  const { t } = useTranslation('settings')
  const state = isLoading ? 'checking' : result?.state || 'skipped'

  return (
    <div
      className={cn(
        'flex min-w-0 items-start gap-2 rounded-md border bg-background/70 px-3 py-2 text-sm',
        state === 'ok' && 'border-cyan-500/35 text-cyan-500',
        state === 'error' && 'border-destructive/35 text-destructive',
      )}
    >
      <div className={cn('mt-0.5', isLoading && 'animate-spin')}>
        {getCapabilityIcon(result)}
      </div>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span className="font-medium text-xs">{label}</span>
          <span className="text-[11px] text-muted-foreground">
            {t(`health.state.${state}`)}
          </span>
        </div>
        {result?.detail ? (
          <p className="mt-1 truncate text-[11px] text-muted-foreground">
            {result.detail}
          </p>
        ) : null}
      </div>
    </div>
  )
}

function UserApiKeyInput({
  accountId,
  id,
  onChange,
  placeholder,
  userId,
  value,
}: {
  accountId: string
  id: string
  onChange: (value: string) => void
  placeholder: string
  userId: string
  value: string
}) {
  const hasIdentity = Boolean(accountId.trim() && userId.trim())
  const identity = hasIdentity ? `${accountId}/${userId}` : '未选择身份'

  return (
    <div className="flex h-9 w-full min-w-0 items-center gap-2 rounded-md border border-input bg-transparent bg-clip-padding px-2.5 shadow-xs transition-[color,box-shadow] focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50 dark:bg-input/30">
      <span className="shrink-0 rounded-sm bg-muted px-2 py-0.5 font-mono text-[11px] text-muted-foreground">
        [{identity}]
      </span>
      <input
        id={id}
        type="password"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="h-full min-w-0 flex-1 bg-transparent text-xs outline-none placeholder:text-muted-foreground"
        {...PLAIN_INPUT_PROPS}
      />
    </div>
  )
}

function applyClientRedaction(text: string, options: { maskCredentials: boolean; maskPii: boolean }): string {
  let out = text
  if (options.maskCredentials) {
    out = out.replace(/\b(sk-[a-zA-Z0-9]{4})[a-zA-Z0-9]{12,}([a-zA-Z0-9]{4})\b/g, '$1****$2')
    out = out.replace(/\b(Bearer\s+)[a-zA-Z0-9._-]{10,}\b/g, '$1[REDACTED_TOKEN]')
    out = out.replace(/(api[_-]?key\s*[:=]\s*["']?)[a-zA-Z0-9._-]{8,}(["']?)/gi, '$1[REDACTED_KEY]$2')
  }
  if (options.maskPii) {
    out = out.replace(/\b([a-zA-Z0-9._%+-]{1,2})[a-zA-Z0-9._%+-]*@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b/g, '$1***@$2')
    out = out.replace(/\b(1[3-9]\d)\d{4}(\d{4})\b/g, '$1****$2')
    out = out.replace(/\b(\d{1,3}\.)\d{1,3}\.\d{1,3}(\.\d{1,3})\b/g, '$1***.***$2')
  }
  return out
}

interface ParsedModelItem {
  model: string
  provider: string
  calls: string
  totalTokens: string
  lastUpdated: string
}

interface ParsedObserverModels {
  vlm: ParsedModelItem[]
  embedding: ParsedModelItem[]
  rerank: ParsedModelItem[]
  compressor: ParsedModelItem[]
}

function parseSectionTable(sectionText: string): ParsedModelItem[] {
  const lines = sectionText.split('\n')
  const results: ParsedModelItem[] = []
  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed.startsWith('|') || !trimmed.endsWith('|')) continue
    const parts = trimmed
      .split('|')
      .map((p) => p.trim())
      .filter((p) => p.length > 0)
    if (parts.length < 5) continue
    if (
      parts[0].toLowerCase() === 'model' ||
      parts[1]?.toLowerCase() === 'provider'
    ) {
      continue
    }
    results.push({
      model: parts[0],
      provider: parts[1] || '--',
      calls: parts[2] || '0',
      totalTokens: parts[5] || parts[parts.length - 2] || '--',
      lastUpdated: parts[parts.length - 1] || '--',
    })
  }
  return results
}

function parseObserverModelsTable(statusText?: string | null): ParsedObserverModels {
  if (!statusText) {
    return { vlm: [], embedding: [], rerank: [], compressor: [] }
  }
  const extractSection = (heading: string, nextHeadings: string[]) => {
    const startIdx = statusText.indexOf(heading)
    if (startIdx === -1) return ''
    let endIdx = statusText.length
    for (const nh of nextHeadings) {
      const idx = statusText.indexOf(nh, startIdx + heading.length)
      if (idx !== -1 && idx < endIdx) {
        endIdx = idx
      }
    }
    return statusText.slice(startIdx + heading.length, endIdx)
  }

  return {
    vlm: parseSectionTable(
      extractSection('VLM Models:', [
        'Embedding Models:',
        'Rerank Models:',
        'Compressor Models:',
      ]),
    ),
    embedding: parseSectionTable(
      extractSection('Embedding Models:', [
        'Rerank Models:',
        'Compressor Models:',
      ]),
    ),
    rerank: parseSectionTable(
      extractSection('Rerank Models:', ['Compressor Models:']),
    ),
    compressor: parseSectionTable(extractSection('Compressor Models:', [])),
  }
}

function ModelTile({
  item,
  title,
  showTokens = true,
}: {
  item: ParsedModelItem | undefined
  title: string
  showTokens?: boolean
}) {
  const { t } = useTranslation('settings')
  return (
    <div className="flex flex-col rounded-md border bg-muted/20 p-3 space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
          {title}
        </span>
        <Badge
          variant="outline"
          className={cn(
            'px-1.5 py-0 text-[11px]',
            item
              ? 'border-cyan-500/30 bg-cyan-500/10 text-cyan-500'
              : 'border-border text-muted-foreground',
          )}
        >
          {item ? 'Ready' : '--'}
        </Badge>
      </div>
      <div
        className="font-mono text-xs font-semibold text-foreground truncate"
        title={item?.model || '--'}
      >
        {item?.model || '--'}
      </div>
      <div className="text-[11px] text-muted-foreground">
        {t('hub.models.provider')}:{' '}
        <span className="font-mono text-foreground">
          {item?.provider || '--'}
        </span>
      </div>
      <div className="text-[11px] text-muted-foreground/80 font-mono tabular-nums truncate">
        {item
          ? showTokens
            ? `${t('hub.models.calls')}: ${Number(item.calls).toLocaleString()} · ${t('hub.models.tokens')}: ${Number(item.totalTokens).toLocaleString()}`
            : `${t('hub.models.calls')}: ${Number(item.calls).toLocaleString()}`
          : t('hub.models.noActiveModel')}
      </div>
    </div>
  )
}

function UnifiedSettingsRoute() {
  const { i18n, t } = useTranslation('settings')
  const isZh = i18n.resolvedLanguage?.startsWith('zh')
  const [activeTab, setActiveTab] = React.useState<SettingsTab>('general')

  // Connection State
  const { connection, saveConnection, serverMode } = useAppConnection()
  const [draft, setDraft] = React.useState<ConnectionDraft>(connection)
  const pendingDraftRef = React.useRef<ConnectionDraft | null>(null)
  const saveTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null)
  const saveConnectionRef = React.useRef(saveConnection)

  React.useEffect(() => {
    saveConnectionRef.current = saveConnection
  }, [saveConnection])

  React.useEffect(() => {
    if (!pendingDraftRef.current) {
      setDraft(connection)
    }
  }, [connection])

  React.useEffect(() => {
    return () => {
      if (saveTimerRef.current) {
        clearTimeout(saveTimerRef.current)
      }
      if (pendingDraftRef.current) {
        saveConnectionRef.current(pendingDraftRef.current)
      }
    }
  }, [])

  function updateDraft(next: Partial<ConnectionDraft>): void {
    const updated = { ...draft, ...next }
    setDraft(updated)
    pendingDraftRef.current = updated
    if (saveTimerRef.current) {
      clearTimeout(saveTimerRef.current)
    }
    saveTimerRef.current = setTimeout(() => {
      saveTimerRef.current = null
      const pending = pendingDraftRef.current
      pendingDraftRef.current = null
      if (pending) {
        saveConnectionRef.current(pending)
      }
    }, 350)
  }

  const probeQuery = useQuery({
    enabled: Boolean(draft.baseUrl) && serverMode !== 'checking',
    placeholderData: keepPreviousData,
    queryFn: () =>
      probeStudioConnection({
        accountId: draft.accountId || DEFAULT_ACCOUNT_ID,
        adminApiKey: draft.adminApiKey,
        apiKey: draft.apiKey,
        baseUrl: draft.baseUrl,
        serverMode,
        userId: draft.userId || DEFAULT_USER_ID,
      }),
    queryKey: [
      'studio-connection-probe',
      draft.baseUrl,
      draft.adminApiKey,
      draft.apiKey,
      draft.accountId,
      draft.userId,
      serverMode,
    ],
    retry: false,
    staleTime: 5_000,
  })

  // Tab 1 Observer Models Query
  const modelsQuery = useQuery({
    enabled: activeTab === 'general' && Boolean(draft.baseUrl),
    queryFn: async () => {
      try {
        const res = await ovClient.instance.get<{
          status: string
          result?: {
            name: string
            is_healthy: boolean
            status: string
          }
        }>('/api/v1/observer/models')
        return res.data?.result ?? null
      } catch {
        return null
      }
    },
    queryKey: ['system-observer-models', draft.baseUrl, draft.adminApiKey, draft.apiKey],
    staleTime: 15_000,
  })

  const parsedModels = React.useMemo(
    () => parseObserverModelsTable(modelsQuery.data?.status),
    [modelsQuery.data?.status],
  )

  const activeVlm =
    parsedModels.vlm.find((m) => m.model === 'qwen3.8-flash-next') ||
    parsedModels.vlm.find((m) => Number(m.calls) > 0) ||
    parsedModels.vlm[0]

  const activeEmbedding =
    parsedModels.embedding.find((m) => Number(m.calls) > 0) ||
    parsedModels.embedding[0]

  const activeRerank =
    parsedModels.rerank.find((m) => Number(m.calls) > 0) ||
    parsedModels.rerank[0]

  const activeCompressor = parsedModels.compressor[0]

  // Tab 1 Workspace Ingest Target Query
  const workspaceQuery = useQuery({
    enabled: activeTab === 'general' && Boolean(draft.baseUrl),
    queryFn: async () => {
      try {
        const res = await ovClient.instance.get<{
          status: string
          result?: {
            effective?: {
              resource_uri?: string
              skill_uri?: string
            }
          }
        }>('/api/v1/user-settings/add-locations')
        return res.data?.result ?? null
      } catch {
        return null
      }
    },
    queryKey: ['user-settings-add-locations', draft.baseUrl, draft.adminApiKey, draft.apiKey],
    staleTime: 30_000,
  })

  // Tab 2: Privacy states
  const [maskCredentials, setMaskCredentials] = React.useState(true)
  const [maskPii, setMaskPii] = React.useState(true)
  const DEFAULT_SAMPLE_TEXT =
    'Authorization: Bearer sk-99887766aabbccddeeff001122, contact: fsk@8.129.0.26, phone: +86-13800138000, client_ip: 192.168.1.100'
  const [sampleInput, setSampleInput] = React.useState(DEFAULT_SAMPLE_TEXT)
  const [sanitizedPreview, setSanitizedPreview] = React.useState(() =>
    applyClientRedaction(DEFAULT_SAMPLE_TEXT, { maskCredentials: true, maskPii: true }),
  )

  const handlePreviewRedaction = () => {
    const result = applyClientRedaction(sampleInput, { maskCredentials, maskPii })
    setSanitizedPreview(result)
    toast.success(isZh ? '脱敏预览已更新' : 'Sanitized preview updated')
  }

  // Tab 3: OVPack Data Ops states
  const [exportUri, setExportUri] = React.useState('viking://resources/')
  const [exportIncludeVectors, setExportIncludeVectors] = React.useState(false)
  const [isExporting, setIsExporting] = React.useState(false)

  const [isBackingUp, setIsBackingUp] = React.useState(false)

  const [selectedPackFile, setSelectedPackFile] = React.useState<File | null>(null)
  const [importParentUri, setImportParentUri] = React.useState('viking://')
  const [onConflict, setOnConflict] = React.useState<'fail' | 'overwrite' | 'skip'>('overwrite')
  const [vectorMode, setVectorMode] = React.useState<'auto' | 'recompute' | 'require'>('auto')
  const [isImporting, setIsImporting] = React.useState(false)
  const [isRestoring, setIsRestoring] = React.useState(false)

  const handleExport = async () => {
    setIsExporting(true)
    try {
      const response = await ovClient.instance.post(
        '/api/v1/pack/export',
        { uri: exportUri.trim() || 'viking://', include_vectors: exportIncludeVectors },
        { responseType: 'blob' },
      )
      const blob = new Blob([response.data as BlobPart], { type: 'application/zip' })
      const downloadUrl = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = downloadUrl
      const baseName = exportUri.trim().replace(/^viking:\/\/?/, '').replace(/\//g, '_') || 'export'
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
      const blob = new Blob([response.data as BlobPart], { type: 'application/zip' })
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
      toast.error(isZh ? '请先选择 .ovpack 归档文件' : 'Please select an .ovpack file first')
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
      toast.success(t('hub.dataOps.successImport', { uri: importRes.data.result?.uri || importParentUri }))
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
      toast.error(isZh ? '请先选择备份归档文件' : 'Please select a backup file first')
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

  const isDevMode = serverMode === 'dev'
  const isUnsupportedAuthMode = serverMode === 'oidc' || serverMode === 'ldap'
  const rootApiKey = connection.adminApiKey.trim()
  const hasControlCredential = Boolean(draft.adminApiKey.trim())
  const hasDataCredential = Boolean(draft.apiKey.trim())
  const adminProbe = probeQuery.data?.admin
  const dataProbe = probeQuery.data?.data
  const hasAdminAccess = !isDevMode && adminProbe?.state === 'ok'
  const authenticationGuideUrl = isZh
    ? 'https://docs.openviking.ai/zh/guides/04-authentication'
    : 'https://docs.openviking.ai/en/guides/04-authentication'

  const trustedCredentialRequired =
    serverMode === 'trusted' &&
    !probeQuery.isFetching &&
    !hasControlCredential &&
    (adminProbe?.state === 'error' || dataProbe?.state === 'error')

  const keyGuide =
    serverMode === 'trusted'
      ? trustedCredentialRequired
        ? {
            primary: t('connection.keyGuide.trusted.primary'),
            secondary: t('connection.keyGuide.trusted.secondary'),
            title: t('connection.keyGuide.trusted.title'),
          }
        : null
      : !hasControlCredential && !hasDataCredential
        ? {
            primary: t('connection.keyGuide.empty.primary'),
            secondary: t('connection.keyGuide.empty.secondary'),
            title: t('connection.keyGuide.empty.title'),
          }
        : !hasControlCredential
          ? {
              primary: t('connection.keyGuide.control.primary'),
              secondary: t('connection.keyGuide.control.secondary'),
              title: t('connection.keyGuide.control.title'),
            }
          : !hasDataCredential
            ? {
                primary: t('connection.keyGuide.data.primary'),
                secondary: t('connection.keyGuide.data.secondary'),
                title: t('connection.keyGuide.data.title'),
              }
            : null

  return (
    <div className="flex w-full min-w-0 flex-col gap-5">
      {/* Top Header */}
      <header className="flex flex-col gap-1">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold tracking-tight">
              {t('hub.title')}
            </h1>
          </div>
          <Badge variant="outline" className="text-[11px] font-normal border-border/80">
            {t(`serverMode.${serverMode}`)}
          </Badge>
        </div>
        <p className="max-w-3xl text-xs leading-5 text-muted-foreground">
          {t('hub.description')}
        </p>
      </header>

      {/* 3-Tab Pill Switcher */}
      <div className="flex items-center gap-1.5 bg-muted/40 p-1 rounded-lg border border-border/60 w-fit">
        <button
          type="button"
          onClick={() => setActiveTab('general')}
          className={cn(
            'flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all cursor-pointer select-none',
            activeTab === 'general'
              ? 'bg-background text-foreground shadow-2xs font-semibold'
              : 'text-muted-foreground hover:text-foreground',
          )}
        >
          <SlidersHorizontalIcon className="size-3.5 text-cyan-500" />
          <span>{t('hub.tabs.general')}</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('privacy')}
          className={cn(
            'flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all cursor-pointer select-none',
            activeTab === 'privacy'
              ? 'bg-background text-foreground shadow-2xs font-semibold'
              : 'text-muted-foreground hover:text-foreground',
          )}
        >
          <ShieldAlertIcon className="size-3.5 text-amber-500" />
          <span>{t('hub.tabs.privacy')}</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('dataOps')}
          className={cn(
            'flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all cursor-pointer select-none',
            activeTab === 'dataOps'
              ? 'bg-background text-foreground shadow-2xs font-semibold'
              : 'text-muted-foreground hover:text-foreground',
          )}
        >
          <PackageIcon className="size-3.5 text-cyan-500" />
          <span>{t('hub.tabs.dataOps')}</span>
        </button>
      </div>

      {/* Tab 1: General & Models */}
      {activeTab === 'general' && (
        <div className="space-y-4">
          {/* Section 1: Connection & Credentials Card */}
          <Card className="gap-0 overflow-hidden border-border/80 bg-card py-0 shadow-sm">
            <CardHeader className="gap-2 border-b border-border/60 bg-muted/20 px-5 py-3.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex min-w-0 items-center gap-2">
                  <div className="flex size-7 items-center justify-center rounded-md bg-cyan-500/10 text-cyan-500 border border-cyan-500/30">
                    <KeyRoundIcon className="size-4" />
                  </div>
                  <div>
                    <CardTitle className="text-sm font-semibold">{t('connection.title')}</CardTitle>
                    <p className="text-[11px] text-muted-foreground">{t('connectionPage.description')}</p>
                  </div>
                </div>

                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={probeQuery.isFetching || modelsQuery.isFetching}
                  onClick={() => {
                    void probeQuery.refetch()
                    void modelsQuery.refetch()
                    void workspaceQuery.refetch()
                    toast.info(t('connection.rechecking'))
                  }}
                  className="h-7 rounded px-2.5 text-xs gap-1.5 cursor-pointer font-sans"
                >
                  <RotateCcwIcon
                    className={cn(
                      'size-3',
                      (probeQuery.isFetching || modelsQuery.isFetching) &&
                        'animate-spin text-cyan-500',
                    )}
                  />
                  <span>{t('connection.recheck')}</span>
                </Button>
              </div>
            </CardHeader>
            <CardContent className="grid gap-4 px-5 py-4">
              <Field>
                <FieldLabel htmlFor="settings-base-url" className="text-xs">
                  {t('fields.baseUrl')}
                </FieldLabel>
                <FieldContent>
                  <Input
                    id="settings-base-url"
                    value={draft.baseUrl}
                    onChange={(event) => updateDraft({ baseUrl: event.target.value })}
                    placeholder={t('placeholders.baseUrl')}
                    inputMode="url"
                    className="h-8 text-xs font-mono"
                    {...PLAIN_INPUT_PROPS}
                  />
                </FieldContent>
              </Field>

              {isDevMode ? (
                <p className="rounded-md border border-dashed bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
                  {t('connection.devMode')}
                </p>
              ) : isUnsupportedAuthMode ? (
                <Alert variant="destructive" className="border-destructive/50">
                  <TriangleAlertIcon className="size-4" />
                  <AlertTitle className="text-xs">{t('connection.unsupportedAuthMode.title')}</AlertTitle>
                  <AlertDescription className="grid gap-1.5 text-xs">
                    <p>{t('connection.unsupportedAuthMode.primary', { mode: serverMode })}</p>
                    <p>{t('connection.unsupportedAuthMode.description', { mode: serverMode, ov: 'ov' })}</p>
                    <a
                      href={authenticationGuideUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-1 inline-flex w-fit items-center gap-1 font-medium text-foreground underline underline-offset-2"
                    >
                      {t('connection.keyGuide.learnMore')}
                      <ExternalLinkIcon className="size-3.5" />
                    </a>
                  </AlertDescription>
                </Alert>
              ) : (
                <>
                  <div className="grid gap-4 md:grid-cols-2">
                    <Field>
                      <FieldLabel htmlFor="settings-root-api-key" className="text-xs">
                        {t('fields.rootApiKey')}
                      </FieldLabel>
                      <FieldContent>
                        <Input
                          id="settings-root-api-key"
                          type="password"
                          value={draft.adminApiKey}
                          onChange={(event) => updateDraft({ adminApiKey: event.target.value })}
                          placeholder={t('placeholders.adminApiKey')}
                          className="h-8 text-xs font-mono"
                          {...PLAIN_INPUT_PROPS}
                        />
                        <FieldDescription className="text-[11px]">
                          {t('connection.rootHint')}
                        </FieldDescription>
                      </FieldContent>
                    </Field>
                    <Field>
                      <FieldLabel htmlFor="settings-user-api-key" className="text-xs">
                        {t('fields.userApiKey')}
                      </FieldLabel>
                      <FieldContent>
                        <UserApiKeyInput
                          accountId={draft.accountId}
                          id="settings-user-api-key"
                          userId={draft.userId}
                          value={draft.apiKey}
                          onChange={(apiKey) => updateDraft({ apiKey })}
                          placeholder={t('placeholders.userApiKey')}
                        />
                        <FieldDescription className="text-[11px]">
                          {t('connection.userHint')}
                        </FieldDescription>
                      </FieldContent>
                    </Field>
                  </div>

                  <div className="grid gap-2 md:grid-cols-2">
                    <CapabilityStatus
                      isLoading={probeQuery.isFetching}
                      label={t('health.admin')}
                      result={adminProbe}
                    />
                    <CapabilityStatus
                      isLoading={probeQuery.isFetching}
                      label={t('health.data')}
                      result={dataProbe}
                    />
                  </div>

                  {(serverMode === 'api_key' || serverMode === 'trusted') && keyGuide ? (
                    <Alert className="border-cyan-500/25 bg-cyan-500/[0.04]">
                      <CircleHelpIcon className="text-cyan-500 size-4" />
                      <AlertTitle className="text-xs">{keyGuide.title}</AlertTitle>
                      <AlertDescription className="grid gap-1 text-xs text-pretty [&_p:not(:last-child)]:mb-0">
                        <p>{keyGuide.primary}</p>
                        <p className="text-muted-foreground">{keyGuide.secondary}</p>
                        <a
                          href={authenticationGuideUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-1 inline-flex w-fit items-center gap-1 font-medium text-foreground text-xs"
                        >
                          {t('connection.keyGuide.learnMore')}
                          <ExternalLinkIcon className="size-3" />
                        </a>
                      </AlertDescription>
                    </Alert>
                  ) : null}

                  {!hasAdminAccess && rootApiKey && adminProbe?.state === 'error' ? (
                    <p className="text-xs text-destructive">
                      {t('connection.adminError', { message: adminProbe.detail || '' })}
                    </p>
                  ) : null}
                </>
              )}
            </CardContent>
          </Card>

          {/* Section 2: Models & Vector Endpoints Card */}
          <Card className="gap-0 overflow-hidden border-border/80 bg-card py-0 shadow-sm">
            <CardHeader className="gap-2 border-b border-border/60 bg-muted/20 px-5 py-3.5">
              <div className="flex items-center gap-2">
                <div className="flex size-7 items-center justify-center rounded-md bg-cyan-500/10 text-cyan-500 border border-cyan-500/30">
                  <CpuIcon className="size-4" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold">{t('hub.models.title')}</CardTitle>
                  <p className="text-[11px] text-muted-foreground">{t('hub.models.description')}</p>
                </div>
              </div>
            </CardHeader>
            <CardContent className="grid gap-3 px-5 py-4 sm:grid-cols-2 lg:grid-cols-4">
              <ModelTile title={t('hub.models.vlm')} item={activeVlm} />
              <ModelTile title={t('hub.models.embedding')} item={activeEmbedding} />
              <ModelTile title={t('hub.models.rerank')} item={activeRerank} />
              <ModelTile title={t('hub.models.compressor')} item={activeCompressor} showTokens={false} />
            </CardContent>
          </Card>

          {/* Section 3: Workspace & Storage Card */}
          <Card className="gap-0 overflow-hidden border-border/80 bg-card py-0 shadow-sm">
            <CardHeader className="gap-2 border-b border-border/60 bg-muted/20 px-5 py-3.5">
              <div className="flex items-center gap-2">
                <div className="flex size-7 items-center justify-center rounded-md bg-cyan-500/10 text-cyan-500 border border-cyan-500/30">
                  <FolderTreeIcon className="size-4" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold">{t('hub.workspace.title')}</CardTitle>
                  <p className="text-[11px] text-muted-foreground">{t('hub.workspace.description')}</p>
                </div>
              </div>
            </CardHeader>
            <CardContent className="grid gap-3 px-5 py-4 sm:grid-cols-3">
              <div className="flex flex-col rounded-md border bg-muted/20 p-3 space-y-1">
                <span className="text-[11px] text-muted-foreground font-medium">{t('hub.workspace.rootUri')}</span>
                <span className="font-mono text-xs font-bold text-foreground">viking://</span>
                <span className="text-[11px] text-muted-foreground">AGFS Root Mount</span>
              </div>
              <div className="flex flex-col rounded-md border bg-muted/20 p-3 space-y-1">
                <span className="text-[11px] text-muted-foreground font-medium">{t('hub.workspace.defaultResourceTarget')}</span>
                <span className="font-mono text-xs font-bold text-foreground">
                  {workspaceQuery.data?.effective?.resource_uri || 'viking://resources/'}
                </span>
                <span className="text-[11px] text-muted-foreground">Auto Ingest Namespace</span>
              </div>
              <div className="flex flex-col rounded-md border bg-muted/20 p-3 space-y-1">
                <span className="text-[11px] text-muted-foreground font-medium">{t('hub.workspace.defaultSkillTarget')}</span>
                <span className="font-mono text-xs font-bold text-foreground">
                  {workspaceQuery.data?.effective?.skill_uri || 'viking://skills/'}
                </span>
                <span className="text-[11px] text-muted-foreground">Skill Protocol Storage</span>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab 2: Privacy & Redaction */}
      {activeTab === 'privacy' && (
        <div className="space-y-4">
          {/* Section 1: Governance & Switches */}
          <Card className="gap-0 overflow-hidden border-border/80 bg-card py-0 shadow-sm">
            <CardHeader className="gap-2 border-b border-border/60 bg-muted/20 px-5 py-3.5">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <div className="flex size-7 items-center justify-center rounded-md bg-amber-500/10 text-amber-500 border border-amber-500/30">
                    <ShieldIcon className="size-4" />
                  </div>
                  <div>
                    <CardTitle className="text-sm font-semibold">{t('hub.privacy.title')}</CardTitle>
                    <p className="text-[11px] text-muted-foreground">{t('hub.privacy.description')}</p>
                  </div>
                </div>
                <Badge variant="outline" className="text-[11px] font-mono border-amber-500/30 bg-amber-500/10 text-amber-500">
                  {t('hub.privacy.activeRules')}: 5
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="grid gap-4 px-5 py-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="flex items-center justify-between rounded-md border bg-muted/20 p-3">
                  <div className="space-y-0.5 pr-2">
                    <div className="text-xs font-semibold text-foreground">{t('hub.privacy.toggleMask')}</div>
                    <div className="text-[11px] text-muted-foreground">{t('hub.privacy.toggleMaskDesc')}</div>
                  </div>
                  <Switch checked={maskCredentials} onCheckedChange={setMaskCredentials} />
                </div>
                <div className="flex items-center justify-between rounded-md border bg-muted/20 p-3">
                  <div className="space-y-0.5 pr-2">
                    <div className="text-xs font-semibold text-foreground">{t('hub.privacy.piiMask')}</div>
                    <div className="text-[11px] text-muted-foreground">{t('hub.privacy.piiMaskDesc')}</div>
                  </div>
                  <Switch checked={maskPii} onCheckedChange={setMaskPii} />
                </div>
              </div>

              {/* Redaction Rules Table */}
              <div className="rounded-md border border-border/80 overflow-hidden mt-2">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b bg-muted/30 text-[11px] text-muted-foreground font-medium">
                      <th className="py-2 px-3">{t('hub.privacy.ruleName')}</th>
                      <th className="py-2 px-3">{t('hub.privacy.rulePattern')}</th>
                      <th className="py-2 px-3">{t('hub.privacy.ruleAction')}</th>
                      <th className="py-2 px-3 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/50 font-mono text-[11px]">
                    <tr>
                      <td className="py-2 px-3 font-sans font-medium text-foreground">API Key / Token</td>
                      <td className="py-2 px-3 text-muted-foreground">sk-[a-zA-Z0-9]{'{20,}'}</td>
                      <td className="py-2 px-3 font-sans text-cyan-500">{t('hub.privacy.actionMask')}</td>
                      <td className="py-2 px-3 text-center">
                        <Badge variant="outline" className="px-1.5 py-0 text-[11px] border-cyan-500/30 text-cyan-500">Active</Badge>
                      </td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-sans font-medium text-foreground">Bearer Auth</td>
                      <td className="py-2 px-3 text-muted-foreground">Bearer\s+[a-zA-Z0-9._-]+</td>
                      <td className="py-2 px-3 font-sans text-amber-500">{t('hub.privacy.actionRedact')}</td>
                      <td className="py-2 px-3 text-center">
                        <Badge variant="outline" className="px-1.5 py-0 text-[11px] border-cyan-500/30 text-cyan-500">Active</Badge>
                      </td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-sans font-medium text-foreground">Phone Number (CN/Intl)</td>
                      <td className="py-2 px-3 text-muted-foreground">\+?[0-9]{'{10,14}'}</td>
                      <td className="py-2 px-3 font-sans text-cyan-500">{t('hub.privacy.actionMask')}</td>
                      <td className="py-2 px-3 text-center">
                        <Badge variant="outline" className="px-1.5 py-0 text-[11px] border-cyan-500/30 text-cyan-500">Active</Badge>
                      </td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-sans font-medium text-foreground">Email Address</td>
                      <td className="py-2 px-3 text-muted-foreground">[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+</td>
                      <td className="py-2 px-3 font-sans text-cyan-500">{t('hub.privacy.actionMask')}</td>
                      <td className="py-2 px-3 text-center">
                        <Badge variant="outline" className="px-1.5 py-0 text-[11px] border-cyan-500/30 text-cyan-500">Active</Badge>
                      </td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-sans font-medium text-foreground">IPv4 / Private Address</td>
                      <td className="py-2 px-3 text-muted-foreground">\b(?:[0-9]{'{1,3}'}\.){'{3}'}[0-9]{'{1,3}'}\b</td>
                      <td className="py-2 px-3 font-sans text-cyan-500">{t('hub.privacy.actionMask')}</td>
                      <td className="py-2 px-3 text-center">
                        <Badge variant="outline" className="px-1.5 py-0 text-[11px] border-cyan-500/30 text-cyan-500">Active</Badge>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Section 2: Live Playground & Audit */}
          <Card className="gap-0 overflow-hidden border-border/80 bg-card py-0 shadow-sm">
            <CardHeader className="gap-2 border-b border-border/60 bg-muted/20 px-5 py-3.5">
              <div className="flex items-center gap-2">
                <div className="flex size-7 items-center justify-center rounded-md bg-cyan-500/10 text-cyan-500 border border-cyan-500/30">
                  <EyeIcon className="size-4" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold">{t('hub.privacy.playgroundTitle')}</CardTitle>
                  <p className="text-[11px] text-muted-foreground">{t('hub.privacy.playgroundDesc')}</p>
                </div>
              </div>
            </CardHeader>
            <CardContent className="grid gap-4 px-5 py-4">
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-foreground">{t('hub.privacy.inputLabel')}</span>
                  <Button
                    onClick={handlePreviewRedaction}
                    size="sm"
                    className="h-7 text-xs font-medium bg-cyan-600 hover:bg-cyan-700 text-white cursor-pointer"
                  >
                    <PlayIcon className="size-3 fill-current mr-1" />
                    <span>{t('hub.privacy.previewBtn')}</span>
                  </Button>
                </div>
                <Textarea
                  value={sampleInput}
                  onChange={(e) => setSampleInput(e.target.value)}
                  placeholder={t('hub.privacy.inputPlaceholder')}
                  rows={3}
                  className="text-xs font-mono"
                />
              </div>

              <div className="space-y-1.5">
                <span className="text-xs font-medium text-foreground">{t('hub.privacy.previewOutput')}</span>
                <div className="rounded-md border border-border/80 bg-muted/20 p-3 font-mono text-xs text-foreground select-all break-all whitespace-pre-wrap">
                  {sanitizedPreview}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab 3: OVPack Data Ops */}
      {activeTab === 'dataOps' && (
        <div className="space-y-4">
          {/* Section 1: Export OVPack Card */}
          <Card className="gap-0 overflow-hidden border-border/80 bg-card py-0 shadow-sm">
            <CardHeader className="gap-2 border-b border-border/60 bg-muted/20 px-5 py-3.5">
              <div className="flex items-center gap-2">
                <div className="flex size-7 items-center justify-center rounded-md bg-cyan-500/10 text-cyan-500 border border-cyan-500/30">
                  <DownloadIcon className="size-4" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold">{t('hub.dataOps.exportTitle')}</CardTitle>
                  <p className="text-[11px] text-muted-foreground">{t('hub.dataOps.exportDesc')}</p>
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
                      onClick={() => setExportUri('viking://resources/master_memory/')}
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

          {/* Section 2: Full System Backup */}
          <Card className="gap-0 overflow-hidden border-border/80 bg-card py-0 shadow-sm">
            <CardHeader className="gap-2 border-b border-border/60 bg-muted/20 px-5 py-3.5">
              <div className="flex items-center gap-2">
                <div className="flex size-7 items-center justify-center rounded-md bg-cyan-500/10 text-cyan-500 border border-cyan-500/30">
                  <FileArchiveIcon className="size-4" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold">{t('hub.dataOps.backupTitle')}</CardTitle>
                  <p className="text-[11px] text-muted-foreground">{t('hub.dataOps.backupDesc')}</p>
                </div>
              </div>
            </CardHeader>
            <CardContent className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
              <div className="text-xs text-muted-foreground max-w-lg">
                一键对全域公开作用域执行快照打包，输出标准全量容灾归档 <span className="font-mono text-foreground">openviking-backup.ovpack</span>，供灾备冷存或跨宿主机完整还原。
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

          {/* Section 3: Import & Restore Card */}
          <Card className="gap-0 overflow-hidden border-border/80 bg-card py-0 shadow-sm">
            <CardHeader className="gap-2 border-b border-border/60 bg-muted/20 px-5 py-3.5">
              <div className="flex items-center gap-2">
                <div className="flex size-7 items-center justify-center rounded-md bg-cyan-500/10 text-cyan-500 border border-cyan-500/30">
                  <UploadIcon className="size-4" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold">{t('hub.dataOps.importTitle')}</CardTitle>
                  <p className="text-[11px] text-muted-foreground">{t('hub.dataOps.importDesc')}</p>
                </div>
              </div>
            </CardHeader>
            <CardContent className="grid gap-3 px-5 py-4">
              {/* File Selector */}
              <div className="space-y-1">
                <span className="text-xs font-medium text-foreground">{t('hub.dataOps.selectPackLabel')}</span>
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
                    <Badge variant="outline" className="text-[11px] font-mono shrink-0 border-cyan-500/30 bg-cyan-500/10 text-cyan-500">
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
                  <span className="text-xs font-medium text-foreground">{t('hub.dataOps.conflictPolicy')}</span>
                  <select
                    value={onConflict}
                    onChange={(e) => setOnConflict(e.target.value as 'fail' | 'overwrite' | 'skip')}
                    className="h-8 w-full rounded-md border border-input bg-transparent px-2 text-xs font-medium outline-none focus:border-ring"
                  >
                    <option value="overwrite" className="bg-background text-foreground">{t('hub.dataOps.conflictOverwrite')}</option>
                    <option value="skip" className="bg-background text-foreground">{t('hub.dataOps.conflictSkip')}</option>
                    <option value="fail" className="bg-background text-foreground">{t('hub.dataOps.conflictFail')}</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <span className="text-xs font-medium text-foreground">{t('hub.dataOps.vectorMode')}</span>
                  <select
                    value={vectorMode}
                    onChange={(e) => setVectorMode(e.target.value as 'auto' | 'recompute' | 'require')}
                    className="h-8 w-full rounded-md border border-input bg-transparent px-2 text-xs font-medium outline-none focus:border-ring"
                  >
                    <option value="auto" className="bg-background text-foreground">{t('hub.dataOps.vectorAuto')}</option>
                    <option value="recompute" className="bg-background text-foreground">{t('hub.dataOps.vectorRecompute')}</option>
                    <option value="require" className="bg-background text-foreground">{t('hub.dataOps.vectorRequire')}</option>
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
        </div>
      )}
    </div>
  )
}
