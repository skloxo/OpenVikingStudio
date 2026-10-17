import { parseObserverStatus } from './parse-status'

export interface ParsedQueueRow {
  name: string
  typeKey?: string
  processing: number
  pending: number
  completed: number
  errors: number
  total: number
}

// 将 Observer status 字符串解析为结构化队列数据
export function parseQueueStatus(status: string): ParsedQueueRow[] {
  if (!status) return []
  const blocks = parseObserverStatus(status)
  const tableBlock = blocks.find((b) => b.kind === 'table')
  if (!tableBlock) return []

  const headers = tableBlock.headers
  const col = {
    name: headers.findIndex((h) => h === 'Queue'),
    inProgress: headers.findIndex((h) => h === 'In Progress'),
    pending: headers.findIndex((h) => h === 'Pending'),
    processed: headers.findIndex((h) => h === 'Processed'),
    errors: headers.findIndex((h) => h === 'Errors'),
    total: headers.findIndex((h) => h === 'Total'),
  }

  return tableBlock.rows.map((row) => ({
    name: col.name >= 0 ? (row[col.name] ?? '') : '',
    processing: col.inProgress >= 0 ? (parseInt(row[col.inProgress] ?? '0', 10) || 0) : 0,
    pending: col.pending >= 0 ? (parseInt(row[col.pending] ?? '0', 10) || 0) : 0,
    completed: col.processed >= 0 ? (parseInt(row[col.processed] ?? '0', 10) || 0) : 0,
    errors: col.errors >= 0 ? (parseInt(row[col.errors] ?? '0', 10) || 0) : 0,
    total: col.total >= 0 ? (parseInt(row[col.total] ?? '0', 10) || 0) : 0,
  }))
}
