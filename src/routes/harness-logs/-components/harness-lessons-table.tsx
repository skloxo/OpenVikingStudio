import * as React from 'react'
import { Badge } from '#/components/ui/badge'
import { SparklesIcon, ShieldAlertIcon } from 'lucide-react'

export interface LessonItem {
  id: number
  title: string
  context: string
  reflection: string
  lesson: string
  source?: string
}

interface HarnessLessonsTableProps {
  lessons: LessonItem[]
  searchQuery: string
}

export function HarnessLessonsTable({ lessons, searchQuery }: HarnessLessonsTableProps) {
  const [categoryFilter, setCategoryFilter] = React.useState<'all' | 'guard' | 'reflexion' | 'call'>('all')

  const filteredLessons = React.useMemo(() => {
    return lessons.filter((item) => {
      const q = searchQuery.toLowerCase()
      const matchesSearch =
        !q ||
        item.title.toLowerCase().includes(q) ||
        item.context.toLowerCase().includes(q) ||
        item.lesson.toLowerCase().includes(q)

      if (!matchesSearch) return false

      if (categoryFilter === 'guard') {
        return (
          item.source === 'local_ast_refinement' ||
          item.title.includes('门禁') ||
          item.title.includes('规约')
        )
      }
      if (categoryFilter === 'reflexion') {
        return (
          item.source === 'master_memory' ||
          item.title.includes('反思') ||
          item.reflection.length > 0
        )
      }
      if (categoryFilter === 'call') {
        return item.source === 'disk_trace'
      }
      return true
    })
  }, [lessons, searchQuery, categoryFilter])

  return (
    <div className="space-y-3">
      {/* Category Tabs */}
      <div className="flex items-center justify-between gap-2 border-b border-border/60 pb-2">
        <div className="flex items-center gap-1 font-mono text-xs">
          {(
            [
              { id: 'all', label: '全部教训' },
              { id: 'guard', label: '门禁阻断' },
              { id: 'reflexion', label: 'Reflexion 反思' },
              { id: 'call', label: '落盘调用' },
            ] as const
          ).map((cat) => (
            <button
              key={cat.id}
              type="button"
              onClick={() => setCategoryFilter(cat.id)}
              className={`rounded px-2 py-1 text-xs transition-colors ${
                categoryFilter === cat.id
                  ? 'bg-cyan-500/10 text-cyan-300 border border-cyan-500/30'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>
        <span className="font-mono text-xs text-muted-foreground">
          显示 {filteredLessons.length} / {lessons.length} 条记录
        </span>
      </div>

      {/* List */}
      <div className="space-y-2.5">
        {filteredLessons.length === 0 ? (
          <div className="rounded-md border border-dashed border-border/60 p-8 text-center text-xs text-muted-foreground">
            未检索到匹配的演进教训与门禁记录
          </div>
        ) : (
          filteredLessons.map((item) => {
            const isRefined = item.source === 'local_ast_refinement'
            return (
              <div
                key={item.id}
                className="flex flex-col gap-2 rounded-md border border-border/70 bg-card/50 p-3 text-xs transition-colors hover:border-cyan-500/30"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5 font-semibold text-foreground">
                    {isRefined ? (
                      <ShieldAlertIcon className="size-3.5 text-cyan-400" />
                    ) : (
                      <SparklesIcon className="size-3.5 text-cyan-400" />
                    )}
                    <span>{item.title}</span>
                  </div>
                  <Badge
                    variant="outline"
                    className="border-border/60 bg-muted/40 font-mono text-xs text-muted-foreground"
                  >
                    {item.source ?? 'evolution'}
                  </Badge>
                </div>

                <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2 text-xs text-muted-foreground">
                  <div>
                    <span className="font-medium text-foreground">背景上下文: </span>
                    {item.context}
                  </div>
                  {item.reflection && (
                    <div>
                      <span className="font-medium text-foreground">经验反思: </span>
                      {item.reflection}
                    </div>
                  )}
                </div>

                <div className="border-t border-border/40 pt-1.5 font-mono text-xs text-cyan-400/90">
                  <span className="font-sans font-medium text-muted-foreground">沉淀 Lesson: </span>
                  {item.lesson}
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
