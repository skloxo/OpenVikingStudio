// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2Icon, DatabaseIcon, RefreshCwIcon, ShieldAlertIcon, WrenchIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Button } from '#/components/ui/button'
import { ovClient } from '#/lib/ov-client'

export interface DbCheckResult {
  path: string
  name: string
  exists: boolean
  passed: boolean
  quick_check: string[] | null
  fts5_tables: string[]
  fts5_rebuilt: string[]
  error: string | null
}

export interface DbHealthReport {
  status: 'healthy' | 'warning'
  total_databases: number
  passed_databases: number
  fts5_rebuilt_count: number
  duration_ms: number
  databases: DbCheckResult[]
}

export function DbIntegrityHealthCard() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const dbHealthQuery = useQuery<DbHealthReport>({
    queryKey: ['rsi', 'bootstrap', 'health'],
    queryFn: async () => {
      const res = await ovClient.instance.get('/api/v1/rsi/bootstrap/health')
      return (res as { data: DbHealthReport }).data
    },
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  })

  const runCheckMutation = useMutation({
    mutationFn: async () => {
      const res = await ovClient.instance.post('/api/v1/rsi/bootstrap/health/run', {})
      return (res as { data: DbHealthReport }).data
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['rsi', 'bootstrap', 'health'], data)
    },
  })

  const report = dbHealthQuery.data
  const isLoading = dbHealthQuery.isLoading || runCheckMutation.isPending
  const isHealthy = report?.status === 'healthy'

  return (
    <div className="rounded-md border border-border/70 bg-card p-3 flex flex-col gap-2.5 shadow-xs">
      <div className="flex items-center justify-between pb-1.5 border-b border-border/50">
        <div className="flex items-center gap-1.5">
          <DatabaseIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
          <span className="text-xs font-semibold text-foreground">
            {t('rsi.dbHealthTitle', 'SQLite 完整性与 FTS5 索引健康自愈')}
          </span>
          {report && (
            <span
              className={`text-xs font-mono font-medium px-1.5 py-0.5 rounded ${
                isHealthy
                  ? 'bg-cyan-50 dark:bg-cyan-950/40 text-cyan-700 dark:text-cyan-300'
                  : 'bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300'
              }`}
            >
              {report.passed_databases}/{report.total_databases} {t('rsi.dbComplete', '库完整')} (
              {report.duration_ms}ms)
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          <Button
            size="sm"
            variant="outline"
            disabled={isLoading}
            onClick={() => runCheckMutation.mutate()}
            className="h-6 px-2 text-xs border-cyan-400/60 dark:border-cyan-700/60 bg-cyan-50/60 dark:bg-cyan-950/40 text-cyan-800 dark:text-cyan-300 hover:bg-cyan-100 dark:hover:bg-cyan-900/50 cursor-pointer"
          >
            <WrenchIcon className="size-2.5 mr-1" />
            {isLoading ? t('rsi.selfChecking', '自检中...') : t('rsi.recheck', '重新体检')}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => queryClient.invalidateQueries({ queryKey: ['rsi', 'bootstrap', 'health'] })}
            className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground cursor-pointer"
          >
            <RefreshCwIcon className="size-2.5" />
          </Button>
        </div>
      </div>

      <div className="text-xs text-muted-foreground leading-relaxed">
        {t(
          'rsi.dbHealthDesc',
          '启动期自动执行 PRAGMA quick_check 验证；遇 FTS5 损坏自动触发 rebuild 物理自愈，杜绝段错误与查询死锁。'
        )}
      </div>

      {report?.databases && report.databases.length > 0 ? (
        <div className="flex flex-col gap-1.5 max-h-45 overflow-y-auto pr-0.5">
          {report.databases.map((db) => (
            <div
              key={db.name}
              className="flex items-center justify-between rounded border border-border/50 bg-muted/20 px-2 py-1.5 text-xs"
            >
              <div className="flex items-center gap-1.5 truncate max-w-[60%]">
                <span className="font-mono text-foreground font-medium truncate">{db.name}</span>
                {db.fts5_tables.length > 0 && (
                  <span className="text-xs font-mono text-muted-foreground">
                    [FTS5: {db.fts5_tables.join(', ')}]
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2 font-mono text-xs">
                {db.fts5_rebuilt.length > 0 && (
                  <span className="text-amber-600 dark:text-amber-400">
                    {t('rsi.healed', '自愈')}: {db.fts5_rebuilt.join(', ')}
                  </span>
                )}
                <span
                  className={`flex items-center gap-1 ${
                    db.passed
                      ? 'text-cyan-600 dark:text-cyan-400'
                      : 'text-rose-600 dark:text-rose-400'
                  }`}
                >
                  {db.passed ? (
                    <>
                      <CheckCircle2Icon className="size-3" />
                      OK
                    </>
                  ) : (
                    <>
                      <ShieldAlertIcon className="size-3" />
                      {db.error || 'FAIL'}
                    </>
                  )}
                </span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-xs text-muted-foreground font-mono p-3 text-center rounded border border-dashed border-border/60">
          {isLoading
            ? t('rsi.dbChecking', '正在进行数据库完整性自检...')
            : t('rsi.dbEmpty', '未探测到活跃 SQLite 数据库，点击上方重新体检')}
        </div>
      )}
    </div>
  )
}
