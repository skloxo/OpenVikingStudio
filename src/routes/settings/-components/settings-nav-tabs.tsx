import * as React from 'react'
import {
  PackageIcon,
  ShieldAlertIcon,
  SlidersHorizontalIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { cn } from '#/lib/utils'
import type { SettingsTab } from '../-lib/settings-types'

interface SettingsNavTabsProps {
  activeTab: SettingsTab
  onTabChange: (tab: SettingsTab) => void
}

export function SettingsNavTabs({
  activeTab,
  onTabChange,
}: SettingsNavTabsProps) {
  const { t } = useTranslation('settings')

  return (
    <div className="flex items-center gap-1.5 bg-muted/40 p-1 rounded-lg border border-border/60 w-fit">
      <button
        type="button"
        onClick={() => onTabChange('general')}
        className={cn(
          'flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all cursor-pointer select-none',
          activeTab === 'general'
            ? 'bg-background text-foreground shadow-2xs font-semibold'
            : 'text-muted-foreground hover:text-foreground',
        )}
      >
        <SlidersHorizontalIcon className="size-3.5 text-cyan-500" />
        <span>{t('hub.tabs.general')}</span>
      </button>

      <button
        type="button"
        onClick={() => onTabChange('privacy')}
        className={cn(
          'flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all cursor-pointer select-none',
          activeTab === 'privacy'
            ? 'bg-background text-foreground shadow-2xs font-semibold'
            : 'text-muted-foreground hover:text-foreground',
        )}
      >
        <ShieldAlertIcon className="size-3.5 text-amber-500" />
        <span>{t('hub.tabs.privacy')}</span>
      </button>

      <button
        type="button"
        onClick={() => onTabChange('dataOps')}
        className={cn(
          'flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all cursor-pointer select-none',
          activeTab === 'dataOps'
            ? 'bg-background text-foreground shadow-2xs font-semibold'
            : 'text-muted-foreground hover:text-foreground',
        )}
      >
        <PackageIcon className="size-3.5 text-cyan-500" />
        <span>{t('hub.tabs.dataOps')}</span>
      </button>
    </div>
  )
}
