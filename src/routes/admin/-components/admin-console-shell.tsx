import * as React from 'react'
import { Link, useNavigate, useRouterState } from '@tanstack/react-router'
import {
  ActivityIcon,
  BotIcon,
  Building2Icon,
  FileCode2Icon,
  KeyRoundIcon,
  LayoutDashboardIcon,
  ServerCogIcon,
  Settings2Icon,
  SlidersHorizontalIcon,
  UsersIcon,
  UsersRoundIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { CrossDeviceVerifyDialog } from '#/components/cross-device-verify-dialog'
import { ServerDoctorDialog } from '#/components/server-doctor-dialog'
import { Button } from '#/components/ui/button'
import { useAppConnection } from '#/hooks/use-app-connection'
import { resolveStudioManagementCapabilities } from '#/lib/studio-permissions'
import { cn } from '#/lib/utils'

const ADMIN_WORKSPACE_PATHS = ['/users', '/accounts', '/settings'] as const

export function isAdminWorkspacePath(pathname: string): boolean {
  return (
    pathname === '/admin' ||
    pathname.startsWith('/admin/') ||
    ADMIN_WORKSPACE_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`))
  )
}

export function AdminConsoleShell({ children }: { children: React.ReactNode }) {
  const { t } = useTranslation('adminConsole')
  const navigate = useNavigate()
  const { connection, connectionRole, isConnectionRoleLoading, serverMode } =
    useAppConnection()
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  })
  const [verifyOpen, setVerifyOpen] = React.useState(false)
  const [doctorOpen, setDoctorOpen] = React.useState(false)

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

  function handleOpenOAuthVerify(): void {
    const useDialog =
      typeof window !== 'undefined' &&
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(min-width: 768px)').matches
    if (useDialog) {
      setVerifyOpen(true)
    } else {
      void navigate({ to: '/oauth/verify' })
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-3 border-b pb-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">{t('title')}</h1>
            <p className="text-xs text-muted-foreground">{t('subtitle')}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleOpenOAuthVerify}
              className="h-8 gap-1.5 text-xs"
            >
              <KeyRoundIcon className="size-3.5 text-cyan-500" />
              <span>{t('actions.oauthVerify')}</span>
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setDoctorOpen(true)}
              className="h-8 gap-1.5 border-cyan-500/30 bg-cyan-500/5 text-xs hover:bg-cyan-500/10"
            >
              <ActivityIcon className="size-3.5 text-cyan-500" />
              <span>{t('actions.doctor')}</span>
            </Button>
          </div>
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

      {children}

      <CrossDeviceVerifyDialog
        open={verifyOpen}
        onOpenChange={setVerifyOpen}
      />
      <ServerDoctorDialog
        open={doctorOpen}
        onOpenChange={setDoctorOpen}
      />
    </div>
  )
}
