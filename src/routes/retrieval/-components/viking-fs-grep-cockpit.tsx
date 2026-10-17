import * as React from 'react'
import { useMutation } from '@tanstack/react-query'
import { Card } from '#/components/ui/card'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { ovClient } from '#/lib/ov-client'
import {
  SearchCodeIcon,
  SearchIcon,
  SparklesIcon,
  CopyIcon,
  CheckIcon,
  FileTextIcon,
  ZapIcon,
  SlidersHorizontalIcon,
} from 'lucide-react'

export interface GrepMatch {
  line: number
  uri: string
  content: string
  before_context?: string[]
  after_context?: string[]
}

export interface GrepResult {
  matches: GrepMatch[]
  count: number
  match_count: number
  files_scanned: number
}

const PRESET_PATTERNS = [
  { label: 'TODO / FIXME 标记', pattern: 'TODO|FIXME' },
  { label: '类定义 (class)', pattern: 'class\\s+\\w+' },
  { label: '函数定义 (def)', pattern: 'def\\s+\\w+' },
  { label: 'SSOT / 契约标记', pattern: 'SSOT|AHE|NO GREEN' },
  { label: 'HTTP URL 链接', pattern: 'https?://[^\\s"\'>]+' },
]

export function VikingFSGrepCockpit() {
  const [uri, setUri] = React.useState('viking://')
  const [pattern, setPattern] = React.useState('SSOT')
  const [caseInsensitive, setCaseInsensitive] = React.useState(false)
  const [beforeContext, setBeforeContext] = React.useState<number>(1)
  const [afterContext, setAfterContext] = React.useState<number>(1)
  const [grepData, setGrepData] = React.useState<GrepResult | null>(null)
  const [elapsedMs, setElapsedMs] = React.useState<number | null>(null)
  const [copiedIndex, setCopiedIndex] = React.useState<number | null>(null)

  const grepMutation = useMutation({
    mutationFn: async (payload: {
      uri: string
      pattern: string
      case_insensitive: boolean
      before_context: number
      after_context: number
    }) => {
      const start = performance.now()
      const res = await ovClient.instance.post<any>('/api/v1/search/grep', {
        uri: payload.uri,
        pattern: payload.pattern,
        case_insensitive: payload.case_insensitive,
        before_context: payload.before_context,
        after_context: payload.after_context,
        node_limit: 100,
      })
      const dur = Math.round(performance.now() - start)
      setElapsedMs(dur)
      return (res.data?.result ?? res.data) as GrepResult
    },
    onSuccess: (data) => {
      setGrepData(data)
    },
  })

  const handleExecuteGrep = (overridePattern?: string) => {
    const pat = (overridePattern !== undefined ? overridePattern : pattern).trim()
    if (!pat) return
    grepMutation.mutate({
      uri: uri.trim() || 'viking://',
      pattern: pat,
      case_insensitive: caseInsensitive,
      before_context: beforeContext,
      after_context: afterContext,
    })
  }

  const handleCopy = (text: string, idx: number) => {
    void navigator.clipboard.writeText(text)
    setCopiedIndex(idx)
    setTimeout(() => setCopiedIndex(null), 1500)
  }

  const matches = grepData?.matches ?? []
  const matchCount = grepData?.match_count ?? grepData?.count ?? 0
  const filesScanned = grepData?.files_scanned ?? 0

  return (
    <Card className="flex flex-col gap-3 p-3.5 border-border/60 bg-card/60 shadow-none">
      {/* 1. Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex size-6 items-center justify-center rounded-md bg-cyan-50 text-cyan-700 border border-cyan-200 dark:bg-cyan-500/10 dark:text-cyan-400 dark:border-transparent">
            <SearchCodeIcon className="size-3.5" />
          </div>
          <div>
            <h3 className="text-xs font-semibold text-foreground">
              VikingFS 多文件正则 Grep 检索
            </h3>
            <p className="text-xs text-muted-foreground">
              基于 VikingFS 原生高速正则扫描算子，支持路径通配、多行上下文与毫秒级即时检索
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <Badge
            variant="outline"
            className="text-xs font-mono border-cyan-800/30 text-cyan-600 dark:text-cyan-400 bg-cyan-950/20"
          >
            <ZapIcon className="size-3 mr-1" />
            Fast Grep Engine
          </Badge>
          {elapsedMs !== null && (
            <Badge
              variant="outline"
              className="text-xs font-mono border-border/60 text-muted-foreground"
            >
              {elapsedMs} ms
            </Badge>
          )}
        </div>
      </div>

      {/* 2. Controls & Filter Bar */}
      <div className="flex flex-col gap-2 rounded-lg border border-border/60 bg-muted/20 p-2.5">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-2 items-center">
          <div className="md:col-span-4 flex items-center gap-1.5">
            <span className="text-xs font-medium text-muted-foreground whitespace-nowrap">
              范围 URI:
            </span>
            <Input
              value={uri}
              onChange={(e) => setUri(e.target.value)}
              placeholder="viking://resources"
              className="h-7 text-xs font-mono"
            />
          </div>

          <div className="md:col-span-5 flex items-center gap-1.5">
            <span className="text-xs font-medium text-muted-foreground whitespace-nowrap">
              正则:
            </span>
            <Input
              value={pattern}
              onChange={(e) => setPattern(e.target.value)}
              placeholder="正则表达式或关键字..."
              className="h-7 text-xs font-mono"
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleExecuteGrep()
              }}
            />
          </div>

          <div className="md:col-span-3 flex items-center justify-end gap-2">
            <Button
              size="sm"
              onClick={() => handleExecuteGrep()}
              disabled={grepMutation.isPending || !pattern.trim()}
              className="h-7 px-3 text-xs bg-cyan-600 hover:bg-cyan-700 text-white cursor-pointer"
            >
              <SearchIcon className="size-3 mr-1" />
              {grepMutation.isPending ? '检索中...' : '开始 Grep'}
            </Button>
          </div>
        </div>

        {/* Options & Context line sliders */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-border/40 text-xs">
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-1.5 cursor-pointer select-none text-muted-foreground hover:text-foreground">
              <input
                type="checkbox"
                checked={caseInsensitive}
                onChange={(e) => setCaseInsensitive(e.target.checked)}
                className="size-3.5 rounded border-border text-cyan-600 focus:ring-0"
              />
              <span>忽略大小写 (-i)</span>
            </label>

            <div className="flex items-center gap-1.5 text-muted-foreground">
              <SlidersHorizontalIcon className="size-3" />
              <span>前置上下文:</span>
              <select
                value={beforeContext}
                onChange={(e) => setBeforeContext(Number(e.target.value))}
                className="h-6 rounded border border-border/60 bg-background px-1.5 text-xs font-mono"
              >
                <option value={0}>0 行</option>
                <option value={1}>1 行</option>
                <option value={2}>2 行</option>
                <option value={3}>3 行</option>
                <option value={5}>5 行</option>
              </select>
            </div>

            <div className="flex items-center gap-1.5 text-muted-foreground">
              <span>后置上下文:</span>
              <select
                value={afterContext}
                onChange={(e) => setAfterContext(Number(e.target.value))}
                className="h-6 rounded border border-border/60 bg-background px-1.5 text-xs font-mono"
              >
                <option value={0}>0 行</option>
                <option value={1}>1 行</option>
                <option value={2}>2 行</option>
                <option value={3}>3 行</option>
                <option value={5}>5 行</option>
              </select>
            </div>
          </div>

          {/* Quick preset chips */}
          <div className="flex flex-wrap items-center gap-1">
            <span className="text-muted-foreground text-xs">预设:</span>
            {PRESET_PATTERNS.map((p) => (
              <button
                key={p.pattern}
                type="button"
                onClick={() => {
                  setPattern(p.pattern)
                  handleExecuteGrep(p.pattern)
                }}
                className="flex items-center gap-1 rounded border border-border/60 bg-background px-1.5 py-0.5 text-xs text-muted-foreground hover:text-cyan-600 dark:hover:text-cyan-400 transition-colors cursor-pointer"
              >
                <SparklesIcon className="size-2.5" />
                {p.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 3. Results Section */}
      <div className="flex flex-col gap-2">
        {grepMutation.isPending && (
          <div className="flex items-center justify-center p-8 rounded-lg border border-border/60 bg-muted/10 text-xs text-muted-foreground">
            <SearchIcon className="size-4 animate-spin mr-2 text-cyan-600 dark:text-cyan-400" />
            正在执行 VikingFS 递归正则扫描...
          </div>
        )}

        {grepMutation.isError && (
          <div className="p-3 rounded-md border border-rose-800/30 bg-rose-950/20 text-rose-400 text-xs">
            检索失败: {grepMutation.error.message || '网络或服务端异常'}
          </div>
        )}

        {!grepMutation.isPending && grepData && (
          <div className="flex items-center justify-between px-1 text-xs text-muted-foreground">
            <div>
              共命中{' '}
              <span className="font-mono font-semibold text-cyan-600 dark:text-cyan-400">
                {matchCount}
              </span>{' '}
              处结果，扫描{' '}
              <span className="font-mono font-semibold text-foreground">
                {filesScanned}
              </span>{' '}
              个文件
            </div>
            {elapsedMs !== null && (
              <div className="font-mono">耗时: {elapsedMs}ms</div>
            )}
          </div>
        )}

        {!grepMutation.isPending && grepData && matches.length === 0 && (
          <div className="p-6 text-center text-xs text-muted-foreground border border-border/40 rounded-lg bg-muted/5">
            未检索到匹配结果，请调整路径 URI 或正则表达式模式重试
          </div>
        )}

        {/* Matches list */}
        <div className="flex flex-col gap-2 max-h-125 overflow-y-auto pr-1">
          {matches.map((m, idx) => (
            <div
              key={`${m.uri}-${m.line}-${idx}`}
              className="flex flex-col rounded-md border border-border/60 bg-card overflow-hidden text-xs"
            >
              {/* File URI & Line Header */}
              <div className="flex items-center justify-between px-2.5 py-1.5 bg-muted/40 border-b border-border/40">
                <div className="flex items-center gap-1.5 min-w-0">
                  <FileTextIcon className="size-3 text-muted-foreground shrink-0" />
                  <span className="font-mono font-medium text-foreground truncate max-w-105">
                    {m.uri}
                  </span>
                  <Badge
                    variant="outline"
                    className="font-mono text-xs px-1.5 py-0 border-cyan-800/30 text-cyan-600 dark:text-cyan-400 bg-cyan-950/20"
                  >
                    L{m.line}
                  </Badge>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleCopy(m.content, idx)}
                  className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground cursor-pointer"
                >
                  {copiedIndex === idx ? (
                    <CheckIcon className="size-3 text-cyan-500" />
                  ) : (
                    <CopyIcon className="size-3" />
                  )}
                  <span className="ml-1">复制</span>
                </Button>
              </div>

              {/* Code Snippet with Before / Match / After lines */}
              <div className="p-2 font-mono text-xs bg-muted/10 overflow-x-auto leading-relaxed">
                {m.before_context?.map((bl, bIdx) => (
                  <div key={bIdx} className="text-muted-foreground/60 flex">
                    <span className="w-8 shrink-0 select-none text-right pr-2 text-muted-foreground/40">
                      {m.line - (m.before_context?.length ?? 0) + bIdx}
                    </span>
                    <span className="whitespace-pre">{bl}</span>
                  </div>
                ))}

                <div className="flex bg-cyan-950/30 text-cyan-200 font-semibold px-1 -mx-1 rounded-sm border-l-2 border-cyan-500">
                  <span className="w-8 shrink-0 select-none text-right pr-2 text-cyan-400">
                    {m.line}
                  </span>
                  <span className="whitespace-pre">{m.content}</span>
                </div>

                {m.after_context?.map((al, aIdx) => (
                  <div key={aIdx} className="text-muted-foreground/60 flex">
                    <span className="w-8 shrink-0 select-none text-right pr-2 text-muted-foreground/40">
                      {m.line + 1 + aIdx}
                    </span>
                    <span className="whitespace-pre">{al}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  )
}
