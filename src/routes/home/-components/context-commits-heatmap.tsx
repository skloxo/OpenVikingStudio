import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import HeatMap from '@uiw/react-heat-map'

import {
  HEATMAP_COLOR_STOPS,
  HEATMAP_MONTH_LABELS,
  HEATMAP_WEEK_LABELS,
} from '../-constants/dashboard'
import type {
  CommitHeatmapStats,
  CommitTooltip,
  HeatMapDayValue,
  HomeT,
} from '../-types/dashboard'
import { asNumber, formatNumber, formatShortDate } from '../-lib/format'
import { getHeatmapFillColor } from '../-lib/normalize'

export function ContextCommitsHeatmap({
  endDate,
  items,
  panelColors,
  startDate,
  stats,
  t,
}: {
  endDate: Date
  items: HeatMapDayValue[]
  panelColors: Record<number, string>
  startDate: Date
  stats: CommitHeatmapStats
  t: HomeT
}) {
  const [tooltip, setTooltip] = useState<CommitTooltip | null>(null)
  const heatmapScrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = heatmapScrollRef.current
    if (!el) return
    // Align the viewport to the newest rendered cell after HeatMap layout.
    const raf = requestAnimationFrame(() => {
      const node = heatmapScrollRef.current
      if (!node) return
      const rects = node.querySelectorAll<SVGRectElement>('svg rect')
      let cellsRight = node.scrollWidth
      if (rects.length > 0) {
        const last = rects[rects.length - 1]
        const bbox = last.getBoundingClientRect()
        const containerLeft = node.getBoundingClientRect().left
        cellsRight = bbox.right - containerLeft + node.scrollLeft
      }
      node.scrollLeft = Math.max(0, cellsRight - node.clientWidth)
    })
    return () => cancelAnimationFrame(raf)
  }, [items])

  return (
    <>
      <div className="grid gap-4 xl:grid-cols-[minmax(820px,auto)_minmax(180px,1fr)]">
        <div className="min-w-0">
          <div ref={heatmapScrollRef} className="overflow-x-auto">
            <HeatMap
              className="[--heatmap-empty:oklch(0.92_0_0)] text-muted-foreground dark:[--heatmap-empty:oklch(0.31_0_0)] [&_.w-heatmap-month]:fill-current [&_.w-heatmap-week]:fill-current"
              endDate={endDate}
              height={128}
              legendCellSize={0}
              monthLabels={HEATMAP_MONTH_LABELS}
              panelColors={panelColors}
              rectProps={{ rx: 2 }}
              rectRender={(props, item) => {
                const value = item as Partial<HeatMapDayValue>
                const heatmapItem = value.details
                  ? (value as HeatMapDayValue)
                  : null
                const count = asNumber(value.count)
                const fill = getHeatmapFillColor(count, panelColors)
                return (
                  <rect
                    {...props}
                    fill={fill}
                    onMouseEnter={(event) => {
                      if (!heatmapItem) return
                      const rect = (
                        event.target as SVGRectElement
                      ).getBoundingClientRect()
                      setTooltip({
                        item: heatmapItem,
                        x: rect.left + rect.width / 2,
                        y: rect.top,
                      })
                    }}
                    onMouseLeave={() => setTooltip(null)}
                    style={{
                      ...props.style,
                      cursor: heatmapItem ? 'pointer' : 'default',
                      fill,
                      transition: 'fill 0.15s, opacity 0.15s',
                    }}
                  />
                )
              }}
              rectSize={11}
              space={3}
              startDate={startDate}
              value={items}
              weekLabels={HEATMAP_WEEK_LABELS}
              width={820}
            />
          </div>
        </div>

        <div className="grid content-start border-t border-border/60 pt-3 sm:grid-cols-3 xl:border-l xl:border-t-0 xl:pl-5 xl:pt-5">
          <ContextCommitStat
            label={t('contextCommits.stats.activeDays')}
            value={formatNumber(stats.activeDays)}
          />
          <ContextCommitStat
            label={t('contextCommits.stats.peakDay')}
            value={formatNumber(stats.peakCount)}
          />
          <ContextCommitStat
            label={t('contextCommits.stats.recentDay')}
            value={stats.recentDate ? formatShortDate(stats.recentDate) : '--'}
          />
        </div>
      </div>

      {tooltip && typeof document !== 'undefined'
        ? createPortal(
            <CommitTooltipView
              item={tooltip.item}
              t={t}
              x={tooltip.x}
              y={tooltip.y}
            />,
            document.body,
          )
        : null}
    </>
  )
}

function ContextCommitStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-b border-border/60 py-1.5 last:border-b-0 sm:border-b-0 sm:border-r sm:px-3 sm:last:border-r-0 xl:border-b xl:border-r-0 xl:px-0 xl:last:border-b-0">
      <div className="text-[11px] leading-none text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 text-xl font-mono font-semibold leading-none tabular-nums">
        {value}
      </div>
    </div>
  )
}

function CommitTooltipView({
  item,
  t,
  x,
  y,
}: {
  item: HeatMapDayValue
  t: HomeT
  x: number
  y: number
}) {
  const details = item.details
  const rows = [
    {
      label: t('contextCommits.operations.addResource'),
      value: details.add_resource,
    },
    {
      label: t('contextCommits.operations.addSkill'),
      value: details.add_skill,
    },
    {
      label: t('contextCommits.operations.sessionAddMessage'),
      value: details.session_add_message,
    },
    {
      label: t('contextCommits.operations.sessionCommit'),
      value: details.session_commit,
    },
  ]

  // Clamp the tooltip into the viewport so it never overflows on narrow screens.
  const tooltipRef = useRef<HTMLDivElement>(null)
  const [horizontalShift, setHorizontalShift] = useState(0)

  useLayoutEffect(() => {
    const el = tooltipRef.current
    if (!el) return
    const margin = 8
    const rect = el.getBoundingClientRect()
    const viewportWidth =
      window.innerWidth || document.documentElement.clientWidth
    let shift = 0
    if (rect.right > viewportWidth - margin) {
      shift = viewportWidth - margin - rect.right
    } else if (rect.left < margin) {
      shift = margin - rect.left
    }
    setHorizontalShift(shift)
  }, [item, x, y])

  return (
    <div
      ref={tooltipRef}
      className="pointer-events-none fixed z-50 w-60 max-w-[calc(100vw-1rem)] rounded-sm border border-border/70 bg-popover/95 p-2.5 text-xs text-popover-foreground shadow-xl ring-1 ring-foreground/5 backdrop-blur-md dark:shadow-black/35"
      style={{
        left: x,
        top: y - 12,
        transform: `translate(calc(-50% + ${horizontalShift}px), -100%)`,
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-mono font-semibold tabular-nums">{details.date}</div>
          <div className="mt-0.5 text-[11px] text-muted-foreground">
            {t('contextCommits.tooltip.total')}
          </div>
        </div>
        <div className="rounded-xs bg-[oklch(0.68_0.12_232_/_0.14)] px-1.5 py-0.5 text-xs font-mono font-semibold tabular-nums text-[oklch(0.45_0.13_242)] dark:bg-[oklch(0.68_0.14_232_/_0.18)] dark:text-[oklch(0.76_0.14_232)]">
          {details.total}
        </div>
      </div>

      <div className="mt-2 space-y-1.5 border-t border-border/70 pt-2">
        {rows.map((row, index) => (
          <div
            key={row.label}
            className="grid grid-cols-[auto_1fr_auto] items-center gap-2"
          >
            <span
              className="size-1.5 rounded-xs"
              style={{
                backgroundColor:
                  HEATMAP_COLOR_STOPS[
                    Math.min(index, HEATMAP_COLOR_STOPS.length - 1)
                  ],
                opacity: row.value > 0 ? 1 : 0.35,
              }}
            />
            <span className="min-w-0 truncate text-muted-foreground">
              {row.label}
            </span>
            <span className="font-mono font-medium tabular-nums">
              {formatNumber(row.value)}
            </span>
          </div>
        ))}
      </div>

      <span
        className="absolute top-full size-2 -translate-x-1/2 -translate-y-1/2 rotate-45 border-b border-r border-border/70 bg-popover/95"
        style={{ left: `calc(50% - ${horizontalShift}px)` }}
      />
    </div>
  )
}
