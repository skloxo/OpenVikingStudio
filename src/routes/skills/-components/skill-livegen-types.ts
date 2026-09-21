// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

export interface LiveGenStats {
  total_scaffolds: number
  total_validations: number
  total_simulations: number
  total_published: number
}

export interface ValidationResult {
  valid: boolean
  name: string
  description: string
  tags: string[]
  allowed_tools: string[]
  body_lines: number
  line_status: string
  errors: Array<{ rule: string; message: string; field: string }>
  warnings: Array<{ rule: string; message: string; field: string }>
}

export interface QuerySimulationItem {
  query: string
  matched: boolean
  confidence: number
  matched_keywords: string[]
  explanation: string
}

export interface SimulationResult {
  skill_name: string
  total_queries: number
  passed_queries: number
  pass_rate: number
  results: QuerySimulationItem[]
}

export interface PublishResult {
  success: boolean
  skill_name: string
  target_path: string
  content_hash: string
  body_lines: number
  message: string
}
