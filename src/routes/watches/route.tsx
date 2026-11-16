import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { Clock3Icon, LoaderCircleIcon, PlusIcon, RefreshCwIcon } from 'lucide-react'
import * as React from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '#/components/ui/alert-dialog'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import { useAppConnection } from '#/hooks/use-app-connection'

import { AddWatchDialog } from './-components/add-watch-dialog'
import { EditWatchDialog } from './-components/edit-watch-dialog'
import { WatchHistorySheet } from './-components/watch-history-sheet'
import { WatchesTable } from './-components/watches-table'
import {
  createWatchResource,
  deleteWatch,
  fetchWatchProcessingHistory,
  fetchWatches,
  triggerWatch,
  updateWatch,
  type CreateWatchInput,
  type UpdateWatchInput,
  type WatchTask,
} from './-lib/api'
import {
  getWatchRefetchInterval,
  hasCompletedTriggeredWatchSync,
  hasDiscoveredWatch,
  hasWatchExecutionAdvanced,
} from './-lib/watch-discovery'

export const Route = createFileRoute('/watches')({
  component: WatchManagementPage,
})

type PendingWatchSync = {
  baselineExecutionTime: string | null
  baselineTaskIds: string[]
  identityScopeKey: string
  taskId: string
  toUri: string
}

export function WatchManagementPage() {
  const { t } = useTranslation('watchesPage')
  const { identityScopeKey } = useAppConnection()
  const queryClient = useQueryClient()

  const [addOpen, setAddOpen] = React.useState(false)
  const [editingWatch, setEditingWatch] = React.useState<WatchTask | null>(null)
  const [deletingWatch, setDeletingWatch] = React.useState<WatchTask | null>(null)
  const [historyWatch, setHistoryWatch] = React.useState<WatchTask | null>(null)
  const [discoverTarget, setDiscoverTarget] = React.useState<string | null>(null)
  const [togglingTaskId, setTogglingTaskId] = React.useState<string | null>(null)
  const [pendingSync, setPendingSync] = React.useState<PendingWatchSync | null>(
    null,
  )

  const watchesQuery = useQuery({
    queryFn: fetchWatches,
    queryKey: ['watches', identityScopeKey],
    refetchInterval: getWatchRefetchInterval(
      Boolean(discoverTarget) || pendingSync?.identityScopeKey === identityScopeKey,
    ),
  })
  const watches = watchesQuery.data ?? []

  const syncHistoryQuery = useQuery({
    enabled: pendingSync?.identityScopeKey === identityScopeKey,
    queryFn: () => fetchWatchProcessingHistory(pendingSync?.toUri ?? ''),
    queryKey: ['watch-sync-progress', identityScopeKey, pendingSync?.taskId],
    refetchInterval:
      pendingSync?.identityScopeKey === identityScopeKey ? 1_000 : false,
  })

  React.useEffect(() => {
    if (!discoverTarget) return
    if (hasDiscoveredWatch(watches, discoverTarget)) {
      setDiscoverTarget(null)
      toast.success(t('toast.created'))
    }
  }, [discoverTarget, t, watches])

  React.useEffect(() => {
    if (!pendingSync || pendingSync.identityScopeKey !== identityScopeKey) return
    const current = watches.find((w) => w.taskId === pendingSync.taskId)
    const advanced =
      current &&
      hasWatchExecutionAdvanced(
        current.lastExecutionTime,
        pendingSync.baselineExecutionTime,
      )
    const completedHistory = hasCompletedTriggeredWatchSync(
      syncHistoryQuery.data ?? [],
      pendingSync.baselineTaskIds,
    )
    if (advanced || completedHistory) {
      setPendingSync(null)
      void queryClient.invalidateQueries({ queryKey: ['watches', identityScopeKey] })
    }
  }, [identityScopeKey, pendingSync, queryClient, syncHistoryQuery.data, watches])

  const createMutation = useMutation({
    mutationFn: (input: CreateWatchInput) => createWatchResource(input),
    onSuccess: (_res, input) => {
      setAddOpen(false)
      if (input.to) setDiscoverTarget(input.to)
      toast.success(t('toast.creating'))
      void queryClient.invalidateQueries({ queryKey: ['watches', identityScopeKey] })
    },
    onError: (err) => {
      toast.error(
        `${t('toast.createFailed')}: ${err instanceof Error ? err.message : String(err)}`,
      )
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, input }: { id: string; input: UpdateWatchInput }) =>
      updateWatch(id, input),
    onSuccess: () => {
      setEditingWatch(null)
      toast.success(t('toast.updated'))
      void queryClient.invalidateQueries({ queryKey: ['watches', identityScopeKey] })
    },
    onSettled: () => setTogglingTaskId(null),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteWatch(id),
    onSuccess: () => {
      setDeletingWatch(null)
      toast.success(t('toast.deleted'))
      void queryClient.invalidateQueries({ queryKey: ['watches', identityScopeKey] })
    },
  })

  const handleTrigger = async (watch: WatchTask) => {
    const baseline = await fetchWatchProcessingHistory(watch.toUri).catch(
      () => [],
    )
    await triggerWatch(watch.taskId)
    toast.success(t('toast.triggered'))
    setPendingSync({
      baselineExecutionTime: watch.lastExecutionTime,
      baselineTaskIds: baseline
        .map((task) => task.task_id)
        .filter((id): id is string => Boolean(id)),
      identityScopeKey,
      taskId: watch.taskId,
      toUri: watch.toUri,
    })
  }

  return (
    <div className="flex w-full min-w-0 flex-col gap-5 p-4 md:p-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="grid gap-1.5">
          <h1 className="text-2xl font-semibold tracking-tight">{t('title')}</h1>
          <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
            {t('description')}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={watchesQuery.isFetching}
            onClick={() => void watchesQuery.refetch()}
          >
            <RefreshCwIcon
              className={watchesQuery.isFetching ? 'animate-spin' : undefined}
            />
            {t('refresh')}
          </Button>
          <Button type="button" size="sm" onClick={() => setAddOpen(true)}>
            <PlusIcon />
            {t('add')}
          </Button>
        </div>
      </header>

      {watchesQuery.isLoading ? (
        <Card className="min-h-56 items-center justify-center">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <LoaderCircleIcon className="size-4 animate-spin" />
            {t('loading')}
          </div>
        </Card>
      ) : watchesQuery.isError ? (
        <Card className="min-h-56 items-center justify-center px-6 text-center">
          <p className="font-medium">{t('loadFailed')}</p>
          <p className="text-sm text-muted-foreground">
            {watchesQuery.error instanceof Error
              ? watchesQuery.error.message
              : String(watchesQuery.error)}
          </p>
        </Card>
      ) : watches.length === 0 ? (
        <Card className="min-h-56 items-center justify-center px-6 py-8 text-center">
          <div className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Clock3Icon className="size-5" />
          </div>
          <p className="font-medium">{t('empty')}</p>
          <p className="text-sm text-muted-foreground">{t('emptyDescription')}</p>
        </Card>
      ) : (
        <Card size="sm" className="rounded-xl bg-background shadow-none ring-border/70 py-0">
          <WatchesTable
            watches={watches}
            pendingSyncTaskId={pendingSync?.taskId ?? null}
            togglingTaskId={togglingTaskId}
            onToggleActive={(watch, isActive) => {
              setTogglingTaskId(watch.taskId)
              updateMutation.mutate({ id: watch.taskId, input: { isActive } })
            }}
            onTrigger={(watch) => void handleTrigger(watch)}
            onEdit={setEditingWatch}
            onHistory={setHistoryWatch}
            onDelete={setDeletingWatch}
          />
        </Card>
      )}

      <AddWatchDialog
        open={addOpen}
        pending={createMutation.isPending}
        onOpenChange={setAddOpen}
        onSubmit={(input) => createMutation.mutate(input)}
      />

      <EditWatchDialog
        watch={editingWatch}
        pending={updateMutation.isPending}
        onOpenChange={(open) => {
          if (!open) setEditingWatch(null)
        }}
        onSubmit={(input) => {
          if (editingWatch) {
            updateMutation.mutate({ id: editingWatch.taskId, input })
          }
        }}
      />

      <WatchHistorySheet
        open={Boolean(historyWatch)}
        watch={historyWatch}
        identityScopeKey={identityScopeKey}
        onOpenChange={(open) => {
          if (!open) setHistoryWatch(null)
        }}
      />

      <AlertDialog
        open={Boolean(deletingWatch)}
        onOpenChange={(open) => {
          if (!open && !deleteMutation.isPending) setDeletingWatch(null)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('deleteDialog.title')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('deleteDialog.description', { uri: deletingWatch?.toUri ?? '' })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('cancel')}</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={() => {
                if (deletingWatch) deleteMutation.mutate(deletingWatch.taskId)
              }}
            >
              {t('deleteConfirm')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
