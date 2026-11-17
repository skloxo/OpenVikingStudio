// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import { useMutation } from '@tanstack/react-query'
import { GaugeIcon, LoaderCircleIcon, ShieldAlertIcon, ShieldCheckIcon, ZapIcon } from 'lucide-react'
import * as React from 'react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import {
  runPlaygroundCompressSimulate,
  type CompressSimulateResponse,
} from '../-lib/playground-api'

interface SkillCompressionBenchProps {
  skillContent: string
  setSkillContent: (val: string) => void
}

export function SkillCompressionBench({
  skillContent,
  setSkillContent,
}: SkillCompressionBenchProps) {
  const [result, setResult] = React.useState<CompressSimulateResponse | null>(null)
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: runPlaygroundCompressSimulate,
    onSuccess: (data) => {
      setErrorMsg(null)
      setResult(data)
    },
    onError: (err: unknown) => {
      setErrorMsg(err instanceof Error ? err.message : '压缩试算失败')
    },
  })

  const handleSimulate = () => {
    if (!skillContent.trim()) return
    mutation.mutate({ skill_content: skillContent })
  }

  return (
    <Card className="p-4 border-border/80 bg-card flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-semibold font-mono text-foreground">
          <GaugeIcon className="size-4 text-cyan-500" />
          <span>动态注脑 Six-Tuple 压缩与保真度度量台</span>
        </div>
        <Button
          type="button"
          size="sm"
          disabled={mutation.isPending || !skillContent.trim()}
          onClick={handleSimulate}
          className="h-8 text-xs font-mono bg-cyan-600 hover:bg-cyan-500 text-white"
        >
          {mutation.isPending ? (
            <LoaderCircleIcon className="size-3.5 mr-1.5 animate-spin" />
          ) : (
            <ZapIcon className="size-3.5 mr-1.5" />
          )}
          试算压缩对比
        </Button>
      </div>

      <textarea
        value={skillContent}
        onChange={(e) => setSkillContent(e.target.value)}
        rows={7}
        placeholder="粘贴或由右侧脚手架导入 SKILL.md 文本..."
        className="w-full rounded-md border border-border bg-background p-2.5 text-xs font-mono text-foreground outline-none focus:border-cyan-500"
      />

      {errorMsg && (
        <div className="rounded border border-rose-500/40 bg-rose-950/20 px-3 py-2 text-xs font-mono text-rose-300">
          {errorMsg}
        </div>
      )}

      {result && (
        <div className="grid gap-3">
          <div className="grid gap-2 sm:grid-cols-4 text-xs font-mono">
            <div className="rounded border border-border/70 bg-muted/20 p-2.5">
              <div className="text-muted-foreground">字符数 (原 ➔ 压)</div>
              <div className="text-sm font-semibold text-foreground mt-0.5">
                {result.compression.original_length} ➔ {result.compression.compressed_length}
              </div>
            </div>
            <div className="rounded border border-border/70 bg-muted/20 p-2.5">
              <div className="text-muted-foreground">压缩率 / 节省 Token</div>
              <div className="text-sm font-semibold text-cyan-400 mt-0.5">
                {(result.compression.compression_ratio * 100).toFixed(1)}% / {result.compression.tokens_saved}
              </div>
            </div>
            <div className="rounded border border-border/70 bg-muted/20 p-2.5">
              <div className="text-muted-foreground">契约保真度 / 耗时</div>
              <div className="text-sm font-semibold text-cyan-400 mt-0.5">
                {(result.compression.contract_fidelity * 100).toFixed(0)}% / {result.compression.latency_ms.toFixed(1)} ms
              </div>
            </div>
            <div className="rounded border border-border/70 bg-muted/20 p-2.5 flex flex-col justify-between">
              <div className="text-muted-foreground">Zip 门禁判定</div>
              <Badge
                variant="outline"
                className={`mt-1 w-fit text-xs font-mono ${result.gate.passed ? 'border-cyan-500/50 text-cyan-400' : 'border-rose-500/50 text-rose-400'}`}
              >
                {result.gate.passed ? (
                  <ShieldCheckIcon className="size-3 mr-1" />
                ) : (
                  <ShieldAlertIcon className="size-3 mr-1" />
                )}
                {result.gate.recommended_action}
              </Badge>
            </div>
          </div>

          <pre className="max-h-56 overflow-auto rounded border border-border/70 bg-background/80 p-2.5 text-xs font-mono text-foreground whitespace-pre-wrap">
            {result.compression.compressed_content}
          </pre>
        </div>
      )}
    </Card>
  )
}
