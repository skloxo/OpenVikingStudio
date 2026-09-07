import * as React from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

import { Badge } from '#/components/ui/badge'
import { useAppConnection } from '#/hooks/use-app-connection'
import { DataOpsTab } from './-components/data-ops-tab'
import { GeneralTab } from './-components/general-tab'
import { PrivacyTab } from './-components/privacy-tab'
import { SettingsNavTabs } from './-components/settings-nav-tabs'
import type { SettingsTab } from './-lib/settings-types'

export const Route = createFileRoute('/settings')({
  component: UnifiedSettingsRoute,
})

function UnifiedSettingsRoute() {
  const { t } = useTranslation('settings')
  const [activeTab, setActiveTab] = React.useState<SettingsTab>('general')
  const { serverMode } = useAppConnection()

  return (
    <div className="flex w-full min-w-0 flex-col gap-5">
      {/* Top Header */}
      <header className="flex flex-col gap-1">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold tracking-tight">
              {t('hub.title')}
            </h1>
          </div>
          <Badge
            variant="outline"
            className="text-[11px] font-normal border-border/80"
          >
            {t(`serverMode.${serverMode}`)}
          </Badge>
        </div>
        <p className="max-w-3xl text-xs leading-5 text-muted-foreground">
          {t('hub.description')}
        </p>
      </header>

      {/* 3-Tab Pill Switcher */}
      <SettingsNavTabs activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Tab Panels */}
      {activeTab === 'general' && <GeneralTab />}
      {activeTab === 'privacy' && <PrivacyTab />}
      {activeTab === 'dataOps' && <DataOpsTab />}
    </div>
  )
}
