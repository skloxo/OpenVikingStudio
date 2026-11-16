import * as React from 'react'
import { useTranslation } from 'react-i18next'

export function HighlightedText({
  keyword,
  text,
}: {
  keyword: string
  text: string
}) {
  const normalizedKeyword = keyword.trim().toLocaleLowerCase()
  if (!normalizedKeyword) return <>{text}</>

  const normalizedText = text.toLocaleLowerCase()
  const fragments: React.ReactNode[] = []
  let cursor = 0
  let matchIndex = normalizedText.indexOf(normalizedKeyword)

  while (matchIndex !== -1) {
    if (matchIndex > cursor) {
      fragments.push(text.slice(cursor, matchIndex))
    }
    const matchEnd = matchIndex + normalizedKeyword.length
    fragments.push(
      <mark
        key={`${matchIndex}-${matchEnd}`}
        className="rounded-xs bg-primary/15 px-0.5 text-inherit"
      >
        {text.slice(matchIndex, matchEnd)}
      </mark>,
    )
    cursor = matchEnd
    matchIndex = normalizedText.indexOf(normalizedKeyword, cursor)
  }
  if (cursor < text.length) {
    fragments.push(text.slice(cursor))
  }
  return <>{fragments}</>
}

export function EmptyHelpChecklist() {
  const { t } = useTranslation('agentExperiencePage')
  const reasons = [
    t('help.reasonConnected'),
    t('help.reasonSessions'),
    t('help.reasonCommit'),
  ]

  return (
    <div className="grid max-w-md gap-2 rounded-lg border border-dashed bg-muted/30 px-4 py-3 text-left">
      <p className="text-sm text-muted-foreground">{t('help.title')}</p>
      <ol className="grid gap-1.5 text-sm text-muted-foreground">
        {reasons.map((reason, index) => (
          <li className="flex items-center gap-2" key={reason}>
            <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-medium text-muted-foreground">
              {index + 1}
            </span>
            {reason}
          </li>
        ))}
      </ol>
    </div>
  )
}
