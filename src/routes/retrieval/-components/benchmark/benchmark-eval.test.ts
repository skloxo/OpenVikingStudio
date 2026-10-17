// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import { describe, expect, it } from 'vitest'
import { computeSummaryMetrics, evaluateRagasSample } from './eval-engine'
import type { BenchmarkResultItem } from './types'

describe('RAGAS Evaluation Engine (eval-engine.ts)', () => {
  it('handles empty hits safely with zeroed metrics', () => {
    const res = evaluateRagasSample([], 'test query')
    expect(res.contextPrecision).toBe(0)
    expect(res.contextRecall).toBe(0)
    expect(res.faithfulness).toBe(0)
    expect(res.answerRelevance).toBe(0)
    expect(res.compositeScore).toBe(0)
  })

  it('evaluates typical hits with valid RAGAS scores', () => {
    const sampleHits = [
      { uri: 'viking://resources/doc1.md', score: 0.88 },
      { uri: 'viking://resources/doc2.md', score: 0.72 },
      { uri: 'viking://resources/doc3.md', score: 0.35 },
    ]

    const res = evaluateRagasSample(sampleHits, 'test query')

    // Precision, Recall, Faithfulness, Relevance should be valid ratios in [0, 1]
    expect(res.contextPrecision).toBeGreaterThan(0)
    expect(res.contextPrecision).toBeLessThanOrEqual(1)
    expect(res.contextRecall).toBeGreaterThan(0)
    expect(res.contextRecall).toBeLessThanOrEqual(1)
    expect(res.faithfulness).toBeGreaterThan(0)
    expect(res.faithfulness).toBeLessThanOrEqual(1)
    expect(res.answerRelevance).toBeGreaterThan(0)
    expect(res.answerRelevance).toBeLessThanOrEqual(1)

    // Harmonic composite score should be valid
    expect(res.compositeScore).toBeGreaterThan(0)
    expect(res.compositeScore).toBeLessThanOrEqual(1)
  })

  it('computes summary metrics for fast mode', () => {
    const results: BenchmarkResultItem[] = [
      { id: '1', query: 'q1', score: 0.85, latencyMs: 120, status: 'hit' },
      { id: '2', query: 'q2', latencyMs: 200, status: 'miss' },
    ]

    const summary = computeSummaryMetrics(results, 'fast')
    expect(summary.total).toBe(2)
    expect(summary.completed).toBe(2)
    expect(summary.hitRate).toBe(50)
    expect(summary.avgLatency).toBe(160)
    expect(summary.avgScore).toBe('0.850')
    expect(summary.ragas).toBeUndefined()
  })

  it('computes summary metrics for ragas mode', () => {
    const results: BenchmarkResultItem[] = [
      {
        id: '1',
        query: 'q1',
        score: 0.85,
        latencyMs: 120,
        status: 'hit',
        ragas: {
          contextPrecision: 0.9,
          contextRecall: 0.8,
          faithfulness: 0.85,
          answerRelevance: 0.88,
          compositeScore: 0.855,
        },
      },
    ]

    const summary = computeSummaryMetrics(results, 'ragas')
    expect(summary.total).toBe(1)
    expect(summary.completed).toBe(1)
    expect(summary.ragas).toBeDefined()
    expect(summary.ragas?.avgPrecision).toBe('0.900')
    expect(summary.ragas?.avgRecall).toBe('0.800')
    expect(summary.ragas?.avgFaithfulness).toBe('0.850')
    expect(summary.ragas?.avgRelevance).toBe('0.880')
    expect(summary.ragas?.compositeScore).toBe('0.855')
  })
})
