import * as React from 'react'
import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import {
  ArrowLeftIcon,
  ClockIcon,
  RefreshCwIcon,
  ShieldAlertIcon,
  SparklesIcon,
  ZapIcon,
} from 'lucide-react'

export const Route = createFileRoute('/harness-logs')({
  component: HarnessLogsPage,
})

function HarnessLogsPage() {
  const { t } = useTranslation('skillsPage')
  const [searchQuery, setSearchQuery] = React.useState('')
  const [categoryFilter, setCategoryFilter] = React.useState<'all' | 'guard' | 'reflexion' | 'call'>('all')

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
          actor_peers?: Record<string, number>
          find_calls?: number
          store_calls?: number
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
    queryKey: ['harness-status-full-logs-page'],
    staleTime: 30_000,
  })

  const metrics = harnessStatusQuery.data ?? null
  const lessonsDetail = Array.isArray(metrics?.lessons_detail) ? metrics.lessons_detail : []
  const blockedCalls = metrics?.blocked_calls ?? 0
  const lessonsCount = metrics?.lessons_count ?? lessonsDetail.length
  const totalCalls = metrics?.total_calls ?? 0

  const filteredLessons = React.useMemo(() => {
    return lessonsDetail.filter((item) => {
      if (categoryFilter === 'guard' && !item.title.includes('门锁') && !item.title.includes('拦截') && !item.title.includes('阻断')) return false
      if (categoryFilter === 'reflexion' && !item.reflection) return false
      if (!searchQuery.trim()) return true
      const q = searchQuery.toLowerCase()
      return (
        item.title.toLowerCase().includes(q) ||
        item.context.toLowerCase().includes(q) ||
        item.reflection.toLowerCase().includes(q) ||
        item.lesson.toLowerCase().includes(q)
      )
    })
  }, [lessonsDetail, searchQuery, categoryFilter])

  return (
    <div className="flex w-full min-w-0 flex-col gap-5 p-4 font-sans text-foreground">
      {/* 顶部面包屑与返回按钮 */}
      <div className="flex items-center justify-between border-b border-border/60 pb-3">
        <div className="flex items-center gap-3">
          <Link to="/skills">
            <Button variant="outline" size="sm" className="h-8 gap-1.5 text-xs text-foreground hover:bg-muted font-sans">
              <ArrowLeftIcon className="size-3.5 text-muted-foreground" />
              返回技能中心
            </Button>
          </Link>
          <div className="grid gap-0.5">
            <h1 className="text-xl font-semibold tracking-tight text-foreground flex items-center gap-2">
              🛡️ Harness 技能引擎全景监控与演进履历中枢
              <Badge variant="outline" className="font-mono text-xs border-border bg-muted/40 text-foreground">
                {lessonsCount} 项规约全景展示
              </Badge>
            </h1>
            <p className="text-xs text-muted-foreground font-mono">
              全量承载与展示物理拦截阻断解锁记录、技能调用明细、以及 Reflexion 自演进变更履历
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索阻断记录 / 调用明细 / Lesson 规约..."
            className="h-8 w-72 rounded border border-border/60 bg-background px-2.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-hidden focus:ring-1 focus:ring-primary font-mono"
          />
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-8 text-xs rounded text-foreground"
            disabled={harnessStatusQuery.isFetching}
            onClick={() => void harnessStatusQuery.refetch()}
          >
            <RefreshCwIcon className={harnessStatusQuery.isFetching ? 'size-3.5 animate-spin' : 'size-3.5'} />
            {t('refresh')}
          </Button>
        </div>
      </div>

      {/* 4 核心统计面板 Banner (极简沉稳风) */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
        <div className="flex flex-col justify-between rounded border border-border/60 bg-card p-3">
          <div className="flex items-center justify-between text-[11px] text-muted-foreground font-sans">
            <span className="flex items-center gap-1 text-foreground font-medium">
              <ZapIcon className="size-3.5 text-muted-foreground" />
              1. 物理前置拦截门锁
            </span>
            <Badge variant="outline" className="text-[9px] font-mono border-rose-500/40 text-rose-500 bg-rose-500/10 px-1 py-0">
              NeMo Interceptor
            </Badge>
          </div>
          <div className="my-1.5 font-mono text-2xl font-bold tracking-tight text-foreground">
            {blockedCalls} <span className="text-xs font-normal text-muted-foreground">次物理阻断</span>
          </div>
          <p className="text-[10px] font-mono text-muted-foreground border-t border-border/40 pt-1">
            拦截非法部署与未终验脚本
          </p>
        </div>

        <div className="flex flex-col justify-between rounded border border-border/60 bg-card p-3">
          <div className="flex items-center justify-between text-[11px] text-muted-foreground font-sans">
            <span className="flex items-center gap-1 text-foreground font-medium">
              <SparklesIcon className="size-3.5 text-muted-foreground" />
              2. Reflexion 自演进记录
            </span>
            <Badge variant="outline" className="text-[9px] font-mono border-cyan-500/40 text-cyan-500 bg-cyan-500/10 px-1 py-0">
              Reflexion Engine
            </Badge>
          </div>
          <div className="my-1.5 font-mono text-2xl font-bold tracking-tight text-foreground">
            {lessonsCount} <span className="text-xs font-normal text-muted-foreground">项演进 Lessons</span>
          </div>
          <p className="text-[10px] font-mono text-muted-foreground border-t border-border/40 pt-1">
            零人类人工提醒全自动落盘
          </p>
        </div>

        <div className="flex flex-col justify-between rounded border border-border/60 bg-card p-3">
          <div className="flex items-center justify-between text-[11px] text-muted-foreground font-sans">
            <span className="flex items-center gap-1 text-foreground font-medium">
              <ShieldAlertIcon className="size-3.5 text-muted-foreground" />
              3. 技能引擎调用总监测
            </span>
            <Badge variant="outline" className="text-[9px] font-mono border-border bg-muted/30 text-muted-foreground px-1 py-0">
              1933 RPC
            </Badge>
          </div>
          <div className="my-1.5 font-mono text-2xl font-bold tracking-tight text-foreground">
            {totalCalls} <span className="text-xs font-normal text-muted-foreground">次引擎交互</span>
          </div>
          <p className="text-[10px] font-mono text-muted-foreground border-t border-border/40 pt-1">
            find / store 双端调用全记录
          </p>
        </div>

        <div className="flex flex-col justify-between rounded border border-border/60 bg-card p-3">
          <div className="flex items-center justify-between text-[11px] text-muted-foreground font-sans">
            <span className="flex items-center gap-1 text-foreground font-medium">
              <ClockIcon className="size-3.5 text-muted-foreground" />
              4. 演进最频繁技能
            </span>
            <Badge variant="outline" className="text-[9px] font-mono border-border bg-muted/30 text-muted-foreground px-1 py-0">
              SKILL.md
            </Badge>
          </div>
          <div className="my-1.5 font-mono text-sm font-bold text-foreground truncate">
            {metrics?.most_evolved_skill ?? 'openviking-studio-dev'}
          </div>
          <p className="text-[10px] font-mono text-muted-foreground border-t border-border/40 pt-1">
            master_memory 物理同步
          </p>
        </div>
      </div>

      {/* 分类过滤与卡片明细 */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-2 rounded border border-border/60 bg-muted/30 p-1 font-mono text-xs">
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setCategoryFilter('all')}
              className={`rounded-xs px-2.5 py-1 text-center font-medium transition-colors ${
                categoryFilter === 'all'
                  ? 'bg-background text-foreground shadow-xs border border-border/60'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              全量明细与规约 ({lessonsDetail.length})
            </button>
            <button
              type="button"
              onClick={() => setCategoryFilter('guard')}
              className={`rounded-xs px-2.5 py-1 text-center font-medium transition-colors ${
                categoryFilter === 'guard'
                  ? 'bg-background text-rose-500 shadow-xs border border-rose-500/40'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              🛡️ 门锁物理阻断明细 ({blockedCalls})
            </button>
            <button
              type="button"
              onClick={() => setCategoryFilter('reflexion')}
              className={`rounded-xs px-2.5 py-1 text-center font-medium transition-colors ${
                categoryFilter === 'reflexion'
                  ? 'bg-background text-cyan-500 shadow-xs border border-cyan-500/40'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              ✨ Reflexion 演进规约 ({lessonsCount})
            </button>
          </div>
          <span className="text-[11px] text-muted-foreground font-mono pr-2">
            Viking 1933 审计日志
          </span>
        </div>

        {filteredLessons.length > 0 ? (
          <div className="grid grid-cols-1 gap-3.5">
            {filteredLessons.map((item) => (
              <div
                key={item.id}
                className="flex flex-col gap-2 rounded border border-border/60 bg-card p-3.5 shadow-2xs hover:border-border transition-colors"
              >
                <div className="flex items-center justify-between border-b border-border/40 pb-2">
                  <span className="font-mono text-xs font-bold text-foreground flex items-center gap-2">
                    <Badge variant="outline" className="text-[10px] font-mono border-border bg-muted/40 text-foreground px-1.5 py-0.5">
                      Lesson #{item.id}
                    </Badge>
                    {item.title}
                  </span>
                  <span className="text-[10px] font-mono text-muted-foreground">
                    归档路径: .agents/skills/openviking-studio-dev/SKILL.md
                  </span>
                </div>

                {item.context && (
                  <div className="text-xs text-muted-foreground bg-muted/30 p-2.5 rounded font-mono">
                    <span className="text-muted-foreground font-semibold">CONTEXT (触发与报错场景):</span> {item.context}
                  </div>
                )}

                {item.reflection && (
                  <div className="text-xs text-foreground bg-muted/20 p-2.5 rounded border border-border/40 font-sans leading-5">
                    <span className="text-foreground font-semibold font-mono">REFLECTION (根因与物理分析):</span> {item.reflection}
                  </div>
                )}

                {item.lesson && (
                  <div className="text-xs text-foreground font-medium bg-muted/40 p-2.5 rounded border border-border/60 font-sans leading-5">
                    <span className="font-bold font-mono text-foreground">LESSON (物理纠偏与防死锁规约):</span> {item.lesson}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded border border-dashed border-border/80 py-12 text-center text-xs font-mono text-muted-foreground">
            {searchQuery ? `未搜到匹配 "${searchQuery}" 的审计记录` : '暂无相关明细与调用记录'}
          </div>
        )}
      </div>
    </div>
  )
}
