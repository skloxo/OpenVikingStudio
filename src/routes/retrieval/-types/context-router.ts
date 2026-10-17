// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

export type SegmentType = 'static_header' | 'natural_language' | 'code_block' | 'skill_contract' | 'dialogue_history'

export type RouteEngine = 'native_caching' | 'llmlingua2' | 'tokenshift' | 'skillzip' | 'active_notes' | 'passthrough'

export interface ContextSegment {
  index: number
  segment_type: SegmentType
  engine: RouteEngine
  language?: string | null
  raw_content: string
  compressed_content: string
  original_tokens: number
  compressed_tokens: number
  tokens_saved: number
  reduction_ratio: number
  latency_ms: number
  status: 'ok' | 'fallback' | 'bypassed' | 'passthrough'
  metadata: Record<string, any>
}

export interface ContextRouteRequest {
  content: string
  default_code_mode?: 'skeleton' | 'outline' | 'compact'
  target_dehydration_rate?: number
  enable_skillzip?: boolean
  preserve_static_header?: boolean
  max_target_tokens?: number | null
}

export interface ContextRouteResult {
  assembled_content: string
  segments: ContextSegment[]
  total_original_tokens: number
  total_compressed_tokens: number
  total_tokens_saved: number
  overall_reduction_ratio: number
  total_latency_ms: number
  ast_syntax_valid: boolean
  engine_distribution: Record<string, number>
}

export interface ContextRouterStats {
  total_requests: number
  total_segments_routed: number
  total_original_tokens: number
  total_compressed_tokens: number
  total_tokens_saved: number
  average_reduction_ratio: number
  engine_call_counts: Record<string, number>
}
