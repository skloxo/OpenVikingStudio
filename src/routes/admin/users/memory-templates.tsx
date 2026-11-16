import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { Loader2Icon, RotateCcwIcon, SaveIcon } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Textarea } from '#/components/ui/textarea'
import { useAppConnection } from '#/hooks/use-app-connection'
import { showErrorToast } from '#/lib/error-toast'
import { cn } from '#/lib/utils'
import {
  editableMemoryTypes,
  fetchMemoryTemplates,
  resetMemoryTemplate,
  templateFieldValue,
  updateMemoryTemplate,
  withTemplateField,
  type EditableMemoryType,
  type MemoryTemplateSchema,
} from '../-lib/templates-groups-api'

const editableFields: Record<EditableMemoryType, string[]> = {
  profile: ['description', 'fields.content.description'],
  preferences: [
    'description',
    'fields.topic.description',
    'fields.content.description',
  ],
  entities: [
    'description',
    'fields.category.description',
    'fields.name.description',
    'fields.content.description',
  ],
  events: [
    'description',
    'fields.event_name.description',
    'fields.summary.description',
    'content_template',
  ],
  soul: ['description', 'fields.core_truths.description', 'fields.boundaries.description'],
  identity: ['description', 'fields.creature.description', 'fields.introduction.description'],
}

export const Route = createFileRoute('/admin/users/memory-templates')({
  component: MemoryTemplatesPage,
})

function MemoryTemplatesPage() {
  const { t } = useTranslation('memoryTemplates')
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
    queryKey: ['admin-memory-templates', identityScopeKey, connection.accountId],
    queryFn: ({ signal }) => fetchMemoryTemplates(connInput, signal),
    enabled: canManage && Boolean(connection.accountId),
  })

  const [selectedType, setSelectedType] = useState<EditableMemoryType>('profile')
  const [draftSchema, setDraftSchema] = useState<MemoryTemplateSchema | null>(null)
  const [dirty, setDirty] = useState(false)

  const templates = query.data?.templates || []
  const current =
    templates.find((item) => item.memory_type === selectedType) || templates[0]

  useEffect(() => {
    if (!current) return
    setDraftSchema(current.effective)
    setDirty(false)
  }, [current])

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (!current || !draftSchema) return
      const fields = editableFields[current.memory_type] || ['description']
      for (const field of fields) {
        const val = templateFieldValue(draftSchema, field)
        if (!val.trim()) throw new Error(t('required'))
        if (field !== 'content_template' && val.length > 50000) {
          throw new Error(t('tooLong'))
        }
      }
      return updateMemoryTemplate(connInput, current.memory_type, draftSchema)
    },
    onSuccess: async () => {
      setDirty(false)
      toast.success(t('saved'))
      await queryClient.invalidateQueries({
        queryKey: ['admin-memory-templates', identityScopeKey],
      })
    },
    onError: (err) => showErrorToast(err),
  })

  const resetMutation = useMutation({
    mutationFn: () => {
      if (!current) throw new Error('No template selected')
      return resetMemoryTemplate(connInput, current.memory_type)
    },
    onSuccess: async () => {
      setDirty(false)
      toast.success(t('resetDone'))
      await queryClient.invalidateQueries({
        queryKey: ['admin-memory-templates', identityScopeKey],
      })
    },
    onError: (err) => showErrorToast(err),
  })

  if (!canManage) {
    return <p className="text-sm text-rose-500">{t('accessDenied')}</p>
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <h2 className="text-lg font-semibold">{t('title')}</h2>
          <p className="text-xs text-muted-foreground">{t('subtitle')}</p>
        </div>
        <Badge variant="outline" className="text-xs">
          {t('account', { account: connection.accountId })}
        </Badge>
      </div>

      {query.isLoading ? (
        <div className="flex items-center gap-2 py-8 text-xs text-muted-foreground">
          <Loader2Icon className="size-4 animate-spin text-cyan-500" />
          {t('loading')}
        </div>
      ) : (
        <div className="grid gap-5 lg:grid-cols-[260px_minmax(0,1fr)]">
          <div className="space-y-1.5 rounded-xl border bg-card p-2">
            {editableMemoryTypes.map((typeKey) => {
              const item = templates.find((tpl) => tpl.memory_type === typeKey)
              const active = selectedType === typeKey
              return (
                <button
                  key={typeKey}
                  type="button"
                  onClick={() => setSelectedType(typeKey)}
                  className={cn(
                    'flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-xs transition-colors',
                    active
                      ? 'bg-cyan-500/15 font-medium text-cyan-600 dark:text-cyan-400'
                      : 'hover:bg-muted',
                  )}
                >
                  <div>
                    <div>{t(typeKey)}</div>
                    <div className="text-xs text-muted-foreground">
                      {t('fileName', { type: typeKey })}
                    </div>
                  </div>
                  <Badge variant="outline" className="text-xs">
                    {t(item?.status === 'custom' ? 'custom' : 'default')}
                  </Badge>
                </button>
              )
            })}
          </div>

          {current && draftSchema && (
            <div className="space-y-5 rounded-xl border bg-card p-5">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-semibold">
                      {t(current.memory_type)}
                    </h3>
                    {dirty && (
                      <Badge variant="outline" className="text-xs text-amber-500">
                        {t('changed')}
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {t(`${current.memory_type}Hint` as never)}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={
                      current.status !== 'custom' || resetMutation.isPending
                    }
                    onClick={() => {
                      if (window.confirm(t('confirmReset'))) {
                        resetMutation.mutate()
                      }
                    }}
                  >
                    <RotateCcwIcon />
                    {t('reset')}
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    disabled={!dirty || saveMutation.isPending}
                    onClick={() => saveMutation.mutate()}
                  >
                    <SaveIcon />
                    {t(saveMutation.isPending ? 'saving' : 'save')}
                  </Button>
                </div>
              </div>

              {(editableFields[current.memory_type] || ['description']).map(
                (fieldPath) => {
                  const val = templateFieldValue(draftSchema, fieldPath)
                  const labelKey =
                    fieldPath === 'description'
                      ? t('typeDescription')
                      : fieldPath === 'content_template'
                        ? t('contentTemplate')
                        : `${t('fieldDescription')}: ${fieldPath.split('.')[1]}`
                  return (
                    <div key={fieldPath} className="space-y-1.5">
                      <label className="block text-xs font-medium">
                        {labelKey}
                      </label>
                      <Textarea
                        rows={fieldPath === 'content_template' ? 8 : 3}
                        className="font-mono text-xs leading-relaxed"
                        value={val}
                        onChange={(e) => {
                          setDraftSchema((prev) =>
                            prev ? withTemplateField(prev, fieldPath, e.target.value) : prev,
                          )
                          setDirty(true)
                        }}
                      />
                    </div>
                  )
                },
              )}

              <p className="text-xs text-muted-foreground">
                {t('syntaxHint')}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
