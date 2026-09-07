import * as React from 'react'
import { ChevronRightIcon, SparklesIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Badge } from '#/components/ui/badge'
import { Card } from '#/components/ui/card'
import { cn } from '#/lib/utils'
import type { SkillItem } from '../-lib/skill-types'
import {
  getChineseSkillDescription,
  getChineseSkillName,
  getSkillSource,
} from '../-lib/skill-translations'

interface SkillCardProps {
  skill: SkillItem
  onSelect: (skill: SkillItem) => void
}

const ACTIVE_CORE_SKILLS = [
  'diagnosing-bugs',
  'tdd',
  'codebase-design',
  'domain-modeling',
  'code-review',
  'to-spec',
  'research',
  'prototype',
  'improve-codebase-architecture',
]

export function SkillCard({ skill, onSelect }: SkillCardProps) {
  const { i18n } = useTranslation('skillsPage')
  const isZh = !i18n.language || i18n.language.startsWith('zh')

  const srcInfo = getSkillSource(skill.name, skill.scope, skill.source)
  const displayName = isZh
    ? skill.cnName || getChineseSkillName(skill.name)
    : skill.name
  const displayDesc = isZh
    ? skill.cnDescription || getChineseSkillDescription(skill.description)
    : skill.description

  const isActive = ACTIVE_CORE_SKILLS.includes(skill.name)

  return (
    <Card
      className="group relative flex cursor-pointer flex-col justify-between rounded border border-border/60 bg-card p-3 transition-all hover:border-border hover:bg-muted/30 shadow-2xs hover:shadow-xs"
      onClick={() => onSelect(skill)}
    >
      <div>
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className="flex size-7 shrink-0 items-center justify-center rounded bg-muted text-foreground font-bold">
              <SparklesIcon className="size-4 text-cyan-500" />
            </div>
            <h3
              className="truncate text-xs font-semibold text-foreground group-hover:text-cyan-500 transition-colors"
              title={displayName}
            >
              {displayName}
            </h3>
          </div>
          <div className="flex items-center gap-1 shrink-0 font-mono text-xs">
            <Badge
              variant="outline"
              className={cn(
                'rounded-xs px-2 py-0.5 text-xs font-medium',
                srcInfo.badgeClass,
              )}
            >
              {srcInfo.label}
            </Badge>
          </div>
        </div>

        <p
          className="line-clamp-2 min-h-8 text-xs text-muted-foreground font-mono leading-relaxed"
          title={displayDesc}
        >
          {displayDesc}
        </p>
      </div>

      <div className="mt-3 flex items-center justify-between border-t border-border/40 pt-2.5 text-xs font-mono text-muted-foreground">
        <div className="flex items-center gap-1.5 min-w-0 truncate">
          <Badge
            variant="outline"
            className="rounded-xs text-xs px-2 py-0.5 border-border/70 bg-muted/30 text-foreground/80 font-normal shrink-0"
          >
            📁{' '}
            {typeof skill.file_count === 'number' && skill.file_count > 0
              ? `${skill.file_count} 文件`
              : 'SOP 规约'}{' '}
            (
            {typeof skill.content === 'string' && skill.content.length > 0
              ? skill.content.length > 1024
                ? `${(skill.content.length / 1024).toFixed(1)}KB`
                : `${skill.content.length}B`
              : '标准件'}
            )
          </Badge>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {isActive ? (
            <Badge
              variant="outline"
              className="text-xs px-2 py-0.5 border-cyan-500/40 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 font-medium"
            >
              🔥 24H 活跃
            </Badge>
          ) : (
            <Badge
              variant="outline"
              className="text-xs px-2 py-0.5 border-border/50 bg-muted/20 text-muted-foreground font-normal"
            >
              💤 闲置
            </Badge>
          )}
          <ChevronRightIcon className="size-4 group-hover:translate-x-0.5 transition-transform text-muted-foreground" />
        </div>
      </div>
    </Card>
  )
}
