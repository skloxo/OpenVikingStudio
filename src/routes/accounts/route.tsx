/**
 * route.tsx
 * 平台级空间 (Account) 管理中枢座舱。
 * 仅在 Root 权限下解锁，负责系统多租户隔离空间的增删改查。
 * 遵循 Agent 编码规范与黄金甜点区（150 ~ 280 行）、NO GREEN EVER 🚫、>= 12px 字体下限。
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import {
  Building2Icon,
  CheckIcon,
  CopyIcon,
  FolderOpenIcon,
  LoaderCircleIcon,
  PlusIcon,
  RefreshCwIcon,
  ShieldAlertIcon,
  Trash2Icon,
  UsersRoundIcon,
} from 'lucide-react'
import * as React from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '#/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '#/components/ui/dialog'
import { Input } from '#/components/ui/input'
import { Label } from '#/components/ui/label'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '#/components/ui/table'
import { useAppConnection } from '#/hooks/use-app-connection'
import {
  createAdminAccount,
  deleteAdminAccount,
  fetchAdminAccounts,
} from '#/lib/admin'
import type { AdminAccount, AdminConnection } from '#/lib/admin'
import { copyTextToClipboard } from '#/lib/clipboard'
import { resolveStudioManagementCapabilities } from '#/lib/studio-permissions'

export const Route = createFileRoute('/accounts')({
  component: AccountsManagementRoute,
})

function AccountsManagementRoute() {
  const { t } = useTranslation('settings')
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const {
    connection,
    connectionRole,
    isConnectionRoleLoading,
    serverMode,
    switchManagementAccount,
  } = useAppConnection()

  const [createDialogOpen, setCreateDialogOpen] = React.useState(false)
  const [newAccountId, setNewAccountId] = React.useState('')
  const [newAdminUserId, setNewAdminUserId] = React.useState('admin')
  const [pendingDeleteAccount, setPendingDeleteAccount] =
    React.useState<AdminAccount | null>(null)
  const [copiedKey, setCopiedKey] = React.useState<string | null>(null)

  const { canManageAccounts } = resolveStudioManagementCapabilities({
    hasControlCredential: Boolean(connection.adminApiKey.trim()),
    isRoleLoading: isConnectionRoleLoading,
    role: connectionRole,
    serverMode,
  })

  const adminConnection = React.useMemo<AdminConnection>(
    () => ({
      accountId: connection.accountId,
      apiKey: connection.adminApiKey,
      baseUrl: connection.baseUrl,
      userId: connection.userId,
    }),
    [
      connection.accountId,
      connection.adminApiKey,
      connection.baseUrl,
      connection.userId,
    ],
  )

  const accountsQuery = useQuery<AdminAccount[], Error>({
    enabled: canManageAccounts,
    queryFn: () => fetchAdminAccounts(adminConnection),
    queryKey: ['admin-accounts', adminConnection.baseUrl, adminConnection.apiKey],
    retry: false,
  })

  const createMutation = useMutation({
    mutationFn: async () => {
      if (!newAccountId.trim()) throw new Error('空间 ID 不能为空')
      return createAdminAccount(adminConnection, {
        accountId: newAccountId.trim(),
        adminUserId: newAdminUserId.trim() || 'admin',
      })
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['admin-accounts'] })
      toast.success(`空间 [${newAccountId}] 创建成功！初始管理员密钥已生成。`)
      setCreateDialogOpen(false)
      setNewAccountId('')
      setNewAdminUserId('admin')
    },
    onError: (err: any) => {
      toast.error(`创建空间失败: ${err.message || '未知错误'}`)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (accId: string) => {
      return deleteAdminAccount(adminConnection, accId)
    },
    onSuccess: (_, accId) => {
      queryClient.invalidateQueries({ queryKey: ['admin-accounts'] })
      toast.success(`空间 [${accId}] 已安全删除`)
      setPendingDeleteAccount(null)
    },
    onError: (err: any) => {
      toast.error(`删除空间失败: ${err.message || '未知错误'}`)
    },
  })

  const handleCopy = async (text: string, id: string) => {
    await copyTextToClipboard(text)
    setCopiedKey(id)
    toast.success('已复制到剪贴板')
    setTimeout(() => setCopiedKey(null), 2000)
  }

  const accounts = accountsQuery.data || []
  const totalUsers = accounts.reduce((sum, a) => sum + (a.userCount || 0), 0)

  if (!canManageAccounts && !isConnectionRoleLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-6 text-center">
        <ShieldAlertIcon className="size-12 text-rose-500 mb-3" />
        <h2 className="text-lg font-medium text-foreground">无空间管理权限</h2>
        <p className="text-xs text-muted-foreground max-w-md mt-1 mb-4">
          空间 (Account) 管理仅对持有系统 Root API Key 的最高管理员开放。
          如需管理多租户空间，请先在连接设置中配置有效的 Root Key。
        </p>
        <Button variant="outline" size="sm" render={<Link to="/settings" />}>
          前往连接设置
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-5 p-6 max-w-7xl mx-auto">
      {/* 顶部标题与操作 */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold tracking-tight text-foreground flex items-center gap-2">
              <Building2Icon className="size-5 text-cyan-500" />
              空间管理 (Accounts)
            </h1>
            <Badge variant="outline" className="font-mono text-xs border-cyan-500/30 text-cyan-400">
              Root SSOT
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            系统三层拓扑顶级容器：Root ➔ 空间 (Account) ➔ 空间成员 (User ≡ Agent)。数据、记忆与知识在空间内严格物理隔离。
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => accountsQuery.refetch()}
            disabled={accountsQuery.isFetching}
            className="h-8 text-xs gap-1.5"
          >
            <RefreshCwIcon className={`size-3.5 ${accountsQuery.isFetching ? 'animate-spin' : ''}`} />
            刷新
          </Button>
          <Button
            size="sm"
            onClick={() => setCreateDialogOpen(true)}
            className="h-8 text-xs gap-1.5 bg-cyan-600 hover:bg-cyan-500 text-white"
          >
            <PlusIcon className="size-3.5" />
            新建空间
          </Button>
        </div>
      </div>

      {/* 顶部指标卡片 */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <Card className="p-3.5 bg-card/60 border-border/70">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">空间总数</span>
            <Building2Icon className="size-4 text-cyan-500/80" />
          </div>
          <div className="text-2xl font-mono font-semibold tabular-nums mt-1 text-foreground">
            {accountsQuery.isLoading ? '--' : accounts.length}
          </div>
          <div className="text-[12px] text-muted-foreground/80 mt-1">
            当前系统活跃多租户物理容器
          </div>
        </Card>

        <Card className="p-3.5 bg-card/60 border-border/70">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">空间成员总数 (User/Agent)</span>
            <UsersRoundIcon className="size-4 text-cyan-500/80" />
          </div>
          <div className="text-2xl font-mono font-semibold tabular-nums mt-1 text-foreground">
            {accountsQuery.isLoading ? '--' : totalUsers}
          </div>
          <div className="text-[12px] text-muted-foreground/80 mt-1">
            全空间真人成员与智能体平权实体
          </div>
        </Card>

        <Card className="p-3.5 bg-card/60 border-border/70">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">当前驻留空间</span>
            <FolderOpenIcon className="size-4 text-cyan-500/80" />
          </div>
          <div className="text-lg font-mono font-semibold mt-1 text-foreground truncate">
            {connection.accountId || 'default'}
          </div>
          <div className="text-[12px] text-muted-foreground/80 mt-1">
            当前控制台工作区上下文
          </div>
        </Card>
      </div>

      {/* 空间列表表格 */}
      <Card className="border-border/70">
        <CardHeader className="py-3 px-4 border-b border-border/50">
          <CardTitle className="text-sm font-medium">租户空间列表</CardTitle>
          <CardDescription className="text-xs">
            每个空间享有独立的 SQLite 数据库、向量集合、记忆总账与 50 项 FastMCP 工具调用权限。
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="text-xs font-semibold">空间标识 (Account ID)</TableHead>
                <TableHead className="text-xs font-semibold">成员总数</TableHead>
                <TableHead className="text-xs font-semibold">创建时间</TableHead>
                <TableHead className="text-xs font-semibold text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {accountsQuery.isLoading ? (
                <TableRow>
                  <TableCell colSpan={4} className="h-28 text-center text-xs text-muted-foreground">
                    <LoaderCircleIcon className="size-5 animate-spin mx-auto mb-2 text-cyan-500" />
                    正在加载系统空间...
                  </TableCell>
                </TableRow>
              ) : accounts.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="h-24 text-center text-xs text-muted-foreground">
                    暂无租户空间
                  </TableCell>
                </TableRow>
              ) : (
                accounts.map((acc) => {
                  const isCurrent = acc.accountId === connection.accountId
                  const isDefault = acc.accountId === 'default'
                  return (
                    <TableRow key={acc.accountId} className="text-xs">
                      <TableCell className="font-mono py-2.5">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-foreground">{acc.accountId}</span>
                          {isCurrent && (
                            <Badge variant="outline" className="text-xs py-0 border-cyan-500/40 text-cyan-400">
                              当前驻留
                            </Badge>
                          )}
                          {isDefault && (
                            <Badge variant="outline" className="text-xs py-0 border-border text-muted-foreground">
                              默认
                            </Badge>
                          )}
                          <Button
                            variant="ghost"
                            size="icon"
                            className="size-5 text-muted-foreground hover:text-foreground"
                            onClick={() => handleCopy(acc.accountId, acc.accountId)}
                            title="复制空间 ID"
                          >
                            {copiedKey === acc.accountId ? (
                              <CheckIcon className="size-3 text-cyan-400" />
                            ) : (
                              <CopyIcon className="size-3" />
                            )}
                          </Button>
                        </div>
                      </TableCell>
                      <TableCell className="font-mono tabular-nums text-muted-foreground">
                        {acc.userCount} 位成员
                      </TableCell>
                      <TableCell className="font-mono text-muted-foreground">
                        {acc.createdAt ? new Date(acc.createdAt).toLocaleString() : '--'}
                      </TableCell>
                      <TableCell className="text-right py-2.5">
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs px-2.5 gap-1"
                            onClick={async () => {
                              await switchManagementAccount(acc.accountId)
                              navigate({ to: '/users' })
                            }}
                          >
                            <UsersRoundIcon className="size-3 text-cyan-500" />
                            管理成员
                          </Button>
                          {!isDefault && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 text-xs px-2 text-rose-500 hover:text-rose-400 hover:bg-rose-500/10"
                              onClick={() => setPendingDeleteAccount(acc)}
                            >
                              <Trash2Icon className="size-3" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 新建空间 Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base font-semibold flex items-center gap-2">
              <Building2Icon className="size-4 text-cyan-500" />
              新建租户空间 (Account)
            </DialogTitle>
            <DialogDescription className="text-xs">
              在 OpenViking 体系中，空间是数据与记忆隔离的物理容器。创建空间时会自动初始化其首位管理员。
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-3 py-2">
            <div className="flex flex-col gap-1.5">
              <Label className="text-xs">空间标识 (Account ID)</Label>
              <Input
                placeholder="例如: team-alpha, enterprise-a"
                value={newAccountId}
                onChange={(e) => setNewAccountId(e.target.value)}
                className="h-8 text-xs font-mono"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label className="text-xs">初始空间管理员 (Admin User ID)</Label>
              <Input
                placeholder="admin"
                value={newAdminUserId}
                onChange={(e) => setNewAdminUserId(e.target.value)}
                className="h-8 text-xs font-mono"
              />
              <span className="text-[12px] text-muted-foreground">
                该用户将拥有此空间的 Admin 权限，并自动签发首张 User Key。
              </span>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCreateDialogOpen(false)}
              className="text-xs h-8"
            >
              取消
            </Button>
            <Button
              size="sm"
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending || !newAccountId.trim()}
              className="text-xs h-8 bg-cyan-600 hover:bg-cyan-500 text-white gap-1.5"
            >
              {createMutation.isPending && <LoaderCircleIcon className="size-3 animate-spin" />}
              确认创建
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 删除空间确认 Dialog */}
      <Dialog
        open={Boolean(pendingDeleteAccount)}
        onOpenChange={(open) => !open && setPendingDeleteAccount(null)}
      >
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-base font-semibold text-rose-500 flex items-center gap-2">
              <ShieldAlertIcon className="size-4" />
              删除空间确认
            </DialogTitle>
            <DialogDescription className="text-xs">
              确定要彻底删除空间 <strong className="font-mono text-foreground">{pendingDeleteAccount?.accountId}</strong> 吗？
              空间内的所有成员、记忆与历史资料将被永久解绑清理，此操作不可逆。
            </DialogDescription>
          </DialogHeader>

          <DialogFooter>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPendingDeleteAccount(null)}
              className="text-xs h-8"
            >
              取消
            </Button>
            <Button
              size="sm"
              variant="destructive"
              onClick={() => {
                if (pendingDeleteAccount) {
                  deleteMutation.mutate(pendingDeleteAccount.accountId)
                }
              }}
              disabled={deleteMutation.isPending}
              className="text-xs h-8 bg-rose-600 hover:bg-rose-500 text-white gap-1.5"
            >
              {deleteMutation.isPending && <LoaderCircleIcon className="size-3 animate-spin" />}
              彻底删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
