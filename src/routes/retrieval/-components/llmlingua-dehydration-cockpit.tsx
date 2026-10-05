import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ActivityIcon,
  CheckCircleIcon,
  CopyIcon,
  FileCheckIcon,
  PlayIcon,
  RefreshCwIcon,
  SaveIcon,
  ScissorsIcon,
  ShieldCheckIcon,
  SparklesIcon,
} from 'lucide-react'
import { Button } from '#/components/ui/button'
import { ovClient } from '#/lib/ov-client'
import { WikiDocumentPicker } from './wiki-document-picker'
import { KpiTile } from './llmlingua-kpi-tile'
import type { ApplyResult, DehydrationResult, DehydrationStats } from './llmlingua-types'
import { PRESET_SAMPLES } from './llmlingua-types'

export function LLMLinguaDehydrationCockpit() {
  const { t } = useTranslation('retrieval')
  const queryClient = useQueryClient()
  const [inputText, setInputText] = useState(PRESET_SAMPLES.spec.content)
  const [selectedUri, setSelectedUri] = useState<string>(PRESET_SAMPLES.spec.uri)
  const [selectedName, setSelectedName] = useState<string>(PRESET_SAMPLES.spec.title)
  const [targetRate, setTargetRate] = useState<number>(0.50)
  const [preserveStructure, setPreserveStructure] = useState<boolean>(true)
  const [copied, setCopied] = useState<boolean>(false)

  // 1. Fetch Aggregated Observability Telemetry
  const { data: telemetry } = useQuery<DehydrationStats>({
    queryKey: ['wiki-dehydrate-stats'],
    queryFn: async () => {
      const res = await ovClient.instance.get('/api/v1/wiki/dehydrate/stats')
      return (res as { data: DehydrationStats }).data
    },
    refetchInterval: 10000,
  })

  // 2. Dehydrate Mutation
  const dehydrateMutation = useMutation<DehydrationResult, Error, void>({
    mutationFn: async () => {
      const res = await ovClient.instance.post('/api/v1/wiki/dehydrate', {
        content: inputText,
        rate: targetRate,
        threshold: 0.35,
        preserve_structure: preserveStructure,
      })
      return (res as { data: DehydrationResult }).data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wiki-dehydrate-stats'] })
      applyMutation.reset()
    },
  })

  // 3. Physical Persistence Apply Mutation (Card-101)
  const applyMutation = useMutation<ApplyResult, Error, { mode: 'mirror' | 'in_place' }>({
    mutationFn: async ({ mode }) => {
      const res = await ovClient.instance.post('/api/v1/wiki/dehydrate/apply', {
        uri: selectedUri,
        dehydrated_content: dehydrateMutation.data?.dehydrated_content || '',
        mode,
        operator: 'wiki_cockpit',
      })
      return (res as { data: { status: string; data: ApplyResult } }).data.data
    },
  })

  const result = dehydrateMutation.data

  const handleCopy = () => {
    if (!result?.dehydrated_content) return
    void navigator.clipboard.writeText(result.dehydrated_content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleSelectRealDoc = async (uri: string, name: string) => {
    try {
      const res = await ovClient.instance.get(`/api/v1/wiki/dehydrate/document?uri=${encodeURIComponent(uri)}`)
      const content = (res as { data: { content: string } }).data.content
      setInputText(content)
      setSelectedUri(uri)
      setSelectedName(name)
      applyMutation.reset()
    } catch (err) {
      console.error('Failed to load wiki doc', err)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {/* 4 大核心遥测 KPI 瓦片 */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <KpiTile
          icon={ScissorsIcon}
          label={t('llmlingua.cumulativeSavedTokens', '累计节省 Token')}
          value={telemetry ? `${telemetry.total_tokens_saved.toLocaleString()} tok` : '--'}
          sub={`累计 ${telemetry?.total_documents ?? 0} 次文档脱水`}
          accent
        />
        <KpiTile
          icon={SparklesIcon}
          label={t('llmlingua.avgDehydrationRatio', '平均抽稀比率')}
          value={telemetry ? `${telemetry.avg_compression_ratio.toFixed(1)}%` : '--'}
          sub="目标基准 50% (rate=0.50)"
          accent
        />
        <KpiTile
          icon={ShieldCheckIcon}
          label={t('llmlingua.structuralFidelity', '结构保真度')}
          value={result ? `${result.structural_fidelity.toFixed(1)}%` : '100.0%'}
          sub="YAML & 代码块物理冻结"
          accent
        />
        <KpiTile
          icon={ActivityIcon}
          label={t('llmlingua.activeEngine', '生效引擎')}
          value={result?.engine_used || (telemetry?.is_model_loaded ? 'LLMLingua-2' : '规则语法脱水器')}
          sub={`平均耗时 ${telemetry ? `${telemetry.avg_latency_ms.toFixed(1)}ms` : '--'}`}
        />
      </div>

      {/* 预置样本与全域知识库文档拾取栏 */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border/70 bg-card px-3 py-2 shadow-xs">
        <div className="flex flex-wrap items-center gap-2">
          <WikiDocumentPicker onSelect={handleSelectRealDoc} currentUri={selectedUri} />
          <span className="text-xs text-muted-foreground">|</span>
          <span className="text-xs font-semibold text-foreground">快速预设:</span>
          <Button
            size="sm"
            variant="outline"
            className="h-6 text-xs px-2"
            onClick={() => {
              setInputText(PRESET_SAMPLES.spec.content)
              setSelectedUri(PRESET_SAMPLES.spec.uri)
              setSelectedName(PRESET_SAMPLES.spec.title)
              applyMutation.reset()
            }}
          >
            {PRESET_SAMPLES.spec.title}
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="h-6 text-xs px-2"
            onClick={() => {
              setInputText(PRESET_SAMPLES.whitepaper.content)
              setSelectedUri(PRESET_SAMPLES.whitepaper.uri)
              setSelectedName(PRESET_SAMPLES.whitepaper.title)
              applyMutation.reset()
            }}
          >
            {PRESET_SAMPLES.whitepaper.title}
          </Button>
          <span className="rounded bg-muted/60 px-2 py-0.5 text-xs font-mono text-cyan-600 dark:text-cyan-400 border border-border/60 max-w-65 truncate">
            {selectedName}
          </span>
        </div>
        <label className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer">
          <input
            type="checkbox"
            checked={preserveStructure}
            onChange={(e) => setPreserveStructure(e.target.checked)}
            className="rounded border-input text-cyan-600 focus:ring-cyan-500"
          />
          {t('llmlingua.freezeStructure', '物理冻结 YAML 头部 & 代码块')}
        </label>
      </div>

      {/* 交互实验台双栏 (原始 vs 脱水成果) */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* 左栏：原始文档输入 */}
        <div className="flex flex-col gap-2 rounded-md border border-border/70 bg-card p-3 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-foreground">
              {t('llmlingua.originalDoc', '原始 Markdown / Wiki 文档')}
            </span>
            <span className="text-xs font-mono text-muted-foreground">
              {inputText.length} {t('llmlingua.charCount', '字符')}
            </span>
          </div>
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            rows={13}
            className="w-full rounded-md border border-input bg-background p-2.5 font-mono text-xs text-foreground placeholder:text-muted-foreground focus:border-cyan-500 focus:outline-none resize-none"
            placeholder={t('llmlingua.placeholderInput', '请输入或粘贴待脱水长篇自然语言文档...')}
          />
          <div className="flex items-center justify-between pt-1">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span>{t('llmlingua.targetDehydrationRate', '目标压缩率')}</span>
              {[0.30, 0.50, 0.70].map((rate) => (
                <button
                  key={rate}
                  type="button"
                  onClick={() => setTargetRate(rate)}
                  className={`rounded px-1.5 py-0.5 font-mono text-xs cursor-pointer transition-colors ${
                    targetRate === rate
                      ? 'bg-cyan-50 dark:bg-cyan-950/60 text-cyan-800 dark:text-cyan-300 border border-cyan-300 dark:border-cyan-700 font-semibold'
                      : 'bg-muted/60 text-muted-foreground hover:text-foreground border border-border'
                  }`}
                >
                  {(rate * 100).toFixed(0)}%
                </button>
              ))}
            </div>
            <Button
              size="sm"
              className="h-8 px-3 text-xs bg-cyan-600 hover:bg-cyan-700 text-white font-medium cursor-pointer"
              disabled={dehydrateMutation.isPending || !inputText.trim()}
              onClick={() => dehydrateMutation.mutate()}
            >
              {dehydrateMutation.isPending ? (
                <RefreshCwIcon className="size-3.5 animate-spin mr-1.5" />
              ) : (
                <PlayIcon className="size-3.5 mr-1.5" />
              )}
              {t('llmlingua.executeDehydration', '执行智能脱水')}
            </Button>
          </div>
        </div>

        {/* 右栏：脱水成果展示与物理落盘闭环 */}
        <div className="flex flex-col gap-2 rounded-md border border-border/70 bg-card p-3 shadow-xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-foreground">
                {t('llmlingua.dehydratedResult', '脱水纯净成果')}
              </span>
              {result && (
                <span className="rounded bg-cyan-50 dark:bg-cyan-950/80 px-1.5 py-0.5 text-xs font-mono font-medium text-cyan-800 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-800/60">
                  节省 {result.tokens_saved} tok ({result.compression_ratio.toFixed(1)}%)
                </span>
              )}
            </div>
            {result && (
              <Button
                size="sm"
                variant="ghost"
                className="h-6 px-2 text-xs text-muted-foreground hover:text-foreground"
                onClick={handleCopy}
              >
                <CopyIcon className="size-3 mr-1" />
                {copied ? t('llmlingua.copied', '已复制') : t('llmlingua.copyResult', '复制结果')}
              </Button>
            )}
          </div>
          <div className="relative h-56 w-full overflow-y-auto rounded-md border border-border/60 bg-muted/20 p-2.5 font-mono text-xs text-foreground">
            {result ? (
              <pre className="whitespace-pre-wrap font-mono leading-relaxed">
                {result.dehydrated_content}
              </pre>
            ) : (
              <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
                {t('llmlingua.placeholderHint', '点击左下方“执行智能脱水”查看抽稀降噪成果')}
              </div>
            )}
          </div>

          {result && (
            <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-border/60">
              <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono">
                <span>冻结: {result.frozen_blocks_count}处</span>
                <span>保真: {result.structural_fidelity.toFixed(1)}%</span>
                <span className="text-cyan-600 dark:text-cyan-400">{result.latency_ms.toFixed(1)}ms</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={applyMutation.isPending || !selectedUri}
                  onClick={() => applyMutation.mutate({ mode: 'mirror' })}
                  className="h-7 text-xs border-cyan-500/40 text-cyan-600 dark:text-cyan-400 hover:bg-cyan-500/10 cursor-pointer"
                >
                  {applyMutation.isPending ? <RefreshCwIcon className="size-3 animate-spin mr-1" /> : <SaveIcon className="size-3 mr-1" />}
                  发布为脱水镜像 (.dehydrated.md)
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={applyMutation.isPending || !selectedUri}
                  onClick={() => applyMutation.mutate({ mode: 'in_place' })}
                  className="h-7 text-xs border-amber-500/40 text-amber-600 dark:text-amber-400 hover:bg-amber-500/10 cursor-pointer"
                >
                  {applyMutation.isPending ? <RefreshCwIcon className="size-3 animate-spin mr-1" /> : <FileCheckIcon className="size-3 mr-1" />}
                  原地安全覆写
                </Button>
              </div>
            </div>
          )}

          {applyMutation.data && (
            <div className="rounded-md border border-cyan-500/30 bg-cyan-50/40 dark:bg-cyan-950/20 p-2.5 text-xs font-mono space-y-1">
              <div className="flex items-center gap-1.5 text-cyan-700 dark:text-cyan-300 font-semibold">
                <CheckCircleIcon className="size-3.5 text-cyan-500" />
                <span>物理落盘成功 ({applyMutation.data.mode === 'mirror' ? '镜像模式' : '原地覆写'})</span>
                <span className="ml-auto text-muted-foreground tabular-nums">节省 {applyMutation.data.saved_chars} 字符</span>
              </div>
              <div className="text-muted-foreground truncate">目标: {applyMutation.data.target_path}</div>
              <div className="text-muted-foreground truncate">快照: {applyMutation.data.snapshot_path}</div>
              <div className="text-muted-foreground truncate">证据: {applyMutation.data.provenance_event_id}</div>
            </div>
          )}

          {applyMutation.error && (
            <div className="rounded-md border border-rose-500/40 bg-rose-50/50 dark:bg-rose-950/20 p-2 text-xs font-mono text-rose-600 dark:text-rose-400">
              落盘受阻: {applyMutation.error.message}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
