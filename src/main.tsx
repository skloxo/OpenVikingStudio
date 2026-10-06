import '#/i18n'
import ReactDOM from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createRouter } from '@tanstack/react-router'
import { ThemeProvider } from 'next-themes'
import { routeTree } from './routeTree.gen'
import { TooltipProvider } from './components/ui/tooltip'
import { queryClient } from './lib/query-client'
import { getRouterBasePath } from './lib/public-path'
import { setupChunkReloadGuard, triggerSmoothReload, isChunkLoadError } from './lib/chunk-reload-guard'

// 启动全局动态模块加载与发版版本漂移自愈守卫
setupChunkReloadGuard()

// PWA: register the service worker at the SPA's base path so the scope
// matches the manifest's start_url / scope. Production builds only — the
// vite dev server's HMR doesn't play nicely with a SW intercepting requests.
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  const basePath = getRouterBasePath() || '/'
  const swUrl = `${basePath}${basePath.endsWith('/') ? '' : '/'}service-worker.js`
  window.addEventListener('load', () => {
    void navigator.serviceWorker.register(swUrl, { scope: basePath })
  })
}

const router = createRouter({
  routeTree,
  basepath: getRouterBasePath(),
  defaultPreload: 'intent',
  scrollRestoration: true,
  defaultErrorComponent: ({ error }) => {
    if (isChunkLoadError(error)) {
      triggerSmoothReload(error)
      return null
    }
    const msg = error.message || 'Unknown routing error'
    return (
      <div className="m-4 rounded-md border border-rose-500/30 bg-rose-500/10 p-4 text-xs font-mono text-rose-400">
        <div className="font-semibold text-rose-300">[Route Error] 页面模块加载异常</div>
        <div className="mt-1 break-all text-muted-foreground">{msg}</div>
        <button
          type="button"
          onClick={() => triggerSmoothReload('user_click_route_error')}
          className="mt-3 inline-flex items-center rounded-md border border-cyan-500/40 bg-cyan-500/10 px-3 py-1.5 text-xs font-medium text-cyan-300 hover:bg-cyan-500/20 active:scale-95 transition-all"
        >
          立即重新同步最新版本
        </button>
      </div>
    )
  },
})

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

const rootElement = document.getElementById('app')!

if (!rootElement.innerHTML) {
  const root = ReactDOM.createRoot(rootElement)
  root.render(
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <RouterProvider router={router} />
        </TooltipProvider>
      </QueryClientProvider>
    </ThemeProvider>,
  )
}
