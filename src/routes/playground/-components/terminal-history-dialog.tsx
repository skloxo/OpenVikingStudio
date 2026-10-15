/**
 * terminal-history-dialog.tsx
 * 从 terminal-panel.tsx 接缝提取的终端历史记录 Dialog 面板。
 */
import { TrashIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Button } from '#/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '#/components/ui/dialog'
import type { ResourceOpenHandler, TerminalEntry } from '../-lib/types'
import { TerminalHistoryItem } from './terminal-history-item'

interface TerminalHistoryDialogProps {
  history: TerminalEntry[]
  open: boolean
  onOpenChange: (open: boolean) => void
  onClearHistory: () => void
  onOpenResource: ResourceOpenHandler
  openingUri: string | null
}

export function TerminalHistoryDialog({
  history,
  open,
  onOpenChange,
  onClearHistory,
  onOpenResource,
  openingUri,
}: TerminalHistoryDialogProps) {
  const { t } = useTranslation('playground')

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="gap-4 sm:max-w-2xl">
        <DialogHeader>
          <div className="flex items-start gap-3">
            <div className="min-w-0 flex-1">
              <DialogTitle>{t('terminal.historyTitle')}</DialogTitle>
              <DialogDescription>
                {t('terminal.historyDescription')}
              </DialogDescription>
            </div>
            {history.length > 0 ? (
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                className="size-7 shrink-0"
                title={t('terminal.clearHistory')}
                onClick={onClearHistory}
              >
                <TrashIcon className="size-3.5" />
              </Button>
            ) : null}
          </div>
        </DialogHeader>
        <div className="max-h-115 overflow-y-auto pr-1">
          {history.length === 0 ? (
            <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
              {t('terminal.noHistory')}
            </div>
          ) : (
            <div className="space-y-3">
              {history.map((entry) => (
                <TerminalHistoryItem
                  key={`dialog-${entry.id}`}
                  entry={entry}
                  onOpenResource={onOpenResource}
                  openingUri={openingUri}
                />
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
