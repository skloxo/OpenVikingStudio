// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  isChunkLoadError,
  triggerSmoothReload,
  setupChunkReloadGuard,
  CHUNK_RELOAD_STORAGE_KEY,
  CHUNK_RELOAD_THROTTLE_MS,
} from './chunk-reload-guard'

describe('chunk-reload-guard', () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.restoreAllMocks()
  })

  afterEach(() => {
    sessionStorage.clear()
    vi.restoreAllMocks()
  })

  describe('isChunkLoadError', () => {
    it('正确识别用户本次上报的真实动态模块加载报错', () => {
      const realErrorMsg =
        'Failed to fetch dynamically imported module: https://vk.tide.red/studio/assets/route-BaTD7QSR.js'
      expect(isChunkLoadError(realErrorMsg)).toBe(true)
      expect(isChunkLoadError(new TypeError(realErrorMsg))).toBe(true)
    })

    it('正确识别常见浏览器关于 chunk 加载失败的各种表述', () => {
      expect(isChunkLoadError('Importing a module script failed')).toBe(true)
      expect(isChunkLoadError('error loading dynamically imported module')).toBe(true)
      expect(isChunkLoadError('Unable to preload /studio/assets/route.js')).toBe(true)
      expect(isChunkLoadError('ChunkLoadError: Loading chunk 5 failed.')).toBe(true)
      expect(isChunkLoadError(new Error('error loading dynamically imported module'))).toBe(true)
      expect(isChunkLoadError({ message: 'Failed to fetch dynamically imported module' })).toBe(true)
    })

    it('不误判普通业务错误或网络超时', () => {
      expect(isChunkLoadError(null)).toBe(false)
      expect(isChunkLoadError(undefined)).toBe(false)
      expect(isChunkLoadError('NetworkError: Failed to fetch')).toBe(false)
      expect(isChunkLoadError(new Error('Internal Server Error 500'))).toBe(false)
      expect(isChunkLoadError(new Error('User not found'))).toBe(false)
    })
  })

  describe('triggerSmoothReload', () => {
    it('首次发生 chunk 错误时触发重载并记录时间戳', () => {
      const reloadMock = vi.fn()
      // Mock window.location
      const originalLocation = window.location
      Object.defineProperty(window, 'location', {
        configurable: true,
        value: { ...originalLocation, reload: reloadMock },
      })

      const triggered = triggerSmoothReload('test-first-failure')
      expect(triggered).toBe(true)
      expect(reloadMock).toHaveBeenCalledTimes(1)

      const storedTs = sessionStorage.getItem(CHUNK_RELOAD_STORAGE_KEY)
      expect(storedTs).toBeTruthy()
      expect(Number(storedTs)).toBeGreaterThan(0)

      // 还原 location
      Object.defineProperty(window, 'location', {
        configurable: true,
        value: originalLocation,
      })
    })

    it('在 10 秒冷却期内再次调用时阻断，防止死循环无限重载', () => {
      const reloadMock = vi.fn()
      const originalLocation = window.location
      Object.defineProperty(window, 'location', {
        configurable: true,
        value: { ...originalLocation, reload: reloadMock },
      })

      // 记录一个刚才的重载时间
      sessionStorage.setItem(CHUNK_RELOAD_STORAGE_KEY, String(Date.now() - 2000))

      const triggered = triggerSmoothReload('test-consecutive-failure')
      expect(triggered).toBe(false)
      expect(reloadMock).not.toHaveBeenCalled()

      // 还原 location
      Object.defineProperty(window, 'location', {
        configurable: true,
        value: originalLocation,
      })
    })

    it('超过冷却期后可以再次触发重载', () => {
      const reloadMock = vi.fn()
      const originalLocation = window.location
      Object.defineProperty(window, 'location', {
        configurable: true,
        value: { ...originalLocation, reload: reloadMock },
      })

      // 模拟超过 10 秒前
      sessionStorage.setItem(CHUNK_RELOAD_STORAGE_KEY, String(Date.now() - CHUNK_RELOAD_THROTTLE_MS - 1000))

      const triggered = triggerSmoothReload('test-expired-throttle')
      expect(triggered).toBe(true)
      expect(reloadMock).toHaveBeenCalledTimes(1)

      Object.defineProperty(window, 'location', {
        configurable: true,
        value: originalLocation,
      })
    })
  })

  describe('setupChunkReloadGuard', () => {
    it('注册并在 vite:preloadError 与 unhandledrejection 时接管', () => {
      const reloadMock = vi.fn()
      const originalLocation = window.location
      Object.defineProperty(window, 'location', {
        configurable: true,
        value: { ...originalLocation, reload: reloadMock },
      })

      const cleanup = setupChunkReloadGuard()

      // 触发 unhandledrejection 事件
      const rejEvent = new Event('unhandledrejection', { cancelable: true }) as PromiseRejectionEvent
      Object.defineProperty(rejEvent, 'reason', {
        value: new Error('Failed to fetch dynamically imported module: https://vk.tide.red/studio/assets/route.js'),
      })
      window.dispatchEvent(rejEvent)

      expect(reloadMock).toHaveBeenCalledTimes(1)

      cleanup()

      Object.defineProperty(window, 'location', {
        configurable: true,
        value: originalLocation,
      })
    })
  })
})
