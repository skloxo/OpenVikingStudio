import * as React from 'react'
import { getTaskDate } from '#/routes/tasks/-lib/task-time'
import type { TaskRecord } from '../../-lib/task-record'

export function DetailField({
  className,
  icon,
  label,
  mono = false,
  value,
}: {
  className?: string
  icon: React.ReactNode
  label: string
  mono?: boolean
  value: string
}) {
  return (
    <div
      className={`min-w-0 rounded-xl border bg-muted/15 p-3 ${className || ''}`}
    >
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground [&_svg]:size-3.5">
        {icon}
        {label}
      </div>
      <p
        className={`mt-1.5 truncate text-sm font-medium ${mono ? 'font-mono text-xs' : ''}`}
        title={value}
      >
        {value}
      </p>
    </div>
  )
}

export function DetailSection({
  children,
  title,
}: {
  children: React.ReactNode
  title: string
}) {
  return (
    <section className="grid gap-2.5">
      <h3 className="text-sm font-semibold">{title}</h3>
      {children}
    </section>
  )
}

export function formatTaskTime(
  task: TaskRecord,
  _language: string | undefined,
  kind: 'created' | 'updated',
): string {
  const date =
    kind === 'created'
      ? getTaskDate(task)
      : getTaskDate({
          created_at: task.updated_at,
          created_at_iso: task.updated_at_iso,
        })
  if (!date) return '-'
  const y = date.getFullYear()
  const m = date.getMonth() + 1
  const d = date.getDate()
  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  const ss = String(date.getSeconds()).padStart(2, '0')
  return `${y}/${m}/${d} ${hh}:${mm}:${ss}`
}

export function formatTaskResult(result: unknown): string {
  if (typeof result === 'string') {
    return result
  }
  try {
    return JSON.stringify(result, null, 2)
  } catch {
    return String(result)
  }
}
