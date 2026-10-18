// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

export type ProvenanceActionType =
  | 'INGEST'
  | 'VALIDATE'
  | 'ROUTE'
  | 'MERGE'
  | 'OPTIMIZE'
  | 'ROLLBACK'

export interface ProvenanceRecordItem {
  event_id: string
  timestamp: number
  action: ProvenanceActionType
  skill_name: string
  version: string
  receipt_id: string
  operator: string
  details: {
    stage?: string
    is_valid?: boolean
    opt_score?: number
    source_path?: string
    target_bundle?: string
    decision?: string
    landing_path?: string
    remediated_fields?: string[]
    errors?: string[] | string
    message?: string
    diff_patch?: string
    before_content?: string
    after_content?: string
    sha256?: string
    nearest_similarity?: number
    [key: string]: any
  }
  snapshot_path?: string
}

export type IngestionStatusType =
  | 'PENDING'
  | 'VALIDATING'
  | 'STAGED'
  | 'REJECTED'
  | 'COMMITTED'
  | 'ERROR'

export interface IngestionRecordItem {
  receipt_id: string
  skill_name: string
  raw_content: string
  author: string
  status: IngestionStatusType
  status_message: string
  validation_report?: {
    is_valid?: boolean
    opt_score?: number
    line_count?: number
    latency_ms?: number
    ante_gate?: Record<string, any>
    source_path?: string
    routing?: {
      action: string
      target_package: string
      top1_score: number
      margin: number
    }
    violations?: Array<{ field: string; message: string; severity?: string }>
    [key: string]: any
  }
  retry_count: number
  created_at: number
  updated_at: number
}

export type LedgerTrack = 'provenance' | 'ingestion'

export type SelectedLedgerItem =
  | { type: 'provenance'; record: ProvenanceRecordItem }
  | { type: 'ingestion'; record: IngestionRecordItem }
