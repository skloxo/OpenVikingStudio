export interface DimensionScore {
  name: string
  label: string
  score: number
  max_score: number
  status: 'good' | 'warning' | 'critical'
  details: string[]
}

export interface SkillOptAuditResult {
  skill_name: string
  total_score: number
  grade: 'S' | 'A' | 'B' | 'C' | 'D'
  line_count: number
  dimensions: DimensionScore[]
  suggestions: string[]
  passed_gate: boolean
}

export interface SkillOptAttemptResult {
  verdict: 'PASS' | 'FAIL' | 'PARTIAL'
  confidence: number
  matched_intent: boolean
  judge_reason: string
  triggered_tools: string[]
}

export interface SkillOptOptimizeResult {
  original_score: number
  optimized_score: number
  applied_fixes: string[]
  optimized_content: string
  diff_summary: string
}

export interface BatchAuditSummary {
  total_audited: number
  avg_score: number
  grade_counts: Record<string, number>
  results: SkillOptAuditResult[]
}
