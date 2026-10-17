/**
 * playground-action-panel.tsx
 * 从 playground/route.tsx L749-L980 提取的 Action 面板相关组件与 hook
 */
import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  ArrowLeftIcon,
  BotIcon,
  LayersIcon,
  PanelRightCloseIcon,
  TerminalIcon,
} from 'lucide-react'
import { Button } from '#/components/ui/button'
import type { VikingFsEntry } from '#/routes/resources/-types/viking-fm'

import { AgentPanel } from './agent-panel'
import { PanelTab } from './context-explorer'
import { TerminalPanel } from './terminal-panel'
import { VisualActionLauncher } from './visual-action-launcher'
import type { PlaygroundPanel, ResourceOpenHandler } from '../-lib/types'

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useIsCompactPlaygroundLayout() {
  const [isCompact, setIsCompact] = useState(() =>
    typeof window !== 'undefined' && typeof window.matchMedia === 'function'
      ? window.matchMedia('(max-width: 1023px)').matches
      : false,
  )

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') {
      return
    }
    const mql = window.matchMedia('(max-width: 1023px)')
    const onChange = () => setIsCompact(mql.matches)
    onChange()
    mql.addEventListener('change', onChange)
    return () => mql.removeEventListener('change', onChange)
  }, [])

  return isCompact
}

// ─── PlaygroundActionTabs ──────────────────────────────────────────────────────

export function PlaygroundActionTabs({
  activePanel,
  onPanelChange,
}: {
  activePanel: PlaygroundPanel
  onPanelChange: (panel: PlaygroundPanel) => void
}) {
  const { t } = useTranslation('playground')

  return (
    <div className="inline-flex rounded-lg border bg-background p-1">
      <PanelTab
        active={activePanel === 'terminal'}
        icon={TerminalIcon}
        label={t('tabs.terminal')}
        onClick={() => onPanelChange('terminal')}
      />
      <PanelTab
        active={activePanel === 'agent'}
        icon={BotIcon}
        label={t('tabs.agent')}
        onClick={() => onPanelChange('agent')}
      />
      <PanelTab
        active={activePanel === 'visualLauncher'}
        icon={LayersIcon}
        label={t('tabs.visualLauncher')}
        onClick={() => onPanelChange('visualLauncher')}
      />
    </div>
  )
}

// ─── PlaygroundActionContent ──────────────────────────────────────────────────

export function PlaygroundActionContent({
  activePanel,
  currentUri,
  entries,
  onOpenAddResource,
  onOpenResource,
  onSessionChange,
  openingUri,
  sessionId,
  toolbarContainer,
}: {
  activePanel: PlaygroundPanel
  currentUri: string
  entries: VikingFsEntry[]
  onOpenAddResource: () => void
  onOpenResource: ResourceOpenHandler
  onSessionChange: (sessionId: string) => void
  openingUri: string | null
  sessionId?: string
  toolbarContainer: HTMLDivElement | null
}) {
  return (
    <div className="flex h-full min-h-0 flex-col">
      {activePanel === 'terminal' ? (
        <TerminalPanel
          currentUri={currentUri}
          entries={entries}
          onOpenAddResource={onOpenAddResource}
          onOpenResource={onOpenResource}
          onSessionChange={onSessionChange}
          openingUri={openingUri}
          sessionId={sessionId}
          toolbarContainer={toolbarContainer}
        />
      ) : activePanel === 'agent' ? (
        <AgentPanel
          initialSessionId={sessionId}
          onOpenResource={onOpenResource}
          onSessionChange={onSessionChange}
          toolbarContainer={toolbarContainer}
        />
      ) : (
        <VisualActionLauncher />
      )}
    </div>
  )
}

// ─── PlaygroundActionPanel ────────────────────────────────────────────────────

export function PlaygroundActionPanel({
  activePanel,
  currentUri,
  entries,
  onCollapse,
  onOpenAddResource,
  onOpenResource,
  onPanelChange,
  onSessionChange,
  openingUri,
  sessionId,
}: {
  activePanel: PlaygroundPanel
  currentUri: string
  entries: VikingFsEntry[]
  onCollapse: () => void
  onOpenAddResource: () => void
  onOpenResource: ResourceOpenHandler
  onPanelChange: (panel: PlaygroundPanel) => void
  onSessionChange: (sessionId: string) => void
  openingUri: string | null
  sessionId?: string
}) {
  const { t } = useTranslation('playground')
  const [toolbarContainer, setToolbarContainer] =
    useState<HTMLDivElement | null>(null)

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex h-14 shrink-0 items-center gap-2 border-b px-3">
        <PlaygroundActionTabs
          activePanel={activePanel}
          onPanelChange={onPanelChange}
        />
        <div
          ref={setToolbarContainer}
          className="ml-auto flex min-w-0 items-center gap-1"
        />
        <Button
          type="button"
          size="icon-sm"
          variant="ghost"
          className="shrink-0"
          title={t('actionPanel.collapse')}
          aria-label={t('actionPanel.collapse')}
          onClick={onCollapse}
        >
          <PanelRightCloseIcon className="size-4" />
        </Button>
      </div>
      <PlaygroundActionContent
        activePanel={activePanel}
        currentUri={currentUri}
        entries={entries}
        onOpenAddResource={onOpenAddResource}
        onOpenResource={onOpenResource}
        onSessionChange={onSessionChange}
        openingUri={openingUri}
        sessionId={sessionId}
        toolbarContainer={toolbarContainer}
      />
    </div>
  )
}

// ─── PlaygroundMobileActionScreen ────────────────────────────────────────────

export function PlaygroundMobileActionScreen({
  activePanel,
  currentUri,
  entries,
  onClose,
  onOpenAddResource,
  onOpenResource,
  onPanelChange,
  onSessionChange,
  open,
  openingUri,
  sessionId,
}: {
  activePanel: PlaygroundPanel
  currentUri: string
  entries: VikingFsEntry[]
  onClose: () => void
  onOpenAddResource: () => void
  onOpenResource: ResourceOpenHandler
  onPanelChange: (panel: PlaygroundPanel) => void
  onSessionChange: (sessionId: string) => void
  open: boolean
  openingUri: string | null
  sessionId?: string
}) {
  const { t } = useTranslation(['playground', 'resources'])
  const [toolbarContainer, setToolbarContainer] =
    useState<HTMLDivElement | null>(null)

  if (!open) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 flex min-h-0 flex-col bg-background lg:hidden">
      <div className="flex h-14 shrink-0 items-center gap-2 border-b bg-background px-3">
        <Button
          type="button"
          size="icon-sm"
          variant="ghost"
          title={t('dirBrowser.back', { ns: 'resources' })}
          aria-label={t('dirBrowser.back', { ns: 'resources' })}
          onClick={onClose}
        >
          <ArrowLeftIcon className="size-4" />
        </Button>
        <PlaygroundActionTabs
          activePanel={activePanel}
          onPanelChange={onPanelChange}
        />
        <div
          ref={setToolbarContainer}
          className="ml-auto flex min-w-0 items-center gap-1"
        />
      </div>
      <div className="min-h-0 flex-1">
        <PlaygroundActionContent
          activePanel={activePanel}
          currentUri={currentUri}
          entries={entries}
          onOpenAddResource={onOpenAddResource}
          onOpenResource={onOpenResource}
          onSessionChange={onSessionChange}
          openingUri={openingUri}
          sessionId={sessionId}
          toolbarContainer={toolbarContainer}
        />
      </div>
    </div>
  )
}
