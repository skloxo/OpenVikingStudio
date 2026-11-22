/**
 * route.tsx
 * 插件中心顶层路由容器 (Cockpit UI 规范)。
 * 容器只负责状态装配，业务解耦至 -components 与 -lib。
 * 严格控制行数 <= 150 行。
 */

import { createFileRoute } from '@tanstack/react-router'
import {
  AlertTriangleIcon,
  BoxesIcon,
  LayersIcon,
  RefreshCwIcon,
  SearchIcon,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { PluginMetricsBar } from './-components/plugin-metrics-bar'
import { PluginQuadCard } from './-components/plugin-quad-card'
import { PluginDetailDrawer } from './-components/plugin-detail-drawer'
import { usePluginsData } from './-lib/use-plugins'

export const Route = createFileRoute('/plugins')({
  component: PluginsRoute,
})

function PluginsRoute() {
  const {
    categoryFilter,
    error,
    filteredPlugins,
    healthSummary,
    isError,
    isLoading,
    plugins,
    refetch,
    searchQuery,
    selectedPlugin,
    setCategoryFilter,
    setSearchQuery,
    setSelectedPlugin,
  } = usePluginsData()

  return (
    <div className="flex w-full min-w-0 flex-col gap-4">
      {/* 头部导航与标题 */}
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div className="grid gap-1">
          <h1 className="flex items-center gap-2 text-xl font-semibold tracking-tight text-foreground">
            <BoxesIcon className="size-5 text-cyan-400" />
            插件中心
          </h1>
          <p className="max-w-3xl text-xs text-muted-foreground font-mono">
            全集群四位一体插件注册中枢：标准 MCP 工具 + Hook 拦截反射 + 认知导轨规约 + 交互配置界面
          </p>
        </div>
        <Badge
          variant="outline"
          className="border-border bg-muted/30 px-2 py-0.5 text-xs font-mono text-foreground"
        >
          ⚡ HTTP 流式通道就绪
        </Badge>
      </header>

      {/* 顶栏高密核心指标瓦片 */}
      <PluginMetricsBar plugins={plugins} healthSummary={healthSummary ?? null} />

      {/* 筛选与搜索工具条 */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-3 pt-1">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline" className="h-7 px-2.5 text-xs font-mono text-muted-foreground border-border/70">
            全集群可用插件 ({plugins.length})
          </Badge>
          <div className="flex items-center rounded-md border border-border/60 bg-muted/20 p-0.5 text-xs font-mono">
            {(
              [
                { id: 'all', label: '全部分类' },
                { id: 'platform', label: '平台内置' },
                { id: 'user', label: '生态扩展' },
              ] as const
            ).map((opt) => (
              <button
                key={opt.id}
                type="button"
                onClick={() => setCategoryFilter(opt.id)}
                className={`rounded px-2.5 py-0.5 text-xs transition-colors cursor-pointer ${
                  categoryFilter === opt.id
                    ? 'bg-cyan-500/15 text-cyan-600 dark:text-cyan-400 font-semibold'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <div className="relative w-64">
          <SearchIcon className="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索插件、工具或事件..."
            className="h-7 pl-8 text-xs font-mono"
          />
        </div>
      </div>

      {/* 插件四位一体卡片列表网格 */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-3.5 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((idx) => (
            <div
              key={idx}
              className="h-44 animate-pulse rounded-md border border-border/40 bg-muted/20"
            />
          ))}
        </div>
      ) : isError && plugins.length === 0 ? (
        <div className="flex min-h-75 flex-col items-center justify-center rounded-md border border-rose-500/40 bg-rose-500/5 p-8 text-center">
          <AlertTriangleIcon className="size-8 text-rose-500" />
          <h3 className="mt-3 text-sm font-semibold text-rose-500">插件中心加载失败</h3>
          <p className="mt-1 max-w-md text-xs text-muted-foreground font-mono">
            {error instanceof Error ? error.message : '无法连接后端插件服务或接口返回异常'}
          </p>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => void refetch()}
            className="mt-4 h-7 text-xs font-mono border-rose-500/40 text-rose-500 hover:bg-rose-500/10"
          >
            <RefreshCwIcon className="mr-1.5 size-3.5" />
            重新加载
          </Button>
        </div>
      ) : filteredPlugins.length === 0 ? (
        <div className="flex min-h-75 flex-col items-center justify-center rounded-md border border-dashed border-border/80 p-8 text-center">
          <LayersIcon className="size-8 text-muted-foreground/50" />
          <h3 className="mt-3 text-sm font-semibold text-foreground">未检索到匹配插件</h3>
          <p className="mt-1 text-xs text-muted-foreground font-mono">
            可尝试调整筛选分类或搜索关键词
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3.5 md:grid-cols-2 lg:grid-cols-3">
          {filteredPlugins.map((plugin) => (
            <PluginQuadCard
              key={plugin.plugin_id}
              plugin={plugin}
              onSelect={setSelectedPlugin}
            />
          ))}
        </div>
      )}

      {/* 抽屉详情展示 */}
      <PluginDetailDrawer
        plugin={selectedPlugin}
        onClose={() => setSelectedPlugin(null)}
      />
    </div>
  )
}
