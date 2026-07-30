export interface ObserverComponentStatus {
  name: string
  is_healthy: boolean
  has_errors: boolean
  status: string
}

export interface MetricTileData {
  id: string
  titleKey: string
  value: string | number
  unit?: string
  subValue?: string
  trend?: 'up' | 'down' | 'neutral'
  badgeText?: string
  badgeVariant?: 'default' | 'outline' | 'secondary' | 'destructive'
  tooltipKey: string
  isMissing?: boolean
}

export interface DeepObserverMetrics {
  // Tile 1: HTTP Request Success Rate
  httpSuccessRate: number | null
  // Tile 2: VikingDB Mounted Vector Count
  vectorCount: number | null
  // Tile 3: Vector Recall Hit Rate (100% - Zero-Result Rate)
  vectorHitRate: number | null
  // Tile 4: GPU & VRAM Memory Usage
  gpuVramUsage: {
    usedGb: number
    totalGb: number
    gpuPercent: number
  } | null
  // Tile 5: Top-1 Vector Recall Accuracy
  top1Accuracy: number | null
  // Tile 6: Average Cosine Score
  avgCosineScore: number | null
  // Tile 7: Embedding Processing Latency (ms)
  embeddingLatencyMs: number | null
  // Tile 8: Max Interface Processing Latency (ms)
  maxLatencyMs: number | null
  // Tile 9: Total Request Logs Count
  totalAuditLogs: number | null
  // Tile 10: Auto Log Refresh Status
  autoRefreshEnabled: boolean
  // Tile 11: Queue State
  queueStats: {
    pending: number
    inProgress: number
    processed: number
    requeued: number
    errors: number
    total: number
  } | null
  // Tile 12: FileSystem Ops & IO Latency
  fsStats: {
    totalOps: number
    avgMs: number
  } | null
  // Tile 13: Total Token Consumption
  tokenStats: {
    today: number
    total: number
  } | null
  // Tile 14: Memory Slimming Rate (Compression ratio)
  memorySlimmingRate: number | null
  // Tile 15: Vectorization Rate (Vec/s)
  vectorizationRate: number | null
  // Tile 16: Active Model Components
  activeModels: {
    vlm?: string
    embedding?: string
    rerank?: string
  }
}
