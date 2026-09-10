import { useMemo, useState } from 'react'
import { BrainCircuitIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Button } from '#/components/ui/button'
import {
  ImpactCounts,
  UnifiedMemoryImpactDrawer,
  summarizeDiffs,
} from '#/components/memory-impact'
import { useSessionMemoryDiffs } from '#/lib/sessions/use-sessions'
import type { SessionMeta } from '@ov-server/api/v1/sessions'

export interface MemoryImpactProps {
  session?: SessionMeta
}

/**
 * 会话记忆影响抽屉适配器 (向后兼容层)
 * 底层已全量收敛至系统通用公共轮子 UnifiedMemoryImpactDrawer。
 */
export function MemoryImpact({ session }: MemoryImpactProps) {
  const { t } = useTranslation('sessions')
  const [open, setOpen] = useState(false)
  const diffsQuery = useSessionMemoryDiffs(session, open)
  const diffs = diffsQuery.data ?? []
  const totals = useMemo(() => summarizeDiffs(diffs), [diffs])
  const totalChanges = totals.adds + totals.updates + totals.deletes

  if (!session || session.commit_count <= 0) return null

  return (
    <>
      <Button
        aria-label={t('impact.open')}
        className="h-7 gap-1.5 rounded-full border-primary/20 bg-primary/5 px-2.5 text-xs text-primary hover:bg-primary/10"
        onClick={() => setOpen(true)}
        size="xs"
        variant="outline"
      >
        <BrainCircuitIcon className="size-3.5" />
        <span>{t('impact.title')}</span>
        {totalChanges > 0 ? <ImpactCounts totals={totals} /> : null}
      </Button>

      <UnifiedMemoryImpactDrawer
        session={session}
        open={open}
        onOpenChange={setOpen}
      />
    </>
  )
}
