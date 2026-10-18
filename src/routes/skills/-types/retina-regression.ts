// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

export interface JudgeResult {
  case_id: string
  skill_name: string
  judge_type: string
  verdict: 'pass' | 'fail' | 'skip'
  actual: string | null
  expected: string | null
  error: string | null
  duration_ms: number
}

export interface EvalRunResult {
  run_id: string
  skill_name: string
  started_at: string
  finished_at: string | null
  total: number
  passed: number
  failed: number
  skipped: number
  pass_rate: number
  results: JudgeResult[]
  status: string
}

export interface EvalSummary {
  total_cases: number
  total_runs: number
  global_pass_rate: number
  last_run_at: string | null
  skills_evaluated: string[]
  recent_runs: EvalRunResult[]
}

export interface RSISummary {
  current_phase: 'daytime_collection' | 'nighttime_dreaming'
  phase_switched_at: number
  total_trajectories_collected: number
  total_turns_collected: number
  total_credit_evaluations: number
  dual_split_verifications: number
  gate_pass_rate: number
  persistence?: {
    persisted_sessions: number
    persisted_turns: number
    total_gate_checks: number
    passed_gate_checks: number
  }
}

export interface DualSplitResult {
  passed: boolean
  train_pass_rate: number
  holdout_pass_rate: number
  baseline_holdout_pass_rate: number
  regression_detected: boolean
  details: string
}

export type RetinaTrackMode = 'retina_eval' | 'rsi_guard'
