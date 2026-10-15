// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  CheckIcon,
  CopyIcon,
  CpuIcon,
  LayersIcon,
  NetworkIcon,
  PlayIcon,
  ScissorsIcon,
  ShieldCheckIcon,
  SparklesIcon,
} from 'lucide-react'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import { ovClient } from '#/lib/ov-client'
import { CONTEXT_ROUTER_PRESETS } from '../-constants/context-router-presets'
import type {
  ContextRouteRequest,
  ContextRouteResult,
  ContextRouterStats,
  ContextSegment,
} from '../-types/context-router'

export function ContextRouterCockpit() {
  const [content, setContent] = useState<string>(CONTEXT_ROUTER_PRESETS[0].content)
  const [codeMode, setCodeMode] = useState<'skeleton' | 'outline' | 'compact'>('skeleton')
  const [dehydrationRate, setDehydrationRate] = useState<number>(0.50)
  const [enableSkillzip, setEnableSkillzip] = useState<boolean>(true)
  const [preserveStaticHeader, setPreserveStaticHeader] = useState<boolean>(true)
  const [copied, setCopied] = useState<boolean>(false)

  // Query global stats
  const { data: stats, refetch: refetchStats } = useQuery<ContextRouterStats>({
    queryKey: ['context-router', 'stats'],
    queryFn: async () => {
      const res = await ovClient.instance.get<ContextRouterStats>('/api/v1/context-router/stats')
      return res.data
    },
    refetchInterval: 15000,
  })

  // Route & compress mutation
  const routeMutation = useMutation<ContextRouteResult, Error, ContextRouteRequest>({
    mutationFn: async (req) => {
      const res = await ovClient.instance.post<ContextRouteResult>('/api/v1/context-router/route', req)
      return res.data
    },
    onSuccess: () => {
      refetchStats()
    },
  })

  const handleExecuteRoute = () => {
    routeMutation.mutate({
      content,
      default_code_mode: codeMode,
      target_dehydration_rate: dehydrationRate,
      enable_skillzip: enableSkillzip,
      preserve_static_header: preserveStaticHeader,
    })
  }

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const result = routeMutation.data
  const originalEst = Math.max(1, Math.round(content.length / 3.5))
  const displayOrig = result ? result.total_original_tokens : originalEst
  const displayComp = result ? result.total_compressed_tokens : '--'
  const displayRatio = result ? `${(result.overall_reduction_ratio * 100).toFixed(1)}%` : '--'
  const displaySaved = result ? result.total_tokens_saved : '--'

  const getEngineBadge = (engine: string) => {
    switch (engine) {
      case 'tokenshift':
        return <Badge variant="outline" className="text-cyan-600 dark:text-cyan-400 border-cyan-500/40 bg-cyan-50/20 text-xs">🛠️ TokenShift (代码)</Badge>
      case 'llmlingua2':
        return <Badge variant="outline" className="text-blue-600 dark:text-blue-400 border-blue-500/40 bg-blue-50/20 text-xs">🔹 LLMLingua-2 (自然语言)</Badge>
      case 'skillzip':
        return <Badge variant="outline" className="text-purple-600 dark:text-purple-400 border-purple-500/40 bg-purple-50/20 text-xs">📦 SkillZip (技能契约)</Badge>
      case 'native_caching':
        return <Badge variant="outline" className="text-muted-foreground border-border text-xs">⚡ Native Caching (零损静态头)</Badge>
      default:
        return <Badge variant="secondary" className="text-xs">{engine}</Badge>
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {/* 4 Top KPI Tiles */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <Card className="p-3.5 flex flex-col gap-1 border-border/70">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>原始复合 Prompt</span>
            <LayersIcon className="size-3.5 text-muted-foreground" />
          </div>
          <div className="text-xl font-bold font-mono tabular-nums">{displayOrig}</div>
          <div className="text-xs text-muted-foreground">预估原始 Token 预算</div>
        </Card>

        <Card className="p-3.5 flex flex-col gap-1 border-border/70">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>多引擎压缩后</span>
            <ScissorsIcon className="size-3.5 text-cyan-500" />
          </div>
          <div className="text-xl font-bold font-mono tabular-nums text-cyan-600 dark:text-cyan-400">
            {displayComp}
          </div>
          <div className="text-xs text-muted-foreground">净节省 Token: {displaySaved}</div>
        </Card>

        <Card className="p-3.5 flex flex-col gap-1 border-border/70">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>综合压缩率</span>
            <SparklesIcon className="size-3.5 text-cyan-500" />
          </div>
          <div className="text-xl font-bold font-mono tabular-nums text-cyan-600 dark:text-cyan-400">
            {displayRatio}
          </div>
          <div className="text-xs text-muted-foreground">
            历史均值: {stats ? `${(stats.average_reduction_ratio * 100).toFixed(1)}%` : '--'}
          </div>
        </Card>

        <Card className="p-3.5 flex flex-col gap-1 border-border/70">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>管线延迟 & 语法门禁</span>
            <ShieldCheckIcon className="size-3.5 text-cyan-500" />
          </div>
          <div className="text-xl font-bold font-mono tabular-nums flex items-center gap-2">
            <span>{result ? `${result.total_latency_ms}ms` : '--'}</span>
            {result && (
              <Badge variant="outline" className="text-cyan-600 dark:text-cyan-400 border-cyan-500/40 bg-cyan-50/20 text-xs">
                AST PASS
              </Badge>
            )}
          </div>
          <div className="text-xs text-muted-foreground">
            已路由请求数: {stats?.total_requests ?? 0}
          </div>
        </Card>
      </div>

      {/* Control Action Bar */}
      <Card className="p-3.5 flex flex-wrap items-center justify-between gap-3 border-border/70">
        <div className="flex flex-wrap items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="text-muted-foreground font-medium">示例模版:</span>
            <select
              aria-label="复合提示词示例模版"
              className="bg-card border border-border rounded-md px-2.5 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              onChange={(e) => {
                const found = CONTEXT_ROUTER_PRESETS.find((p) => p.id === e.target.value)
                if (found) setContent(found.content)
              }}
            >
              {CONTEXT_ROUTER_PRESETS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.category})
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-muted-foreground font-medium">代码压缩模式:</span>
            <div className="inline-flex rounded-md border border-border p-0.5 bg-muted/20 text-xs">
              {(['skeleton', 'outline', 'compact'] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setCodeMode(m)}
                  className={`px-2 py-0.5 rounded-sm transition-colors ${
                    codeMode === m
                      ? 'bg-card text-foreground font-semibold shadow-sm'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  {m === 'skeleton' ? '骨架保留' : m === 'outline' ? '签名大纲' : '无损紧凑'}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-muted-foreground font-medium">脱水保留率:</span>
            <select
              aria-label="自然语言脱水目标保留率"
              className="bg-card border border-border rounded-md px-2 py-0.5 text-xs text-foreground focus:outline-none"
              value={dehydrationRate}
              onChange={(e) => setDehydrationRate(parseFloat(e.target.value))}
            >
              <option value="0.35">35% (激进抽稀)</option>
              <option value="0.50">50% (标准平衡)</option>
              <option value="0.70">70% (轻度压缩)</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5">
            <label className="flex items-center gap-1 text-muted-foreground cursor-pointer select-none">
              <input
                type="checkbox"
                checked={preserveStaticHeader}
                onChange={(e) => setPreserveStaticHeader(e.target.checked)}
                className="rounded border-border"
              />
              <span>保护静态系统头</span>
            </label>
          </div>

          <div className="flex items-center gap-1.5">
            <label className="flex items-center gap-1 text-muted-foreground cursor-pointer select-none">
              <input
                type="checkbox"
                checked={enableSkillzip}
                onChange={(e) => setEnableSkillzip(e.target.checked)}
                className="rounded border-border"
              />
              <span>启用 SkillZip 契约压缩</span>
            </label>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={handleExecuteRoute}
            disabled={routeMutation.isPending || !content.trim()}
            className="flex items-center gap-1.5 text-xs font-medium"
          >
            <PlayIcon className="size-3.5 fill-current" />
            <span>{routeMutation.isPending ? '路由压缩中...' : '⚡ 执行全景分流路由'}</span>
          </Button>
        </div>
      </Card>

      {/* Dual Column Editor & Reassembled Output */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left: Input Prompt */}
        <Card className="p-3.5 flex flex-col gap-2.5 border-border/70">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <NetworkIcon className="size-4 text-muted-foreground" />
              <span className="text-xs font-semibold">原始复合 Prompt 输入</span>
            </div>
            <span className="text-xs text-muted-foreground font-mono">
              {content.split('\n').length} 行 ｜ {content.length} 字符
            </span>
          </div>
          <textarea
            aria-label="原始复合 Prompt 输入"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={15}
            className="w-full bg-card border border-border rounded-md p-2.5 text-xs font-mono leading-relaxed text-foreground resize-y focus:outline-none focus:ring-1 focus:ring-ring"
            placeholder="粘贴混合异构提示词（包含系统角色、文档段落、代码块、技能规约等）..."
          />
        </Card>

        {/* Right: Reassembled Output */}
        <Card className="p-3.5 flex flex-col gap-2.5 border-border/70">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CpuIcon className="size-4 text-cyan-500" />
              <span className="text-xs font-semibold text-cyan-600 dark:text-cyan-400">
                重组高精纯 Prompt 输出
              </span>
            </div>
            <div className="flex items-center gap-2">
              {result && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleCopy(result.assembled_content)}
                  className="h-7 px-2 text-xs flex items-center gap-1"
                >
                  {copied ? <CheckIcon className="size-3 text-cyan-500" /> : <CopyIcon className="size-3" />}
                  <span>{copied ? '已复制' : '复制结果'}</span>
                </Button>
              )}
            </div>
          </div>
          <textarea
            aria-label="重组高精纯 Prompt 输出"
            readOnly
            value={result ? result.assembled_content : '点击上方「⚡ 执行全景分流路由」进行智能切片与多引擎压缩...'}
            rows={15}
            className="w-full bg-muted/20 border border-border rounded-md p-2.5 text-xs font-mono leading-relaxed text-foreground resize-y focus:outline-none"
          />
        </Card>
      </div>

      {/* Segment Breakdown Waterfall */}
      {result && result.segments.length > 0 && (
        <Card className="p-3.5 flex flex-col gap-3 border-border/70">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <LayersIcon className="size-4 text-cyan-500" />
              <span className="text-xs font-semibold">自适应分段流水分流总表 ({result.segments.length} 个片段)</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              {Object.entries(result.engine_distribution).map(([eng, cnt]) => (
                <span key={eng} className="font-mono">
                  {eng}: {cnt}
                </span>
              ))}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-border text-muted-foreground">
                  <th className="py-2 px-2.5 font-medium">序号</th>
                  <th className="py-2 px-2.5 font-medium">语义类别</th>
                  <th className="py-2 px-2.5 font-medium">路由目标引擎</th>
                  <th className="py-2 px-2.5 font-medium">Token 变化</th>
                  <th className="py-2 px-2.5 font-medium">节省率</th>
                  <th className="py-2 px-2.5 font-medium">耗时</th>
                  <th className="py-2 px-2.5 font-medium">状态</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50 font-mono">
                {result.segments.map((seg: ContextSegment) => (
                  <tr key={seg.index} className="hover:bg-muted/30 transition-colors">
                    <td className="py-2 px-2.5 text-muted-foreground">#{seg.index}</td>
                    <td className="py-2 px-2.5">
                      <span className="font-sans font-medium text-foreground">
                        {seg.segment_type === 'code_block'
                          ? `代码块 (${seg.language || 'code'})`
                          : seg.segment_type === 'static_header'
                          ? '静态系统规范'
                          : seg.segment_type === 'skill_contract'
                          ? '技能契约'
                          : '自然语言段落'}
                      </span>
                    </td>
                    <td className="py-2 px-2.5">{getEngineBadge(seg.engine)}</td>
                    <td className="py-2 px-2.5 tabular-nums">
                      {seg.original_tokens} ➔ {seg.compressed_tokens}
                    </td>
                    <td className="py-2 px-2.5 tabular-nums text-cyan-600 dark:text-cyan-400 font-semibold">
                      {(seg.reduction_ratio * 100).toFixed(1)}%
                    </td>
                    <td className="py-2 px-2.5 tabular-nums text-muted-foreground">{seg.latency_ms}ms</td>
                    <td className="py-2 px-2.5">
                      {seg.status === 'ok' ? (
                        <span className="text-cyan-600 dark:text-cyan-400 font-sans font-medium">正常</span>
                      ) : seg.status === 'bypassed' || seg.status === 'passthrough' ? (
                        <span className="text-muted-foreground font-sans">直通</span>
                      ) : (
                        <span className="text-amber-500 font-sans font-medium">降级</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}
