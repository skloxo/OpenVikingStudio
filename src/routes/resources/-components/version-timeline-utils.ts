export interface ParsedDiffLine {
  line: string
  type: 'add' | 'del' | 'meta' | 'normal'
  key: number
}

export function formatCommitTime(timeSeconds?: number): string {
  if (!timeSeconds) return '--'
  const date = new Date(timeSeconds * 1000)
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatRelativeTime(timeSeconds?: number): string {
  if (!timeSeconds) return ''
  const diffSec = Math.floor(Date.now() / 1000 - timeSeconds)
  if (diffSec < 60) return '刚刚'
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)} 分钟前`
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} 小时前`
  return `${Math.floor(diffSec / 86400)} 天前`
}

export function parseUnifiedDiff(diffContent?: string): ParsedDiffLine[] {
  if (!diffContent || typeof diffContent !== 'string') return []
  return diffContent.split('\n').map((line, idx) => {
    let type: 'add' | 'del' | 'meta' | 'normal' = 'normal'
    if (
      line.startsWith('+++') ||
      line.startsWith('---') ||
      line.startsWith('@@')
    ) {
      type = 'meta'
    } else if (line.startsWith('+')) {
      type = 'add'
    } else if (line.startsWith('-')) {
      type = 'del'
    }
    return { line, type, key: idx }
  })
}
