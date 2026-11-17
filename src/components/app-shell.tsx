import * as React from 'react'
import { Link, useRouterState } from '@tanstack/react-router'
import {
  BookOpenIcon,
  BracesIcon,
  GlobeIcon,
  LayoutGridIcon,
  MoonIcon,
  PlugZapIcon,
  ShieldCheckIcon,
  SunIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useTheme } from 'next-themes'

import { AccessRequiredGate } from '#/components/access-required-gate'
import { AccountSwitcher } from '#/components/account-switcher'
import { GeneratedCredentialDialog } from '#/components/generated-credential-dialog'
import { ScrollArea } from '#/components/ui/scroll-area'

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
} from '#/components/ui/sidebar'
import {
  AppConnectionProvider,
  useAppConnection,
} from '#/hooks/use-app-connection'
import { useServerVersionDetails } from '#/hooks/use-server-version'
import { isAdminWorkspacePath } from '#/routes/admin/-components/admin-console-shell'
import {
  NAV_ITEMS,
  NAV_SECTIONS,
  NavGroupItem,
  resolveLanguage,
  type NavItem,
  type NavSubItem,
} from './app-shell-nav'

export { NAV_ITEMS, NAV_SECTIONS, resolveLanguage }
export type { NavItem, NavSubItem }

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <AppConnectionProvider>
      <IdentityScopedAppShell>{children}</IdentityScopedAppShell>
    </AppConnectionProvider>
  )
}

function IdentityScopedAppShell({ children }: { children: React.ReactNode }) {
  const { identityScopeKey } = useAppConnection()
  return <AppShellInner key={identityScopeKey}>{children}</AppShellInner>
}

function AppShellInner({ children }: { children: React.ReactNode }) {
  const { i18n, t } = useTranslation(['appShell', 'common'])
  const versionDetails = useServerVersionDetails()
  const appVersion = versionDetails.version
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  })
  const { setTheme, resolvedTheme } = useTheme()
  const currentLanguage = resolveLanguage(
    i18n.resolvedLanguage ?? i18n.language,
  )
  const agentIntegrationsHref = `https://docs.openviking.ai/${
    currentLanguage === 'zh-CN' ? 'zh' : 'en'
  }/agent-integrations/01-overview`
  const sdkApiHref = `https://docs.openviking.ai/${
    currentLanguage === 'zh-CN' ? 'zh' : 'en'
  }/api/01-overview`
  const { connection, serverMode } = useAppConnection()
  const settingsActive = pathname === '/settings'
  const crossDeviceVerifyActive =
    pathname === '/oauth/verify' || pathname.startsWith('/oauth/verify/')
  const visibleNavItems = NAV_ITEMS

  return (
    <SidebarProvider
      defaultOpen
      className="flex h-svh overflow-hidden bg-sidebar"
    >
      <Sidebar variant="sidebar" collapsible="icon">
        <SidebarHeader className="h-12 border-b border-sidebar-border/70 px-2 py-0">
          <div className="flex h-full items-center justify-between gap-2 group-data-[collapsible=icon]:justify-center">
            <div className="min-w-0 flex-1 group-data-[collapsible=icon]:hidden">
              <AccountSwitcher />
              <div className="flex items-center gap-1.5 px-2 -mt-1">
                <span
                  className="text-xs font-mono text-slate-400 dark:text-slate-500 font-normal leading-none select-none cursor-pointer hover:text-foreground transition-colors"
                  title={
                    versionDetails.isDrifted
                      ? `⚠️ 版本脱节: 前端 UI (v${versionDetails.appVersion}) 与 服务端 (v${versionDetails.remoteVersion}) 不一致，点击刷新网页`
                      : `OpenViking v${appVersion}`
                  }
                  onClick={() => {
                    if (versionDetails.isDrifted) {
                      window.location.reload()
                    }
                  }}
                >
                  v{appVersion}
                </span>
                {versionDetails.isDrifted && (
                  <span
                    className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"
                    title={`前后端版本脱节 (UI: v${versionDetails.appVersion} / Server: v${versionDetails.remoteVersion})`}
                  />
                )}
              </div>
            </div>
            <SidebarTrigger className="shrink-0" />
          </div>
        </SidebarHeader>

        <SidebarContent className="gap-0 py-1">
          {NAV_SECTIONS.map((section) => (
            <SidebarGroup key={section.id} className="pb-1">
              <SidebarGroupLabel className="h-7 px-2 pt-2 text-xs font-semibold uppercase tracking-[0.12em] text-sidebar-foreground/45">
                {t(section.titleKey, { ns: 'appShell' })}
              </SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {visibleNavItems
                    .filter((item) => item.section === section.id)
                    .map((item) => {
                      const isActive =
                        pathname === item.to ||
                        pathname.startsWith(`${item.to}/`)
                      const title = t(item.titleKey, { ns: 'appShell' })

                      if (item.children) {
                        return (
                          <NavGroupItem
                            key={item.id}
                            item={
                              item as NavItem & {
                                children: readonly NavSubItem[]
                              }
                            }
                            pathname={pathname}
                            title={title}
                            t={t}
                          />
                        )
                      }

                      const Icon = item.icon

                      return (
                        <SidebarMenuItem key={item.id}>
                          <SidebarMenuButton
                            render={<Link to={item.to} />}
                            isActive={isActive}
                            tooltip={title}
                            className="h-9"
                          >
                            <Icon />
                            <span>{title}</span>
                          </SidebarMenuButton>
                        </SidebarMenuItem>
                      )
                    })}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          ))}

          <SidebarGroup className="pb-1">
            <SidebarGroupLabel className="h-7 px-2 pt-2 text-xs font-semibold uppercase tracking-[0.12em] text-sidebar-foreground/45">
              {t('sidebar.groups.resources', { ns: 'appShell' })}
            </SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    render={
                      <a
                        href="https://docs.openviking.ai/"
                        target="_blank"
                        rel="noreferrer"
                      />
                    }
                    tooltip={t('footer.docs', { ns: 'appShell' })}
                    className="h-9"
                  >
                    <BookOpenIcon />
                    <span>{t('footer.docs', { ns: 'appShell' })}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    render={
                      <a href={sdkApiHref} target="_blank" rel="noreferrer" />
                    }
                    tooltip={t('footer.sdkApi', { ns: 'appShell' })}
                    className="h-9"
                  >
                    <BracesIcon />
                    <span>{t('footer.sdkApi', { ns: 'appShell' })}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    render={
                      <a
                        href={agentIntegrationsHref}
                        target="_blank"
                        rel="noreferrer"
                      />
                    }
                    tooltip={t('footer.agentIntegrations', {
                      ns: 'appShell',
                    })}
                    className="h-9"
                  >
                    <PlugZapIcon />
                    <span>
                      {t('footer.agentIntegrations', { ns: 'appShell' })}
                    </span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>

        <SidebarFooter className="border-t border-sidebar-border/70 p-2">
          <div className="flex items-center gap-1 group-data-[collapsible=icon]:flex-col">
            <SidebarMenuButton
              onClick={() =>
                void i18n.changeLanguage(
                  currentLanguage === 'zh-CN' ? 'en' : 'zh-CN',
                )
              }
              tooltip={currentLanguage === 'zh-CN' ? '语言切换' : 'Language'}
              className="h-8 flex-1 justify-center gap-1.5 text-xs"
            >
              <GlobeIcon className="size-3.5 shrink-0" />
              <span className="font-mono font-medium group-data-[collapsible=icon]:hidden">
                {currentLanguage === 'zh-CN' ? '中 / EN' : 'EN / 中'}
              </span>
            </SidebarMenuButton>
            <SidebarMenuButton
              onClick={() =>
                setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')
              }
              tooltip={resolvedTheme === 'dark' ? '浅色主题' : '深色主题'}
              className="h-8 flex-1 justify-center gap-1.5 text-xs"
            >
              <SunIcon className="size-3.5 shrink-0 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
              <MoonIcon className="absolute size-3.5 shrink-0 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
              <span className="group-data-[collapsible=icon]:hidden">
                {resolvedTheme === 'dark' ? '浅色' : '深色'}
              </span>
            </SidebarMenuButton>
          </div>
        </SidebarFooter>
      </Sidebar>

      <SidebarInset className="min-h-0 flex-1 overflow-hidden rounded-none border-0 bg-background shadow-none ring-0 md:m-0 md:ml-0">
        {/* 统一顶栏（工作台 ↔ 管理后台切换与移动端菜单触发器） */}
        <header className="flex h-12 shrink-0 items-center justify-between border-b border-border/60 bg-background/95 backdrop-blur-md px-3 md:px-5 sticky top-0 z-30">
          <div className="flex items-center gap-2">
            <SidebarTrigger className="h-8 w-8 rounded text-foreground hover:bg-muted font-mono md:hidden" />
            <span className="font-semibold text-xs tracking-tight text-foreground flex items-center gap-1.5 md:hidden">
              <span>🧠</span>
              <span>OpenViking Studio</span>
            </span>
          </div>
          <div className="flex items-center gap-2 ml-auto">
            {isAdminWorkspacePath(pathname) ? (
              <Link
                to="/"
                className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border px-3 text-xs font-medium text-foreground transition-colors hover:bg-muted"
              >
                <LayoutGridIcon className="size-3.5 text-cyan-500" />
                <span>{t('backToWorkspace', { ns: 'adminConsole' })}</span>
              </Link>
            ) : (
              <Link
                to="/admin"
                className="inline-flex h-8 items-center gap-1.5 rounded-md border border-cyan-500/30 bg-cyan-500/5 px-3 text-xs font-medium text-foreground transition-colors hover:bg-cyan-500/10"
              >
                <ShieldCheckIcon className="size-3.5 text-cyan-500" />
                <span>{t('enterAdmin', { ns: 'adminConsole' })}</span>
              </Link>
            )}
            <span
              className="flex md:hidden text-xs font-mono text-muted-foreground bg-muted/40 px-1.5 py-0.5 rounded border border-border/40 cursor-pointer"
              title={
                versionDetails.isDrifted
                  ? `UI: v${versionDetails.appVersion} / Server: v${versionDetails.remoteVersion}`
                  : `v${appVersion}`
              }
              onClick={() => {
                if (versionDetails.isDrifted) {
                  window.location.reload()
                }
              }}
            >
              v{appVersion}
              {versionDetails.isDrifted && (
                <span className="ml-1 text-amber-400">⚠️</span>
              )}
            </span>
          </div>
        </header>

        <ScrollArea className="min-h-0 flex-1">
          <div className="flex w-full flex-col gap-6 px-4 py-6 md:px-6">
            {!settingsActive &&
            !crossDeviceVerifyActive &&
            serverMode !== 'trusted' &&
            serverMode !== 'dev' &&
            !connection.adminApiKey.trim() &&
            !connection.apiKey.trim() ? (
              <AccessRequiredGate />
            ) : (
              children
            )}
          </div>
        </ScrollArea>
      </SidebarInset>

      <GeneratedCredentialDialog />
    </SidebarProvider>
  )
}
