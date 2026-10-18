import * as React from 'react'
import { Link, createFileRoute } from '@tanstack/react-router'
import { InboxIcon, LayersIcon, LoaderCircleIcon, SparklesIcon, WorkflowIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import { ActiveIngestionView } from './-components/active-ingestion-view'
import { B6EvolutionPipelineCockpit } from './-components/b6-evolution-pipeline-cockpit'
import { B6RetinaRegressionCockpit } from './-components/b6-retina-regression-cockpit'
import { B6HermesAheCockpit } from './-components/b6-hermes-ahe-cockpit'
import { B6ProvenanceMultiLedger } from './-components/b6-provenance-multi-ledger'
import { SkillsPagination } from './-components/pagination'
import { SkillCard } from './-components/skill-card'
import { SkillsFilterBar } from './-components/skills-filter-bar'
import { SkillsMetricsCards } from './-components/skills-metrics-cards'
import { SkillDetailSheet } from './-components/skill-detail-sheet'
import { SkillIngestionCockpit } from './-components/skill-ingestion-cockpit'
import { SkillRoiCockpitCard } from './-components/skill-roi-cockpit-card'
import { useSkillEventBus } from './-hooks/use-skill-event-bus'
import { getErrorMessage } from './-lib/skill-data'
import { useSkillsData } from './-lib/use-skills'

export const Route = createFileRoute('/skills')({
  component: SkillsRoute,
})

function SkillsRoute() {
  const { t } = useTranslation('skillsPage')
  const [centerMode, setCenterMode] = React.useState<'catalog' | 'pipeline'>('catalog')
  const [showIngestionCockpit, setShowIngestionCockpit] = React.useState(false)
  const { isConnected: isEventBusConnected } = useSkillEventBus()
  const data = useSkillsData()

  React.useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search)
      const modeParam = params.get('mode') || params.get('tab')
      if (modeParam === 'pipeline') {
        setCenterMode('pipeline')
      }
    }
  }, [])
  const {
    skills, bundles, flatSkills, viewMode, setViewMode,
    filteredSkills, paginatedSkills, skillsQuery, detailQuery,
    selectedSkill, setSelectedSkill, searchQuery, setSearchQuery,
    activeScopeFilter, setActiveScopeFilter,
    currentPage, setCurrentPage, pageSize, setPageSize,
    connectionUnavailable, harnessMetrics,
    queueDepth, activeIngestionCount,
  } = data

  return (
    <div className="flex w-full min-w-0 flex-col gap-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div className="grid gap-1">
          <h1 className="text-xl font-semibold tracking-tight flex items-center gap-2">🧠 技能中心</h1>
          <p className="max-w-3xl text-xs text-muted-foreground font-mono">{t('description')}</p>
        </div>
        <Badge variant="outline" className="text-xs font-mono border-border bg-muted/30 text-foreground px-1.5 py-0.5">
          🕒 统计范围: 最近 24 小时 (24H Rolling)
        </Badge>
      </header>

      {/* 技能中心顶层双模式导航：核心资产大盘 vs B6 全息演进运行中枢 */}
      <div className="flex items-center gap-1.5 border-b border-border/60 pb-1">
        <button
          type="button"
          onClick={() => setCenterMode('catalog')}
          className={`flex items-center rounded-t-md px-3.5 py-1.5 text-xs font-mono font-medium transition-all cursor-pointer ${
            centerMode === 'catalog'
              ? 'border-b-2 border-cyan-600 dark:border-cyan-400 bg-card text-foreground font-semibold shadow-2xs'
              : 'text-muted-foreground hover:text-foreground hover:bg-muted/40'
          }`}
        >
          <LayersIcon className="size-3.5 mr-1.5 text-cyan-600 dark:text-cyan-400" />
          <span>📚 核心领域技能大盘 ({skills.length})</span>
        </button>
        <button
          type="button"
          onClick={() => setCenterMode('pipeline')}
          className={`flex items-center rounded-t-md px-3.5 py-1.5 text-xs font-mono font-medium transition-all cursor-pointer ${
            centerMode === 'pipeline'
              ? 'border-b-2 border-cyan-600 dark:border-cyan-400 bg-card text-foreground font-semibold shadow-2xs'
              : 'text-muted-foreground hover:text-foreground hover:bg-muted/40'
          }`}
        >
          <WorkflowIcon className="size-3.5 mr-1.5 text-cyan-600 dark:text-cyan-400" />
          <span>⚡ B6 全息演进流水线与运行中枢</span>
          <span className="ml-1.5 size-1.5 rounded-full bg-cyan-500 animate-pulse" />
        </button>
      </div>

      {centerMode === 'pipeline' ? (
        <div className="flex flex-col gap-4">
          <B6EvolutionPipelineCockpit />
          <B6RetinaRegressionCockpit />
          <B6HermesAheCockpit />
          <B6ProvenanceMultiLedger />
        </div>
      ) : (
        <>
          {/* 7x24h Autonomous Pipeline Live Status Bar */}
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-cyan-200 bg-cyan-50/70 dark:border-cyan-500/30 dark:bg-cyan-950/20 px-3 py-2 text-xs font-mono">
            <div className="flex items-center gap-2">
              <span className="flex size-2 rounded-full bg-cyan-500 animate-pulse" />
              <span className="font-semibold text-cyan-800 dark:text-cyan-300">⚡ B6 自主闭环流水线</span>
              <span className="text-muted-foreground/60">|</span>
              <span className="text-muted-foreground">
                工序联动: 📥 准入排队 ➔ 🎯 SkillOpt 质检 ➔ ⚡ SkillZip 压缩 ➔ ⚖️ B6 亲和分流 ➔ 🚦 Pytest 门禁 ➔ 🌐 别名透明投影
              </span>
            </div>
            <div className="flex items-center gap-2">
              {activeIngestionCount > 0 && (
                <button
                  type="button"
                  onClick={() => setViewMode('ingesting')}
                  className="flex items-center gap-1.5 rounded border border-amber-300 bg-amber-50 px-2 py-0.5 text-xs font-mono font-medium text-amber-800 hover:bg-amber-100 dark:border-amber-700/60 dark:bg-amber-950/40 dark:text-amber-200 transition-colors cursor-pointer"
                >
                  <span className="size-2 rounded-full bg-amber-500 animate-pulse" />
                  <span>发现 {activeIngestionCount} 项新技能入库质检中 ➔</span>
                </button>
              )}
              <Badge variant="outline" className="border-cyan-300 bg-cyan-100/70 text-cyan-800 dark:border-cyan-700 dark:bg-cyan-950/50 dark:text-cyan-200 text-xs font-mono font-medium">
                7x24H 无人值守生效中
              </Badge>
              <Badge variant="outline" className="border-border bg-background/80 text-foreground text-xs font-mono">
                外部 Agent 零修改无感调用
              </Badge>
              <Badge variant="outline" className="border-border bg-background/80 text-foreground text-xs font-mono flex items-center gap-1.5">
                <span className={`size-1.5 rounded-full ${isEventBusConnected ? 'bg-cyan-500 animate-pulse' : 'bg-muted-foreground'}`} />
                <span>{isEventBusConnected ? 'SSE 实时双工已联通' : '60S 轮询保障中'}</span>
              </Badge>
            </div>
          </div>

          {/* 核心领域技能资产总览条 */}
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border/70 bg-card px-3 py-1.5 text-xs font-mono shadow-2xs">
            <div className="flex items-center gap-2">
              <LayersIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
              <span className="font-semibold text-foreground">
                🧠 核心领域技能中枢 ({skills.length} 项全域就绪)
              </span>
              <span className="text-muted-foreground/60">|</span>
              <span className="text-muted-foreground">
                内聚工程研发、智能体治理、底座运维与逆向学习全域母能力 · 支持智能别名透明投影
              </span>
            </div>

            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Badge variant="outline" className="border-border bg-muted/40 text-foreground text-xs font-mono">
                零手动配置 · 自动化后台护航
              </Badge>
            </div>
          </div>

          <SkillsMetricsCards metrics={harnessMetrics} totalSkills={skills.length} />

          <SkillRoiCockpitCard />

          {/* 自动化准入流水线与黑匣子演变审计折叠看板 */}
          <div className="rounded-md border border-border/80 bg-card px-3 py-2.5 shadow-2xs">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <InboxIcon className="size-4 text-cyan-600 dark:text-cyan-400" />
                <span className="text-xs font-semibold font-mono text-foreground">
                  🚀 技能自动化准入流水线与黑匣子演变审计
                </span>
                <Badge variant="outline" className="text-xs font-mono text-cyan-800 bg-cyan-50 border-cyan-300 dark:text-cyan-300 dark:bg-cyan-950/40 dark:border-cyan-800 font-medium">
                  全链路日志可感知
                </Badge>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowIngestionCockpit((prev) => !prev)}
                className="text-xs font-mono h-7 px-2.5 text-cyan-700 border-cyan-300 hover:bg-cyan-50 dark:text-cyan-300 dark:border-cyan-700 dark:hover:bg-cyan-950/40 font-medium"
              >
                {showIngestionCockpit ? '收起流水线证据链 ▴' : '展开流水线与证据链日志 ▾'}
              </Button>
            </div>
            {showIngestionCockpit && (
              <div className="mt-3 pt-3 border-t border-border/60">
                <SkillIngestionCockpit />
              </div>
            )}
          </div>

          <SkillsFilterBar
            skills={skills}
            activeScopeFilter={activeScopeFilter}
            onSelectScopeFilter={setActiveScopeFilter}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            viewMode={viewMode}
            onViewModeChange={setViewMode}
            bundlesCount={bundles.length}
            ingestionCount={activeIngestionCount}
            flatCount={flatSkills.length}
          />

          {viewMode === 'ingesting' ? (
            <ActiveIngestionView />
          ) : skillsQuery.isLoading ? (
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
        </>
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
