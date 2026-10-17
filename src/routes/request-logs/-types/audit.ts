export type LogTypeFilter = 'all' | 'error'

export type RequestLogStatus = 'success' | 'error'

export type AuditFilters = {
  apiType: string
  logType: LogTypeFilter
  requestId: string
  statusCode: string
}

export type EndpointFrequencyWindow = '24h' | '7d' | '30d' | 'all'

export interface EndpointFrequencyItem {
  route: string
  method: string
  api_type: string
  category: string
  call_count: number
  share_percent: number
  avg_duration_ms: number
  error_rate: number
  last_called_at: string | null
}

export interface DormantEndpointItem {
  route: string
  methods: string[]
  category: string
  status: string
  call_count: number
  recommendation: string
}

export interface CategoryBreakdownItem {
  category: string
  call_count: number
  share_percent: number
}

export interface EndpointFrequencyResult {
  window: EndpointFrequencyWindow
  total_calls: number
  active_endpoints_count: number
  dormant_endpoints_count: number
  total_endpoints_count: number
  active_rate: number
  top_hot_endpoints: EndpointFrequencyItem[]
  dormant_endpoints: DormantEndpointItem[]
  category_breakdown: CategoryBreakdownItem[]
}

