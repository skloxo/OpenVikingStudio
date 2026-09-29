/**
 * playground-dialogs.tsx
 * Playground 的模态弹窗与移动端抽屉聚合组件：
 * 包括添加资源弹窗、后台任务追踪弹窗、FindPalette 搜索浮层与移动端 Action 抽屉。
 */
import { toast } from 'sonner'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '#/components/ui/dialog'
import { AddResourceForm } from '#/routes/resources/-components/add-resource-page'
import { FindPalette } from '#/routes/resources/-components/find-palette'
import { UploadTaskDialog } from '#/routes/resources/-components/upload-task-dialog'
import type { ResourceUploadTask } from '#/routes/resources/-hooks/use-resource-upload'
import type { VikingFsEntry } from '#/routes/resources/-types/viking-fm'
import type { PlaygroundPanel, ResourceOpenHandler } from '../-lib/types'
import { PlaygroundMobileActionScreen } from './playground-action-panel'

export type PlaygroundDialogsProps = {
  actionPanelOpen: boolean
  activePanel: PlaygroundPanel
  currentUri: string
  entries: VikingFsEntry[]
  findPaletteOpen: boolean
  isCompactLayout: boolean
  onClearTasks: () => void
  onCloseActionPanel: () => void
  onCloseFindPalette: () => void
  onInvalidateList: () => void
  onNavigateDirectory: (rawUri: string) => void
  onOpenAddResource: () => void
  onOpenResource: ResourceOpenHandler
  onPanelChange: (panel: PlaygroundPanel) => void
  onSessionChange: (sessionId: string) => void
  onSetTaskDialogOpen: (open: boolean) => void
  onUploadDialogOpenChange: (open: boolean) => void
  openingUri: string | null
  sessionId?: string
  t: (key: string, options?: Record<string, unknown>) => string
  taskDialogOpen: boolean
  tasks: ResourceUploadTask[]
  uploadDialogOpen: boolean
}

export function PlaygroundDialogs({
  actionPanelOpen,
  activePanel,
  currentUri,
  entries,
  findPaletteOpen,
  isCompactLayout,
  onClearTasks,
  onCloseActionPanel,
  onCloseFindPalette,
  onInvalidateList,
  onNavigateDirectory,
  onOpenAddResource,
  onOpenResource,
  onPanelChange,
  onSessionChange,
  onSetTaskDialogOpen,
  onUploadDialogOpenChange,
  openingUri,
  sessionId,
  t,
  taskDialogOpen,
  tasks,
  uploadDialogOpen,
}: PlaygroundDialogsProps) {
  return (
    <>
      {actionPanelOpen && isCompactLayout ? (
        <PlaygroundMobileActionScreen
          activePanel={activePanel}
          currentUri={currentUri}
          entries={entries}
          onClose={onCloseActionPanel}
          onOpenAddResource={onOpenAddResource}
          onOpenResource={onOpenResource}
          onPanelChange={onPanelChange}
          onSessionChange={onSessionChange}
          open={actionPanelOpen}
          openingUri={openingUri}
          sessionId={sessionId}
        />
      ) : null}

      <Dialog
        open={uploadDialogOpen}
        onOpenChange={onUploadDialogOpenChange}
      >
        <DialogContent className="max-h-[min(86vh,760px)] gap-0 overflow-hidden p-0 sm:max-w-4xl">
          <DialogHeader className="border-b px-6 py-5">
            <DialogTitle className="text-xl">
              {t('addResource.title')}
            </DialogTitle>
            <DialogDescription>
              {t('addResource.description')}
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-[calc(min(86vh,760px)-6rem)] overflow-y-auto px-6 py-5">
            <AddResourceForm
              onSubmitted={() => {
                onUploadDialogOpenChange(false)
                onInvalidateList()
                toast.success(t('addResource.submitted'))
              }}
            />
          </div>
        </DialogContent>
      </Dialog>

      <UploadTaskDialog
        open={taskDialogOpen}
        onOpenChange={onSetTaskDialogOpen}
        tasks={tasks}
        onClearTasks={onClearTasks}
      />

      <FindPalette
        open={findPaletteOpen}
        onClose={onCloseFindPalette}
        onNavigate={(uri) => void onOpenResource(uri)}
        onNavigateDir={onNavigateDirectory}
        scopeUri={currentUri}
      />
    </>
  )
}
