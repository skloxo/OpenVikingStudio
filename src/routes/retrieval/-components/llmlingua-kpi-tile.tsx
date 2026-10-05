// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'

export interface KpiTileProps {
  icon: React.ElementType
  label: string
  value: string | number
  sub?: string
  accent?: boolean
}

export function KpiTile({
  icon: Icon,
  label,
  value,
  sub,
  accent,
}: KpiTileProps) {
  return (
    <div className="flex flex-col gap-1 rounded-md border border-border/70 bg-card p-3 shadow-xs">
      <div className="flex items-center gap-1.5 text-muted-foreground">
        <Icon className="size-3.5 shrink-0 text-cyan-500" />
        <span className="text-xs truncate">{label}</span>
      </div>
      <div
        className={`text-base font-mono font-semibold tabular-nums ${
          accent ? 'text-cyan-600 dark:text-cyan-400' : 'text-foreground'
        }`}
      >
        {value}
      </div>
      {sub && <span className="text-xs text-muted-foreground truncate">{sub}</span>}
    </div>
  )
}
