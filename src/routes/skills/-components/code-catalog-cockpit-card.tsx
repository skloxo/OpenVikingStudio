// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  CpuIcon,
  DatabaseIcon,
  FileCheckIcon,
  LayersIcon,
  RefreshCwIcon,
  ShieldCheckIcon,
} from 'lucide-react'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import { Badge } from '#/components/ui/badge'
import { CopyButton } from '#/components/common/copy-button'
import { ovClient } from '#/lib/ov-client'

interface CatalogSummaryResponse {
  status: string
  summary: {
    skills_compiled: number
    mcp_tools_detected: number
    routes_detected: number
    verification_mode: string
    hallucination_rate: number
  }
}

interface RoleProjectionResponse {
  status: string
  role: string
  projection: {
    role: string
    total_endpoints?: number
    total_tools?: number
    endpoints?: Array<{ method: string; path: string; handler: string }>
    tools?: Array<{ name: string; handler: string; returns: string }>
    contracts?: Array<{
      name?: string
      method?: string
      path?: string
      signature?: string
      returns?: string
      expected_status_codes?: number[]
    }>
    storage_tables?: string[]
  }
}

interface TestRetinaResponse {
  status: string
  total_routes_covered: number
  generated_test_code: string
}

export function CodeCatalogCockpitCard() {
  const [activeRole, setActiveRole] = React.useState<'dev' | 'test' | 'ops'>('dev')
  const [targetRoute, setTargetRoute] = React.useState<string>('/api/v1/catalog/summary')

  // 1. Fetch high-level summary facts
  const summaryQuery = useQuery<CatalogSummaryResponse>({
    queryKey: ['catalog-summary'],
    queryFn: async () => (await ovClient.instance.get('/api/v1/catalog/summary')).data,
    staleTime: 30_000,
  })

  // 2. Fetch role projection
  const projectionQuery = useQuery<RoleProjectionResponse>({
    queryKey: ['catalog-projection', activeRole],
    queryFn: async () => (await ovClient.instance.get(`/api/v1/catalog/projections/${activeRole}`)).data,
    staleTime: 30_000,
  })

  // 3. Generate test retina
  const testGenQuery = useQuery<TestRetinaResponse>({
    queryKey: ['catalog-test-retina', targetRoute],
    queryFn: async () =>
      (await ovClient.instance.get(`/api/v1/catalog/generate-tests?target_route=${encodeURIComponent(targetRoute)}`)).data,
    enabled: Boolean(targetRoute),
    staleTime: 30_000,
  })

  const summary = summaryQuery.data?.summary
  const projection = projectionQuery.data?.projection

  return (
    <Card className="flex flex-col gap-3 p-3.5 bg-card/60 border-border/80 rounded-md">
      {/* Top Header & Core Metrics */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-2.5">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-md bg-muted/60 text-cyan-400">
            <CpuIcon className="size-4" />
          </div>
          <div>
            <h2 className="text-xs font-semibold tracking-tight text-foreground flex items-center gap-1.5">
              🧬 源码事实与多角色视网膜座舱
              <Badge variant="outline" className="text-xs font-mono border-cyan-500/30 text-cyan-400 bg-cyan-950/20 px-1 py-0">
                JIT AST SSOT
              </Badge>
            </h2>
            <p className="text-xs text-muted-foreground font-mono">
              纯静态 AST 抽取真实契约，拒绝文档行号漂移与上下文毒化
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="xs"
            onClick={() => {
              summaryQuery.refetch()
              projectionQuery.refetch()
              testGenQuery.refetch()
            }}
            className="h-7 text-xs font-mono text-muted-foreground hover:text-foreground"
          >
            <RefreshCwIcon className={`size-3.5 mr-1 ${summaryQuery.isFetching ? 'animate-spin' : ''}`} />
            刷新事实
          </Button>
        </div>
      </div>

      {/* Metric Tiles */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <div className="p-2.5 rounded-md bg-muted/30 border border-border/50">
          <div className="text-xs text-muted-foreground font-mono">REST 路由端点</div>
          <div className="text-sm font-bold font-mono tabular-nums text-foreground mt-0.5">
            {summary?.routes_detected ?? '--'}
          </div>
        </div>
        <div className="p-2.5 rounded-md bg-muted/30 border border-border/50">
          <div className="text-xs text-muted-foreground font-mono">FastMCP 智能体工具</div>
          <div className="text-sm font-bold font-mono tabular-nums text-cyan-400 mt-0.5">
            {summary?.mcp_tools_detected ?? '--'}
          </div>
        </div>
        <div className="p-2.5 rounded-md bg-muted/30 border border-border/50">
          <div className="text-xs text-muted-foreground font-mono">事实校验模式</div>
          <div className="text-xs font-mono text-foreground mt-0.5 flex items-center gap-1">
            <ShieldCheckIcon className="size-3 text-cyan-400" />
            {summary?.verification_mode ?? 'strict_code_ast'}
          </div>
        </div>
        <div className="p-2.5 rounded-md bg-muted/30 border border-border/50">
          <div className="text-xs text-muted-foreground font-mono">事实幻觉率</div>
          <div className="text-sm font-bold font-mono tabular-nums text-cyan-400 mt-0.5">
            {summary ? `${summary.hallucination_rate.toFixed(1)}%` : '--'}
          </div>
        </div>
      </div>

      {/* Role Projection Section */}
      <div className="flex flex-col gap-2 pt-1">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-foreground flex items-center gap-1.5">
            <LayersIcon className="size-3.5 text-cyan-400" />
            多角色切片投影 (Role-Specific Projections)
          </span>
          <div className="flex items-center gap-1 bg-muted/40 p-0.5 rounded-md border border-border/50">
            {(['dev', 'test', 'ops'] as const).map((r) => (
              <Button
                key={r}
                variant={activeRole === r ? 'default' : 'ghost'}
                size="xs"
                onClick={() => setActiveRole(r)}
                className={`text-xs h-6 px-2 font-mono uppercase ${
                  activeRole === r ? 'bg-cyan-600 text-white' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {r === 'dev' ? '💻 Dev 研发' : r === 'test' ? '🧪 Test 契约' : '🛠️ Ops 运维'}
              </Button>
            ))}
          </div>
        </div>

        {/* Projection Content Cards */}
        <div className="p-2.5 rounded-md bg-muted/20 border border-border/60 max-h-48 overflow-y-auto font-mono text-xs text-foreground/90 space-y-1.5">
          {projectionQuery.isLoading ? (
            <div className="text-muted-foreground text-xs py-3 text-center">正在投影 {activeRole} 视角事实...</div>
          ) : activeRole === 'dev' ? (
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">提取到 {projection?.endpoints?.length ?? 0} 个路由接缝与 {projection?.tools?.length ?? 0} 个 MCP 工具：</div>
              {projection?.endpoints?.slice(0, 8).map((ep, idx) => (
                <div
                  key={idx}
                  onClick={() => setTargetRoute(ep.path)}
                  className={`flex items-center justify-between text-xs py-0.5 border-b border-border/30 last:border-0 cursor-pointer hover:bg-muted/40 px-1 rounded transition-colors ${
                    targetRoute === ep.path ? 'bg-cyan-950/30 text-cyan-300' : ''
                  }`}
                  title="点击为此接口生成测试视网膜"
                >
                  <span className="text-cyan-400 font-bold">{ep.method}</span>
                  <span className="text-muted-foreground truncate max-w-xs">{ep.path}</span>
                  <span className="text-foreground/80">{ep.handler}</span>
                </div>
              ))}
            </div>
          ) : activeRole === 'test' ? (
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">提取到契约测试边界与断言集合：</div>
              {projection?.contracts?.slice(0, 6).map((c, idx) => (
                <div key={idx} className="p-1.5 rounded bg-muted/40 border border-border/40 text-xs">
                  <div className="flex items-center justify-between font-bold text-cyan-300">
                    <span>{c.name || `${c.method} ${c.path}`}</span>
                    <span className="text-muted-foreground font-normal">状态码: {c.expected_status_codes?.join(', ')}</span>
                  </div>
                  {c.signature && <div className="text-muted-foreground mt-0.5 truncate">入参: {c.signature}</div>}
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">存储与探针拓扑：</div>
              <div className="flex flex-wrap gap-1.5 pt-1">
                {projection?.storage_tables?.map((table) => (
                  <Badge key={table} variant="outline" className="text-xs font-mono border-border bg-muted/50 text-foreground">
                    <DatabaseIcon className="size-3 mr-1 text-cyan-400" />
                    {table}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Test Retina Interactive Generator */}
      <div className="flex flex-col gap-2 pt-1 border-t border-border/60">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-foreground flex items-center gap-1.5">
            <FileCheckIcon className="size-3.5 text-cyan-400" />
            自动化测试视网膜生成台 (Pytest Retina Generator)
          </span>
          {testGenQuery.data?.generated_test_code && (
            <CopyButton
              value={testGenQuery.data.generated_test_code}
              label="复制 Pytest 测试用例"
              size="xs"
              variant="outline"
              className="h-6 text-xs font-mono border-border"
            />
          )}
        </div>

        <div className="relative rounded-md bg-muted/30 border border-border/60 p-2 font-mono text-xs overflow-x-auto max-h-44 text-muted-foreground">
          {testGenQuery.isLoading ? (
            <div className="py-4 text-center">正在从 AST 事实即时生成测试视网膜...</div>
          ) : (
            <pre className="text-xs text-foreground/90 whitespace-pre leading-relaxed">
              {testGenQuery.data?.generated_test_code || '# 暂无可生成的测试代码'}
            </pre>
          )}
        </div>
      </div>
    </Card>
  )
}
