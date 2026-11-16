import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { Loader2Icon, ShieldIcon, SparklesIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '#/components/ui/card'
import { Switch } from '#/components/ui/switch'
import { useAppConnection } from '#/hooks/use-app-connection'
import { showErrorToast } from '#/lib/error-toast'
import {
  fetchAccountConfiguration,
  patchAccountConfiguration,
} from '../-lib/config-api'

export const Route = createFileRoute('/admin/configuration/')({
  component: AccountConfigurationPage,
})

function AccountConfigurationPage() {
  const { t } = useTranslation('adminConsole')
  const { connection, connectionRole, identityScopeKey, serverMode } =
    useAppConnection()
  const queryClient = useQueryClient()

  const canManage =
    connectionRole === 'root' ||
    connectionRole === 'admin' ||
    serverMode === 'trusted'
  const connInput = {
    accountId: connection.accountId,
    adminApiKey: connection.adminApiKey,
    apiKey: connection.apiKey,
  }

  const query = useQuery({
    queryKey: ['admin-account-config', identityScopeKey, connection.accountId],
    queryFn: ({ signal }) => fetchAccountConfiguration(connInput, signal),
    enabled: canManage && Boolean(connection.accountId),
  })

  const mutation = useMutation({
    mutationFn: (patch: Record<string, unknown>) => {
      if (query.data && query.data.accountId !== connection.accountId) {
        throw new Error(t('configuration.scopeMismatch'))
      }
      return patchAccountConfiguration(connInput, patch)
    },
    onSuccess: (next) => {
      queryClient.setQueryData(
        ['admin-account-config', identityScopeKey, connection.accountId],
        next,
      )
      toast.success(t('configuration.toggleSuccess'))
    },
    onError: (err) => {
      showErrorToast(err)
    },
  })

  if (!canManage) {
    return <p className="text-sm text-rose-500">{t('adminOrRootRequired')}</p>
  }

  const evolutionEnabled = Boolean(query.data?.settings?.agent_evolution?.enabled)
  const aclEnabled = query.data?.settings?.acl?.enabled

  return (
    <div className="max-w-3xl space-y-5">
      <div>
        <h2 className="text-lg font-semibold">{t('configuration.accountTitle')}</h2>
        <p className="text-xs text-muted-foreground">
          {t('configuration.accountSubtitle', { account: connection.accountId })}
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <SparklesIcon className="size-4 text-cyan-500" />
            {t('configuration.evolutionLabel')}
          </CardTitle>
          <CardDescription className="text-xs">
            {t('configuration.evolutionHint')}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            {query.isLoading ? (
              <Loader2Icon className="size-4 animate-spin text-cyan-500" />
            ) : (
              <Badge
                variant="outline"
                className={
                  evolutionEnabled
                    ? 'border-cyan-500/40 bg-cyan-500/15 text-xs text-cyan-600 dark:text-cyan-400'
                    : 'text-xs text-muted-foreground'
                }
              >
                {t(
                  evolutionEnabled
                    ? 'configuration.evolutionEnabled'
                    : 'configuration.evolutionDisabled',
                )}
              </Badge>
            )}
          </div>
          <Switch
            checked={evolutionEnabled}
            disabled={query.isLoading || mutation.isPending}
            onCheckedChange={(enabled) =>
              mutation.mutate({ agent_evolution: { enabled } })
            }
          />
        </CardContent>
      </Card>

      {aclEnabled !== undefined && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ShieldIcon className="size-4 text-cyan-500" />
              {t('configuration.aclEnabled')}
            </CardTitle>
            <CardDescription className="text-xs">
              {t('configuration.aclHint')}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex items-center justify-end">
            <Switch
              checked={Boolean(aclEnabled)}
              disabled={query.isLoading || mutation.isPending}
              onCheckedChange={(enabled) =>
                mutation.mutate({ acl: { enabled } })
              }
            />
          </CardContent>
        </Card>
      )}
    </div>
  )
}
