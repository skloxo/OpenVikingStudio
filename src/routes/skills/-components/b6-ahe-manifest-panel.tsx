// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import {
  ChevronDownIcon,
  ChevronRightIcon,
  ShieldAlertIcon,
  ShieldCheckIcon,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { cn } from '#/lib/utils'
import type { AHEManifest } from '../-types/hermes-ahe'

interface B6AheManifestPanelProps {
  manifests: AHEManifest[]
  isLoading: boolean
}

export function B6AheManifestPanel({
  manifests,
  isLoading,
}: B6AheManifestPanelProps) {
  const [expandedManifestId, setExpandedManifestId] = React.useState<string | null>(null)

  return (
    <div className="rounded-md border border-border/70 overflow-hidden bg-background">
      <div className="bg-muted/40 px-3 py-2 border-b border-border/60 flex items-center justify-between text-xs font-mono">
        <span className="font-semibold text-foreground flex items-center gap-1.5">
          <ShieldCheckIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
          AHE 契约假设清单 (Manifest Contract Protection)
        </span>
        <span className="text-muted-foreground">Polar 断言验证</span>
      </div>

      <div className="divide-y divide-border/30 max-h-72 overflow-y-auto">
        {manifests.length === 0 ? (
          <div className="p-6 text-center text-xs font-mono text-muted-foreground">
            {isLoading ? '加载 AHE 契约清单中...' : '暂无 AHE 契约假设条目'}
          </div>
        ) : (
          manifests.map((m) => {
            const isExpanded = expandedManifestId === m.manifest_id
            const isVerified = m.status === 'verified'
            const isViolated = m.status === 'violated'

            return (
              <div key={m.manifest_id} className="text-xs font-mono">
                <button
                  type="button"
                  data-testid={`manifest-toggle-${m.manifest_id}`}
                  onClick={() => setExpandedManifestId(isExpanded ? null : m.manifest_id)}
                  className="w-full flex items-center justify-between px-3 py-2 hover:bg-muted/30 transition-colors text-left cursor-pointer"
                >
                  <div className="flex items-center gap-2 truncate">
                    {isExpanded ? (
                      <ChevronDownIcon className="size-3.5 text-muted-foreground shrink-0" />
                    ) : (
                      <ChevronRightIcon className="size-3.5 text-muted-foreground shrink-0" />
                    )}
                    <Badge
                      variant="outline"
                      className={cn(
                        'text-xs font-mono px-1.5 py-0 border',
                        isVerified &&
                          'border-cyan-300 bg-cyan-50 text-cyan-800 dark:bg-cyan-950/40 dark:text-cyan-300 dark:border-cyan-800',
                        isViolated &&
                          'border-rose-300 bg-rose-50 text-rose-800 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800',
                        !isVerified &&
                          !isViolated &&
                          'border-border bg-muted/40 text-muted-foreground'
                      )}
                    >
                      {m.status.toUpperCase()}
                    </Badge>
                    <span className="font-semibold text-foreground">{m.skill_name}</span>
                    <span className="text-muted-foreground truncate">
                      ({m.assumptions?.length || 0} 项假设)
                    </span>
                  </div>
                  <span className="text-xs text-muted-foreground">{m.manifest_id}</span>
                </button>

                {isExpanded && (
                  <div className="px-4 pb-2.5 pt-1 bg-muted/20 border-t border-border/20 space-y-2">
                    {m.violation_cause && (
                      <div className="p-2 rounded bg-rose-50/70 border border-rose-300 text-rose-800 dark:bg-rose-950/40 dark:border-rose-800 dark:text-rose-300">
                        <div className="flex items-center gap-1.5 font-bold mb-1">
                          <ShieldAlertIcon className="size-3.5 text-rose-600 dark:text-rose-400" />
                          <span>违规根因</span>
                        </div>
                        <p>{m.violation_cause}</p>
                        {m.violation_detail && <p className="mt-1 opacity-90">{m.violation_detail}</p>}
                      </div>
                    )}
                    <div className="space-y-1">
                      {m.assumptions?.map((ass) => (
                        <div key={ass.assumption_id} className="p-2 rounded bg-card border border-border/50">
                          <div className="text-foreground font-medium">{ass.description}</div>
                          {ass.frozen_surface && (
                            <div className="text-muted-foreground mt-0.5">
                              <span>冻结面: </span>
                              <code>{ass.frozen_surface}</code>
                            </div>
                          )}
                          {ass.validation_command && (
                            <div className="text-cyan-800 dark:text-cyan-300 mt-0.5">
                              <span>验证命令: </span>
                              <code>{ass.validation_command}</code>
                            </div>
                          )}
                        </div>
                      ))}
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
