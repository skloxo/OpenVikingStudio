// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0
import * as React from 'react'
import {
  CopyIcon,
  FilterIcon,
  LayersIcon,
  SearchIcon,
  XIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { cn } from '#/lib/utils'

interface BundleScenariosBrowserProps {
  scenarios: string[]
  bundleName: string
}

interface SubCluster {
  id: string
  label: string
  count: number
}

function escapeRegExp(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

export function BundleScenariosBrowser({
  scenarios,
  bundleName,
}: BundleScenariosBrowserProps) {
  const [searchQuery, setSearchQuery] = React.useState('')
  const [activeCluster, setActiveCluster] = React.useState('all')

  // 1. 动态自适应多维分簇算法 (Dynamic Faceted Cluster Extraction)
  const { clusters, scenarioPrefixMap } = React.useMemo(() => {
    const prefixMap = new Map<string, string>()
    const prefixCounts = new Map<string, number>()

    for (const sc of scenarios) {
      const parts = sc.split(/[-_]/)
      const prefix = (parts[0] || 'misc').toLowerCase()
      prefixMap.set(sc, prefix)
      prefixCounts.set(prefix, (prefixCounts.get(prefix) || 0) + 1)
    }

    // 动态阈值：工序很多时要求 >= 3 项聚类，较少时 >= 2 项
    const threshold = scenarios.length > 20 ? 3 : 2
    const validClusters: SubCluster[] = []
    let otherCount = 0

    for (const [prefix, count] of prefixCounts.entries()) {
      if (count >= threshold) {
        validClusters.push({
          id: prefix,
          label: prefix,
          count,
        })
      } else {
        otherCount += count
      }
    }

    // 按数量降序排序
    validClusters.sort((a, b) => b.count - a.count)

    if (otherCount > 0) {
      validClusters.push({
        id: 'other',
        label: '其他工序',
        count: otherCount,
      })
    }

    const allClusters: SubCluster[] = [
      {
        id: 'all',
        label: '全部工序',
        count: scenarios.length,
      },
      ...validClusters,
    ]

    return { clusters: allClusters, scenarioPrefixMap: prefixMap }
  }, [scenarios])

  // 2. 毫秒级联合多维过滤 (In-Bundle Instant Search & Cluster Filter)
  const filteredScenarios = React.useMemo(() => {
    const query = searchQuery.trim().toLowerCase()

    return scenarios.filter((sc) => {
      // 分簇过滤
      if (activeCluster !== 'all') {
        const scPrefix = scenarioPrefixMap.get(sc) || 'misc'
        const isClusterValid = clusters.some(
          (c) => c.id === scPrefix && c.id !== 'all' && c.id !== 'other',
        )

        if (activeCluster === 'other') {
          if (isClusterValid) return false
        } else if (scPrefix !== activeCluster) {
          return false
        }
      }

      // 关键词过滤
      if (query && !sc.toLowerCase().includes(query)) {
        return false
      }

      return true
    })
  }, [scenarios, searchQuery, activeCluster, scenarioPrefixMap, clusters])

  // 3. 点击一键复制工序真实调用 URI 与标识
  const handleCopyScenario = (sc: string, e: React.MouseEvent) => {
    e.stopPropagation()
    const uri = `viking://agent/skills/${bundleName}/scenarios/${sc}.md`
    void navigator.clipboard.writeText(uri)
    toast.success(`已复制工序调用 URI`, {
      description: uri,
      duration: 2500,
    })
  }

  // 4. 高亮匹配子串
  const renderHighlightedName = (name: string) => {
    const query = searchQuery.trim()
    if (!query) return name

    try {
      const regex = new RegExp(`(${escapeRegExp(query)})`, 'gi')
      const parts = name.split(regex)
      return (
        <>
          {parts.map((part, i) =>
            regex.test(part) ? (
              <span
                key={i}
                className="bg-cyan-500/25 text-cyan-600 dark:text-cyan-300 font-bold px-0.5 rounded-xs"
              >
                {part}
              </span>
            ) : (
              part
            ),
          )}
        </>
      )
    } catch {
      return name
    }
  }

  if (!scenarios || scenarios.length === 0) {
    return (
      <div className="rounded border border-dashed border-border/50 bg-muted/10 p-3 text-center text-xs text-muted-foreground font-mono">
        暂无专精工序场景
      </div>
    )
  }

  return (
    <div className="space-y-2.5 font-sans">
      {/* 顶部搜索框与即时匹配回显 */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <SearchIcon className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground pointer-events-none" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={`毫秒级检索 ${scenarios.length} 项工序 (支持关键词搜索)...`}
            className="h-8 pl-8 pr-7 text-xs font-mono bg-muted/20 border-border/60 focus-visible:ring-cyan-500/40 rounded-md"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="absolute right-2 top-2 p-0.5 text-muted-foreground hover:text-foreground cursor-pointer rounded"
              title="清空搜索"
            >
              <XIcon className="size-3.5" />
            </button>
          )}
        </div>
        <div className="shrink-0 flex items-center gap-1.5 px-2 py-1 rounded bg-muted/30 border border-border/40 text-xs font-mono">
          <span className="text-muted-foreground">匹配:</span>
          <span
            data-testid="scenarios-match-count"
            className="font-semibold text-cyan-600 dark:text-cyan-400 tabular-nums"
          >
            {filteredScenarios.length}
          </span>
          <span className="text-muted-foreground/40">/</span>
          <span
            data-testid="scenarios-total-count"
            className="text-muted-foreground tabular-nums"
          >
            {scenarios.length}
          </span>
        </div>
      </div>

      {/* 二级多维分簇筛选胶囊 (Sub-Cluster Faceted Filter) */}
      {clusters.length > 2 && (
        <div className="space-y-1">
          <div className="flex items-center gap-1 text-xs text-muted-foreground font-sans">
            <FilterIcon className="size-3 text-cyan-500" />
            <span>工序领域分簇:</span>
          </div>
          <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto pr-1">
            {clusters.map((cluster) => {
              const isSelected = activeCluster === cluster.id
              return (
                <button
                  key={cluster.id}
                  type="button"
                  onClick={() => setActiveCluster(cluster.id)}
                  className={cn(
                    'flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-mono transition-all cursor-pointer border',
                    isSelected
                      ? 'bg-cyan-500/15 border-cyan-500/40 text-cyan-700 dark:text-cyan-300 font-semibold shadow-xs'
                      : 'bg-muted/20 border-border/40 text-muted-foreground hover:text-foreground hover:border-border',
                  )}
                >
                  <span>{cluster.label}</span>
                  <span
                    className={cn(
                      'text-xs tabular-nums px-1 py-0 rounded',
                      isSelected
                        ? 'bg-cyan-500/20 text-cyan-700 dark:text-cyan-300 font-bold'
                        : 'bg-muted/40 text-muted-foreground',
                    )}
                  >
                    {cluster.count}
                  </span>
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* 工序徽章流式卡片与高密交互区 */}
      <div className="rounded-md border border-border/50 bg-muted/20 p-2 space-y-1">
        {filteredScenarios.length === 0 ? (
          <div className="py-6 text-center text-xs text-muted-foreground space-y-2">
            <LayersIcon className="size-5 mx-auto text-muted-foreground/40" />
            <p className="font-mono">未找到与 &quot;{searchQuery}&quot; 匹配的专精工序</p>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setSearchQuery('')
                setActiveCluster('all')
              }}
              className="h-6 text-xs font-mono px-2"
            >
              重置所有筛选
            </Button>
          </div>
        ) : (
          <div className="flex flex-wrap gap-1.5 max-h-48 overflow-y-auto pr-1">
            {filteredScenarios.map((sc) => (
              <Badge
                key={sc}
                data-scenario={sc}
                variant="outline"
                onClick={(e) => handleCopyScenario(sc, e)}
                title={`点击复制: viking://agent/skills/${bundleName}/scenarios/${sc}.md`}
                className="text-xs px-2 py-1 border-cyan-500/30 bg-background/80 hover:bg-cyan-500/10 hover:border-cyan-500/50 text-foreground transition-all font-mono cursor-pointer flex items-center gap-1 group shadow-2xs"
              >
                <span className="text-cyan-600 dark:text-cyan-400 select-none">⚡</span>
                <span>{renderHighlightedName(sc)}</span>
                <CopyIcon className="size-2.5 opacity-0 group-hover:opacity-60 transition-opacity ml-0.5 text-muted-foreground" />
              </Badge>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
