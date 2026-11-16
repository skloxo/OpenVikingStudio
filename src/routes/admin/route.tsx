import {
  createFileRoute,
  Link,
  Outlet,
  useRouterState,
} from '@tanstack/react-router'
import {
  BotIcon,
  Building2Icon,
  FileCode2Icon,
  LayoutDashboardIcon,
  ServerCogIcon,
  Settings2Icon,
  SlidersHorizontalIcon,
  UsersIcon,
  UsersRoundIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAppConnection } from '#/hooks/use-app-connection'
import { cn } from '#/lib/utils'
import { resolveStudioManagementCapabilities } from '#/lib/studio-permissions'

export const Route = createFileRoute('/admin')({
  component: AdminLayout,
})

function AdminLayout() {
  const { t } = useTranslation('adminConsole')
  const { connection, connectionRole, isConnectionRoleLoading, serverMode } =
    useAppConnection()
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  })
  const { canManageAccounts, canManageUsers } =
    resolveStudioManagementCapabilities({
      hasControlCredential: Boolean(connection.adminApiKey.trim()),
      isRoleLoading: isConnectionRoleLoading,
      role: connectionRole,
      serverMode,
    })

  const navItems = [
    {
      to: '/admin' as const,
      label: t('nav.overview'),
      icon: LayoutDashboardIcon,
      exact: true,
      visible: true,
    },
    {
      to: '/admin/configuration/server' as const,
      label: t('nav.serverConfig'),
      icon: ServerCogIcon,
      exact: false,
      visible: connectionRole === 'root' || canManageAccounts,
    },
    {
      to: '/admin/configuration' as const,
      label: t('nav.accountConfig'),
      icon: SlidersHorizontalIcon,
      exact: true,
      visible: canManageUsers || serverMode === 'trusted',
    },
    {
      to: '/admin/users/memory-templates' as const,
      label: t('nav.memoryTemplates'),
      icon: FileCode2Icon,
      exact: false,
      visible: canManageUsers || serverMode === 'trusted',
    },
    {
      to: '/admin/users/groups' as const,
      label: t('nav.groups'),
      icon: UsersIcon,
      exact: false,
      visible: canManageUsers || serverMode === 'trusted',
    },
    {
      to: '/admin/vikingbot' as const,
      label: t('nav.vikingbot'),
      icon: BotIcon,
      exact: false,
      visible: connectionRole === 'root' || canManageAccounts,
    },
    {
      to: '/users' as const,
      label: t('nav.users'),
      icon: UsersRoundIcon,
      exact: false,
      visible: canManageUsers,
    },
    {
      to: '/accounts' as const,
      label: t('nav.accounts'),
      icon: Building2Icon,
      exact: false,
      visible: canManageAccounts,
    },
    {
      to: '/settings' as const,
      label: t('nav.settings'),
      icon: Settings2Icon,
      exact: false,
      visible: true,
    },
  ].filter((item) => item.visible)

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b pb-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">{t('title')}</h1>
          <p className="text-xs text-muted-foreground">{t('subtitle')}</p>
        </div>
        <nav
          aria-label={t('title')}
          className="flex flex-wrap items-center gap-1.5"
        >
          {navItems.map((item) => {
            const Icon = item.icon
            const active = item.exact
              ? pathname === item.to
              : pathname === item.to || pathname.startsWith(`${item.to}/`)
            return (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-medium transition-colors',
                  active
                    ? 'border-cyan-500/40 bg-cyan-500/15 text-cyan-600 dark:text-cyan-400'
                    : 'border-transparent bg-muted/40 text-muted-foreground hover:bg-muted hover:text-foreground',
                )}
              >
                <Icon className="size-3.5" />
                <span>{item.label}</span>
              </Link>
            )
          })}
        </nav>
      </div>
      <Outlet />
    </div>
  )
}
