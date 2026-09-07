// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useTranslation } from 'react-i18next'
import { DownloadIcon, Loader2Icon, PlayIcon, PlusIcon, RotateCcwIcon, ZapIcon, SparklesIcon } from 'lucide-react'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { cn } from '#/lib/utils'
import type { BenchmarkMode } from './types'

interface BenchmarkQuerySuiteProps {
  mode: BenchmarkMode
  onModeChange: (mode: BenchmarkMode) => void
  queries: string[]
  onAddQuery: (q: string) => void
  onResetSuite: () => void
  onRun: () => void
  onExport: () => void
  isRunning: boolean
  currentIndex: number
  hasCompletedResults: boolean
}

export function BenchmarkQuerySuite({
  mode,
  onModeChange,
  queries,
  onAddQuery,
  onResetSuite,
  onRun,
  onExport,
  isRunning,
  currentIndex,
  hasCompletedResults,
}: BenchmarkQuerySuiteProps) {
  const { t } = useTranslation('retrieval')
  const [newQueryInput, setNewQueryInput] = React.useState('')

  const handleAdd = () => {
    const trimmed = newQueryInput.trim()
    if (!trimmed || queries.includes(trimmed)) return
    onAddQuery(trimmed)
    setNewQueryInput('')
  }

  return (
    <div className="space-y-3">
      {/* 模式选择 Segment 与操作按钮栏 */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 p-2 rounded-lg border border-border/70 bg-muted/20">
        <div className="flex items-center gap-1.5 flex-wrap">
          <button
            type="button"
            disabled={isRunning}
            onClick={() => onModeChange('fast')}
            className={cn(
              'flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-all cursor-pointer',
              mode === 'fast'
                ? 'bg-background text-foreground shadow-sm border border-border'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <ZapIcon className="size-3 text-cyan-500" />
            <span>{t('benchmark.fastMode', 'Fast 延迟跑分')}</span>
          </button>
          <button
            type="button"
            disabled={isRunning}
            onClick={() => onModeChange('ragas')}
            className={cn(
              'flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-all cursor-pointer',
              mode === 'ragas'
                ? 'bg-background text-cyan-500 shadow-sm border border-cyan-500/40'
                : 'text-muted-foreground hover:text-cyan-500'
            )}
          >
            <SparklesIcon className="size-3 text-cyan-500" />
            <span>{t('benchmark.ragasMode', 'RAGAS 评测实验室 (04A~04B)')}</span>
          </button>
        </div>

        {/* 状态动作区 */}
        <div className="flex items-center gap-2 flex-wrap sm:flex-nowrap">
          <Button
            onClick={onRun}
            disabled={isRunning || queries.length === 0}
            size="sm"
            className="h-7.5 gap-1.5 text-xs font-medium bg-cyan-600 hover:bg-cyan-700 text-white cursor-pointer px-3 shrink-0"
          >
            {isRunning ? (
              <>
                <Loader2Icon className="size-3 animate-spin" />
                <span>{t('benchmark.running', { completed: currentIndex + 1, total: queries.length })}</span>
              </>
            ) : (
              <>
                <PlayIcon className="size-3 fill-current" />
                <span>{mode === 'ragas' ? t('benchmark.runRagasBtn', '开始 RAGAS 评测') : t('benchmark.runBtn')}</span>
              </>
            )}
          </Button>

          <Button
            onClick={onResetSuite}
            disabled={isRunning}
            variant="ghost"
            size="sm"
            className="h-7.5 gap-1 text-xs text-muted-foreground hover:text-foreground cursor-pointer px-2 shrink-0 border border-border/40 hover:border-border"
            title={t('benchmark.resetSuite')}
          >
            <RotateCcwIcon className="size-3" />
            <span className="text-[11px]">{t('benchmark.resetSuite')}</span>
          </Button>

          {hasCompletedResults && (
            <Button
              onClick={onExport}
              variant="outline"
              size="sm"
              className="h-7.5 gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground cursor-pointer px-2.5 shrink-0"
            >
              <DownloadIcon className="size-3" />
              <span className="text-[11px]">{t('benchmark.exportReport')}</span>
            </Button>
          )}
        </div>
      </div>

      {/* 追加测试用例输入 */}
      <div className="flex items-center gap-2">
        <Input
          value={newQueryInput}
          onChange={(e) => setNewQueryInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              handleAdd()
            }
          }}
          disabled={isRunning}
          placeholder={t('benchmark.addQueryPlaceholder')}
          className="h-8 text-xs font-sans"
        />
        <Button
          onClick={handleAdd}
          disabled={isRunning || !newQueryInput.trim()}
          variant="outline"
          size="sm"
          className="h-8 gap-1 text-xs shrink-0 cursor-pointer"
        >
          <PlusIcon className="size-3" />
          <span>{t('benchmark.addQueryBtn')}</span>
        </Button>
      </div>
    </div>
  )
}
