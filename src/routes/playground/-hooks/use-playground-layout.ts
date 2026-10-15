/**
 * use-playground-layout.ts
 * Playground 三栏布局尺寸、左右折叠状态、双向拖拽调整与全屏画布管理 hook。
 */
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
} from 'react'

import {
  PLAYGROUND_LEFT_WIDTH,
  PLAYGROUND_LEFT_WIDTH_STORAGE_KEY,
  PLAYGROUND_MAIN_MIN_WIDTH,
  PLAYGROUND_RIGHT_COLLAPSED_STORAGE_KEY,
  PLAYGROUND_RIGHT_WIDTH,
  PLAYGROUND_RIGHT_WIDTH_STORAGE_KEY,
} from '../-lib/constants'
import { clampNumber, readStoredNumber } from '../-lib/utils'

export function usePlaygroundLayout() {
  const layoutRef = useRef<HTMLDivElement>(null)
  const [leftWidth, setLeftWidth] = useState(() =>
    readStoredNumber(
      PLAYGROUND_LEFT_WIDTH_STORAGE_KEY,
      PLAYGROUND_LEFT_WIDTH.default,
      PLAYGROUND_LEFT_WIDTH.min,
      PLAYGROUND_LEFT_WIDTH.max,
    ),
  )
  const [rightWidth, setRightWidth] = useState(() =>
    readStoredNumber(
      PLAYGROUND_RIGHT_WIDTH_STORAGE_KEY,
      PLAYGROUND_RIGHT_WIDTH.default,
      PLAYGROUND_RIGHT_WIDTH.min,
      PLAYGROUND_RIGHT_WIDTH.max,
    ),
  )
  const [resizingPane, setResizingPane] = useState<'context' | 'action' | null>(
    null,
  )
  const [rightCollapsed, setRightCollapsed] = useState(
    () =>
      typeof window !== 'undefined' &&
      window.localStorage.getItem(PLAYGROUND_RIGHT_COLLAPSED_STORAGE_KEY) ===
        '1',
  )

  const toggleRightCollapsed = useCallback(
    () =>
      setRightCollapsed((collapsed) => {
        window.localStorage.setItem(
          PLAYGROUND_RIGHT_COLLAPSED_STORAGE_KEY,
          collapsed ? '0' : '1',
        )
        return !collapsed
      }),
    [],
  )

  const [isFocusCanvas, setIsFocusCanvas] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false
    return (
      window.localStorage.getItem('openviking:playground:focus_mode') === 'true'
    )
  })

  const handleToggleFocusCanvas = useCallback(() => {
    setIsFocusCanvas((prev) => {
      const next = !prev
      try {
        window.localStorage.setItem(
          'openviking:playground:focus_mode',
          String(next),
        )
      } catch {}
      return next
    })
  }, [])

  const isDraggingPaneRef = useRef(false)
  const activeResizeTeardownRef = useRef<(() => void) | null>(null)
  const leftWidthRef = useRef(leftWidth)
  const rightWidthRef = useRef(rightWidth)
  leftWidthRef.current = leftWidth
  rightWidthRef.current = rightWidth

  const layoutStyle = useMemo(
    () =>
      ({
        '--playground-left-width': `${leftWidth}px`,
        '--playground-right-width': `${rightWidth}px`,
      }) as CSSProperties,
    [leftWidth, rightWidth],
  )

  const handleResizeStart = useCallback(
    (pane: 'context' | 'action', event: ReactPointerEvent<HTMLDivElement>) => {
      event.preventDefault()
      event.currentTarget.setPointerCapture(event.pointerId)
      isDraggingPaneRef.current = true
      setResizingPane(pane)

      const startX = event.clientX
      const startLeftWidth = leftWidthRef.current
      const startRightWidth = rightWidthRef.current
      const layoutRect = layoutRef.current?.getBoundingClientRect()

      const getMaxWidth = (
        side: 'left' | 'right',
        currentOppositeWidth: number,
      ) => {
        if (!layoutRect) {
          return side === 'left'
            ? PLAYGROUND_LEFT_WIDTH.max
            : PLAYGROUND_RIGHT_WIDTH.max
        }

        const hardMax =
          side === 'left'
            ? PLAYGROUND_LEFT_WIDTH.max
            : PLAYGROUND_RIGHT_WIDTH.max
        const availableMax =
          layoutRect.width - currentOppositeWidth - PLAYGROUND_MAIN_MIN_WIDTH
        return Math.max(
          side === 'left'
            ? PLAYGROUND_LEFT_WIDTH.min
            : PLAYGROUND_RIGHT_WIDTH.min,
          Math.min(hardMax, availableMax),
        )
      }

      const onMove = (moveEvent: PointerEvent) => {
        const deltaX = moveEvent.clientX - startX
        if (pane === 'context') {
          const nextWidth = clampNumber(
            startLeftWidth + deltaX,
            PLAYGROUND_LEFT_WIDTH.min,
            getMaxWidth('left', rightWidthRef.current),
          )
          setLeftWidth(nextWidth)
          window.localStorage.setItem(
            PLAYGROUND_LEFT_WIDTH_STORAGE_KEY,
            String(nextWidth),
          )
          return
        }

        const nextWidth = clampNumber(
          startRightWidth - deltaX,
          PLAYGROUND_RIGHT_WIDTH.min,
          getMaxWidth('right', leftWidthRef.current),
        )
        setRightWidth(nextWidth)
        window.localStorage.setItem(
          PLAYGROUND_RIGHT_WIDTH_STORAGE_KEY,
          String(nextWidth),
        )
      }

      const onUp = () => {
        isDraggingPaneRef.current = false
        activeResizeTeardownRef.current = null
        setResizingPane(null)
        document.removeEventListener('pointermove', onMove)
        document.removeEventListener('pointerup', onUp)
        document.removeEventListener('pointercancel', onUp)
        document.body.style.cursor = ''
        document.body.style.userSelect = ''
      }

      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'
      document.addEventListener('pointermove', onMove)
      document.addEventListener('pointerup', onUp)
      document.addEventListener('pointercancel', onUp)
      activeResizeTeardownRef.current = onUp
    },
    [],
  )

  useEffect(() => {
    return () => {
      activeResizeTeardownRef.current?.()
    }
  }, [])

  return {
    handleResizeStart,
    handleToggleFocusCanvas,
    isFocusCanvas,
    layoutRef,
    layoutStyle,
    leftWidth,
    resizingPane,
    rightCollapsed,
    rightWidth,
    toggleRightCollapsed,
  }
}
