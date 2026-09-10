/**
 * 通用标准化格式化工具函数库 (Formatters SSOT)
 * 彻底收口散落各处的 formatBytes 与时间转换，提供严谨防御与单一真相源。
 */

/**
 * 格式化字节大小 (B, KB, MB, GB, TB)
 * @param bytes 字节数值
 * @param decimals 小数点后保留位数，默认 1
 */
export function formatBytes(bytes?: number, decimals = 1): string {
  if (bytes === undefined || Number.isNaN(bytes)) return '--'
  if (bytes === 0) return '0 B'

  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
  const i = Math.floor(Math.log(Math.abs(bytes)) / Math.log(k))
  const index = Math.min(i, sizes.length - 1)

  const value = (bytes / Math.pow(k, index)).toFixed(dm)
  return `${value} ${sizes[index]}`
}

/**
 * 格式化毫秒耗时 (如 45ms, 1.25s, 3m 12s)
 * @param ms 毫秒数值
 */
export function formatDurationMs(ms?: number): string {
  if (ms === undefined || Number.isNaN(ms)) return '--'
  if (ms < 1000) return `${Math.round(ms)}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`
  const minutes = Math.floor(ms / 60000)
  const seconds = Math.floor((ms % 60000) / 1000)
  return `${minutes}m ${seconds}s`
}

/**
 * 格式化秒数耗时 (如 4s, 1m 20s, 2h 10m)
 * @param seconds 秒数值
 */
export function formatDurationSec(seconds?: number): string {
  if (seconds === undefined || Number.isNaN(seconds)) return '--'
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) {
    const m = Math.floor(seconds / 60)
    const s = Math.round(seconds % 60)
    return s > 0 ? `${m}m ${s}s` : `${m}m`
  }
  const h = Math.floor(seconds / 3600)
  const m = Math.round((seconds % 3600) / 60)
  return m > 0 ? `${h}h ${m}m` : `${h}h`
}

/**
 * 格式化紧凑计数值 (如 1.2k, 25.4M)
 * @param num 数值
 */
export function formatNumberCompact(num?: number): string {
  if (num === undefined || Number.isNaN(num)) return '--'
  if (num < 1000) return num.toString()
  if (num < 1000000) return `${(num / 1000).toFixed(1)}k`
  return `${(num / 1000000).toFixed(1)}M`
}
