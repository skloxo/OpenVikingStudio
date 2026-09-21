import { lazy, Suspense } from 'react'
import { RotateCcwIcon, TriangleAlertIcon } from 'lucide-react'
import { Outlet, createRootRoute } from '@tanstack/react-router'
import type { ErrorComponentProps } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

import { AppShell } from '#/components/app-shell'
import { Button } from '#/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '#/components/ui/card'
import { Toaster } from '#/components/ui/sonner'
import '../styles.css'

const AppDevtools = import.meta.env.DEV
  ? lazy(() =>
      import('#/components/app-devtools').then((module) => ({
        default: module.AppDevtools,
      })),
    )
  : null

export const Route = createRootRoute({
  component: RootComponent,
  errorComponent: RootErrorComponent,
  notFoundComponent: RootNotFoundComponent,
})

function RootComponent() {
  return (
    <>
      <AppShell>
        <Outlet />
      </AppShell>
      <Toaster />
      <DevtoolsSlot />
    </>
  )
}

function DevtoolsSlot() {
  if (!AppDevtools) return null

  return (
    <Suspense fallback={null}>
      <AppDevtools />
    </Suspense>
  )
}

function RootErrorComponent({ error, reset }: ErrorComponentProps) {
  const { t } = useTranslation('common')
  const message = error instanceof Error ? error.message : 'Unknown error'

  return (
    <>
      <div className="flex min-h-svh items-center justify-center bg-[radial-gradient(circle_at_top_left,rgba(242,105,38,0.12),transparent_28%),linear-gradient(180deg,rgba(255,248,245,0.92)_0%,rgba(255,255,255,1)_32%)] px-4 py-10">
        <Card className="w-full max-w-2xl border-destructive/20 bg-background/95 shadow-lg">
          <CardHeader className="gap-3">
            <div className="flex items-center gap-3 text-destructive">
              <TriangleAlertIcon className="size-5" />
              <CardTitle>{t('errorBoundary.title')}</CardTitle>
            </div>
            <CardDescription>{t('errorBoundary.description')}</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            <div className="rounded-lg border border-destructive/15 bg-destructive/5 px-4 py-3 font-mono text-sm text-foreground">
              {message}
            </div>
          </CardContent>
          <CardFooter className="justify-end gap-2">
            <Button variant="outline" onClick={() => window.location.reload()}>
              {t('errorBoundary.reload')}
            </Button>
            <Button onClick={() => reset()}>
              <RotateCcwIcon />
              {t('errorBoundary.retry')}
            </Button>
          </CardFooter>
        </Card>
      </div>
      <DevtoolsSlot />
    </>
  )
}

function RootNotFoundComponent() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center p-6 text-center">
      <div className="rounded-full border border-border/80 bg-muted/40 p-3 text-muted-foreground">
        <TriangleAlertIcon className="size-6 text-amber-500" />
      </div>
      <h2 className="mt-3 text-sm font-semibold text-foreground">页面不存在 (404 Not Found)</h2>
      <p className="mt-1 text-xs text-muted-foreground font-mono">
        您访问的路径未注册或已整合至全局中枢。
      </p>
      <div className="mt-4 flex gap-2">
        <Button variant="outline" size="sm" onClick={() => window.history.back()} className="text-xs">
          返回上一页
        </Button>
        <Button size="sm" onClick={() => { window.location.href = '/home' }} className="text-xs">
          返回首页
        </Button>
      </div>
    </div>
  )
}
