// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { HarnessLessonsTable, type LessonItem } from '#/routes/harness-logs/-components/harness-lessons-table'

interface B6LessonsPanelProps {
  lessons: LessonItem[]
  searchQuery: string
  isLoading?: boolean
}

export function B6LessonsPanel({ lessons, searchQuery, isLoading }: B6LessonsPanelProps) {
  if (isLoading) {
    return (
      <div className="rounded-md border border-border/70 bg-card p-8 text-center text-xs font-mono text-muted-foreground">
        <span className="inline-block size-3.5 animate-spin border-2 border-cyan-500 border-t-transparent rounded-full mr-2 align-middle" />
        正在调取全量演进教训档案 (Master Memory)...
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-2">
      <HarnessLessonsTable lessons={lessons} searchQuery={searchQuery} />
    </div>
  )
}
