// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import {
  BanIcon,
  CheckIcon,
  CopyIcon,
  FileCheckIcon,
  FingerprintIcon,
  LayersIcon,
  SparklesIcon,
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

export interface FactCrystal {
  uri: string
  axiom: string
  context_bounds: {
    version_range: string
    source_uris: string[]
    evidence_hashes: string[]
    distilled_at: number
    distiller_id: string
  }
  negative_boundary: {
    deprecated_patterns: string[]
    forbidden_keywords: string[]
  }
  status: string
  created_at: number
}

interface FactCrystalDrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  crystal: FactCrystal | null
}

export function FactCrystalDrawer({
  open,
  onOpenChange,
  crystal,
}: FactCrystalDrawerProps) {
  const [copiedUri, setCopiedUri] = React.useState(false)
  const [copiedJson, setCopiedJson] = React.useState(false)
  const [showJson, setShowJson] = React.useState(false)

  const handleCopyUri = () => {
    if (!crystal) return
    void navigator.clipboard.writeText(crystal.uri)
    setCopiedUri(true)
    setTimeout(() => setCopiedUri(false), 2000)
  }

  const handleCopyJson = () => {
    if (!crystal) return
    void navigator.clipboard.writeText(JSON.stringify(crystal, null, 2))
    setCopiedJson(true)
    setTimeout(() => setCopiedJson(false), 2000)
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="sm:max-w-xl flex flex-col h-full overflow-hidden p-0 gap-0"
      >
        <SheetHeader className="p-4 border-b border-border/60 bg-muted/20">
          <div className="flex items-center justify-between">
            <SheetTitle className="text-sm font-semibold flex items-center gap-2 text-foreground">
              <SparklesIcon className="size-4 text-cyan-500" />
              不可变事实晶体详情 (SSOT Crystal)
            </SheetTitle>
            {crystal && (
              <span className="text-xs px-2 py-0.5 rounded font-mono font-medium bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/30">
                {crystal.status.toUpperCase()}
              </span>
            )}
          </div>
          <SheetDescription className="text-xs text-muted-foreground mt-0.5">
            三层拓扑（L0 公理 / L1 边界 / L2 哨兵）· 不可变净减熵事实
          </SheetDescription>
        </SheetHeader>

        {crystal ? (
          <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
            {/* L0 顶级事实公理 */}
            <div className="rounded-md border border-cyan-500/40 bg-cyan-500/5 p-3 flex flex-col gap-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-cyan-700 dark:text-cyan-300 flex items-center gap-1.5">
                  <SparklesIcon className="size-3.5 text-cyan-500" />
                  L0 核心事实公理 (Axiom)
                </span>
                <span className="text-xs font-mono text-muted-foreground">不可变真理</span>
              </div>
              <p className="text-xs text-foreground font-semibold leading-relaxed pt-1">
                {crystal.axiom}
              </p>
            </div>

            {/* 基本元数据 */}
            <div className="rounded-md border border-border/70 bg-card p-3 flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">晶体 URI</span>
                <div className="flex items-center gap-1.5 font-mono text-xs text-foreground font-semibold">
                  <span className="break-all">{crystal.uri}</span>
                  <button
                    type="button"
                    onClick={handleCopyUri}
                    className="p-1 hover:bg-muted rounded text-muted-foreground hover:text-foreground cursor-pointer shrink-0"
                    title="复制 URI"
                  >
                    {copiedUri ? <CheckIcon className="size-3 text-cyan-500" /> : <CopyIcon className="size-3" />}
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">适用版本范围 (L1)</span>
                <span className="font-mono text-cyan-600 dark:text-cyan-400 font-medium">
                  {crystal.context_bounds.version_range}
                </span>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">熔铸者 ID</span>
                <span className="font-mono text-foreground">{crystal.context_bounds.distiller_id}</span>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">熔铸时间戳</span>
                <span className="font-mono text-muted-foreground">
                  {new Date(crystal.context_bounds.distilled_at * 1000).toLocaleString()}
                </span>
              </div>
            </div>

            {/* 来源碎片与证据哈希链 */}
            <div className="rounded-md border border-border/70 bg-card p-3 flex flex-col gap-2.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <LayersIcon className="size-3.5 text-cyan-500" />
                  关联证据与来源碎片 ({crystal.context_bounds.source_uris.length})
                </span>
              </div>

              <div className="flex flex-col gap-1.5 max-h-36 overflow-y-auto pr-1">
                {crystal.context_bounds.source_uris.map((u, i) => (
                  <div
                    key={i}
                    className="rounded bg-muted/40 px-2 py-1 text-xs font-mono text-muted-foreground break-all flex items-center gap-1.5"
                  >
                    <FileCheckIcon className="size-3 text-cyan-500 shrink-0" />
                    <span>{u}</span>
                  </div>
                ))}
              </div>

              {crystal.context_bounds.evidence_hashes.length > 0 && (
                <div className="pt-2 border-t border-border/50 flex flex-col gap-1.5">
                  <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                    <FingerprintIcon className="size-3.5 text-cyan-500" />
                    SHA-256 证据链指纹
                  </span>
                  <div className="flex flex-col gap-1 max-h-24 overflow-y-auto">
                    {crystal.context_bounds.evidence_hashes.map((h, i) => (
                      <span key={i} className="text-xs font-mono text-muted-foreground/80 break-all">
                        {h}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* L2 负向排斥哨兵 */}
            <div className="rounded-md border border-border/70 bg-card p-3 flex flex-col gap-2">
              <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                <BanIcon className="size-3.5 text-amber-500" />
                L2 负向排斥边界与废弃模式
              </span>

              {crystal.negative_boundary.deprecated_patterns.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {crystal.negative_boundary.deprecated_patterns.map((p, i) => (
                    <span
                      key={i}
                      className="rounded bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 text-xs text-amber-700 dark:text-amber-300 font-mono"
                    >
                      {p}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">暂无显式声明的废弃模式</p>
              )}

              {crystal.negative_boundary.forbidden_keywords.length > 0 && (
                <div className="pt-1 flex flex-wrap gap-1.5">
                  {crystal.negative_boundary.forbidden_keywords.map((k, i) => (
                    <span
                      key={i}
                      className="rounded bg-rose-500/10 border border-rose-500/30 px-2 py-0.5 text-xs text-rose-700 dark:text-rose-300 font-mono"
                    >
                      禁止: {k}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* 原始 JSON 折叠 */}
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
                  {JSON.stringify(crystal, null, 2)}
                </pre>
              )}
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center p-6 text-xs text-muted-foreground">
            未选择事实晶体
          </div>
        )}

        {crystal && (
          <SheetFooter className="p-4 border-t border-border/60 bg-muted/20 flex flex-row items-center justify-between gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onOpenChange(false)}
              className="text-xs h-8"
            >
              关闭
            </Button>

            <Button
              size="sm"
              variant="outline"
              onClick={handleCopyJson}
              className="text-xs h-8 gap-1.5"
            >
              {copiedJson ? (
                <>
                  <CheckIcon className="size-3 text-cyan-500" />
                  已复制 JSON
                </>
              ) : (
                <>
                  <CopyIcon className="size-3" />
                  复制完整 JSON
                </>
              )}
            </Button>
          </SheetFooter>
        )}
      </SheetContent>
    </Sheet>
  )
}
