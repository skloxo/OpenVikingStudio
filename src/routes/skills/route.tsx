import * as React from 'react'
import { Link, createFileRoute } from '@tanstack/react-router'
import { LoaderCircleIcon, SparklesIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import { SkillsPagination } from './-components/pagination'
import { SkillCard } from './-components/skill-card'
import { SkillsFilterBar } from './-components/skills-filter-bar'
import { SkillsMetricsCards } from './-components/skills-metrics-cards'
import { SkillDetailSheet } from './-components/skill-detail-sheet'
import { getErrorMessage } from './-lib/skill-data'
import { useSkillsData } from './-lib/use-skills'

export const Route = createFileRoute('/skills')({
  component: SkillsRoute,
})

function SkillsRoute() {
  const { t } = useTranslation('skillsPage')
  const data = useSkillsData()
  const {
    skills, filteredSkills, paginatedSkills, skillsQuery, detailQuery,
    selectedSkill, setSelectedSkill, searchQuery, setSearchQuery,
    activeScopeFilter, setActiveScopeFilter, refinedSkills, handleRefineSkill,
    currentPage, setCurrentPage, pageSize, setPageSize,
    connectionUnavailable, harnessMetrics,
  } = data

  return (
    <div className="flex w-full min-w-0 flex-col gap-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div className="grid gap-1">
          <h1 className="text-xl font-semibold tracking-tight flex items-center gap-2">🧠 技能中心</h1>
          <p className="max-w-3xl text-xs text-muted-foreground font-mono">{t('description')}</p>
        </div>
        <Badge variant="outline" className="text-[10px] font-mono border-border bg-muted/30 text-foreground px-1.5 py-0.5">
          🕒 统计范围: 最近 24 小时 (24H Rolling)
        </Badge>
      </header>

      <SkillsMetricsCards metrics={harnessMetrics} totalSkills={skills.length} />

      <SkillsFilterBar
        skills={skills}
        activeScopeFilter={activeScopeFilter}
        onSelectScopeFilter={setActiveScopeFilter}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        refinedSkills={refinedSkills}
        onRefineSkill={handleRefineSkill}
      />

      {skillsQuery.isLoading ? (
        <Card className="min-h-56 items-center justify-center">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <LoaderCircleIcon className="size-4 animate-spin" />
            {t('loading')}
          </div>
        </Card>
      ) : skillsQuery.isError ? (
        <Card className="min-h-56 items-center justify-center px-6 text-center">
          <SparklesIcon className="size-8 text-destructive/70" />
          <div className="grid gap-1">
            <p className="font-medium">{t('loadFailed')}</p>
            <p className="max-w-xl text-sm text-muted-foreground">
              {connectionUnavailable ? t('networkError') : getErrorMessage(skillsQuery.error)}
            </p>
            {connectionUnavailable ? (
              <Button render={<Link to="/settings" />} nativeButton={false} variant="outline" size="sm" className="mx-auto mt-2">
                {t('connectionSettings')}
              </Button>
            ) : null}
          </div>
        </Card>
      ) : filteredSkills.length === 0 ? (
        <Card className="rounded border border-dashed border-border/60 bg-muted/10 p-8 text-center">
          <p className="text-xs text-muted-foreground font-mono">{searchQuery ? '未找到匹配的技能' : t('empty')}</p>
        </Card>
      ) : (
        <div className="flex flex-col gap-3">
          <SkillsPagination
            currentPage={currentPage}
            pageSize={pageSize}
            totalItems={filteredSkills.length}
            onPageChange={setCurrentPage}
            onPageSizeChange={setPageSize}
          />

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {paginatedSkills.map((skill) => (
              <SkillCard key={`${skill.scope}:${skill.uri}`} skill={skill} onSelect={setSelectedSkill} />
            ))}
          </div>

          <SkillsPagination
            currentPage={currentPage}
            pageSize={pageSize}
            totalItems={filteredSkills.length}
            onPageChange={setCurrentPage}
            onPageSizeChange={setPageSize}
          />
        </div>
      )}

      <SkillDetailSheet
        open={Boolean(selectedSkill)}
        onOpenChange={(open) => { if (!open) setSelectedSkill(null) }}
        detail={detailQuery.data ?? null}
        isLoading={detailQuery.isLoading}
      />
    </div>
  )
}
