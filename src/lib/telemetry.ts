import { ovClient } from './ov-client'

export type TelemetryMetricType = 'sla' | 'retrieval'
export type TelemetryTimeWindow = '24h' | '7d' | '30d' | 'all'

export interface SlaDataPoint {
  date: string
  successRate: number
  totalRequests: number
  tokenSavingRate: number
  latencyMs: number
}

export interface RetrievalAccuracyDataPoint {
  date: string
  hitRate: number
  avgScore: number
  queries: number
}

export interface TelemetryTrendsResponse<T> {
  status?: string
  metric?: string
  window?: string
  points?: T[]
}

/**
 * Single source of truth (SSOT) helper to fetch aggregated historical
 * telemetry trend series from OpenViking backend (/api/v1/system/telemetry/trends).
 */
export async function fetchTelemetryTrends<T>(
  metric: TelemetryMetricType,
  window: TelemetryTimeWindow = '24h'
): Promise<T[]> {
  try {
    const res = await ovClient.instance.get<TelemetryTrendsResponse<T>>(
      `/api/v1/system/telemetry/trends?metric=${metric}&window=${window}`
    )
    const points = res.data?.points
    if (Array.isArray(points)) {
      return points
    }
  } catch {
    // Graceful network or timeout fallback
  }
  return []
}
