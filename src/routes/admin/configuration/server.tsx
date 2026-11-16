import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import {
  AlertTriangleIcon,
  Loader2Icon,
  RefreshCwIcon,
  RotateCwIcon,
  SaveIcon,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Textarea } from '#/components/ui/textarea'
import { useAppConnection } from '#/hooks/use-app-connection'
import { showErrorToast } from '#/lib/error-toast'
import { ModelProbeCard } from '../-components/model-probe-card'
import {
  fetchServerConfigFile,
  isConfigFileObject,
  saveServerConfigFile,
  triggerServerRestart,
  waitForServerRestart,
} from '../-lib/config-api'

export const Route = createFileRoute('/admin/configuration/server')({
  component: ServerConfigurationPage,
})

function ServerConfigurationPage() {
  const { t } = useTranslation('adminConsole')
  const { connection, connectionRole, identityScopeKey, serverMode } =
    useAppConnection()
  const queryClient = useQueryClient()
  const isRoot = connectionRole === 'root' || serverMode === 'trusted'

  const connInput = {
    accountId: connection.accountId,
    adminApiKey: connection.adminApiKey,
    apiKey: connection.apiKey,
  }

  const query = useQuery({
    queryKey: ['admin-server-config-file', identityScopeKey],
    queryFn: ({ signal }) => fetchServerConfigFile(connInput, signal),
    enabled: isRoot,
    retry: false,
  })

  const [draftContent, setDraftContent] = useState('')
  const [dirty, setDirty] = useState(false)
  const [restarting, setRestarting] = useState(false)

  useEffect(() => {
    if (!query.data || dirty) return
    setDraftContent(query.data.content || '')
  }, [query.data, dirty])

  const saveMutation = useMutation({
    mutationFn: () => {
      if (!isConfigFileObject(draftContent)) {
        throw new Error('ov.conf must contain a valid JSON object')
      }
      if (!query.data?.revision) throw new Error('Missing configuration revision')
      return saveServerConfigFile(connInput, draftContent, query.data.revision)
    },
    onSuccess: async () => {
      setDirty(false)
      toast.success(t('configuration.configSaved'))
      await queryClient.invalidateQueries({
        queryKey: ['admin-server-config-file', identityScopeKey],
      })
    },
    onError: (err) => showErrorToast(err),
  })

  const handleRestart = async () => {
    if (!query.data?.revision || !query.data?.restart?.supported) return
    if (!window.confirm(t('configuration.confirmRestart'))) return
    const controller = new AbortController()
    setRestarting(true)
    try {
      const status = await triggerServerRestart(connInput, query.data.revision)
      await waitForServerRestart(
        () => fetchServerConfigFile(connInput, controller.signal),
        status.instance_id,
        controller.signal,
      )
      toast.success(t('configuration.restartSuccess'))
      await queryClient.invalidateQueries({
        queryKey: ['admin-server-config-file', identityScopeKey],
      })
    } catch (err) {
      showErrorToast(err)
    } finally {
      setRestarting(false)
    }
  }

  if (!isRoot) {
    return <p className="text-sm text-rose-500">{t('rootRequired')}</p>
  }

  const cfg = query.data
  const overrideList = [
    ...(cfg?.overrides?.cluster || []),
    ...(cfg?.overrides?.account || []),
  ]

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <h2 className="text-lg font-semibold">
            {t('configuration.serverTitle')}
          </h2>
          <p className="text-xs text-muted-foreground">
            {t('configuration.serverSubtitle')}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={query.isFetching || restarting}
            onClick={() => {
              setDirty(false)
              void query.refetch()
            }}
          >
            <RefreshCwIcon />
            {t('actions.refresh')}
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={!cfg?.restart?.supported || restarting}
            onClick={() => void handleRestart()}
          >
            {restarting ? (
              <Loader2Icon className="animate-spin" />
            ) : (
              <RotateCwIcon />
            )}
            {t(restarting ? 'actions.restarting' : 'actions.restart')}
          </Button>
          <Button
            type="button"
            size="sm"
            disabled={!dirty || saveMutation.isPending || cfg?.writable === false}
            onClick={() => saveMutation.mutate()}
          >
            {saveMutation.isPending ? (
              <Loader2Icon className="animate-spin" />
            ) : (
              <SaveIcon />
            )}
            {t(saveMutation.isPending ? 'actions.saving' : 'actions.save')}
          </Button>
        </div>
      </div>

      {cfg && (
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {cfg.file_path && (
            <Badge variant="outline" className="font-mono">
              {t('configuration.filePath', { path: cfg.file_path })}
            </Badge>
          )}
          <Badge variant="outline" className="font-mono">
            {t('configuration.revision', { rev: cfg.revision.slice(0, 12) })}
          </Badge>
          <Badge
            variant="outline"
            className={
              cfg.restart?.supported
                ? 'border-cyan-500/40 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400'
                : 'text-muted-foreground'
            }
          >
            {t(
              cfg.restart?.supported
                ? 'configuration.restartSupported'
                : 'configuration.restartUnsupported',
            )}
          </Badge>
          {cfg.restart_required && (
            <Badge className="gap-1 bg-amber-500/15 text-amber-600 dark:text-amber-400">
              <AlertTriangleIcon className="size-3" />
              {t('configuration.restartRequired')}
            </Badge>
          )}
        </div>
      )}

      {overrideList.length > 0 && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-2.5 text-xs text-amber-700 dark:text-amber-300">
          {t('configuration.overrideWarning', {
            scopes: [...new Set(overrideList)].join(', '),
          })}
        </div>
      )}

      {query.isLoading ? (
        <div className="flex items-center gap-2 py-8 text-xs text-muted-foreground">
          <Loader2Icon className="size-4 animate-spin text-cyan-500" />
          Loading...
        </div>
      ) : (
        <>
          <div className="space-y-2 rounded-xl border bg-card p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium">{t('configuration.jsonMode')}</span>
            </div>
            <Textarea
              rows={16}
              value={draftContent}
              readOnly={cfg?.writable === false}
              onChange={(e) => {
                setDraftContent(e.target.value)
                setDirty(true)
              }}
              className="font-mono text-xs leading-relaxed"
            />
          </div>

          <ModelProbeCard
            initialVlm={cfg?.models?.vlm?.config}
            initialEmbedding={cfg?.models?.embedding?.config}
          />
        </>
      )}
    </div>
  )
}
