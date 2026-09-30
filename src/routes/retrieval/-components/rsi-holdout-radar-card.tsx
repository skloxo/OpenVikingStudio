// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2Icon, PlayIcon, RefreshCwIcon, ShieldAlertIcon, ShieldCheckIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Button } from '#/components/ui/button'
import { ovClient } from '#/lib/ov-client'

export interface HoldoutCaseResult {
  name: string
  description: string
  passed: boolean
  diagnostic: string
}

export interface HoldoutSuiteReport {
  total_cases: number
  passed_cases: number
  pass_rate: number
  results: HoldoutCaseResult[]
}

export function RSIHoldoutRadarCard() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const holdoutQuery = useQuery<HoldoutSuiteReport>({
    queryKey: ['rsi', 'holdout', 'report'],
    queryFn: async () => {
      const res = await ovClient.instance.get('/api/v1/rsi/holdout/report')
      return (res as { data: HoldoutSuiteReport }).data
    },
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  })

  const runHoldoutMutation = useMutation({
    mutationFn: async () => {
      const res = await ovClient.instance.post('/api/v1/rsi/holdout/run', {})
      return (res as { data: HoldoutSuiteReport }).data
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['rsi', 'holdout', 'report'], data)
    },
  })

  const report = holdoutQuery.data
  const isLoading = holdoutQuery.isLoading || runHoldoutMutation.isPending

  return (
    <div className="rounded-md border border-border/70 bg-card p-3 flex flex-col gap-2.5 shadow-xs">
      <div className="flex items-center justify-between pb-1.5 border-b border-border/50">
        <div className="flex items-center gap-1.5">
          <ShieldCheckIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
          <span className="text-xs font-semibold text-foreground">
            {t('rsi.holdoutTitle', '8 大物理安全不变量 Holdout 盲测雷达')}
          </span>
          {report && (
            <span
              className={`text-xs font-mono font-medium px-1.5 py-0.5 rounded ${
                report.passed_cases === report.total_cases
                  ? 'bg-cyan-50 dark:bg-cyan-950/40 text-cyan-700 dark:text-cyan-300'
                  : 'bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300'
              }`}
            >
              {report.passed_cases}/{report.total_cases} {t('rsi.gatesPassed', '门禁通过')} (
              {Math.round(report.pass_rate * 100)}%)
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          <Button
            size="sm"
            variant="outline"
            disabled={isLoading}
            onClick={() => runHoldoutMutation.mutate()}
            className="h-6 px-2 text-xs border-cyan-400/60 dark:border-cyan-700/60 bg-cyan-50/60 dark:bg-cyan-950/40 text-cyan-800 dark:text-cyan-300 hover:bg-cyan-100 dark:hover:bg-cyan-900/50 cursor-pointer"
          >
            <PlayIcon className="size-2.5 mr-1" />
            {isLoading ? t('rsi.evaluating', '评测中...') : t('rsi.runHoldout', '运行盲测')}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => queryClient.invalidateQueries({ queryKey: ['rsi', 'holdout'] })}
            className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground cursor-pointer"
          >
            <RefreshCwIcon className="size-2.5" />
          </Button>
        </div>
      </div>

      <div className="text-xs text-muted-foreground leading-relaxed">
        {t(
          'rsi.holdoutDesc',
          '严格基于第一性原理检验外部策略：防偷懒省略、强类型导轨、零 Mock 真实性、单文件 ≤500 行及 NO GREEN EVER 规范。'
        )}
      </div>

      {report?.results && report.results.length > 0 ? (
        <div className="grid grid-cols-2 gap-2">
          {report.results.map((item, idx) => (
            <div
              key={item.name}
              className={`rounded border p-2 flex flex-col gap-1 transition-colors ${
                item.passed
                  ? 'border-border/60 bg-muted/20'
                  : 'border-rose-400/60 bg-rose-50/30 dark:bg-rose-950/20'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-medium text-foreground truncate max-w-[70%]">
                  #{idx + 1} {item.name.replace('invariant_', '')}
                </span>
                <span
                  className={`text-xs font-mono flex items-center gap-1 ${
                    item.passed
                      ? 'text-cyan-600 dark:text-cyan-400'
                      : 'text-rose-600 dark:text-rose-400'
                  }`}
                >
                  {item.passed ? (
                    <>
                      <CheckCircle2Icon className="size-3" />
                      PASS
                    </>
                  ) : (
                    <>
                      <ShieldAlertIcon className="size-3" />
                      FAIL
                    </>
                  )}
                </span>
              </div>
              <p className="text-xs text-muted-foreground leading-tight line-clamp-1">
                {item.description}
              </p>
              <div className="text-xs font-mono text-muted-foreground/80 bg-background/50 px-1 py-0.5 rounded truncate">
                {item.diagnostic}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-xs text-muted-foreground font-mono p-4 text-center rounded border border-dashed border-border/60">
          {isLoading
            ? t('rsi.loadingHoldout', '正在载入 8 大安全门禁 Holdout 评测报告...')
            : t('rsi.emptyHoldout', '暂无 Holdout 盲测记录，点击右上角运行盲测')}
        </div>
      )}
    </div>
  )
}
