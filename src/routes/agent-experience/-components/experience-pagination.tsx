import { useTranslation } from 'react-i18next'

import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from '#/components/ui/pagination'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '#/components/ui/select'
import { cn } from '#/lib/utils'

const EXPERIENCE_PAGE_SIZE_OPTIONS = [10, 20, 50, 100] as const

export function ExperiencePagination({
  onPageChange,
  onPageSizeChange,
  page,
  hasMore,
  disabled,
  pageSize,
}: {
  onPageChange: (page: number) => void
  onPageSizeChange: (pageSize: number) => void
  page: number
  hasMore: boolean
  disabled: boolean
  pageSize: number
}) {
  const { t } = useTranslation('agentExperiencePage')

  return (
    <div className="flex flex-col gap-3 border-t border-border/60 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-wrap items-center justify-center gap-3 sm:justify-start">
        <p className="text-sm text-muted-foreground">
          {t('pagination.summary', { page })}
        </p>
        <Select
          disabled={disabled}
          value={String(pageSize)}
          onValueChange={(value) => onPageSizeChange(Number(value))}
        >
          <SelectTrigger size="sm" aria-label={t('pagination.pageSize')}>
            <SelectValue>
              {t('pagination.pageSizeValue', { count: pageSize })}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            {EXPERIENCE_PAGE_SIZE_OPTIONS.map((option) => (
              <SelectItem key={option} value={String(option)}>
                {t('pagination.pageSizeValue', { count: option })}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <Pagination className="mx-0 w-auto justify-center sm:justify-end">
        <PaginationContent>
          <PaginationItem>
            <PaginationPrevious
              href="#"
              text={t('pagination.previous')}
              aria-disabled={disabled || page <= 1}
              className={cn(
                (disabled || page <= 1) && 'pointer-events-none opacity-50',
              )}
              onClick={(event) => {
                event.preventDefault()
                if (!disabled && page > 1) onPageChange(page - 1)
              }}
            />
          </PaginationItem>
          <PaginationItem>
            <PaginationNext
              href="#"
              text={t('pagination.next')}
              aria-disabled={disabled || !hasMore}
              className={cn(
                (disabled || !hasMore) && 'pointer-events-none opacity-50',
              )}
              onClick={(event) => {
                event.preventDefault()
                if (!disabled && hasMore) onPageChange(page + 1)
              }}
            />
          </PaginationItem>
        </PaginationContent>
      </Pagination>
    </div>
  )
}
