// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import { ovClient } from '#/lib/ov-client'

export interface HitTestMatchItem {
  skill_name: string
  domain: string
  matched: boolean
  score: number
  best_trigger: string
  reason: string
}

export interface HitTestCollisionItem {
  conflicting_skill: string
  max_similarity: number
  overlapping_triggers: Array<{
    candidate_trigger: string
    existing_trigger: string
    similarity: number
  }>
}

export interface HitTestResponse {
  status: string
  query: string
  catalog_size: number
  top1_score: number
  top2_score: number
  margin: number
  candidate_match: {
    matched: boolean
    best_trigger: string
    score: number
    reason: string
  } | null
  matches: HitTestMatchItem[]
  collisions: {
    has_collision: boolean
    collisions: HitTestCollisionItem[]
  }
  routing_decision: {
    action: 'MERGE' | 'PACKAGE_ADD' | 'NEW_PACKAGE'
    target_package: string
    top1_candidate: string | null
    top1_score: number
    top2_candidate: string | null
    top2_score: number
    margin: number
    rationale: string
  }
  alias_resolution: {
    type?: string
    target_name?: string
    bundle_name?: string
    is_virtual?: boolean
  } | null
}

export interface CompressSimulateResponse {
  status: string
  compression: {
    original_length: number
    compressed_length: number
    compression_ratio: number
    tokens_saved: number
    contract_fidelity: number
    latency_ms: number
    compressed_content: string
    six_tuple: {
      interface: string
      workflow: string[]
      protocol: string[]
      rules: string[]
      contracts: string[]
      evidence: string[]
    }
  }
  gate: {
    passed: boolean
    multiplier: number
    recommended_action: string
    reason: string
  }
}

export interface ScaffoldResponse {
  status: string
  name: string
  sections: string[]
  content: string
  validation: {
    valid: boolean
    errors: Array<{ rule: string; message: string; field: string }>
    warnings: Array<{ rule: string; message: string; field: string }>
  }
}

export async function runPlaygroundHitTest(payload: {
  query: string
  candidate_name?: string
  candidate_triggers?: string[]
  candidate_content?: string
}): Promise<HitTestResponse> {
  const res = await ovClient.instance.post<HitTestResponse>(
    '/api/v1/skills/playground/hit-test',
    payload,
  )
  return res.data
}

export async function runPlaygroundCompressSimulate(payload: {
  skill_content: string
  seed_length?: number
}): Promise<CompressSimulateResponse> {
  const res = await ovClient.instance.post<CompressSimulateResponse>(
    '/api/v1/skills/playground/compress-simulate',
    payload,
  )
  return res.data
}

export async function generatePlaygroundScaffold(payload: {
  name: string
  description: string
  domain?: string
  triggers?: string[]
  role?: string
  constraints?: string[]
}): Promise<ScaffoldResponse> {
  const res = await ovClient.instance.post<ScaffoldResponse>(
    '/api/v1/skills/playground/scaffold',
    payload,
  )
  return res.data
}
