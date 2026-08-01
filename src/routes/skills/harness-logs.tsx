import * as React from 'react'
import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import {
  ArrowLeftIcon,
  Badge,
  Button,
  ClockIcon,
  RefreshCwIcon,
  SparklesIcon,
  ZapIcon,
} from 'lucide-react'

export const Route = createFileRoute('/skills/harness-logs')({
  component: HarnessLogsPage,
})

function HarnessLogsPage() {
  const { t } = useTranslation('skillsPage')
  const [searchQuery, setSearchQuery] = React.useState('')

  const harnessStatusQuery = useQuery({
    queryFn: async () => {
      try {
        const res = await fetch('/api/v1/system/harness_metrics')
        if (!res.ok) return null
        return (await res.json()) as {
          lessons_count?: number
          total_calls?: number
          blocked_calls?: number
          most_evolved_skill?: string
          lessons_detail?: Array<{
            id: number
            title: string
            context: string
            reflection: string
            lesson: string
          }>
        }
      } catch {
        return null
      }
    },
    queryKey: ['harness-status-full-logs'],
    staleTime: 60_000,
  })

  const metrics = harnessStatusQuery.data ?? null
  const lessonsDetail = Array.isArray(metrics?.lessons_detail) ? metrics.lessons_detail : []
  const blockedCalls = metrics?.blocked_calls ?? 0
  const lessonsCount = metrics?.lessons_count ?? lessonsDetail.length

  const filteredLessons = React.useMemo(() => {
    if (!searchQuery.trim()) return lessonsDetail
    const q = searchQuery.toLowerCase()
    return lessonsDetail.filter(
      (item) =>
        item.title.toLowerCase().includes(q) ||
        item.context.toLowerCase().includes(q) ||
        item.reflection.toLowerCase().includes(q) ||
        item.lesson.toLowerCase().includes(q)
    )
  }, [lessonsDetail, searchQuery])

  return (
    <div className="flex w-full min-w-0 flex-col gap-5 p-4 font-sans">
      {/* 顶部面包屑与返回按钮 */}
      <div className="flex items-center justify-between border-b border-border/60 pb-3">
        <div className="flex items-center gap-3">
          <Link to="/skills">
            <Button variant="outline" size="sm" className="h-8 gap-1.5 text-xs border-cyan-500/40 text-cyan-600 dark:text-cyan-400 hover:bg-cyan-500/10">
              <ArrowLeftIcon className="size-3.5" />
              返回技能中心
            </Button>
          </Link>
          <div className="grid gap-0.5">
            <h1 className="text-xl font-semibold tracking-tight flex items-center gap-2">
              📜 Harness 物理自演进日志与用户纠偏全景面板
              <Badge variant="outline" className="font-mono text-xs border-cyan-500/40 bg-cyan-500/10 text-cyan-500">
                {lessonsCount} 条 Lessons 归档
              </Badge>
            </h1>
            <p className="text-xs text-muted-foreground font-mono">
              白盒透视底层 Reflexion 反思钩子与物理拦截器记录的全量演进规约明细
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索 Lesson 标题 / 场景 / 规约..."
            className="h-8 w-64 rounded border border-border/60 bg-muted/20 px-2.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-hidden focus:ring-1 focus:ring-cyan-500 font-mono"
          />
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-8 text-xs rounded"
            disabled={harnessStatusQuery.isFetching}
            onClick={() => void harnessStatusQuery.refetch()}
          >
            <RefreshCwIcon className={harnessStatusQuery.isFetching ? 'size-3.5 animate-spin' : 'size-3.5'} />
            {t('refresh')}
          </Button>
        </div>
      </div>

      {/* 4 核心统计面板 Banner */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="flex flex-col justify-between rounded border border-cyan-500/30 bg-cyan-500/5 p-3">
          <div className="flex items-center justify-between text-[11px] text-muted-foreground font-sans">
            <span className="flex items-center gap-1 text-cyan-600 dark:text-cyan-400 font-medium">
              <SparklesIcon className="size-3.5 text-cyan-500" />
              总累积演进 Lessons
            </span>
            <Badge variant="outline" className="text-[9px] font-mono border-cyan-500/40 text-cyan-500 px-1 py-0 bg-cyan-500/10">
              Reflexion Engine
            </Badge>
          </div>
          <div className="my-1.5 font-mono text-2xl font-bold tracking-tight text-cyan-600 dark:text-cyan-400">
            {lessonsCount} <span className="text-xs font-normal text-muted-foreground">项用户规约</span>
          </div>
          <p className="text-[10px] font-mono text-muted-foreground border-t border-cyan-500/20 pt-1">
            无须人类提醒，隐式/阻断全自动落盘
          </p>
        </div>

        <div className="flex flex-col justify-between rounded border border-cyan-500/30 bg-cyan-500/5 p-3">
          <div className="flex items-center justify-between text-[11px] text-muted-foreground font-sans">
            <span className="flex items-center gap-1 text-cyan-600 dark:text-cyan-400 font-medium">
              <ZapIcon className="size-3.5 text-cyan-500" />
              拦截器硬性阻断次数
            </span>
            <Badge variant="outline" className="text-[9px] font-mono border-cyan-500/40 text-cyan-500 px-1 py-0 bg-cyan-500/10">
              NeMo Guard
            </Badge>
          </div>
          <div className="my-1.5 font-mono text-2xl font-bold tracking-tight text-cyan-600 dark:text-cyan-400">
            {blockedCalls} <span className="text-xs font-normal text-muted-foreground">次物理阻断</span>
          </div>
          <p className="text-[10px] font-mono text-muted-foreground border-t border-cyan-500/20 pt-1">
            物理阻断游离脚本与非法部署
          </p>
        </div>

        <div className="flex flex-col justify-between rounded border border-cyan-500/30 bg-cyan-500/5 p-3">
          <div className="flex items-center justify-between text-[11px] text-muted-foreground font-sans">
            <span className="flex items-center gap-1 text-cyan-600 dark:text-cyan-400 font-medium">
              <ClockIcon className="size-3.5 text-cyan-500" />
              演进最频繁技能
            </span>
            <Badge variant="outline" className="text-[9px] font-mono border-cyan-500/40 text-cyan-500 px-1 py-0 bg-cyan-500/10">
              SKILL.md
            </Badge>
          </div>
          <div className="my-1.5 font-mono text-sm font-bold text-cyan-600 dark:text-cyan-400 truncate">
            {metrics?.most_evolved_skill ?? 'openviking-studio-dev'}
          </div>
          <p className="text-[10px] font-mono text-muted-foreground border-t border-cyan-500/20 pt-1">
            物理同步至 master_memory 向量库
          </p>
        </div>
      </div>

      {/* 演进日志全景卡片网格列表 */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
            📋 全量 Lesson 履历明细 ({filteredLessons.length} / {lessonsDetail.length})
          </h2>
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="text-xs font-mono text-cyan-500 hover:underline"
            >
              清除搜索条件 ✕
            </button>
          )}
        </div>

        {filteredLessons.length > 0 ? (
          <div className="grid grid-cols-1 gap-3.5">
            {filteredLessons.map((item) => (
              <div
                key={item.id}
                className="flex flex-col gap-2 rounded border border-border/60 bg-muted/10 p-3.5 shadow-2xs hover:border-cyan-500/40 transition-colors"
              >
                <div className="flex items-center justify-between border-b border-border/40 pb-2">
                  <span className="font-mono text-xs font-bold text-cyan-600 dark:text-cyan-400 flex items-center gap-2">
                    <Badge variant="outline" className="text-[10px] font-mono border-cyan-500/40 text-cyan-500 bg-cyan-500/10 px-1.5 py-0.5">
                      Lesson #{item.id}
                    </Badge>
                    {item.title}
                  </span>
                  <span className="text-[10px] font-mono text-muted-foreground/80">
                    存储路径: .agents/skills/openviking-studio-dev/SKILL.md
                  </span>
                </div>

                {item.context && (
                  <div className="text-xs text-muted-foreground bg-muted/30 p-2 rounded font-mono">
                    <span className="text-muted-foreground/70 font-semibold">CONTEXT (触发场景):</span> {item.context}
                  </div>
                )}

                {item.reflection && (
                  <div className="text-xs text-foreground/90 bg-cyan-500/5 p-2 rounded border border-cyan-500/10 font-sans">
                    <span className="text-cyan-500 font-semibold font-mono">REFLECTION (根因分析):</span> {item.reflection}
                  </div>
                )}

                {item.lesson && (
                  <div className="text-xs text-cyan-600 dark:text-cyan-400 font-medium bg-cyan-500/10 p-2 rounded border border-cyan-500/20 font-sans">
                    <span className="font-bold font-mono">LESSON (物理规约):</span> {item.lesson}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded border border-dashed border-border/80 py-12 text-center text-xs font-mono text-muted-foreground">
            {searchQuery ? `未搜到包含 "${searchQuery}" 的演进日志` : '暂无演进日志明细'}
          </div>
        )}
      </div>
    </div>
  )
}
