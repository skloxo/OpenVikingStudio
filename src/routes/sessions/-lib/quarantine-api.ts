import { useQuery } from '@tanstack/react-query'
import { ovClient } from '#/lib/ov-client'

export interface QuarantineItem {
  name: string
  source: string
  destination: string
  size_bytes: number
  file_count: number
  batch_id: string
  category: string
  created_at: string
  uri?: string
}

export interface QuarantineBatch {
  batch_id: string
  category: string
  created_at: string
  total_targets: number
  total_files: number
  total_bytes: number
  archive_dir: string
}

export interface QuarantineManifestSnapshot {
  total_quarantined_targets: number
  total_quarantined_files: number
  total_quarantined_bytes: number
  total_quarantined_mb: number
  total_batches: number
  batches: QuarantineBatch[]
  items: QuarantineItem[]
  filtered_count: number
  cache_timestamp: number
}

export interface RestoreDryRunResult {
  success: boolean
  item_name: string
  batch_id: string
  destination_exists: boolean
  destination_files_count: number
  destination_size_bytes: number
  target_restore_path: string
  target_already_exists: boolean
  safe_to_restore: boolean
  message: string
  integrity_checked_at: number
}

export async function fetchQuarantineManifest(params: {
  search?: string
  category?: string
  limit?: number
}): Promise<QuarantineManifestSnapshot> {
  const qs = new URLSearchParams()
  if (params.search?.trim()) qs.append('search', params.search.trim())
  if (params.category && params.category !== 'all') qs.append('category', params.category)
  qs.append('limit', String(params.limit ?? 100))
  const res = await ovClient.instance.get<QuarantineManifestSnapshot>(
    `/api/v1/memory/quarantine_manifest?${qs.toString()}`,
  )
  return res.data
}

export function useQuarantineSummary() {
  return useQuery({
    queryKey: ['quarantine-summary'],
    queryFn: () => fetchQuarantineManifest({ limit: 1 }),
    staleTime: 30_000,
    retry: false,
  })
}
