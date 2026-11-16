import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import {
  Loader2Icon,
  PlusIcon,
  Trash2Icon,
  UserPlusIcon,
  UsersIcon,
} from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { useAppConnection } from '#/hooks/use-app-connection'
import { showErrorToast } from '#/lib/error-toast'
import { cn } from '#/lib/utils'
import {
  addGroupMember,
  createAdminGroup,
  deleteAdminGroup,
  fetchAdminGroups,
  fetchGroupMembers,
  removeGroupMember,
} from '../-lib/templates-groups-api'

export const Route = createFileRoute('/admin/users/groups')({
  component: UserGroupsPage,
})

function UserGroupsPage() {
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

  const [newGroupId, setNewGroupId] = useState('')
  const [selectedGroup, setSelectedGroup] = useState('')
  const [newMemberId, setNewMemberId] = useState('')

  const groupsQuery = useQuery({
    queryKey: ['admin-groups', identityScopeKey, connection.accountId],
    queryFn: ({ signal }) => fetchAdminGroups(connInput, signal),
    enabled: canManage && Boolean(connection.accountId),
  })

  const activeGroup = selectedGroup || groupsQuery.data?.[0]?.group_id || ''

  const membersQuery = useQuery({
    queryKey: ['admin-group-members', identityScopeKey, connection.accountId, activeGroup],
    queryFn: () => fetchGroupMembers(connInput, activeGroup),
    enabled: canManage && Boolean(activeGroup),
  })

  const createGroupMut = useMutation({
    mutationFn: () => createAdminGroup(connInput, newGroupId),
    onSuccess: async () => {
      const created = newGroupId.trim()
      setNewGroupId('')
      setSelectedGroup(created)
      toast.success(t('groups.created'))
      await queryClient.invalidateQueries({
        queryKey: ['admin-groups', identityScopeKey],
      })
    },
    onError: (err) => showErrorToast(err),
  })

  const deleteGroupMut = useMutation({
    mutationFn: (groupId: string) => deleteAdminGroup(connInput, groupId),
    onSuccess: async () => {
      setSelectedGroup('')
      toast.success(t('groups.deleted'))
      await queryClient.invalidateQueries({
        queryKey: ['admin-groups', identityScopeKey],
      })
    },
    onError: (err) => showErrorToast(err),
  })

  const addMemberMut = useMutation({
    mutationFn: () => addGroupMember(connInput, activeGroup, newMemberId),
    onSuccess: async () => {
      setNewMemberId('')
      toast.success(t('groups.memberAdded'))
      await queryClient.invalidateQueries({
        queryKey: ['admin-group-members', identityScopeKey],
      })
    },
    onError: (err) => showErrorToast(err),
  })

  const removeMemberMut = useMutation({
    mutationFn: (userId: string) =>
      removeGroupMember(connInput, activeGroup, userId),
    onSuccess: async () => {
      toast.success(t('groups.memberRemoved'))
      await queryClient.invalidateQueries({
        queryKey: ['admin-group-members', identityScopeKey],
      })
    },
    onError: (err) => showErrorToast(err),
  })

  if (!canManage) {
    return <p className="text-sm text-rose-500">{t('adminOrRootRequired')}</p>
  }

  const groups = groupsQuery.data || []
  const members = membersQuery.data || []

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold">{t('groups.title')}</h2>
        <p className="text-xs text-muted-foreground">
          {t('groups.subtitle', { account: connection.accountId })}
        </p>
      </div>

      <form
        className="flex flex-wrap items-center gap-2"
        onSubmit={(e) => {
          e.preventDefault()
          if (newGroupId.trim()) createGroupMut.mutate()
        }}
      >
        <Input
          className="max-w-xs text-xs"
          placeholder={t('groups.groupNamePlaceholder')}
          value={newGroupId}
          onChange={(e) => setNewGroupId(e.target.value)}
        />
        <Button
          type="submit"
          size="sm"
          disabled={!newGroupId.trim() || createGroupMut.isPending}
        >
          <PlusIcon />
          {t('groups.createGroup')}
        </Button>
      </form>

      <div className="grid gap-5 md:grid-cols-[260px_minmax(0,1fr)]">
        <div className="space-y-1.5 rounded-xl border bg-card p-3">
          {groupsQuery.isLoading ? (
            <Loader2Icon className="size-4 animate-spin text-cyan-500" />
          ) : !groups.length ? (
            <p className="text-xs text-muted-foreground">{t('groups.emptyGroups')}</p>
          ) : (
            groups.map((grp) => (
              <div
                key={grp.group_id}
                className={cn(
                  'flex items-center justify-between rounded-lg px-3 py-2 text-xs',
                  activeGroup === grp.group_id
                    ? 'bg-cyan-500/15 text-cyan-600 dark:text-cyan-400 font-medium'
                    : 'hover:bg-muted',
                )}
              >
                <button
                  type="button"
                  className="flex min-w-0 flex-1 items-center gap-2 text-left"
                  onClick={() => setSelectedGroup(grp.group_id)}
                >
                  <UsersIcon className="size-3.5 shrink-0" />
                  <span className="truncate">{grp.group_id}</span>
                </button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-xs"
                  onClick={() => {
                    if (
                      window.confirm(
                        t('groups.deleteGroupConfirm', { group: grp.group_id }),
                      )
                    ) {
                      deleteGroupMut.mutate(grp.group_id)
                    }
                  }}
                >
                  <Trash2Icon className="size-3.5 text-rose-500" />
                </Button>
              </div>
            ))
          )}
        </div>

        <div className="space-y-4 rounded-xl border bg-card p-5">
          {!activeGroup ? (
            <p className="text-xs text-muted-foreground">{t('groups.selectGroup')}</p>
          ) : (
            <>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-semibold">{activeGroup}</h3>
                <Badge variant="outline" className="text-xs">
                  {t('groups.members', { count: members.length })}
                </Badge>
              </div>

              <form
                className="flex flex-wrap items-center gap-2"
                onSubmit={(e) => {
                  e.preventDefault()
                  if (newMemberId.trim()) addMemberMut.mutate()
                }}
              >
                <Input
                  className="max-w-xs text-xs"
                  placeholder={t('groups.addUserPlaceholder')}
                  value={newMemberId}
                  onChange={(e) => setNewMemberId(e.target.value)}
                />
                <Button
                  type="submit"
                  size="sm"
                  variant="outline"
                  disabled={!newMemberId.trim() || addMemberMut.isPending}
                >
                  <UserPlusIcon />
                  {t('groups.addMember')}
                </Button>
              </form>

              {!members.length ? (
                <p className="text-xs text-muted-foreground">{t('groups.noMembers')}</p>
              ) : (
                <ul className="divide-y rounded-lg border">
                  {members.map((userId) => (
                    <li
                      key={userId}
                      className="flex items-center justify-between px-3 py-2 text-xs"
                    >
                      <span className="font-mono">{userId}</span>
                      <Button
                        type="button"
                        variant="ghost"
                        size="xs"
                        onClick={() => removeMemberMut.mutate(userId)}
                      >
                        <Trash2Icon className="size-3.5 text-rose-500" />
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
