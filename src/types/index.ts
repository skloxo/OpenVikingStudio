export interface ContextCounts {
  total: number;
  directories: number;
  files: number;
  skills?: number;
  memories?: number;
}

export interface TodayTokens {
  total: number;
  prompt: number;
  completion: number;
  embedding: number;
  vlm_input?: number;
  vlm_output?: number;
  embedding_input?: number;
}

export interface TodayRetrievals {
  total: number;
  zero_result: number;
  avg_latency_ms: number;
  find?: number;
  search?: number;
}

export interface ConsoleDashboardSummary {
  context_counts: ContextCounts;
  today_tokens: TodayTokens;
  today_retrievals: TodayRetrievals;
}

export interface SystemStatus {
  status: string;
  healthy: boolean;
  version: string;
  auth_mode: string;
  role: string;
  role_name?: string;
  is_admin: boolean;
  is_root: boolean;
  account_id: string;
}

export type ActiveTab = 'home' | 'playground' | 'search' | 'logs' | 'sessions';
