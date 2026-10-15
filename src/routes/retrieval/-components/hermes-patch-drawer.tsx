// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import {
  AlertCircleIcon,
  CheckIcon,
  CodeIcon,
  CopyIcon,
  FileCodeIcon,
  PlayIcon,
  RotateCcwIcon,
} from 'lucide-react'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from '#/components/ui/sheet'
import { Button } from '#/components/ui/button'

export interface SkillPatch {
  patch_id: string
  skill_name: string
  file_path: string
  target_content: string
  replacement_content: string
  reason: string
  status: 'proposed' | 'applied' | 'reverted'
  created_at: number
  applied_at?: number
  target_line_count: number
  replacement_line_count: number
}

interface HermesPatchDrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  patch: SkillPatch | null
  onApply: (patchId: string) => Promise<void> | void
  onRevert: (patchId: string) => Promise<void> | void
  isApplying?: boolean
  isReverting?: boolean
}

export function HermesPatchDrawer({
  open,
  onOpenChange,
  patch,
  onApply,
  onRevert,
  isApplying = false,
  isReverting = false,
}: HermesPatchDrawerProps) {
  const [copiedId, setCopiedId] = React.useState(false)
  const [showJson, setShowJson] = React.useState(false)

  const handleCopyId = () => {
    if (!patch) return
    void navigator.clipboard.writeText(patch.patch_id)
    setCopiedId(true)
    setTimeout(() => setCopiedId(false), 2000)
  }

  const targetLines = patch?.target_content ? patch.target_content.split('\n') : []
  const replacementLines = patch?.replacement_content ? patch.replacement_content.split('\n') : []

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="sm:max-w-xl flex flex-col h-full overflow-hidden p-0 gap-0"
      >
        <SheetHeader className="p-4 border-b border-border/60 bg-muted/20">
          <div className="flex items-center justify-between">
            <SheetTitle className="text-sm font-semibold flex items-center gap-2 text-foreground">
              <CodeIcon className="size-4 text-cyan-500" />
              Hermes 微手术补丁审查
            </SheetTitle>
            {patch && (
              <span
                className={`text-xs px-2 py-0.5 rounded font-mono font-medium ${
                  patch.status === 'applied'
                    ? 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/30'
                    : patch.status === 'reverted'
                      ? 'bg-muted text-muted-foreground border border-border'
                      : 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30'
                }`}
              >
                {patch.status.toUpperCase()}
              </span>
            )}
          </div>
          <SheetDescription className="text-xs text-muted-foreground mt-0.5">
            ≤30 行物理微手术门禁 · 1-Click 审查与原子化应用/回滚
          </SheetDescription>
        </SheetHeader>

        {patch ? (
          <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
            {/* 补丁元数据与路径 */}
            <div className="rounded-md border border-border/70 bg-card p-3 flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">补丁 ID</span>
                <div className="flex items-center gap-1.5 font-mono text-xs text-foreground font-semibold">
                  <span>{patch.patch_id}</span>
                  <button
                    type="button"
                    onClick={handleCopyId}
                    className="p-1 hover:bg-muted rounded text-muted-foreground hover:text-foreground cursor-pointer"
                    title="复制 Patch ID"
                  >
                    {copiedId ? <CheckIcon className="size-3 text-cyan-500" /> : <CopyIcon className="size-3" />}
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">所属技能</span>
                <span className="font-mono text-cyan-600 dark:text-cyan-400 font-medium">
                  {patch.skill_name}
                </span>
              </div>

              <div className="flex items-start justify-between text-xs gap-2">
                <span className="text-muted-foreground shrink-0">目标文件</span>
                <span className="font-mono text-foreground break-all text-right text-xs">
                  {patch.file_path}
                </span>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">行数变更</span>
                <span className="font-mono text-xs">
                  <span className="text-rose-500 font-semibold">-{patch.target_line_count}</span>
                  {' / '}
                  <span className="text-cyan-500 font-semibold">+{patch.replacement_line_count}</span>
                  <span className="text-muted-foreground ml-1.5">(≤30行 门禁通过)</span>
                </span>
              </div>

              <div className="pt-2 border-t border-border/50 text-xs">
                <span className="text-muted-foreground block mb-1">变更动因:</span>
                <p className="text-foreground bg-muted/40 p-2 rounded leading-relaxed">
                  {patch.reason}
                </p>
              </div>
            </div>

            {/* 微手术 Diff 审查面板 */}
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <FileCodeIcon className="size-3.5 text-cyan-500" />
                  微手术变更 Diff 对比
                </span>
                <span className="text-xs text-muted-foreground font-mono">
                  Unified View
                </span>
              </div>

              <div className="rounded-md border border-border/70 bg-card overflow-hidden font-mono text-xs">
                <div className="bg-muted/40 px-3 py-1.5 border-b border-border/60 text-xs text-muted-foreground flex items-center justify-between">
                  <span>@@ -1,{patch.target_line_count} +1,{patch.replacement_line_count} @@</span>
                  <span>{patch.file_path.split('/').pop()}</span>
                </div>

                <div className="max-h-64 overflow-y-auto divide-y divide-border/20">
                  {targetLines.map((line, idx) => (
                    <div
                      key={`del-${idx}`}
                      className="flex items-start px-2 py-0.5 bg-rose-500/10 text-rose-600 dark:text-rose-400 hover:bg-rose-500/15"
                    >
                      <span className="select-none w-6 text-muted-foreground/60 text-right pr-2 shrink-0">
                        {idx + 1}
                      </span>
                      <span className="select-none text-rose-500 font-bold px-1 shrink-0">-</span>
                      <pre className="flex-1 overflow-x-auto whitespace-pre font-mono text-xs leading-5">
                        {line}
                      </pre>
                    </div>
                  ))}

                  {replacementLines.map((line, idx) => (
                    <div
                      key={`add-${idx}`}
                      className="flex items-start px-2 py-0.5 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 hover:bg-cyan-500/15"
                    >
                      <span className="select-none w-6 text-muted-foreground/60 text-right pr-2 shrink-0">
                        {idx + 1}
                      </span>
                      <span className="select-none text-cyan-500 font-bold px-1 shrink-0">+</span>
                      <pre className="flex-1 overflow-x-auto whitespace-pre font-mono text-xs leading-5">
                        {line}
                      </pre>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* 原始 JSON 抽屉展示折叠 */}
            <div className="flex flex-col gap-1.5 pt-1">
              <button
                type="button"
                onClick={() => setShowJson(!showJson)}
                className="text-xs text-muted-foreground hover:text-foreground text-left cursor-pointer flex items-center justify-between"
              >
                <span>{showJson ? '收起完整原始 JSON' : '查看完整原始 JSON 结构'}</span>
                <span className="font-mono text-xs text-muted-foreground">
                  {showJson ? '▲' : '▼'}
                </span>
              </button>
              {showJson && (
                <pre className="rounded-md border border-border/60 bg-muted/30 p-2.5 text-xs font-mono text-muted-foreground overflow-x-auto max-h-40">
                  {JSON.stringify(patch, null, 2)}
                </pre>
              )}
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center p-6 text-xs text-muted-foreground">
            <AlertCircleIcon className="size-4 mr-2 text-muted-foreground" />
            未选择微手术补丁
          </div>
        )}

        {patch && (
          <SheetFooter className="p-4 border-t border-border/60 bg-muted/20 flex flex-row items-center justify-between gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onOpenChange(false)}
              className="text-xs h-8"
            >
              关闭
            </Button>

            <div className="flex items-center gap-2">
              {patch.status === 'proposed' && (
                <Button
                  size="sm"
                  disabled={isApplying}
                  onClick={() => onApply(patch.patch_id)}
                  className="text-xs h-8 bg-cyan-600 dark:bg-cyan-500 text-white hover:bg-cyan-700 gap-1.5"
                >
                  <PlayIcon className="size-3" />
                  {isApplying ? '正在原子应用...' : 'Approve & Apply (应用)'}
                </Button>
              )}
              {patch.status === 'applied' && (
                <Button
                  size="sm"
                  variant="outline"
                  disabled={isReverting}
                  onClick={() => onRevert(patch.patch_id)}
                  className="text-xs h-8 text-amber-600 dark:text-amber-400 border-amber-500/40 hover:bg-amber-500/10 gap-1.5"
                >
                  <RotateCcwIcon className="size-3" />
                  {isReverting ? '正在回滚...' : '一键回滚 (Revert)'}
                </Button>
              )}
            </div>
          </SheetFooter>
        )}
      </SheetContent>
    </Sheet>
  )
}
