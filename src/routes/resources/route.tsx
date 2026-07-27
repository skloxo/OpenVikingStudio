import * as React from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { Plus, Search } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '#/components/ui/dialog'
import { normalizeDirUri, parentUri } from './-lib/normalize'
import { useVikingFsList } from './-hooks/viking-fm'
import { DirBrowser } from './-components/dir-browser'
import { FindPalette } from './-components/find-palette'
import { AddResourceForm } from './-components/add-resource-page'

export const Route = createFileRoute('/resources')({
  component: ResourcesRoute,
})

const VIKING_ROOT_URI = 'viking://'

function ResourcesRoute() {
  const { t } = useTranslation('resources')
  const [currentUri, setCurrentUri] = React.useState(VIKING_ROOT_URI)
  const [historyStack, setHistoryStack] = React.useState<string[]>([])
  const [activeIndex, setActiveIndex] = React.useState<number>(-1)
  const [paletteOpen, setPaletteOpen] = React.useState(false)
  const [addDialogOpen, setAddDialogOpen] = React.useState(false)

  const normalizedUri = normalizeDirUri(currentUri)
  const listQuery = useVikingFsList(normalizedUri, {
    output: 'agent',
    showAllHidden: true,
    nodeLimit: 200,
  })

  const items = React.useMemo(() => {
    if (!listQuery.data?.entries) return []
    const entries = listQuery.data.entries
    const dirs = entries.filter((e) => e.isDir)
    const files = entries.filter((e) => !e.isDir)
    return [...dirs, ...files]
  }, [listQuery.data])

  const handleEnterDir = React.useCallback(
    (uri: string) => {
      setHistoryStack((prev) => [...prev, currentUri])
      setCurrentUri(uri)
      setActiveIndex(-1)
    },
    [currentUri],
  )

  const handleGoBack = React.useCallback(() => {
    if (historyStack.length > 0) {
      const prev = historyStack[historyStack.length - 1]
      setHistoryStack((stack) => stack.slice(0, -1))
      setCurrentUri(prev)
      setActiveIndex(-1)
    } else if (currentUri !== VIKING_ROOT_URI) {
      setCurrentUri(parentUri(currentUri))
      setActiveIndex(-1)
    }
  }, [currentUri, historyStack])

  return (
    <div className="flex h-[calc(100vh-5.5rem)] w-full min-w-0 flex-col gap-4">
      <header className="flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="grid gap-1">
          <h1 className="text-2xl font-semibold tracking-tight">
            {t('title', { defaultValue: '资源库' })}
          </h1>
          <p className="text-sm text-muted-foreground">
            {t('subtitle', {
              defaultValue: '管理与浏览 OpenViking 文件系统资源 (viking://)',
            })}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-8 gap-1.5 rounded-sm px-3 text-xs"
            onClick={() => setPaletteOpen(true)}
          >
            <Search className="size-3.5" />
            <span>{t('searchPalette', { defaultValue: '查找与快捷搜索' })}</span>
          </Button>
          <Button
            type="button"
            size="sm"
            className="h-8 gap-1.5 rounded-sm px-3 text-xs"
            onClick={() => setAddDialogOpen(true)}
          >
            <Plus className="size-3.5" />
            <span>{t('addResource', { defaultValue: '添加资源' })}</span>
          </Button>
        </div>
      </header>

      <Card className="flex min-h-0 flex-1 flex-col overflow-hidden rounded border border-border/60 shadow-xs">
        <DirBrowser
          currentUri={currentUri}
          items={items}
          activeIndex={activeIndex}
          loading={listQuery.isLoading}
          errored={listQuery.isError}
          onCursorChange={setActiveIndex}
          onEnterDir={handleEnterDir}
          onOpenFile={() => {}}
          onGoBack={handleGoBack}
        />
      </Card>

      <FindPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onNavigate={(uri) => {
          setPaletteOpen(false)
          if (uri.endsWith('/')) {
            handleEnterDir(uri)
          }
        }}
        onNavigateDir={handleEnterDir}
      />

      <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
        <DialogContent className="max-w-2xl rounded p-0 overflow-hidden">
          <DialogHeader className="px-5 pt-4 pb-2 border-b border-border/60">
            <DialogTitle className="text-base font-semibold">
              {t('addResourceTitle', { defaultValue: '添加新资源' })}
            </DialogTitle>
          </DialogHeader>
          <div className="p-4 max-h-[80vh] overflow-y-auto">
            <AddResourceForm onSubmitted={() => setAddDialogOpen(false)} />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
