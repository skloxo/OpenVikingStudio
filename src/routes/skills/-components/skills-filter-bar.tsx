import * as React from 'react'
import { SearchIcon, SparklesIcon } from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import { cn } from '#/lib/utils'
import type { SkillItem, SkillScopeFilter } from '../-lib/skill-types'
import { isDataSkill, isEngineeringSkill } from '../-lib/skill-translations'

interface SkillsFilterBarProps {
  skills: SkillItem[]
  activeScopeFilter: SkillScopeFilter
  onSelectScopeFilter: (scope: SkillScopeFilter) => void
  searchQuery: string
  onSearchChange: (query: string) => void
  refinedSkills: Record<string, 'idle' | 'p1' | 'p2' | 'done'>
  onRefineSkill: (key: string, skillsList: string[]) => void
}

export function SkillsFilterBar({
  skills,
  activeScopeFilter,
  onSelectScopeFilter,
  searchQuery,
  onSearchChange,
  refinedSkills,
  onRefineSkill,
}: SkillsFilterBarProps) {
  const engineeringCount = skills.filter((s) => isEngineeringSkill(s.name, s.source)).length
  const agentCount = skills.filter((s) => s.scope === 'agent' && !isEngineeringSkill(s.name, s.source)).length
  const dataCount = skills.filter((s) => isDataSkill(s.name)).length
  const idleCount = skills.filter((s) => !isEngineeringSkill(s.name, s.source)).length

  return (
    <div className="flex flex-col gap-3">
      {/* Scope 分类筛选标签栏 + 搜索框 */}
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
                ? 'bg-background text-foreground shadow-xs border border-border/60'
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
                ? 'bg-background text-foreground shadow-xs border border-border/60'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            📊 数据办公 ({dataCount})
          </button>
          <button
            type="button"
            onClick={() => onSelectScopeFilter('idle')}
            className={cn(
              'rounded-xs px-2.5 py-1 text-center font-medium transition-colors cursor-pointer',
              activeScopeFilter === 'idle'
                ? 'bg-rose-500/10 text-rose-500 shadow-xs border border-rose-500/30 font-semibold'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            💤 待提炼 ({idleCount})
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
            className="h-6 w-48 rounded-xs border border-border/60 bg-background pl-6 pr-2 font-mono text-[11px] text-foreground placeholder:text-muted-foreground focus:border-cyan-500 focus:outline-hidden transition-colors"
          />
        </div>
      </div>

      {/* 待提炼打包合并建议面板 */}
      {activeScopeFilter === 'idle' && (
        <Card
          className={cn(
            'rounded p-3.5 font-mono text-xs shadow-2xs flex flex-col gap-2.5 transition-colors',
            refinedSkills['excel-chart'] === 'done' &&
              refinedSkills['log-trace'] === 'done'
              ? 'border-cyan-500/40 bg-cyan-500/5 text-cyan-600 dark:text-cyan-400'
              : 'border-rose-500/30 bg-rose-500/5 text-rose-500',
          )}
        >
          <div className="flex items-center justify-between font-semibold">
            <span className="flex items-center gap-1.5">
              <SparklesIcon className="size-4" />
              {refinedSkills['excel-chart'] === 'done' &&
              refinedSkills['log-trace'] === 'done'
                ? '✨ 技能资产打包精简已完成 (工具箱已瘦身降本)'
                : '⚡ 技能资产打包与合并建议 (工具箱瘦身 · 降低 Token 消耗)'}
            </span>
            <div className="flex items-center gap-2">
              <Badge
                variant="outline"
                className={cn(
                  'text-[11px]',
                  refinedSkills['excel-chart'] === 'done' &&
                    refinedSkills['log-trace'] === 'done'
                    ? 'border-cyan-500/40 text-cyan-500 bg-cyan-500/10'
                    : 'border-rose-500/30 text-rose-500 bg-rose-500/10',
                )}
              >
                {refinedSkills['excel-chart'] === 'done' &&
                refinedSkills['log-trace'] === 'done'
                  ? '✅ 打包提炼闭环完成'
                  : '重叠度 > 75% 推荐合并'}
              </Badge>
              <Badge
                variant="outline"
                className="border-cyan-500/40 text-cyan-500 text-[11px] bg-cyan-500/10"
              >
                🤖 全无人值守自动门禁
              </Badge>
            </div>
          </div>
          <p className="text-muted-foreground leading-relaxed text-[11px]">
            {refinedSkills['excel-chart'] === 'done' &&
            refinedSkills['log-trace'] === 'done'
              ? '🎉 下述高重叠离散技能已成功打包提炼为统一多功能 SOP，已在全局 Agent 意图库中消除了双重召唤与冗余 Token 浪费。'
              : '下述离散技能功能高度重叠（>75%）。一键打包合并后可消除冗余提示词，提升 AI 响应速度并降低 Token 算力开销：'}
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-0.5">
            <div
              className={cn(
                'rounded p-2.5 text-[11px] flex flex-col gap-2 border transition-colors',
                refinedSkills['excel-chart'] === 'done'
                  ? 'border-cyan-500/30 bg-background/80'
                  : 'border-rose-500/20 bg-background/60',
              )}
            >
              <div className="flex items-center justify-between">
                <div className="flex flex-col gap-0.5 min-w-0">
                  <span className="text-foreground font-medium truncate">
                    excel-format & chart-gen
                  </span>
                  <span
                    className={cn(
                      'font-bold shrink-0',
                      refinedSkills['excel-chart'] === 'done'
                        ? 'text-cyan-500'
                        : 'text-rose-500',
                    )}
                  >
                    {refinedSkills['excel-chart'] === 'done'
                      ? '✅ 78.5% 重叠已完成打包合并'
                      : '78.5% 重叠 ➔ 推荐打包'}
                  </span>
                </div>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={
                    refinedSkills['excel-chart'] === 'done' ||
                    refinedSkills['excel-chart'] === 'p1' ||
                    refinedSkills['excel-chart'] === 'p2'
                  }
                  className={cn(
                    'h-7 text-[11px] shrink-0 font-mono transition-all',
                    refinedSkills['excel-chart'] === 'done'
                      ? 'border-cyan-500/60 bg-cyan-500/20 text-cyan-500'
                      : 'border-cyan-500/40 text-cyan-600 dark:text-cyan-400 hover:bg-cyan-500/10',
                  )}
                  onClick={() =>
                    onRefineSkill('excel-chart', [
                      'excel-format',
                      'chart-gen',
                    ])
                  }
                >
                  {refinedSkills['excel-chart'] === 'done'
                    ? '✅ 已物理打包合并落盘'
                    : refinedSkills['excel-chart'] === 'p2'
                      ? '⏳ 2/3 用例跑集中...'
                      : refinedSkills['excel-chart'] === 'p1'
                        ? '⏳ 1/3 语法分析中...'
                        : '⚡ 一键物理打包合并'}
                </Button>
              </div>
            </div>
            <div
              className={cn(
                'rounded p-2.5 text-[11px] flex flex-col gap-2 border transition-colors',
                refinedSkills['log-trace'] === 'done'
                  ? 'border-cyan-500/30 bg-background/80'
                  : 'border-rose-500/20 bg-background/60',
              )}
            >
              <div className="flex items-center justify-between">
                <div className="flex flex-col gap-0.5 min-w-0">
                  <span className="text-foreground font-medium truncate">
                    log-extractor & trace-parser
                  </span>
                  <span
                    className={cn(
                      'font-bold shrink-0',
                      refinedSkills['log-trace'] === 'done'
                        ? 'text-cyan-500'
                        : 'text-rose-500',
                    )}
                  >
                    {refinedSkills['log-trace'] === 'done'
                      ? '✅ 81.2% 重叠已完成打包合并'
                      : '81.2% 重叠 ➔ 推荐合并'}
                  </span>
                </div>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={
                    refinedSkills['log-trace'] === 'done' ||
                    refinedSkills['log-trace'] === 'p1' ||
                    refinedSkills['log-trace'] === 'p2'
                  }
                  className={cn(
                    'h-7 text-[11px] shrink-0 font-mono transition-all',
                    refinedSkills['log-trace'] === 'done'
                      ? 'border-cyan-500/60 bg-cyan-500/20 text-cyan-500'
                      : 'border-cyan-500/40 text-cyan-600 dark:text-cyan-400 hover:bg-cyan-500/10',
                  )}
                  onClick={() =>
                    onRefineSkill('log-trace', [
                      'log-extractor',
                      'trace-parser',
                    ])
                  }
                >
                  {refinedSkills['log-trace'] === 'done'
                    ? '✅ 已物理打包合并落盘'
                    : refinedSkills['log-trace'] === 'p2'
                      ? '⏳ 2/3 用例跑集中...'
                      : refinedSkills['log-trace'] === 'p1'
                        ? '⏳ 1/3 语法分析中...'
                        : '⚡ 一键物理打包合并'}
                </Button>
              </div>
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}
