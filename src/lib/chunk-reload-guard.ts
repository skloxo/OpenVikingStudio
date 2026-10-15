/**
 * 动态模块加载失败与发版版本漂移自愈守卫 (Chunk Reload & Self-Healing Guard)
 *
 * 核心原理：
 * 在单页面应用 (SPA) 发版重新构建后，Vite 生成的 chunk hash 发生变更。
 * 停留在旧版本的客户端在路由懒加载或动态 import() 时，若请求已不存在的旧 hash chunk，
 * 浏览器会抛出 `Failed to fetch dynamically imported module`。
 *
 * 本模块通过三道自愈防线拦截该类错误：
 * 1. Vite 原生 `vite:preloadError` 事件
 * 2. `unhandledrejection` 捕获动态 import 异常
 * 3. `window.onerror` 全局脚本加载异常拦截
 *
 * 结合 10 秒会话级防抖，自动触发平滑静默重载，让用户无感进入最新版本，彻底杜绝崩溃白屏。
 */

export const CHUNK_RELOAD_STORAGE_KEY = 'ov_last_chunk_reload_ts'
export const CHUNK_RELOAD_THROTTLE_MS = 10_000

const CHUNK_ERROR_PATTERNS: readonly string[] = [
  'failed to fetch dynamically imported module',
  'importing a module script failed',
  'error loading dynamically imported module',
  'unable to preload',
  'chunkloaderror',
  'loading chunk',
  'dynamically imported module',
]

/**
 * 判断给定错误是否属于动态模块加载/版本漂移失败
 */
export function isChunkLoadError(err: unknown): boolean {
  if (!err) return false

  let message = ''
  if (typeof err === 'string') {
    message = err
  } else if (err instanceof Error) {
    message = `${err.name} ${err.message} ${err.stack || ''}`
  } else if (typeof err === 'object') {
    const obj = err as Record<string, unknown>
    message = String(obj.message || obj.reason || obj.detail || '')
  }

  const normalized = message.toLowerCase()
  return CHUNK_ERROR_PATTERNS.some((pattern) => normalized.includes(pattern))
}

/**
 * 触发平滑重载（带防抖保护，避免死循环）
 * @returns boolean 是否实际执行了 window.location.reload()
 */
export function triggerSmoothReload(reason?: unknown): boolean {
  try {
    const hasStorage = typeof window !== 'undefined' && typeof window.sessionStorage !== 'undefined'
    const lastReload = hasStorage ? Number(window.sessionStorage.getItem(CHUNK_RELOAD_STORAGE_KEY) || 0) : 0
    const now = Date.now()

    if (now - lastReload < CHUNK_RELOAD_THROTTLE_MS) {
      console.warn(
        '[OpenViking] 动态模块加载失败，但处于 10s 重载冷却保护期中，跳过强制刷新以防止死循环。',
        reason,
      )
      return false
    }

    if (hasStorage) {
      window.sessionStorage.setItem(CHUNK_RELOAD_STORAGE_KEY, String(now))
    }
    console.warn(
      '[OpenViking] 检测到前端静态资源版本漂移或动态模块缺失，正在自动平滑重载同步最新版本...',
      reason,
    )

    if (typeof window !== 'undefined') {
      window.location.reload()
      return true
    }
  } catch (storageErr) {
    console.error('[OpenViking] 访问 sessionStorage 失败，直接执行重载兜底:', storageErr)
    if (typeof window !== 'undefined') {
      window.location.reload()
      return true
    }
  }
  return false
}

/**
 * 全局安装动态模块加载自愈守卫
 * @returns cleanup 清理函数
 */
export function setupChunkReloadGuard(): () => void {
  if (typeof window === 'undefined') {
    return () => {}
  }

  // 1. Vite 原生动态加载 preload 错误事件
  const onVitePreloadError = (event: Event) => {
    // 阻止浏览器默认冒泡，接管自愈
    event.preventDefault()
    triggerSmoothReload('vite:preloadError')
  }

  // 2. 捕获未处理的 Promise Rejection (dynamic import() 失败属于 Promise rejection)
  const onUnhandledRejection = (event: PromiseRejectionEvent) => {
    if (isChunkLoadError(event.reason)) {
      event.preventDefault()
      triggerSmoothReload(event.reason)
    }
  }

  // 3. 捕获全局运行时 Error (某些浏览器上作为 ErrorEvent 抛出)
  const onError = (event: ErrorEvent) => {
    if (isChunkLoadError(event.error || event.message)) {
      event.preventDefault()
      triggerSmoothReload(event.error || event.message)
    }
  }

  window.addEventListener('vite:preloadError', onVitePreloadError)
  window.addEventListener('unhandledrejection', onUnhandledRejection)
  window.addEventListener('error', onError)

  return () => {
    window.removeEventListener('vite:preloadError', onVitePreloadError)
    window.removeEventListener('unhandledrejection', onUnhandledRejection)
    window.removeEventListener('error', onError)
  }
}
