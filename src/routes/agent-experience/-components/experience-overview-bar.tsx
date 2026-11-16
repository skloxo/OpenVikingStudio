import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'

import { Card, CardContent } from '#/components/ui/card'
import { useAppConnection } from '#/hooks/use-app-connection'
import { fetchAgentEvolutionOverview } from '#/lib/agent-evolution/api'

export function ExperienceOverviewBar() {
  const { t } = useTranslation('agentExperiencePage')
  const { identityScopeKey } = useAppConnection()

  const overviewQuery = useQuery({
    queryFn: () => fetchAgentEvolutionOverview(),
    queryKey: ['agent-evolution-overview', identityScopeKey],
    retry: false,
    staleTime: 30_000,
  })

  if (!overviewQuery.data) return null
  const {
    total_experiences: totalExperiences,
    total_trajectories: totalTrajectories,
    success_rate: successRate,
    recent_24h_active_count: active24h,
  } = overviewQuery.data

  const tiles = [
    {
      label: t('overview.experiences'),
      value: String(totalExperiences),
      accent: 'text-foreground',
    },
    {
      label: t('overview.trajectories'),
      value: String(totalTrajectories),
      accent: 'text-foreground',
    },
    {
      label: t('overview.successRate'),
      value: `${successRate}%`,
      accent: 'text-cyan-600 dark:text-cyan-400',
    },
    {
      label: t('overview.active24h'),
      value: String(active24h),
      accent: 'text-cyan-600 dark:text-cyan-400',
    },
  ] as const

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {tiles.map((tile) => (
        <Card
          key={tile.label}
          size="sm"
          className="bg-background shadow-none ring-border/70"
        >
          <CardContent className="grid gap-1 py-1">
            <span className="text-xs text-muted-foreground">{tile.label}</span>
            <span className={`text-xl font-semibold tabular-nums ${tile.accent}`}>
              {tile.value}
            </span>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
