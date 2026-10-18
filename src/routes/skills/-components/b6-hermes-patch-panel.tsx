// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import {
  ChevronDownIcon,
  ChevronRightIcon,
  CodeIcon,
  RotateCcwIcon,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { cn } from '#/lib/utils'
import type { SkillPatch } from '../-types/hermes-ahe'

interface B6HermesPatchPanelProps {
  patches: SkillPatch[]
  isLoading: boolean
  onApplyPatch: (patchId: string) => void
  onRevertPatch: (patchId: string) => void
  isApplying: boolean
  isReverting: boolean
}

export function B6HermesPatchPanel({
  patches,
  isLoading,
  onApplyPatch,
  onRevertPatch,
  isApplying,
  isReverting,
}: B6HermesPatchPanelProps) {
  const [expandedPatchId, setExpandedPatchId] = React.useState<string | null>(null)

  return (
    <div className="rounded-md border border-border/70 overflow-hidden bg-background">
      <div className="bg-muted/40 px-3 py-2 border-b border-border/60 flex items-center justify-between text-xs font-mono">
        <span className="font-semibold text-foreground flex items-center gap-1.5">
          <CodeIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
          Hermes 经历微手术补丁列表 (≤30 行细粒度局部手术)
        </span>
        <span className="text-muted-foreground">可逆秒级一键回滚</span>
      </div>

      <div className="divide-y divide-border/30 max-h-72 overflow-y-auto">
        {patches.length === 0 ? (
          <div className="p-6 text-center text-xs font-mono text-muted-foreground">
            {isLoading ? '加载微补丁中...' : '暂无微手术补丁提议记录'}
          </div>
        ) : (
          patches.map((patch) => {
            const isExpanded = expandedPatchId === patch.patch_id
            const isProposed = patch.status === 'proposed'
            const isApplied = patch.status === 'applied'

            return (
              <div key={patch.patch_id} className="text-xs font-mono">
                <div className="flex items-center justify-between px-3 py-2 hover:bg-muted/30 transition-colors">
                  <button
                    type="button"
                    data-testid={`patch-toggle-${patch.patch_id}`}
                    onClick={() => setExpandedPatchId(isExpanded ? null : patch.patch_id)}
                    className="flex items-center gap-2 truncate text-left cursor-pointer flex-1 mr-2"
                  >
                    {isExpanded ? (
                      <ChevronDownIcon className="size-3.5 text-muted-foreground shrink-0" />
                    ) : (
                      <ChevronRightIcon className="size-3.5 text-muted-foreground shrink-0" />
                    )}
                    <Badge
                      variant="outline"
                      className={cn(
                        'text-xs font-mono px-1.5 py-0 border shrink-0',
                        isProposed &&
                          'border-amber-300 bg-amber-50 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800',
                        isApplied &&
                          'border-cyan-300 bg-cyan-50 text-cyan-800 dark:bg-cyan-950/40 dark:text-cyan-300 dark:border-cyan-800',
                        !isProposed && !isApplied && 'border-border bg-muted/40 text-muted-foreground'
                      )}
                    >
                      {patch.status.toUpperCase()}
                    </Badge>
                    <span className="font-semibold text-foreground truncate">{patch.skill_name}</span>
                    <span className="text-muted-foreground truncate max-w-xs">{patch.reason}</span>
                  </button>

                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-xs text-muted-foreground">
                      -{patch.target_line_count}/+{patch.replacement_line_count}行
                    </span>
                    {isProposed && (
                      <Button
                        size="sm"
                        onClick={() => onApplyPatch(patch.patch_id)}
                        disabled={isApplying}
                        className="text-xs h-6 px-2 font-mono bg-cyan-600 hover:bg-cyan-700 text-white font-medium cursor-pointer"
                      >
                        应用补丁
                      </Button>
                    )}
                    {isApplied && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onRevertPatch(patch.patch_id)}
                        disabled={isReverting}
                        className="text-xs h-6 px-2 font-mono border-rose-300 text-rose-800 hover:bg-rose-50 dark:border-rose-800 dark:text-rose-300 dark:hover:bg-rose-950/40 cursor-pointer"
                      >
                        <RotateCcwIcon className="size-3 mr-1 text-rose-600" />
                        秒级回退
                      </Button>
                    )}
                  </div>
                </div>

                {isExpanded && (
                  <div className="px-4 pb-3 pt-1 bg-muted/20 border-t border-border/20 space-y-2">
                    <div className="text-xs text-muted-foreground flex items-center justify-between">
                      <span>目标文件: {patch.file_path}</span>
                      <span>ID: {patch.patch_id}</span>
                    </div>
                    {/* 紧凑 Diff 面板 */}
                    <div className="rounded border border-border/60 bg-card overflow-hidden">
                      <div className="bg-rose-500/10 text-rose-600 dark:text-rose-400 px-2 py-1 flex items-start gap-1.5 border-b border-border/20">
                        <span className="font-bold shrink-0">-</span>
                        <pre data-testid={`patch-target-${patch.patch_id}`} className="overflow-x-auto whitespace-pre-wrap font-mono text-xs">
                          {patch.target_content}
                        </pre>
                      </div>
                      <div className="bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 px-2 py-1 flex items-start gap-1.5">
                        <span className="font-bold shrink-0">+</span>
                        <pre data-testid={`patch-replacement-${patch.patch_id}`} className="overflow-x-auto whitespace-pre-wrap font-mono text-xs">
                          {patch.replacement_content}
                        </pre>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
