// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import { ovClient } from '#/lib/ov-client'

export type DeficitStatus = 'observing' | 'pending_fulfillment' | 'fulfilled' | 'dismissed'
export type DeficitRoute = 'human_assistance' | 'autonomous_researcher'

export interface DeficitStepTrace {
  step: string
  status: string
  detail: string
  ts: number
}

export interface KnowledgeDeficitItem {
  deficit_id: string
  canonical_query: string
  aliases: string[]
  entity_name: string
  entity_category: string
  suggested_route: DeficitRoute
  miss_count: number
  status: DeficitStatus
  top_score: number
  source_op: string
  scaffold_markdown: string
  fulfillment_content: string
  deliverable_uri: string
  fulfillment_track: string
  stage_task_id: string
  step_trace: DeficitStepTrace[]
  dismiss_reason?: string
  created_at: number
  updated_at: number
  promoted_at?: number | null
  fulfilled_at?: number | null
}

export interface KnowledgeDeficitSummary {
  total_tracked: number
  total_misses: number
  observing_count: number
  pending_fulfillment_count: number
  fulfilled_count: number
  dismissed_count: number
  human_assistance_pending: number
  autonomous_researcher_pending: number
  storm_suppression_pct: number
  miss_threshold: number
}

export async function fetchDeficitSummary(): Promise<KnowledgeDeficitSummary> {
  const res = await ovClient.instance.get('/api/v1/knowledge-deficits/summary')
  return res.data.result as KnowledgeDeficitSummary
}

export async function fetchDeficitsList(status: DeficitStatus | 'all'): Promise<KnowledgeDeficitItem[]> {
  const res = await ovClient.instance.get('/api/v1/knowledge-deficits', {
    params: { status, limit: 100 },
  })
  return (res.data.result?.items || []) as KnowledgeDeficitItem[]
}

export async function castDeficitScaffold(deficitId: string): Promise<KnowledgeDeficitItem> {
  const res = await ovClient.instance.post(`/api/v1/knowledge-deficits/${encodeURIComponent(deficitId)}/scaffold`)
  return res.data.result as KnowledgeDeficitItem
}

export async function fulfillDeficitCard(
  deficitId: string,
  payload: { content: string; track?: string },
): Promise<KnowledgeDeficitItem> {
  const res = await ovClient.instance.post(
    `/api/v1/knowledge-deficits/${encodeURIComponent(deficitId)}/fulfill`,
    payload,
  )
  return res.data.result as KnowledgeDeficitItem
}

export async function dismissDeficitCard(deficitId: string, reason = ''): Promise<KnowledgeDeficitItem> {
  const res = await ovClient.instance.post(
    `/api/v1/knowledge-deficits/${encodeURIComponent(deficitId)}/dismiss`,
    { reason },
  )
  return res.data.result as KnowledgeDeficitItem
}
