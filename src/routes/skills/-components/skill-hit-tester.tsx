// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import { useMutation } from '@tanstack/react-query'
import { AlertTriangleIcon, CrosshairIcon, GitMergeIcon, LoaderCircleIcon, SparklesIcon } from 'lucide-react'
import * as React from 'react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import { runPlaygroundHitTest, type HitTestResponse } from '../-lib/playground-api'

interface SkillHitTesterProps {
  draftContent: string
}

export function SkillHitTester({ draftContent }: SkillHitTesterProps) {
  const [query, setQuery] = React.useState('帮我抓取网页正文并提纯归档')
  const [candidateName, setCandidateName] = React.useState('wechat-article-reader')
  const [triggersText, setTriggersText] = React.useState('抓取网页正文, extract webpage article')
  const [result, setResult] = React.useState<HitTestResponse | null>(null)
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: runPlaygroundHitTest,
    onSuccess: (data) => {
      setErrorMsg(null)
      setResult(data)
    },
    onError: (err: unknown) => {
      setErrorMsg(err instanceof Error ? err.message : '意图试算请求失败')
    },
  })

  const handleRun = (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return
    const triggers = triggersText
      .split(/[,，\n]/)
      .map((s) => s.trim())
      .filter(Boolean)
    mutation.mutate({
      query: query.trim(),
      candidate_name: candidateName.trim(),
      candidate_triggers: triggers,
      candidate_content: draftContent,
    })
  }

  return (
    <Card className="p-4 border-border/80 bg-card flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-semibold font-mono text-foreground">
          <CrosshairIcon className="size-4 text-cyan-500" />
          <span>Prompt 意图命中试算器与 KNN Margin 路由追踪</span>
        </div>
        {result && (
          <Badge variant="outline" className="text-xs font-mono border-cyan-500/40 text-cyan-400">
            在册技能样本: {result.catalog_size} 项
          </Badge>
        )}
      </div>

      <form onSubmit={handleRun} className="grid gap-2.5 md:grid-cols-3">
        <label className="grid gap-1 md:col-span-2 text-xs font-mono text-muted-foreground">
          <span>测试自然语言 Prompt</span>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="输入要模拟的 Agent 触发问句..."
            className="h-8 rounded-md border border-border bg-background px-2.5 text-xs text-foreground outline-none focus:border-cyan-500"
          />
        </label>
        <label className="grid gap-1 text-xs font-mono text-muted-foreground">
          <span>候选技能/别名 (可选)</span>
          <input
            value={candidateName}
            onChange={(e) => setCandidateName(e.target.value)}
            placeholder="例如 wechat-article-reader"
            className="h-8 rounded-md border border-border bg-background px-2.5 text-xs text-foreground outline-none focus:border-cyan-500"
          />
        </label>
        <label className="grid gap-1 md:col-span-2 text-xs font-mono text-muted-foreground">
          <span>候选触发词 (逗号分隔)</span>
          <input
            value={triggersText}
            onChange={(e) => setTriggersText(e.target.value)}
            placeholder="关键词 A, 关键词 B"
            className="h-8 rounded-md border border-border bg-background px-2.5 text-xs text-foreground outline-none focus:border-cyan-500"
          />
        </label>
        <div className="flex items-end">
          <Button
            type="submit"
            disabled={mutation.isPending || !query.trim()}
            className="w-full h-8 text-xs font-mono bg-cyan-600 hover:bg-cyan-500 text-white"
          >
            {mutation.isPending ? (
              <LoaderCircleIcon className="size-3.5 mr-1.5 animate-spin" />
            ) : (
              <SparklesIcon className="size-3.5 mr-1.5" />
            )}
            执行意图 Hit-Test
          </Button>
        </div>
      </form>

      {errorMsg && (
        <div className="rounded border border-rose-500/40 bg-rose-950/20 px-3 py-2 text-xs font-mono text-rose-300">
          {errorMsg}
        </div>
      )}

      {result && (
        <div className="grid gap-3 pt-1">
          <div className="grid gap-2 sm:grid-cols-4">
            <div className="rounded border border-border/70 bg-muted/20 p-2.5 text-xs font-mono">
              <div className="text-muted-foreground">Top-1 亲和度</div>
              <div className="text-sm font-semibold text-cyan-400 mt-0.5">
                {(result.top1_score * 100).toFixed(1)}%
              </div>
            </div>
            <div className="rounded border border-border/70 bg-muted/20 p-2.5 text-xs font-mono">
              <div className="text-muted-foreground">Top-2 竞争分</div>
              <div className="text-sm font-semibold text-foreground mt-0.5">
                {(result.top2_score * 100).toFixed(1)}%
              </div>
            </div>
            <div className="rounded border border-border/70 bg-muted/20 p-2.5 text-xs font-mono">
              <div className="text-muted-foreground">KNN Margin</div>
              <div className="text-sm font-semibold text-cyan-400 mt-0.5">
                {(result.margin * 100).toFixed(1)}%
              </div>
            </div>
            <div className="rounded border border-border/70 bg-muted/20 p-2.5 text-xs font-mono">
              <div className="text-muted-foreground">推荐归包决策</div>
              <div className="text-sm font-semibold text-foreground mt-0.5 flex items-center gap-1">
                <GitMergeIcon className="size-3.5 text-cyan-400" />
                {result.routing_decision.action} ({result.routing_decision.target_package})
              </div>
            </div>
          </div>

          {result.alias_resolution && (
            <div className="rounded border border-cyan-500/30 bg-cyan-950/15 px-3 py-2 text-xs font-mono text-foreground">
              别名透明投影流向：<span className="text-cyan-400 font-semibold">{candidateName || 'top-hit'}</span>{' '}
              ➔ 母包 <span className="text-cyan-400 font-semibold">{result.alias_resolution.bundle_name}</span>{' '}
              （目标：{result.alias_resolution.target_name || '--'}）
            </div>
          )}

          {result.collisions.has_collision && (
            <div className="rounded border border-rose-500/40 bg-rose-950/20 px-3 py-2 text-xs font-mono text-rose-300 flex flex-col gap-1">
              <div className="font-semibold flex items-center gap-1.5">
                <AlertTriangleIcon className="size-3.5 text-rose-400" />
                检测到触发词碰撞（{result.collisions.collisions.length} 项）
              </div>
              {result.collisions.collisions.map((c, idx) => (
                <div key={idx}>
                  • 与 [{c.conflicting_skill}] 最高相似度 {(c.max_similarity * 100).toFixed(1)}%
                </div>
              ))}
            </div>
          )}

          <div className="grid gap-1.5">
            <div className="text-xs font-mono text-muted-foreground">Top 命中排序结果</div>
            {result.matches.length === 0 ? (
              <div className="text-xs font-mono text-muted-foreground">当前技能库为空或未命中。</div>
            ) : (
              result.matches.map((m) => (
                <div
                  key={m.skill_name}
                  className="flex flex-wrap items-center justify-between gap-2 rounded border border-border/60 bg-background/60 px-2.5 py-1.5 text-xs font-mono"
                >
                  <div className="flex items-center gap-2">
                    <Badge
                      variant="outline"
                      className={`text-xs font-mono ${m.matched ? 'border-cyan-500/50 text-cyan-400' : 'border-border text-muted-foreground'}`}
                    >
                      {m.matched ? '命中' : '未达阈值'}
                    </Badge>
                    <span className="font-semibold text-foreground">{m.skill_name}</span>
                    <span className="text-muted-foreground">({m.best_trigger || '--'})</span>
                  </div>
                  <span className="text-cyan-400 font-semibold">{(m.score * 100).toFixed(1)}%</span>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </Card>
  )
}
