import React from 'react'
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  ChevronsLeftIcon,
  ChevronsRightIcon,
} from 'lucide-react'
import { Button } from '#/components/ui/button'

export interface SkillsPaginationProps {
  currentPage: number
  pageSize: number
  totalItems: number
  onPageChange: (page: number) => void
  onPageSizeChange: (size: number) => void
}

export function SkillsPagination({
  currentPage,
  pageSize,
  totalItems,
  onPageChange,
  onPageSizeChange,
}: SkillsPaginationProps) {
  const totalPages = pageSize > 0 ? Math.ceil(totalItems / pageSize) : 1
  const startIndex = totalItems === 0 ? 0 : (currentPage - 1) * pageSize + 1
  const endIndex = pageSize > 0 ? Math.min(currentPage * pageSize, totalItems) : totalItems

  const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      onPageChange(page)
    }
  }

  // Generate page numbers array with dynamic ellipsis
  const getPageNumbers = () => {
    if (totalPages <= 7) {
      return Array.from({ length: totalPages }, (_, i) => i + 1)
    }

    const pages: (number | string)[] = [1]
    if (currentPage > 3) {
      pages.push('...')
    }

    const start = Math.max(2, currentPage - 1)
    const end = Math.min(totalPages - 1, currentPage + 1)

    for (let i = start; i <= end; i++) {
      pages.push(i)
    }

    if (currentPage < totalPages - 2) {
      pages.push('...')
    }
    pages.push(totalPages)

    return pages
  }

  if (totalItems === 0) return null

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded border border-border/60 bg-muted/10 p-2.5 font-mono text-xs text-muted-foreground">
      {/* Items count summary */}
      <div className="flex items-center gap-2">
        <span className="text-foreground/90 font-medium">
          显示第 <strong className="text-cyan-500">{startIndex}</strong> - <strong className="text-cyan-500">{endIndex}</strong> 项
        </span>
        <span className="text-muted-foreground/60">|</span>
        <span>共 <strong className="text-foreground">{totalItems}</strong> 项技能资产</span>
      </div>

      {/* Pagination controls & Page Size select */}
      <div className="flex items-center gap-3">
        {/* Page size picker */}
        <div className="flex items-center gap-1.5">
          <span className="text-muted-foreground/80">每页:</span>
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            className="h-7 rounded border border-border/60 bg-background px-2 font-mono text-xs text-foreground focus:border-cyan-500 focus:outline-hidden"
          >
            <option value={12}>12 条</option>
            <option value={24}>24 条</option>
            <option value={48}>48 条</option>
            <option value={1000}>全部 ({totalItems})</option>
          </select>
        </div>

        {/* Page number buttons */}
        {pageSize < 1000 && totalPages > 1 && (
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="icon"
              className="size-7 rounded border-border/60 p-0 text-foreground hover:bg-muted"
              disabled={currentPage === 1}
              onClick={() => handlePageChange(1)}
              title="第一页"
            >
              <ChevronsLeftIcon className="size-3.5" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              className="size-7 rounded border-border/60 p-0 text-foreground hover:bg-muted"
              disabled={currentPage === 1}
              onClick={() => handlePageChange(currentPage - 1)}
              title="上一页"
            >
              <ChevronLeftIcon className="size-3.5" />
            </Button>

            {getPageNumbers().map((p, idx) => (
              <React.Fragment key={idx}>
                {typeof p === 'number' ? (
                  <Button
                    variant={currentPage === p ? 'default' : 'outline'}
                    size="sm"
                    className={`size-7 rounded p-0 text-xs font-mono transition-colors ${
                      currentPage === p
                        ? 'bg-cyan-500 text-cyan-950 font-bold border-cyan-500'
                        : 'border-border/60 text-foreground hover:bg-muted'
                    }`}
                    onClick={() => handlePageChange(p)}
                  >
                    {p}
                  </Button>
                ) : (
                  <span className="px-1 text-muted-foreground/60">...</span>
                )}
              </React.Fragment>
            ))}

            <Button
              variant="outline"
              size="icon"
              className="size-7 rounded border-border/60 p-0 text-foreground hover:bg-muted"
              disabled={currentPage === totalPages}
              onClick={() => handlePageChange(currentPage + 1)}
              title="下一页"
            >
              <ChevronRightIcon className="size-3.5" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              className="size-7 rounded border-border/60 p-0 text-foreground hover:bg-muted"
              disabled={currentPage === totalPages}
              onClick={() => handlePageChange(totalPages)}
              title="最后一页"
            >
              <ChevronsRightIcon className="size-3.5" />
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
