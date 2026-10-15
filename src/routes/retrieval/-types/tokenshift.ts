// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

export type TokenShiftMode = 'outline' | 'skeleton' | 'compact'
export type TokenShiftLanguage = 'python' | 'typescript' | 'javascript' | 'sql' | 'shell' | 'json' | 'auto'

export interface SyntaxValidationResult {
  valid: boolean
  parser: string
  error?: string | null
}

export interface TokenShiftRequest {
  code: string
  language?: TokenShiftLanguage
  mode?: TokenShiftMode
  preserve_docstrings?: boolean
  strip_comments?: boolean
}

export interface TokenShiftResult {
  compressed_code: string
  original_code: string
  language: string
  mode: string
  original_lines: number
  compressed_lines: number
  original_tokens_est: number
  compressed_tokens_est: number
  reduction_ratio: number
  protected_nodes_count: number
  syntax_validation: SyntaxValidationResult
  elapsed_ms: number
}

export interface TokenShiftProtectResult {
  language: string
  total_symbols: number
  protected_symbols: string[]
  frozen_signatures: string[]
  ast_nodes_identified: number
}

export interface TokenShiftStats {
  total_calls: number
  total_original_tokens: number
  total_compressed_tokens: number
  total_tokens_saved: number
  average_reduction_ratio: number
  syntax_pass_rate: number
}

export interface CodeFileItem {
  rel_path: string
  filename: string
  language: string
  size_bytes: number
  line_count: number
  preview: string
}

export interface ApplyTokenShiftRequest {
  rel_path: string
  compressed_code: string
  mode: 'skeleton_file' | 'in_place'
  operator?: string
}

export interface ApplyTokenShiftResult {
  success: boolean
  mode: string
  target_path: string
  snapshot_path: string
  original_chars: number
  compressed_chars: number
  saved_chars: number
  syntax_valid: boolean
  message: string
}

