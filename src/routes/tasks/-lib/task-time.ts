export type TaskTimestamp = {
  created_at?: number | string
  created_at_iso?: string
  status?: string
  updated_at?: number | string
  updated_at_iso?: string
}

export function getTaskDate(task: TaskTimestamp): Date | undefined {
  const value =
    task.created_at_iso ??
    task.updated_at_iso ??
    task.created_at ??
    task.updated_at
  if (value === undefined) return undefined

  const numericValue =
    typeof value === 'number'
      ? value
      : value.trim() !== '' && Number.isFinite(Number(value))
        ? Number(value)
        : undefined
  const normalizedValue =
    numericValue === undefined
      ? value
      : Math.abs(numericValue) < 1_000_000_000_000
        ? numericValue * 1_000
        : numericValue
  const date = new Date(normalizedValue)
  return Number.isNaN(date.getTime()) ? undefined : date
}

export function formatTaskDuration(
  task: TaskTimestamp,
  isZh: boolean = true,
): string {
  const createdDate = getTaskDate(task)
  if (!createdDate) return '-'

  const createdMs = createdDate.getTime()
  const status = task.status || 'unknown'
  const isFinished = status === 'completed' || status === 'failed'

  let endMs = Date.now()
  if (isFinished) {
    const updatedDate =
      task.updated_at || task.updated_at_iso
        ? getTaskDate({
            created_at: task.updated_at,
            created_at_iso: task.updated_at_iso,
          })
        : undefined
    endMs =
      updatedDate && updatedDate.getTime() >= createdMs
        ? updatedDate.getTime()
        : createdMs
  }

  const diffSec = Math.max(0, Math.floor((endMs - createdMs) / 1000))

  if (diffSec < 1) return isZh ? '< 1 秒' : '< 1s'
  if (diffSec < 60) return isZh ? `${diffSec} 秒` : `${diffSec}s`

  const mins = Math.floor(diffSec / 60)
  const secs = diffSec % 60

  if (mins < 60) {
    return isZh ? `${mins} 分 ${secs} 秒` : `${mins}m ${secs}s`
  }

  const hours = Math.floor(mins / 60)
  const remMins = mins % 60
  return isZh ? `${hours} 小时 ${remMins} 分` : `${hours}h ${remMins}m`
}
