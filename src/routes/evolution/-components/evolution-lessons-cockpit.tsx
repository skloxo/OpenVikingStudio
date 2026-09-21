import * as React from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { RefreshCwIcon, LayersIcon, SearchIcon } from 'lucide-react'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { ovClient } from '#/lib/ov-client'
import { HarnessLessonsTable, type LessonItem } from '#/routes/harness-logs/-components/harness-lessons-table'

export function EvolutionLessonsCockpit() {
  const { t } = useTranslation('skillsPage')
  const [searchQuery, setSearchQuery] = React.useState('')

  const lessonsQuery = useQuery({
    queryKey: ['evolution-harness-lessons-cockpit'],
    queryFn: async () => {
      try {
        const res = await ovClient.instance.get<{
          lessons_count?: number
          lessons_detail?: LessonItem[]
        }>('/api/v1/system/harness_metrics')
        return res.data?.lessons_detail ?? []
      } catch (err) {
        console.warn('Failed to fetch evolution lessons:', err)
        return []
      }
    },
    staleTime: 15_000,
  })

  const lessons = lessonsQuery.data ?? []

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border/60 bg-card/60 p-3">
        <div className="flex items-center gap-2">
          <LayersIcon className="size-4 text-cyan-400" />
          <div>
            <div className="text-xs font-semibold text-foreground">
              事故与演进教训档案库
            </div>
            <div className="text-[12px] text-muted-foreground font-mono">
              汇集运行时门禁拦截事件与历史反思，作为 Hermes 经历微补丁的一手输入原料
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative">
            <SearchIcon className="absolute left-2.5 top-2 size-3.5 text-muted-foreground" />
            <Input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索规则 / 故障 / 反思..."
              className="h-7 w-60 rounded border-border/60 pl-8 text-xs font-mono"
            />
          </div>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-7 text-xs rounded"
            disabled={lessonsQuery.isFetching}
            onClick={() => void lessonsQuery.refetch()}
          >
            <RefreshCwIcon className={lessonsQuery.isFetching ? 'size-3.5 animate-spin' : 'size-3.5'} />
            {t('refresh')}
          </Button>
        </div>
      </div>

      <HarnessLessonsTable lessons={lessons} searchQuery={searchQuery} />
    </div>
  )
}
