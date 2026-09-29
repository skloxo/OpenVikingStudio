/**
 * playground-main-toolbar.tsx
 * Playground 主内容区域顶栏：展示当前选中的 URI、复制路径、响应式面板切换与右栏展开折叠按钮。
 */
import {
  BotIcon,
  ClipboardIcon,
  PanelRightOpenIcon,
  TerminalIcon,
} from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '#/components/ui/button'
import { copyTextToClipboard } from '#/lib/clipboard'
import type { PlaygroundPanel } from '../-lib/types'

export type PlaygroundMainToolbarProps = {
  activePanel: PlaygroundPanel
  displayUri: string
  isFocusCanvas: boolean
  onOpenActionPanel: (panel: PlaygroundPanel) => void
  onRevealResource: (uri: string) => void
  onToggleRightCollapsed: () => void
  rightCollapsed: boolean
  selectedUri: string
  t: (key: string, options?: Record<string, unknown>) => string
}

export function PlaygroundMainToolbar({
  activePanel,
  displayUri,
  isFocusCanvas,
  onOpenActionPanel,
  onRevealResource,
  onToggleRightCollapsed,
  rightCollapsed,
  selectedUri,
  t,
}: PlaygroundMainToolbarProps) {
  return (
    <div className="flex min-h-14 items-center gap-3 border-b px-4">
      <button
        type="button"
        className="min-w-0 flex-1 truncate rounded px-1.5 py-1 text-left font-mono text-xs font-semibold text-foreground transition-colors hover:bg-muted"
        title={selectedUri}
        onClick={() => void onRevealResource(selectedUri)}
      >
        {displayUri}
      </button>
      <Button
        type="button"
        size="icon-sm"
        variant="ghost"
        title={t('copyUri')}
        onClick={() => {
          void copyTextToClipboard(selectedUri)
            .then(() => {
              toast.success(t('copied'))
            })
            .catch(() => {
              toast.error(t('copyFailed'))
            })
        }}
      >
        <ClipboardIcon className="size-4" />
      </Button>
      <div className="flex shrink-0 items-center gap-1 lg:hidden">
        <Button
          type="button"
          size="icon-sm"
          variant={activePanel === 'terminal' ? 'secondary' : 'ghost'}
          title={t('tabs.terminal')}
          aria-label={t('tabs.terminal')}
          onClick={() => onOpenActionPanel('terminal')}
        >
          <TerminalIcon className="size-4" />
        </Button>
        <Button
          type="button"
          size="icon-sm"
          variant={activePanel === 'agent' ? 'secondary' : 'ghost'}
          title={t('tabs.agent')}
          aria-label={t('tabs.agent')}
          onClick={() => onOpenActionPanel('agent')}
        >
          <BotIcon className="size-4" />
        </Button>
      </div>
      {rightCollapsed && !isFocusCanvas ? (
        <Button
          type="button"
          size="icon-sm"
          variant="ghost"
          className="hidden shrink-0 lg:inline-flex"
          title={t('actionPanel.expand')}
          aria-label={t('actionPanel.expand')}
          onClick={onToggleRightCollapsed}
        >
          <PanelRightOpenIcon className="size-4" />
        </Button>
      ) : null}
    </div>
  )
}
