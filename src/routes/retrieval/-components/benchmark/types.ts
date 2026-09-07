// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

export type BenchmarkMode = 'fast' | 'ragas'

export interface RagasScoreBreakdown {
  contextPrecision: number // 上下文排布精度 [0, 1]
  contextRecall: number // 知识域覆盖率 [0, 1]
  faithfulness: number // 语义忠实度/纯净度 [0, 1]
  answerRelevance: number // 答案相关度 [0, 1]
  compositeScore: number // 综合 RAGAS 指数 (调和平均) [0, 1]
}

export interface BenchmarkResultItem {
  id: string
  query: string
  top1Title?: string
  top1Uri?: string
  score?: number
  latencyMs?: number
  status: 'pending' | 'running' | 'hit' | 'miss' | 'error'
  errorMsg?: string
  ragas?: RagasScoreBreakdown
}

export interface BenchmarkSummaryMetrics {
  total: number
  completed: number
  hitRate: number
  avgLatency: number
  avgScore: string
  ragas?: {
    avgPrecision: string
    avgRecall: string
    avgFaithfulness: string
    avgRelevance: string
    compositeScore: string
  }
}
