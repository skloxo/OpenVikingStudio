// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  CodeIcon,
  CopyIcon,
  CpuIcon,
  PlayIcon,
  ScissorsIcon,
  ShieldCheckIcon,
  SparklesIcon,
} from 'lucide-react'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import { ovClient } from '#/lib/ov-client'
import { TOKENSHIFT_PRESETS } from '../-constants/tokenshift-presets'
import type {
  TokenShiftLanguage,
  TokenShiftMode,
  TokenShiftProtectResult,
  TokenShiftRequest,
  TokenShiftResult,
  TokenShiftStats,
} from '../-types/tokenshift'

export function TokenShiftCockpit() {
  const [code, setCode] = useState<string>(TOKENSHIFT_PRESETS[0].code)
  const [mode, setMode] = useState<TokenShiftMode>('skeleton')
  const [language, setLanguage] = useState<TokenShiftLanguage>('auto')
  const [preserveDocstrings, setPreserveDocstrings] = useState<boolean>(true)
  const [stripComments, setStripComments] = useState<boolean>(true)
  const [copied, setCopied] = useState<boolean>(false)

  // Query global stats
  const { data: stats, refetch: refetchStats } = useQuery<TokenShiftStats>({
    queryKey: ['tokenshift', 'stats'],
    queryFn: async () => {
      const res = await ovClient.instance.get<TokenShiftStats>('/api/v1/tokenshift/stats')
      return res.data
    },
    refetchInterval: 15000,
  })

  // Compress mutation
  const compressMutation = useMutation<TokenShiftResult, Error, TokenShiftRequest>({
    mutationFn: async (req) => {
      const res = await ovClient.instance.post<TokenShiftResult>('/api/v1/tokenshift/compress', req)
      return res.data
    },
    onSuccess: () => {
      refetchStats()
    },
  })

  // Protect symbols mutation
  const protectMutation = useMutation<TokenShiftProtectResult, Error, { code: string; language: TokenShiftLanguage }>({
    mutationFn: async (body) => {
      const res = await ovClient.instance.post<TokenShiftProtectResult>('/api/v1/tokenshift/protect', body)
      return res.data
    },
  })

  const handleCompress = () => {
    compressMutation.mutate({
      code,
      mode,
      language,
      preserve_docstrings: preserveDocstrings,
      strip_comments: stripComments,
    })
  }

  const handleProtect = () => {
    protectMutation.mutate({ code, language })
  }

  const handleCopy = () => {
    const textToCopy = compressMutation.data?.compressed_code || ''
    if (textToCopy) {
      navigator.clipboard.writeText(textToCopy)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const result = compressMutation.data

  return (
    <div className="flex flex-col gap-4">
      {/* 4 High-Density Metrics Tiles */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card className="p-3.5 bg-card/60 border-border/70">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-mono mb-1">
            <span>原始 Token 预算</span>
            <CpuIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
          </div>
          <div className="text-xl font-mono font-semibold tabular-nums text-foreground">
            {result ? result.original_tokens_est : (stats?.total_original_tokens ? `${stats.total_original_tokens} (累计)` : '--')}
            <span className="text-xs text-muted-foreground font-normal ml-1">tokens</span>
          </div>
          <div className="text-xs text-muted-foreground font-mono mt-1">
            行数: {result ? result.original_lines : '--'} 行
          </div>
        </Card>

        <Card className="p-3.5 bg-card/60 border-border/70">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-mono mb-1">
            <span>压缩后 Token</span>
            <ScissorsIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
          </div>
          <div className="text-xl font-mono font-semibold tabular-nums text-cyan-600 dark:text-cyan-400">
            {result ? result.compressed_tokens_est : (stats?.total_compressed_tokens ? `${stats.total_compressed_tokens} (累计)` : '--')}
            <span className="text-xs text-muted-foreground font-normal ml-1">tokens</span>
          </div>
          <div className="text-xs text-muted-foreground font-mono mt-1">
            行数: {result ? result.compressed_lines : '--'} 行
          </div>
        </Card>

        <Card className="p-3.5 bg-card/60 border-border/70">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-mono mb-1">
            <span>Token 压缩节省率</span>
            <SparklesIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
          </div>
          <div className="text-xl font-mono font-semibold tabular-nums text-foreground">
            {result ? `${(result.reduction_ratio * 100).toFixed(1)}%` : (stats?.average_reduction_ratio ? `${(stats.average_reduction_ratio * 100).toFixed(1)}%` : '--%')}
          </div>
          <div className="text-xs text-muted-foreground font-mono mt-1">
            耗时: {result ? `${result.elapsed_ms}ms` : '--'}
          </div>
        </Card>

        <Card className="p-3.5 bg-card/60 border-border/70">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-mono mb-1">
            <span>AST 语法树校验</span>
            <ShieldCheckIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            {result ? (
              result.syntax_validation.valid ? (
                <Badge className="bg-cyan-50 dark:bg-cyan-950/40 text-cyan-700 dark:text-cyan-300 border-cyan-200 dark:border-cyan-800/40 text-xs px-2 py-0.5 font-mono">
                  PASS 100% 合法
                </Badge>
              ) : (
                <Badge className="bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 border-rose-200 dark:border-rose-800/40 text-xs px-2 py-0.5 font-mono">
                  FAIL 语法异常
                </Badge>
              )
            ) : (
              <span className="text-xl font-mono font-semibold text-muted-foreground">
                {stats?.syntax_pass_rate ? `${(stats.syntax_pass_rate * 100).toFixed(0)}% 通过` : '--'}
              </span>
            )}
          </div>
          <div className="text-xs text-muted-foreground font-mono mt-1.5">
            解析器: {result ? result.syntax_validation.parser : '--'}
          </div>
        </Card>
      </div>

      {/* Control Bar & Preset Chips */}
      <Card className="p-3 bg-card/60 border-border/70 flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground font-mono">预设示例:</span>
            {TOKENSHIFT_PRESETS.map((p) => (
              <Button
                key={p.id}
                variant="outline"
                size="sm"
                className="h-7 text-xs font-mono border-border/70"
                onClick={() => {
                  setCode(p.code)
                  setLanguage(p.language)
                }}
              >
                {p.label}
              </Button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs font-mono border-border/70"
              onClick={handleProtect}
              disabled={protectMutation.isPending}
            >
              <ShieldCheckIcon className="size-3.5 mr-1 text-cyan-600 dark:text-cyan-400" />
              {protectMutation.isPending ? '分析中...' : '提取保护符号'}
            </Button>
            <Button
              variant="default"
              size="sm"
              className="h-7 text-xs font-mono bg-primary text-primary-foreground"
              onClick={handleCompress}
              disabled={compressMutation.isPending}
            >
              <PlayIcon className="size-3.5 mr-1" />
              {compressMutation.isPending ? '压缩中...' : '执行 AST 压缩'}
            </Button>
          </div>
        </div>

        {/* Modes & Options */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-border/50 text-xs font-mono">
          <div className="flex items-center gap-1.5">
            <span className="text-muted-foreground">压缩阶梯:</span>
            {(['outline', 'skeleton', 'compact'] as TokenShiftMode[]).map((m) => (
              <Button
                key={m}
                variant={mode === m ? 'secondary' : 'ghost'}
                size="sm"
                className={`h-6 text-xs font-mono px-2 ${mode === m ? 'border border-cyan-500/40 text-cyan-600 dark:text-cyan-400' : ''}`}
                onClick={() => setMode(m)}
              >
                {m === 'outline' && 'L0 大纲 (~70%)'}
                {m === 'skeleton' && 'L1 骨架 (~50%)'}
                {m === 'compact' && 'L2 紧凑 (~25%)'}
              </Button>
            ))}
          </div>

          <div className="flex items-center gap-4 text-muted-foreground">
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={preserveDocstrings}
                onChange={(e) => setPreserveDocstrings(e.target.checked)}
                className="rounded border-border size-3.5"
              />
              保留 Docstring
            </label>
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={stripComments}
                onChange={(e) => setStripComments(e.target.checked)}
                className="rounded border-border size-3.5"
              />
              剔除冗余注释
            </label>
          </div>
        </div>
      </Card>

      {/* Protected Symbols Tray (if extracted) */}
      {protectMutation.data && (
        <Card className="p-3 bg-muted/20 border-border/70 flex flex-col gap-2">
          <div className="flex items-center justify-between text-xs font-mono text-muted-foreground">
            <span>🛡️ 语法树受保护符号与签名 ({protectMutation.data.total_symbols} 个)</span>
            <span>语言: {protectMutation.data.language}</span>
          </div>
          <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
            {protectMutation.data.frozen_signatures.map((sig, idx) => (
              <Badge
                key={idx}
                variant="outline"
                className="text-xs font-mono px-1.5 py-0.5 border-border bg-card/60 text-foreground"
              >
                {sig}
              </Badge>
            ))}
          </div>
        </Card>
      )}

      {/* Two-Column Code Workbench */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 min-h-105">
        {/* Left Column: Raw Source */}
        <Card className="p-3 bg-card/60 border-border/70 flex flex-col gap-2">
          <div className="flex items-center justify-between text-xs font-mono text-muted-foreground border-b border-border/50 pb-2">
            <span className="flex items-center gap-1.5 font-semibold text-foreground">
              <CodeIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
              原始源代码 (Source Input)
            </span>
            <span>{code.split('\n').length} 行 ｜ {code.length} 字符</span>
          </div>
          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="flex-1 w-full p-2.5 font-mono text-xs bg-muted/20 border border-border/60 rounded-md focus:outline-none focus:ring-1 focus:ring-cyan-500 min-h-90 resize-y"
            placeholder="粘贴待压缩代码..."
          />
        </Card>

        {/* Right Column: Compressed Output */}
        <Card className="p-3 bg-card/60 border-border/70 flex flex-col gap-2">
          <div className="flex items-center justify-between text-xs font-mono text-muted-foreground border-b border-border/50 pb-2">
            <span className="flex items-center gap-1.5 font-semibold text-cyan-600 dark:text-cyan-400">
              <SparklesIcon className="size-3.5" />
              TokenShift 压缩代码 (AST-Protected)
            </span>
            <div className="flex items-center gap-2">
              {result && (
                <span>
                  {result.compressed_lines} 行 ｜ 保护节点: {result.protected_nodes_count}
                </span>
              )}
              <Button
                variant="outline"
                size="sm"
                className="h-6 text-xs font-mono px-2 border-border/70"
                onClick={handleCopy}
                disabled={!result?.compressed_code}
              >
                <CopyIcon className="size-3 mr-1" />
                {copied ? '已复制' : '复制结果'}
              </Button>
            </div>
          </div>
          <textarea
            readOnly
            value={result?.compressed_code || ''}
            className="flex-1 w-full p-2.5 font-mono text-xs bg-muted/10 border border-border/60 rounded-md focus:outline-none text-foreground min-h-90 resize-y"
            placeholder="执行压缩后将在此高密呈现语法树保护代码..."
          />
        </Card>
      </div>
    </div>
  )
}
