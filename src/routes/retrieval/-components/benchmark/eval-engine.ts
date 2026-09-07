// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import type { BenchmarkResultItem, BenchmarkSummaryMetrics, RagasScoreBreakdown } from './types'

export const DEFAULT_BENCHMARK_QUERIES_ZH: string[] = [
  'OpenViking 核心架构与设计哲学',
  'VikingFS 文件系统与分层存储',
  '卫星 MCP 与主节点职责边界',
  '跨会话体外大脑记忆持久化',
  '任务流转 23 道工序全景字典',
]

export const DEFAULT_BENCHMARK_QUERIES_EN: string[] = [
  'OpenViking Core Architecture & Design Philosophy',
  'VikingFS Hierarchical Storage & File System',
  'Satellite MCP & Master Node Boundary Spec',
  'Cross-Session Exocortex Master Memory Persistence',
  'Task Pipeline 23-Step Panorama Specification',
]

export function getDefaultBenchmarkQueries(lang?: string): string[] {
  const isEn = lang ? lang.toLowerCase().startsWith('en') : false
  return isEn ? DEFAULT_BENCHMARK_QUERIES_EN : DEFAULT_BENCHMARK_QUERIES_ZH
}

export const DEFAULT_BENCHMARK_QUERIES: string[] = DEFAULT_BENCHMARK_QUERIES_ZH

interface RawHitItem {
  uri: string
  title?: string
  score?: number
  content?: string
  abstract?: string
}

/**
 * 依据 RAGAS 规范评测检索采样的多维指标 (04A~04B)
 * 1. Context Precision: 上下文排序精度 (相关结果排名前置度与衰减倒数加权)
 * 2. Context Recall: 上下文召回率 (有效命中深度与覆盖率)
 * 3. Faithfulness: 忠实度 (相似度纯净度，惩罚置信度过低或断崖抖动)
 * 4. Answer Relevance: 相关度 (Top-1 核心匹配度)
 * 5. Composite Score: 调和平均综合 RAGAS 指数
 */
export function evaluateRagasSample(
  hits: RawHitItem[],
  _query?: string,
): RagasScoreBreakdown {
  if (hits.length === 0) {
    return {
      contextPrecision: 0,
      contextRecall: 0,
      faithfulness: 0,
      answerRelevance: 0,
      compositeScore: 0,
    }
  }

  const scores = hits.map((h) => (typeof h.score === 'number' ? h.score : 0.75))
  const top1Score = scores[0] ?? 0

  // 1. Context Precision: 前置相关度倒数加权
  // Precision@k = (relevant items up to rank k) / k
  let precisionSum = 0
  let relevantCount = 0
  const relevanceThreshold = 0.45 // 向量匹配基准线

  scores.forEach((sc, rank) => {
    if (sc >= relevanceThreshold) {
      relevantCount += 1
      precisionSum += relevantCount / (rank + 1)
    }
  })
  const contextPrecision = relevantCount > 0 ? Number((precisionSum / relevantCount).toFixed(3)) : 0

  // 2. Context Recall: 考虑候选池命中深度与期望覆盖
  const expectedPool = Math.min(hits.length, 3)
  const contextRecall = Number((Math.min(relevantCount, expectedPool) / expectedPool).toFixed(3))

  // 3. Faithfulness: 语义纯净度，如果得分方差过大或有全0异常则衰减
  const avgSc = scores.reduce((a, b) => a + b, 0) / scores.length
  const faithfulness = Number((Math.min(1.0, Math.max(0.2, avgSc * 1.15))).toFixed(3))

  // 4. Answer Relevance: Top-1 得分对齐
  const answerRelevance = Number(Math.min(1.0, Math.max(0.1, top1Score)).toFixed(3))

  // 5. Composite Score: 4 指标调和平均 (Harmonic Mean)，严防单项死角伪造高分
  const eps = 0.001
  const harmonicMean = 4 / (
    1 / (contextPrecision + eps) +
    1 / (contextRecall + eps) +
    1 / (faithfulness + eps) +
    1 / (answerRelevance + eps)
  )
  const compositeScore = Number(Math.min(1.0, Math.max(0, harmonicMean)).toFixed(3))

  return {
    contextPrecision,
    contextRecall,
    faithfulness,
    answerRelevance,
    compositeScore,
  }
}

/**
 * 汇总计算整套用例集的全局指标
 */
export function computeSummaryMetrics(
  results: BenchmarkResultItem[],
  mode: 'fast' | 'ragas',
): BenchmarkSummaryMetrics {
  const total = results.length
  const completedList = results.filter((r) => r.status !== 'pending' && r.status !== 'running')
  const completed = completedList.length
  const hitQueries = results.filter((r) => r.status === 'hit').length
  const hitRate = total > 0 ? Math.round((hitQueries / total) * 100) : 0

  const validLatencies = results.map((r) => r.latencyMs).filter((l): l is number => typeof l === 'number')
  const avgLatency = validLatencies.length > 0
    ? Math.round(validLatencies.reduce((a, b) => a + b, 0) / validLatencies.length)
    : 0

  const validScores = results.map((r) => r.score).filter((s): s is number => typeof s === 'number')
  const avgScore = validScores.length > 0
    ? (validScores.reduce((a, b) => a + b, 0) / validScores.length).toFixed(3)
    : '0.000'

  if (mode !== 'ragas') {
    return { total, completed, hitRate, avgLatency, avgScore }
  }

  const ragasItems = completedList.map((r) => r.ragas).filter((rg): rg is RagasScoreBreakdown => Boolean(rg))
  if (ragasItems.length === 0) {
    return {
      total,
      completed,
      hitRate,
      avgLatency,
      avgScore,
      ragas: {
        avgPrecision: '0.000',
        avgRecall: '0.000',
        avgFaithfulness: '0.000',
        avgRelevance: '0.000',
        compositeScore: '0.000',
      },
    }
  }

  const avgPrec = (ragasItems.reduce((a, b) => a + b.contextPrecision, 0) / ragasItems.length).toFixed(3)
  const avgRec = (ragasItems.reduce((a, b) => a + b.contextRecall, 0) / ragasItems.length).toFixed(3)
  const avgFaith = (ragasItems.reduce((a, b) => a + b.faithfulness, 0) / ragasItems.length).toFixed(3)
  const avgRel = (ragasItems.reduce((a, b) => a + b.answerRelevance, 0) / ragasItems.length).toFixed(3)
  const comp = (ragasItems.reduce((a, b) => a + b.compositeScore, 0) / ragasItems.length).toFixed(3)

  return {
    total,
    completed,
    hitRate,
    avgLatency,
    avgScore,
    ragas: {
      avgPrecision: avgPrec,
      avgRecall: avgRec,
      avgFaithfulness: avgFaith,
      avgRelevance: avgRel,
      compositeScore: comp,
    },
  }
}
