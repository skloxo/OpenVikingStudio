import { useTranslation } from 'react-i18next'

const KEY_ESCAPE_LABEL = 'esc'

export interface FindPaletteFooterProps {
  isDirBrowse: boolean
  hasResults: boolean
  visibleCount: number
}

export function FindPaletteFooter({
  isDirBrowse,
  hasResults,
  visibleCount,
}: FindPaletteFooterProps) {
  const { t } = useTranslation('resources')

  if (isDirBrowse) {
    return (
      <div className="flex items-center gap-3 border-t px-4 py-2 text-xs text-muted-foreground/70">
        <span>
          <kbd className="rounded border border-border bg-muted/50 px-1.5 py-0.5 font-mono text-xs text-foreground/70">
            ↑↓
          </kbd>{' '}
          {t('searchPalette.footer.dirMode.select')}
        </span>
        <span>
          <kbd className="rounded border border-border bg-muted/50 px-1.5 py-0.5 font-mono text-xs text-foreground/70">
            ←→
          </kbd>{' '}
          {t('searchPalette.footer.dirMode.level')}
        </span>
        <span>
          <kbd className="rounded border border-border bg-muted/50 px-1.5 py-0.5 font-mono text-xs text-foreground/70">
            ↵
          </kbd>{' '}
          {t('searchPalette.footer.dirMode.confirm')}
        </span>
        <span>
          <kbd className="rounded border border-border bg-muted/50 px-1.5 py-0.5 font-mono text-xs text-foreground/70">
            {KEY_ESCAPE_LABEL}
          </kbd>{' '}
          {t('searchPalette.footer.dirMode.cancel')}
        </span>
      </div>
    )
  }

  if (!hasResults) return null

  return (
    <div className="flex items-center gap-3 border-t px-4 py-2 text-xs text-muted-foreground/70">
      <span>
        <kbd className="rounded border border-border bg-muted/50 px-1.5 py-0.5 font-mono text-xs text-foreground/70">
          ↑↓
        </kbd>{' '}
        {t('searchPalette.footer.resultMode.navigate')}
      </span>
      <span>
        <kbd className="rounded border border-border bg-muted/50 px-1.5 py-0.5 font-mono text-xs text-foreground/70">
          ↵
        </kbd>{' '}
        {t('searchPalette.footer.resultMode.open')}
      </span>
      <span>
        <kbd className="rounded border border-border bg-muted/50 px-1.5 py-0.5 font-mono text-xs text-foreground/70">
          {KEY_ESCAPE_LABEL}
        </kbd>{' '}
        {t('searchPalette.footer.resultMode.close')}
      </span>
      <span className="ml-auto tabular-nums">
        {t('searchPalette.footer.resultMode.count', {
          count: visibleCount,
        })}
      </span>
    </div>
  )
}
