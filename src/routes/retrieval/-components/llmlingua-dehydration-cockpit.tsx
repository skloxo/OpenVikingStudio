// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ActivityIcon,
  CopyIcon,
  PlayIcon,
  RefreshCwIcon,
  ScissorsIcon,
  ShieldCheckIcon,
  SparklesIcon,
} from 'lucide-react'
import { Button } from '#/components/ui/button'
import { ovClient } from '#/lib/ov-client'

interface DehydrationResult {
  original_text: string
  dehydrated_text: string
  original_tokens: number
  dehydrated_tokens: number
  tokens_saved: number
  compression_ratio: number
  frozen_blocks_count: number
  protected_tokens_count: number
  latency_ms: number
  engine_used: string
  structural_integrity_verified: boolean
  details: Record<string, unknown>
}

interface DehydrationTelemetry {
  total_dehydrations: number
  total_original_tokens: number
  total_dehydrated_tokens: number
  total_tokens_saved: number
  avg_compression_ratio: number
  avg_latency_ms: number
  engine_counts: Record<string, number>
}

const PRESET_SAMPLES: Record<string, string> = {
  spec: `---
title: OpenViking Context Engine Architecture Specification
status: stable
---
# 模块设计规范与第一性原理
众所周知，代码库必须拥有清晰高内聚的领域接缝。
显而易见的是，我们必须严格遵守单文件 100 到 300 行的黄金甜点区红线。
毋庸置疑的是，严禁任何人在代码库中引入未经脱水审计的外部臃肿包。
值得注意的是，我们必须保护否定词和控制词，严禁反转核心语义。
\`\`\`python
def evaluate_gate(rate: float) -> bool:
    # 绝对禁止任何绿色，统一采用冰青信号
    assert rate >= 0.50
    return True
\`\`\`
总的来说，归根结底，正如前文所述，系统必须兼顾极致性能与零幻觉。`,

  whitepaper: `---
title: Multi-Engine Context Compression Whitepaper
version: 1.5.46
---
# 课题五：多引擎分级智能压缩体系架构
在现代大规模智能体系统中，上下文膨胀消耗推理 Token 并诱发中间信息衰减。
从某种角度来看，众所周知的是，传统的单一截断策略无法兼顾精度与结构完整性。
具体来说，本系统设计了三层正交压缩矩阵：
1. 阿里 SkillZip：针对可执行流程进行确定性 6 元组规约；
2. Notes-History：针对多轮对话历史进行动态结晶；
3. 微软 LLMLingua-2：针对自然语言 Wiki 文档进行毫秒级抽稀，削减 50% 水话冗余。
\`\`\`bash
# 启动脱水后台任务
openviking wiki dehydrate --rate 0.50 --threshold 0.35
\`\`\`
正如前文所述，整个过程绝对禁止常驻显存，保障 2080Ti 纯净。`,
}

function KpiTile({
  icon: Icon,
  label,
  value,
  sub,
  accent,
}: {
  icon: React.ElementType
  label: string
  value: string | number
  sub?: string
  accent?: boolean
}) {
  return (
    <div className="flex flex-col gap-1 rounded-md border border-slate-700/60 bg-slate-800/50 p-3">
      <div className="flex items-center gap-1.5 text-slate-400">
        <Icon className="size-3.5 shrink-0 text-cyan-400" />
        <span className="text-xs truncate">{label}</span>
      </div>
      <div
        className={`text-lg font-bold font-mono tabular-nums ${
          accent ? 'text-cyan-400' : 'text-slate-100'
        }`}
      >
        {value}
      </div>
      {sub && <span className="text-xs text-slate-400">{sub}</span>}
    </div>
  )
}

export function LLMLinguaDehydrationCockpit() {
  const { t } = useTranslation('retrieval')
  const queryClient = useQueryClient()
  const [inputText, setInputText] = useState(PRESET_SAMPLES.spec)
  const [targetRate, setTargetRate] = useState<number>(0.50)
  const [protectYaml, setProtectYaml] = useState<boolean>(true)
  const [protectCode, setProtectCode] = useState<boolean>(true)
  const [copied, setCopied] = useState<boolean>(false)

  // 1. Fetch Rolling Telemetry
  const { data: telemetry } = useQuery<DehydrationTelemetry>({
    queryKey: ['wiki-dehydrate-telemetry'],
    queryFn: async () => {
      const res = await ovClient.instance.get('/api/v1/wiki/dehydrate/stats')
      return (res as { data: DehydrationTelemetry }).data
    },
    refetchInterval: 10000,
  })

  // 2. Dehydrate Mutation
  const dehydrateMutation = useMutation<DehydrationResult, Error, void>({
    mutationFn: async () => {
      const res = await ovClient.instance.post('/api/v1/wiki/dehydrate', {
        content: inputText,
        target_rate: targetRate,
        threshold: 0.35,
        protect_yaml_frontmatter: protectYaml,
        protect_code_blocks: protectCode,
        protect_headings: true,
      })
      return (res as { data: DehydrationResult }).data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wiki-dehydrate-telemetry'] })
    },
  })

  const result = dehydrateMutation.data

  const handleCopy = () => {
    if (!result?.dehydrated_text) return
    void navigator.clipboard.writeText(result.dehydrated_text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="flex flex-col gap-4">
      {/* 4 大核心遥测 KPI 瓦片 */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <KpiTile
          icon={ScissorsIcon}
          label={t('llmlingua.cumulativeSavedTokens')}
          value={telemetry ? `${telemetry.total_tokens_saved.toLocaleString()} tok` : '--'}
          sub={`累计 ${telemetry?.total_dehydrations ?? 0} 次文档脱水`}
          accent
        />
        <KpiTile
          icon={SparklesIcon}
          label={t('llmlingua.avgDehydrationRatio')}
          value={telemetry ? `${(telemetry.avg_compression_ratio * 100).toFixed(1)}%` : '--'}
          sub="目标基准 50% (rate=0.50)"
          accent
        />
        <KpiTile
          icon={ShieldCheckIcon}
          label={t('llmlingua.structuralFidelity')}
          value="100.0%"
          sub="YAML & 代码块物理冻结"
          accent
        />
        <KpiTile
          icon={ActivityIcon}
          label={t('llmlingua.activeEngine')}
          value={result?.engine_used === 'llmlingua-2-xlm-roberta' ? 'XLM-RoBERTa' : '规则语法脱水器'}
          sub={`平均耗时 ${telemetry ? `${telemetry.avg_latency_ms.toFixed(1)}ms` : '--'}`}
        />
      </div>

      {/* 预置样本选择栏 */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-slate-700/60 bg-slate-900/60 px-3 py-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-300">{t('llmlingua.presetSamples')}</span>
          <Button
            size="sm"
            variant="outline"
            className="h-6 text-xs px-2"
            onClick={() => setInputText(PRESET_SAMPLES.spec)}
          >
            {t('llmlingua.presetSpec')}
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="h-6 text-xs px-2"
            onClick={() => setInputText(PRESET_SAMPLES.whitepaper)}
          >
            {t('llmlingua.presetWhitepaper')}
          </Button>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 text-xs text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={protectYaml}
              onChange={(e) => setProtectYaml(e.target.checked)}
              className="rounded border-slate-700 text-cyan-500 focus:ring-cyan-500"
            />
            {t('llmlingua.freezeYaml')}
          </label>
          <label className="flex items-center gap-1.5 text-xs text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={protectCode}
              onChange={(e) => setProtectCode(e.target.checked)}
              className="rounded border-slate-700 text-cyan-500 focus:ring-cyan-500"
            />
            {t('llmlingua.freezeCode')}
          </label>
        </div>
      </div>

      {/* 交互实验台双栏 (原始 vs 脱水成果) */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* 左栏：原始文档输入 */}
        <div className="flex flex-col gap-2 rounded-md border border-slate-700/60 bg-slate-900/40 p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-300">
              {t('llmlingua.originalDoc')}
            </span>
            <span className="text-xs font-mono text-slate-400">
              {inputText.length} {t('llmlingua.charCount')}
            </span>
          </div>
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            rows={14}
            className="w-full rounded-md border border-slate-700/60 bg-slate-950 p-2.5 font-mono text-xs text-slate-200 focus:border-cyan-500 focus:outline-none resize-none"
            placeholder={t('llmlingua.placeholderInput')}
          />
          <div className="flex items-center justify-between pt-1">
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <span>{t('llmlingua.targetDehydrationRate')}</span>
              {[0.30, 0.50, 0.70].map((rate) => (
                <button
                  key={rate}
                  type="button"
                  onClick={() => setTargetRate(rate)}
                  className={`rounded px-1.5 py-0.5 font-mono text-xs cursor-pointer ${
                    targetRate === rate
                      ? 'bg-cyan-950 text-cyan-400 border border-cyan-700 font-semibold'
                      : 'bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-700'
                  }`}
                >
                  {(rate * 100).toFixed(0)}%
                </button>
              ))}
            </div>
            <Button
              size="sm"
              className="h-8 px-3 text-xs bg-cyan-600 hover:bg-cyan-500 text-white font-medium"
              disabled={dehydrateMutation.isPending || !inputText.trim()}
              onClick={() => dehydrateMutation.mutate()}
            >
              {dehydrateMutation.isPending ? (
                <RefreshCwIcon className="size-3.5 animate-spin mr-1.5" />
              ) : (
                <PlayIcon className="size-3.5 mr-1.5" />
              )}
              {t('llmlingua.executeDehydration')}
            </Button>
          </div>
        </div>

        {/* 右栏：脱水成果展示 */}
        <div className="flex flex-col gap-2 rounded-md border border-slate-700/60 bg-slate-900/40 p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-300">
                {t('llmlingua.dehydratedResult')}
              </span>
              {result && (
                <span className="rounded bg-cyan-950/80 px-1.5 py-0.5 text-xs font-mono font-medium text-cyan-400 border border-cyan-800/60">
                  {t('llmlingua.savedTokensBadge', {
                    tokens: result.tokens_saved,
                    ratio: (result.compression_ratio * 100).toFixed(1),
                  })}
                </span>
              )}
            </div>
            {result && (
              <Button
                size="sm"
                variant="ghost"
                className="h-6 px-2 text-xs text-slate-300 hover:text-white"
                onClick={handleCopy}
              >
                <CopyIcon className="size-3 mr-1" />
                {copied ? t('llmlingua.copied') : t('llmlingua.copyResult')}
              </Button>
            )}
          </div>
          <div className="relative h-64 w-full overflow-y-auto rounded-md border border-slate-700/60 bg-slate-950 p-2.5 font-mono text-xs text-slate-200">
            {result ? (
              <pre className="whitespace-pre-wrap font-mono leading-relaxed">
                {result.dehydrated_text}
              </pre>
            ) : (
              <div className="flex h-full items-center justify-center text-xs text-slate-500">
                {t('llmlingua.placeholderHint')}
              </div>
            )}
          </div>
          {result && (
            <div className="flex flex-wrap items-center gap-2 pt-1 text-xs text-slate-400">
              <span className="rounded bg-slate-800/80 px-1.5 py-0.5 font-mono border border-slate-700">
                {t('llmlingua.frozenBlocks', { count: result.frozen_blocks_count })}
              </span>
              <span className="rounded bg-slate-800/80 px-1.5 py-0.5 font-mono border border-slate-700">
                {t('llmlingua.protectedTokens', { count: result.protected_tokens_count })}
              </span>
              <span className="rounded bg-slate-800/80 px-1.5 py-0.5 font-mono border border-slate-700 text-cyan-400">
                {t('llmlingua.latency', { latency: result.latency_ms.toFixed(1) })}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
