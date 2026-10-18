// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

export interface SkillPatch {
  patch_id: string
  skill_name: string
  file_path: string
  target_content: string
  replacement_content: string
  reason: string
  status: 'proposed' | 'applied' | 'reverted'
  created_at: number
  applied_at?: number
  target_line_count: number
  replacement_line_count: number
}

export interface HermesSummary {
  experience: {
    total_messages: number
    total_sessions: number
    db_path: string
  }
  nudge: {
    queue_depth: number
    completed_reviews: number
    is_running: boolean
  }
  patches: {
    total_patches: number
    proposed: number
    applied: number
    reverted: number
    max_allowed_lines: number
  }
}

export interface FTS5SearchResult {
  msg_id: string
  session_id: string
  role: string
  snippet: string
  created_at: number
  rank: number
}

export interface AHEAssumption {
  assumption_id: string
  description: string
  validation_command?: string
  frozen_surface?: string
  verified_at?: number
}

export interface FileSnapshot {
  path: string
  sha256: string
}

export interface AHEManifest {
  manifest_id: string
  skill_name: string
  status: 'active' | 'verified' | 'violated' | 'retired'
  assumptions: AHEAssumption[]
  snapshots: FileSnapshot[]
  violation_cause?: string
  violation_detail?: string
}

export interface AHESummary {
  manifests: {
    total: number
    active: number
    verified: number
    violated: number
    retired: number
  }
  clusters: {
    total_clusters: number
    patched_clusters: number
    unpatched_clusters: number
    top_mechanism?: string
    total_occurrences: number
  }
}

export type HermesAheTrackMode = 'hermes_patch' | 'ahe_guard'
