import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  ChevronsLeftIcon,
  ChevronsRightIcon,
} from 'lucide-react'
import { Button } from '#/components/ui/button'
import { cn } from '#/lib/utils'

export interface UniversalPaginationProps {
  page: number
  pageSize: number
  total: number
  onPageChange: (newPage: number) => void
  onPageSizeChange?: (newPageSize: number) => void
  pageSizeOptions?: number[]
  showTotal?: boolean
  showPageSizeSelect?: boolean
  compact?: boolean
  className?: string
}

export function UniversalPagination({
  page,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [10, 20, 50, 100],
  showTotal = true,
  showPageSizeSelect = true,
  compact = false,
  className,
}: UniversalPaginationProps) {
  const { t } = useTranslation('common')
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const safePage = Math.min(Math.max(1, page), totalPages)

  const startItem = total === 0 ? 0 : (safePage - 1) * pageSize + 1
  const endItem = Math.min(safePage * pageSize, total)

  // 智能计算页码序列（显示当前页前后 1-2 页与首尾页）
  const pageNumbers = useMemo(() => {
    if (totalPages <= 5) {
      return Array.from({ length: totalPages }, (_, i) => i + 1)
    }

    const pages: (number | 'ellipsis')[] = []
    const leftBound = Math.max(2, safePage - 1)
    const rightBound = Math.min(totalPages - 1, safePage + 1)

    pages.push(1)

    if (leftBound > 2) {
      pages.push('ellipsis')
    }

    for (let i = leftBound; i <= rightBound; i++) {
      pages.push(i)
    }

    if (rightBound < totalPages - 1) {
      pages.push('ellipsis')
    }

    pages.push(totalPages)
    return pages
  }, [safePage, totalPages])

  if (total === 0 && !showTotal) {
    return null
  }

  return (
    <div
      className={cn(
        'flex flex-wrap items-center justify-between gap-3 text-xs text-muted-foreground select-none',
        className,
      )}
    >
      {/* 左侧：条目计数度量衡 */}
      {showTotal && (
        <div className="flex items-center gap-1.5 font-mono tabular-nums">
          <span>
            {t('common.pagination.range', {
              start: startItem,
              end: endItem,
              defaultValue: `${startItem}-${endItem}`,
            })}
          </span>
          <span className="text-muted-foreground/60">/</span>
          <span>
            {t('common.pagination.total', {
              total,
              defaultValue: `Total ${total}`,
            })}
          </span>
        </div>
      )}

      {/* 右侧：条数切换与翻页控制器 */}
      <div className="flex items-center gap-2 ml-auto">
        {showPageSizeSelect && onPageSizeChange && (
          <div className="flex items-center gap-1.5">
            <span className="hidden sm:inline">
              {t('common.pagination.pageSize', { defaultValue: 'Per page' })}
            </span>
            <select
              aria-label={t('common.pagination.pageSizeAria', {
                defaultValue: 'Items per page',
              })}
              className="h-7 rounded border border-border/60 bg-background px-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-cyan-500 font-mono"
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
              value={pageSize}
            >
              {pageSizeOptions.map((opt) => (
                <option key={opt} value={opt}>
                  {t('common.pagination.pageSizeUnit', {
                    count: opt,
                    defaultValue: `${opt} / page`,
                  })}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* 翻页按钮组 */}
        <div className="flex items-center gap-1">
          {/* 首页 */}
          {!compact && (
            <Button
              aria-label={t('common.pagination.firstPage', {
                defaultValue: 'First page',
              })}
              disabled={safePage <= 1}
              onClick={() => onPageChange(1)}
              size="icon"
              variant="outline"
              className="size-7"
            >
              <ChevronsLeftIcon className="size-3.5" />
            </Button>
          )}

          {/* 上一页 */}
          <Button
            aria-label={t('common.pagination.previousPage', {
              defaultValue: 'Previous page',
            })}
            disabled={safePage <= 1}
            onClick={() => onPageChange(safePage - 1)}
            size="icon"
            variant="outline"
            className="size-7"
          >
            <ChevronLeftIcon className="size-3.5" />
          </Button>

          {/* 页码序列 */}
          {!compact && (
            <div className="hidden sm:flex items-center gap-1">
              {pageNumbers.map((p, idx) => {
                if (p === 'ellipsis') {
                  return (
                    <span
                      key={`ellipsis-${idx}`}
                      className="px-1 text-muted-foreground font-mono"
                    >
                      ...
                    </span>
                  )
                }

                const isActive = p === safePage
                return (
                  <Button
                    key={p}
                    aria-current={isActive ? 'page' : undefined}
                    onClick={() => onPageChange(p)}
                    size="sm"
                    variant={isActive ? 'default' : 'ghost'}
                    className={cn(
                      'size-7 p-0 font-mono text-xs tabular-nums',
                      isActive
                        ? 'bg-foreground text-background font-semibold hover:bg-foreground/90'
                        : 'text-muted-foreground hover:text-foreground',
                    )}
                  >
                    {p}
                  </Button>
                )
              })}
            </div>
          )}

          {/* 紧凑模式页码指示器 */}
          {compact && (
            <span className="px-2 font-mono tabular-nums text-xs text-foreground">
              {safePage} / {totalPages}
            </span>
          )}

          {/* 下一页 */}
          <Button
            aria-label={t('common.pagination.nextPage', {
              defaultValue: 'Next page',
            })}
            disabled={safePage >= totalPages}
            onClick={() => onPageChange(safePage + 1)}
            size="icon"
            variant="outline"
            className="size-7"
          >
            <ChevronRightIcon className="size-3.5" />
          </Button>

          {/* 尾页 */}
          {!compact && (
            <Button
              aria-label={t('common.pagination.lastPage', {
                defaultValue: 'Last page',
              })}
              disabled={safePage >= totalPages}
              onClick={() => onPageChange(totalPages)}
              size="icon"
              variant="outline"
              className="size-7"
            >
              <ChevronsRightIcon className="size-3.5" />
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
