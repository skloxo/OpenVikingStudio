import i18n from './index'

export function formatNumber(value: number): string {
  return value.toLocaleString(i18n.resolvedLanguage ?? i18n.language)
}

export function formatDateTime(
  value: Date | number,
  options?: Intl.DateTimeFormatOptions,
): string {
  const date = typeof value === 'number' ? new Date(value) : value
  return date.toLocaleString(i18n.resolvedLanguage ?? i18n.language, options)
}
