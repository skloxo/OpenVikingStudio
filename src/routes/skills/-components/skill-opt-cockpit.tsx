// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { ActivityIcon, RefreshCwIcon } from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import { ovClient } from '#/lib/ov-client'
import { SkillOptScorecard } from './skill-opt-scorecard'
import { SkillOptWorkbench } from './skill-opt-workbench'
import type {
  BatchAuditSummary,
  SkillOptAttemptResult,
  SkillOptAuditResult,
  SkillOptOptimizeResult,
} from './skill-opt-types'

const DEFAULT_SAMPLE_SKILL = `---
name: diagnosing-bugs
description: 深度排查高难度 Bug、内存泄露与死锁的 SOP 闭环规约。
tools:
  - openviking_find
  - openviking_read
---

# Diagnosing Bugs SOP

## 1. 触发意图与场景 (When to Use)
- 触发关键词：程序崩溃、内存泄露、性能骤降、报错分析、死锁排查。

## 2. 边界约束与负向判定 (Boundary Constraints)
- **何时严禁使用**：当仅是简单编译语法错误时，严禁滥用本排障流程；
- **职责隔离**：常规功能重构请路由至 master-dev 技能。

## 3. 标准排查清单 (Workflow Steps)
1. 提取错误日志与异常堆栈；
2. 构造最小隔离复现用例；
3. 执行根因诊断与回归门禁。

## 4. 工具调用示例
\`\`\`bash
# 执行定向单测定位
pytest tests/unit/ -k test_leak -v
\`\`\`
`

export function SkillOptCockpit() {
  const [content, setContent] = React.useState(DEFAULT_SAMPLE_SKILL)
  const [auditResult, setAuditResult] = React.useState<SkillOptAuditResult | null>(null)
  const [attemptResult, setAttemptResult] = React.useState<SkillOptAttemptResult | null>(null)
  const [optimizeResult, setOptimizeResult] = React.useState<SkillOptOptimizeResult | null>(null)

  // 1. Batch Audit Query
  const { data: batchData, refetch: refetchBatch, isLoading: isBatchLoading } = useQuery({
    queryKey: ['skill-opt-batch-audit'],
    queryFn: async () => {
      const res = await ovClient.instance.get<BatchAuditSummary>('/api/v1/skill-opt/batch-audit')
      return res.data
    },
    staleTime: 60_000,
  })

  // 2. Audit Mutation
  const auditMutation = useMutation({
    mutationFn: async (skillContent: string) => {
      const res = await ovClient.instance.post<SkillOptAuditResult>('/api/v1/skill-opt/audit', {
        skill_content: skillContent,
      })
      return res.data
    },
    onSuccess: (data) => {
      setAuditResult(data)
    },
  })

  // 3. Attempt Mutation
  const attemptMutation = useMutation({
    mutationFn: async (query: string) => {
      const res = await ovClient.instance.post<SkillOptAttemptResult>('/api/v1/skill-opt/attempt', {
        skill_content: content,
        test_query: query,
      })
      return res.data
    },
    onSuccess: (data) => {
      setAttemptResult(data)
    },
  })

  // 4. Optimize Mutation
  const optimizeMutation = useMutation({
    mutationFn: async () => {
      const res = await ovClient.instance.post<SkillOptOptimizeResult>('/api/v1/skill-opt/optimize', {
        skill_content: content,
      })
      return res.data
    },
    onSuccess: (data) => {
      setOptimizeResult(data)
    },
  })

  // 初始自动体检一次
  React.useEffect(() => {
    auditMutation.mutate(DEFAULT_SAMPLE_SKILL)
  }, [])

  return (
    <div className="flex flex-col gap-3.5 w-full min-w-0">
      {/* Top Banner: Global Health Overview */}
      <Card className="p-3.5 border-border/60 bg-muted/10 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <ActivityIcon className="size-4 text-cyan-400" />
          <div className="grid gap-0.5">
            <span className="text-xs font-semibold tracking-tight">全库技能 SkillOpt 质量健康大盘</span>
            <span className="text-xs font-mono text-muted-foreground">
              基于四维质量标尺 (规范完整度 / 工具精准度 / 注意力信噪比 / 触发区分度)
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          <Badge variant="outline" className="border-border bg-background/80 px-2 py-0.5">
            已体检: <strong className="text-foreground ml-1 tabular-nums">{batchData?.total_audited ?? 0} 个</strong>
          </Badge>
          <Badge variant="outline" className="border-cyan-500/30 text-cyan-400 bg-cyan-500/10 px-2 py-0.5">
            均分: <strong className="ml-1 tabular-nums">{batchData?.avg_score ?? 0} 分</strong>
          </Badge>
          <div className="flex items-center gap-1">
            <Badge variant="outline" className="border-cyan-500/40 text-cyan-300 px-1 py-0.2">
              S: {batchData?.grade_counts.S ?? 0}
            </Badge>
            <Badge variant="outline" className="border-cyan-500/30 text-cyan-400 px-1 py-0.2">
              A: {batchData?.grade_counts.A ?? 0}
            </Badge>
            <Badge variant="outline" className="border-border text-foreground px-1 py-0.2">
              B: {batchData?.grade_counts.B ?? 0}
            </Badge>
            <Badge variant="outline" className="border-amber-500/40 text-amber-400 px-1 py-0.2">
              C: {batchData?.grade_counts.C ?? 0}
            </Badge>
            <Badge variant="outline" className="border-rose-500/40 text-rose-400 px-1 py-0.2">
              D: {batchData?.grade_counts.D ?? 0}
            </Badge>
          </div>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => refetchBatch()}
            disabled={isBatchLoading}
            className="h-6 px-1.5 text-xs text-muted-foreground hover:text-cyan-400"
          >
            <RefreshCwIcon className={`size-3 ${isBatchLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </Card>

      {/* Main Grid: Workbench on left, Scorecard on right */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5 items-start">
        <SkillOptWorkbench
          content={content}
          onContentChange={(val) => {
            setContent(val)
            setOptimizeResult(null)
          }}
          onAudit={() => auditMutation.mutate(content)}
          onAttempt={(q) => attemptMutation.mutate(q)}
          onOptimize={() => optimizeMutation.mutate()}
          attemptResult={attemptResult}
          optimizeResult={optimizeResult}
          isAuditing={auditMutation.isPending}
          isAttempting={attemptMutation.isPending}
          isOptimizing={optimizeMutation.isPending}
        />

        <SkillOptScorecard audit={auditResult} isLoading={auditMutation.isPending} />
      </div>
    </div>
  )
}
