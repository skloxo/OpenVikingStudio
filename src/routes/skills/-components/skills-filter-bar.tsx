import * as React from 'react'
import { SearchIcon } from 'lucide-react'
import { cn } from '#/lib/utils'
import type { SkillItem, SkillScopeFilter } from '../-lib/skill-types'
import { isDataSkill, isEngineeringSkill } from '../-lib/skill-translations'

interface SkillsFilterBarProps {
  skills: SkillItem[]
  activeScopeFilter: SkillScopeFilter
  onSelectScopeFilter: (scope: SkillScopeFilter) => void
  searchQuery: string
  onSearchChange: (query: string) => void
}

export function SkillsFilterBar({
  skills,
  activeScopeFilter,
  onSelectScopeFilter,
  searchQuery,
  onSearchChange,
}: SkillsFilterBarProps) {
  const engineeringCount = skills.filter((s) => isEngineeringSkill(s.name, s.source)).length
  const agentCount = skills.filter((s) => s.scope === 'agent' && !isEngineeringSkill(s.name, s.source)).length
  const dataCount = skills.filter(
    (s) => !isEngineeringSkill(s.name, s.source) && s.scope !== 'agent' && isDataSkill(s.name),
  ).length
  const generalCount = Math.max(0, skills.length - engineeringCount - agentCount - dataCount)

  return (
    <div className="flex flex-col gap-3">
      {/* 技能业务领域正交分类筛选标签栏 + 搜索框 */}
      <div className="flex items-center justify-between gap-2 rounded border border-border/60 bg-muted/20 p-1 font-mono text-xs">
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => onSelectScopeFilter('all')}
            className={cn(
              'rounded-xs px-2.5 py-1 text-center font-medium transition-colors cursor-pointer',
              activeScopeFilter === 'all'
                ? 'bg-background text-foreground shadow-xs border border-border/60'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            全部 ({skills.length})
          </button>
          <button
            type="button"
            onClick={() => onSelectScopeFilter('engineering')}
            className={cn(
              'rounded-xs px-2.5 py-1 text-center font-medium transition-colors cursor-pointer',
              activeScopeFilter === 'engineering'
                ? 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 shadow-xs border border-cyan-500/30'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            ⚡ 工程研发 ({engineeringCount})
          </button>
          <button
            type="button"
            onClick={() => onSelectScopeFilter('agent')}
            className={cn(
              'rounded-xs px-2.5 py-1 text-center font-medium transition-colors cursor-pointer',
              activeScopeFilter === 'agent'
                ? 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 shadow-xs border border-cyan-500/30'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            🤖 智能体 ({agentCount})
          </button>
          <button
            type="button"
            onClick={() => onSelectScopeFilter('data')}
            className={cn(
              'rounded-xs px-2.5 py-1 text-center font-medium transition-colors cursor-pointer',
              activeScopeFilter === 'data'
                ? 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 shadow-xs border border-cyan-500/30'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            📊 数据办公 ({dataCount})
          </button>
          <button
            type="button"
            onClick={() => onSelectScopeFilter('general')}
            className={cn(
              'rounded-xs px-2.5 py-1 text-center font-medium transition-colors cursor-pointer',
              activeScopeFilter === 'general'
                ? 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 shadow-xs border border-cyan-500/30'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            🧩 通用与偏好 ({generalCount})
          </button>
        </div>

        {/* 搜索框 */}
        <div className="relative">
          <SearchIcon className="absolute left-2 top-1/2 size-3 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="搜索技能 (名称 / 中文自解释)..."
            className="h-6 w-48 rounded-xs border border-border/60 bg-background pl-6 pr-2 font-mono text-xs text-foreground placeholder:text-muted-foreground focus:border-cyan-500 focus:outline-hidden transition-colors"
          />
        </div>
      </div>
    </div>
  )
}

