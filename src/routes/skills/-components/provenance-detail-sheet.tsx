// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArchiveRestoreIcon,
  CheckCircleIcon,
  CopyIcon,
  FileCodeIcon,
  FileTextIcon,
  GitBranchIcon,
  HistoryIcon,
  ShieldAlertIcon,
  ShieldCheckIcon,
  Wand2Icon,
} from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '#/components/ui/sheet'
import { ovClient } from '#/lib/ov-client'
import { cn } from '#/lib/utils'
import type { SelectedLedgerItem } from '../-types/provenance-ledger'

interface ProvenanceDetailSheetProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  item: SelectedLedgerItem | null
  onRollbackSuccess?: () => void
}

export function ProvenanceDetailSheet({
  open,
  onOpenChange,
  item,
  onRollbackSuccess,
}: ProvenanceDetailSheetProps) {
  const queryClient = useQueryClient()
  const [copied, setCopied] = React.useState(false)

  const rollbackMutation = useMutation({
    mutationFn: async ({
      snapshotPath,
      targetPath,
    }: {
      snapshotPath: string
      targetPath: string
    }) => {
      const res = await ovClient.instance.post('/api/v1/skills/ingestion/rollback', {
        snapshot_path: snapshotPath,
        target_file_path: targetPath,
      })
      return res.data
    },
    onSuccess: () => {
      toast.success('已从快照秒级还原物理技能文件')
      queryClient.invalidateQueries({ queryKey: ['skills-provenance-events'] })
      queryClient.invalidateQueries({ queryKey: ['skills-ingestion-queue'] })
      onRollbackSuccess?.()
    },
    onError: (err: any) => {
      toast.error(`还原快照失败: ${err?.message || '未知错误'}`)
    },
  })

  if (!item) return null

  const isProv = item.type === 'provenance'
  const prov = isProv ? item.record : null
  const ing = !isProv ? item.record : null

  const skillName = isProv ? prov!.skill_name : ing!.skill_name
  const id = isProv ? prov!.event_id : ing!.receipt_id
  const timestamp = isProv ? prov!.timestamp : ing!.created_at
  const dateStr = new Date(timestamp * 1000).toLocaleString()

  const snapshotPath = prov?.snapshot_path
  const sourcePath = isProv ? prov?.details?.source_path : ing?.validation_report?.source_path
  const landingPath = isProv ? prov?.details?.landing_path : undefined
  const targetBundle = isProv ? prov?.details?.target_bundle : ing?.validation_report?.routing?.target_package
  const optScore = isProv ? prov?.details?.opt_score : ing?.validation_report?.opt_score
  const remediatedFields = prov?.details?.remediated_fields
  const errors = isProv ? prov?.details?.errors : ing?.validation_report?.violations
  const diffPatch = prov?.details?.diff_patch

  const copyContent = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
    toast.success('路径已复制至剪贴板')
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="sm:max-w-xl w-full p-0 flex flex-col h-full bg-background border-l border-border/80 shadow-2xl"
      >
        <SheetHeader className="p-4 border-b border-border/70 bg-card/60">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <HistoryIcon className="size-4 text-cyan-600 dark:text-cyan-400" />
              <SheetTitle className="text-sm font-semibold font-mono tracking-tight text-foreground">
                {isProv ? '黑匣子演变审计证据' : 'SQLite 准入队列记录'}
              </SheetTitle>
            </div>
            {isProv ? (
              <Badge variant="outline" className="text-xs font-mono border-cyan-300 bg-cyan-50 text-cyan-800 dark:bg-cyan-950/40 dark:text-cyan-300 dark:border-cyan-800">
                [{prov!.action}]
              </Badge>
            ) : (
              <Badge variant="outline" className="text-xs font-mono border-border bg-muted/40 text-foreground">
                {ing!.status}
              </Badge>
            )}
          </div>
          <SheetDescription className="text-xs font-mono text-muted-foreground mt-1 flex items-center justify-between">
            <span>ID: {id}</span>
            <span>{dateStr}</span>
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* 技能主体与定位卡片 */}
          <div className="rounded-md border border-border/70 bg-card p-3 shadow-2xs space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 font-mono text-xs font-semibold text-foreground">
                <FileCodeIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
                <span>{skillName}</span>
                {isProv && prov!.version && (
                  <span className="text-muted-foreground font-normal">v{prov!.version}</span>
                )}
              </div>
              <span className="text-xs font-mono text-muted-foreground">
                操作源: {isProv ? prov!.operator : ing!.author}
              </span>
            </div>

            {sourcePath && (
              <div className="flex items-center justify-between gap-2 text-xs font-mono text-muted-foreground bg-muted/30 px-2 py-1 rounded border border-border/50">
                <span className="truncate">源文件: {sourcePath}</span>
                <button
                  type="button"
                  onClick={() => copyContent(sourcePath)}
                  className="hover:text-foreground shrink-0 cursor-pointer"
                  title="复制路径"
                >
                  <CopyIcon className="size-3" />
                </button>
              </div>
            )}

            {landingPath && (
              <div className="flex items-center justify-between gap-2 text-xs font-mono text-muted-foreground bg-cyan-50/50 dark:bg-cyan-950/20 px-2 py-1 rounded border border-cyan-200 dark:border-cyan-800/60">
                <span className="text-cyan-800 dark:text-cyan-300 truncate">落地: {landingPath}</span>
                <button
                  type="button"
                  onClick={() => copyContent(landingPath)}
                  className="hover:text-foreground shrink-0 cursor-pointer"
                  title="复制落地路径"
                >
                  <CopyIcon className="size-3" />
                </button>
              </div>
            )}
          </div>

          {/* 快照与秒级回退动作栏 */}
          {snapshotPath && (
            <div className="rounded-md border border-cyan-300/80 bg-cyan-50/60 dark:border-cyan-800/80 dark:bg-cyan-950/30 p-3 shadow-2xs space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-cyan-900 dark:text-cyan-200 font-mono">
                  <ArchiveRestoreIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
                  <span>隔离区物理快照就绪 (Zero-Loss Snapshot)</span>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    rollbackMutation.mutate({
                      snapshotPath,
                      targetPath: landingPath || `~/.openviking/data/viking/default/skills/${skillName}/SKILL.md`,
                    })
                  }
                  disabled={rollbackMutation.isPending}
                  className="text-xs h-7 px-2.5 font-mono border-cyan-400 text-cyan-800 hover:bg-cyan-100 dark:border-cyan-700 dark:text-cyan-200 dark:hover:bg-cyan-950/60 cursor-pointer font-medium"
                >
                  <ArchiveRestoreIcon className="size-3 mr-1 text-cyan-600 dark:text-cyan-400" />
                  {rollbackMutation.isPending ? '还原中...' : '⚡ 一键秒级回退 (<50ms)'}
                </Button>
              </div>
              <div className="text-xs font-mono text-muted-foreground truncate bg-background/80 p-1.5 rounded border border-border/60">
                {snapshotPath}
              </div>
            </div>
          )}

          {/* 准入指标与决策网格 */}
          <div className="grid grid-cols-2 gap-2">
            <div className="rounded border border-border/70 bg-card p-2.5">
              <div className="text-xs text-muted-foreground font-mono flex items-center justify-between">
                <span>SkillOpt 评分</span>
                <ShieldCheckIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
              </div>
              <div className="text-base font-bold font-mono text-foreground mt-1">
                {optScore !== undefined ? `${Number(optScore).toFixed(1)} / 100` : '--'}
              </div>
            </div>

            <div className="rounded border border-border/70 bg-card p-2.5">
              <div className="text-xs text-muted-foreground font-mono flex items-center justify-between">
                <span>归宿大包 (Target)</span>
                <GitBranchIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
              </div>
              <div className="text-xs font-bold font-mono text-foreground mt-1 truncate">
                {targetBundle || '独立领域母包'}
              </div>
            </div>
          </div>

          {/* AST 自愈记录 */}
          {remediatedFields && remediatedFields.length > 0 && (
            <div className="rounded-md border border-violet-200 bg-violet-50/60 dark:border-violet-800/60 dark:bg-violet-950/30 p-2.5 space-y-1">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-violet-900 dark:text-violet-200 font-mono">
                <Wand2Icon className="size-3.5 text-violet-600 dark:text-violet-400" />
                <span>AST 语法自愈已补齐缺失字段</span>
              </div>
              <div className="flex flex-wrap gap-1.5 pt-1">
                {remediatedFields.map((field) => (
                  <span
                    key={field}
                    className="px-2 py-0.5 rounded text-xs font-mono font-medium bg-violet-100 text-violet-800 border border-violet-300 dark:bg-violet-900/60 dark:text-violet-200 dark:border-violet-700"
                  >
                    +{field}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 阻断与错误提示 */}
          {errors && (
            <div className="rounded-md border border-rose-300 bg-rose-50/70 dark:border-rose-800/80 dark:bg-rose-950/40 p-3 space-y-1">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-rose-900 dark:text-rose-200 font-mono">
                <ShieldAlertIcon className="size-3.5 text-rose-600 dark:text-rose-400" />
                <span>静态门禁阻断原因 (Gatekeeper Rejection)</span>
              </div>
              <pre className="text-xs font-mono text-rose-800 dark:text-rose-300 whitespace-pre-wrap break-all mt-1">
                {typeof errors === 'string' ? errors : JSON.stringify(errors, null, 2)}
              </pre>
            </div>
          )}

          {/* Diff 比对审查区 */}
          {diffPatch ? (
            <div className="rounded-md border border-border/80 bg-card overflow-hidden">
              <div className="bg-muted/40 px-3 py-1.5 border-b border-border/60 text-xs font-mono text-muted-foreground flex items-center justify-between">
                <span>演变差异对比 (Diff Patch)</span>
                <span>Unified View</span>
              </div>
              <div className="max-h-60 overflow-y-auto divide-y divide-border/20 font-mono text-xs">
                {diffPatch.split('\n').map((line: string, idx: number) => {
                  const isDel = line.startsWith('-')
                  const isAdd = line.startsWith('+')
                  return (
                    <div
                      key={idx}
                      className={cn(
                        'flex items-start px-2 py-0.5',
                        isDel && 'bg-rose-500/10 text-rose-600 dark:text-rose-400',
                        isAdd && 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400',
                        !isDel && !isAdd && 'text-muted-foreground'
                      )}
                    >
                      <pre className="overflow-x-auto whitespace-pre font-mono text-xs leading-5">
                        {line}
                      </pre>
                    </div>
                  )
                })}
              </div>
            </div>
          ) : (
            <div className="rounded-md border border-border/70 bg-card p-3 space-y-1.5">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground font-mono">
                <FileTextIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
                <span>{isProv ? '审计留痕元数据' : '收件箱原始草稿'}</span>
              </div>
              <pre className="text-xs font-mono text-muted-foreground bg-muted/30 p-2.5 rounded border border-border/40 max-h-52 overflow-y-auto whitespace-pre-wrap break-all">
                {isProv
                  ? JSON.stringify(prov?.details || {}, null, 2)
                  : ing?.raw_content || ing?.status_message || '无内容'}
              </pre>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
