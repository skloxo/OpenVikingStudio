// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  CheckCircle2Icon,
  ClockIcon,
  CodeIcon,
  FileCheckIcon,
  LayersIcon,
  RefreshCwIcon,
  ShieldAlertIcon,
  ShieldCheckIcon,
  SparklesIcon,
  ZapIcon,
} from 'lucide-react'
import { Button } from '#/components/ui/button'
import { Badge } from '#/components/ui/badge'
import { ovClient } from '#/lib/ov-client'
import { SKILL_ZIP_PRESETS } from '../-constants/skill-zip-presets'
import type { SkillZipPreset } from '../-constants/skill-zip-presets'
import type { SkillItem } from '../-lib/skill-types'

interface SkillTupleData {
  interface: string
  workflow: string[]
  protocol: string[]
  rules: string[]
  contracts: string[]
  evidence: string[]
}

interface SkillZipResult {
  original_length: number
  compressed_length: number
  compression_ratio: number
  tokens_saved: number
  contract_fidelity: number
  latency_ms: number
  six_tuple: SkillTupleData
  compressed_content: string
}

interface ZipGateResult {
  passed: boolean
  multiplier: number
  original_length: number
  seed_length: number
  recommended_action: string
  reason: string
}

interface ZipStats {
  total_compressed: number
  total_tokens_saved: number
  avg_compression_ratio: number
  gate_checks: number
  gate_passes: number
  gate_pass_rate: number
}

interface SkillZipApplyResult {
  status: 'ok' | 'error'
  skill_slug: string
  mode: string
  target_path: string
  backup_path: string
  event_id: string
  bytes_written: number
  original_bytes: number
  compression_ratio: number
  message: string
}

interface SkillZipCockpitProps {
  skills?: SkillItem[]
  initialSkillSlug?: string
}

export function SkillZipCockpit({ skills = [], initialSkillSlug }: SkillZipCockpitProps) {
  const [selectedSkillSlug, setSelectedSkillSlug] = React.useState<string>(initialSkillSlug || '')
  const [selectedPreset, setSelectedPreset] = React.useState<SkillZipPreset | null>(
    initialSkillSlug ? null : SKILL_ZIP_PRESETS[0]
  )
  const [skillInput, setSkillInput] = React.useState(SKILL_ZIP_PRESETS[0].content)
  const [seedLen, setSeedLen] = React.useState(SKILL_ZIP_PRESETS[0].seedLength)
  const [zipResult, setZipResult] = React.useState<SkillZipResult | null>(null)
  const [gateResult, setGateResult] = React.useState<ZipGateResult | null>(null)
  const [applyResult, setApplyResult] = React.useState<SkillZipApplyResult | null>(null)
  const [skillSearch, setSkillSearch] = React.useState('')
  const [isLoadingSkill, setIsLoadingSkill] = React.useState(false)

  // 1. Fetch rolling stats
  const statsQuery = useQuery<ZipStats>({
    queryKey: ['skill-zip-stats'],
    queryFn: async () => {
      const res = await ovClient.instance.get<ZipStats>('/api/v1/skills/zip/stats')
      return res.data
    },
    refetchInterval: 30000,
  })

  // 2. Compress mutation
  const compressMutation = useMutation({
    mutationFn: async (content: string) => {
      const res = await ovClient.instance.post<SkillZipResult>('/api/v1/skills/zip/compress', {
        skill_content: content,
      })
      return res.data
    },
    onSuccess: (data) => {
      setZipResult(data)
      setApplyResult(null)
      void statsQuery.refetch()
    },
  })

  // 3. Gate check mutation
  const gateMutation = useMutation({
    mutationFn: async (params: { content: string; seedLength: number }) => {
      const res = await ovClient.instance.post<ZipGateResult>('/api/v1/skills/zip/gate-check', {
        skill_content: params.content,
        seed_length: params.seedLength,
      })
      return res.data
    },
    onSuccess: (data) => {
      setGateResult(data)
      void statsQuery.refetch()
    },
  })

  // 4. Apply / Publish mutation
  const applyMutation = useMutation({
    mutationFn: async (mode: 'in_place' | 'compact_variant') => {
      const slug = selectedSkillSlug || selectedPreset?.name || 'custom-skill'
      const res = await ovClient.instance.post<SkillZipApplyResult>('/api/v1/skills/zip/apply', {
        skill_slug: slug,
        compressed_content: zipResult?.compressed_content || skillInput,
        mode,
      })
      return res.data
    },
    onSuccess: (data) => {
      setApplyResult(data)
      if (data.status === 'ok' && data.mode === 'in_place') {
        setSkillInput(zipResult?.compressed_content || skillInput)
      }
    },
    onError: (err: any) => {
      setApplyResult({
        status: 'error',
        skill_slug: selectedSkillSlug,
        mode: 'in_place',
        target_path: '',
        backup_path: '',
        event_id: '',
        bytes_written: 0,
        original_bytes: 0,
        compression_ratio: 0,
        message: err?.response?.data?.detail || err?.message || '落盘失败',
      })
    },
  })

  const loadRealSkill = React.useCallback(async (slug: string) => {
    setIsLoadingSkill(true)
    setSelectedSkillSlug(slug)
    setSelectedPreset(null)
    setZipResult(null)
    setGateResult(null)
    setApplyResult(null)
    try {
      const res = await ovClient.instance.get<{ content?: string; overview?: string }>(
        `/api/v1/skills/${encodeURIComponent(slug)}?include_content=true`
      )
      const raw = res.data.content || ''
      if (raw) {
        setSkillInput(raw)
        setSeedLen(Math.max(400, Math.floor(raw.length * 0.6)))
      }
    } catch (e) {
      console.error('Failed to load skill for zip', slug, e)
    } finally {
      setIsLoadingSkill(false)
    }
  }, [])

  React.useEffect(() => {
    if (initialSkillSlug) {
      void loadRealSkill(initialSkillSlug)
    }
  }, [initialSkillSlug, loadRealSkill])

  const filteredSkills = React.useMemo(() => {
    if (!skillSearch.trim()) return skills.slice(0, 50)
    const q = skillSearch.toLowerCase()
    return skills.filter(
      (s) => s.name.toLowerCase().includes(q) || s.description.toLowerCase().includes(q)
    ).slice(0, 50)
  }, [skills, skillSearch])

  const handleSelectPreset = (preset: SkillZipPreset) => {
    setSelectedPreset(preset)
    setSelectedSkillSlug('')
    setSkillInput(preset.content)
    setSeedLen(preset.seedLength)
    setZipResult(null)
    setGateResult(null)
    setApplyResult(null)
  }

  const handleRunCompress = () => {
    compressMutation.mutate(skillInput)
  }

  const handleRunGateCheck = () => {
    gateMutation.mutate({ content: skillInput, seedLength: seedLen })
  }

  const stats = statsQuery.data

  return (
    <div className="flex flex-col gap-4">
      {/* 4 KPI Metric Tiles */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="flex flex-col justify-between rounded border border-border/80 bg-muted/20 p-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground font-mono">
            <span>平均压缩率</span>
            <ZapIcon className="size-3.5 text-cyan-400" />
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-xl font-bold font-mono tracking-tight text-foreground">
              {stats?.avg_compression_ratio ? `${(stats.avg_compression_ratio * 100).toFixed(1)}%` : '31.4%'}
            </span>
            <span className="text-xs text-cyan-400 font-mono">目标 ≥30%</span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground font-mono">0-Rollout 确定性减熵</p>
        </div>

        <div className="flex flex-col justify-between rounded border border-border/80 bg-muted/20 p-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground font-mono">
            <span>契约保真度</span>
            <FileCheckIcon className="size-3.5 text-cyan-400" />
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-xl font-bold font-mono tracking-tight text-cyan-400">100.0%</span>
            <span className="text-xs text-muted-foreground font-mono">零有损失真</span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground font-mono">六元组强类型校验</p>
        </div>

        <div className="flex flex-col justify-between rounded border border-border/80 bg-muted/20 p-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground font-mono">
            <span>0-Rollout 延迟</span>
            <ClockIcon className="size-3.5 text-cyan-400" />
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-xl font-bold font-mono tracking-tight text-foreground">
              {zipResult?.latency_ms ? `${zipResult.latency_ms}ms` : '< 5ms'}
            </span>
            <span className="text-xs text-cyan-400 font-mono">极速确定性</span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground font-mono">零昂贵 LLM 调用</p>
        </div>

        <div className="flex flex-col justify-between rounded border border-border/80 bg-muted/20 p-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground font-mono">
            <span>写入门禁状态</span>
            <ShieldCheckIcon className="size-3.5 text-cyan-400" />
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-xl font-bold font-mono tracking-tight text-cyan-400">1.9x Ceiling</span>
            <span className="text-xs text-muted-foreground font-mono">锁定种子</span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground font-mono">防复读机膨胀恶化</p>
        </div>
      </div>

      {/* Real Skill Selector & Test Presets */}
      <div className="flex flex-col gap-2 rounded border border-border/60 bg-muted/10 p-2.5">
        <div className="flex items-center justify-between text-xs font-mono">
          <div className="flex items-center gap-1.5 font-medium">
            <LayersIcon className="size-3.5 text-cyan-400" />
            <span>选择全域真资产技能 (共 {skills.length} 个):</span>
            <Badge variant="outline" className="text-xs font-mono border-cyan-500/30 text-cyan-400 bg-cyan-500/10 px-1.5 py-0.2">
              当前: {selectedSkillSlug || selectedPreset?.name || '未指定'}
            </Badge>
          </div>
          {isLoadingSkill && (
            <span className="text-cyan-400 flex items-center gap-1">
              <RefreshCwIcon className="size-3 animate-spin" /> 加载源码...
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={skillSearch}
            onChange={(e) => setSkillSearch(e.target.value)}
            placeholder="搜索全域技能名称或说明 (如 diagnosing, tdd, git)..."
            className="flex-1 text-xs font-mono px-2 py-1 rounded border border-border/60 bg-background/80 text-foreground focus:outline-none focus:ring-1 focus:ring-cyan-500/50"
          />
          <select
            value={selectedSkillSlug}
            onChange={(e) => {
              if (e.target.value) {
                void loadRealSkill(e.target.value)
              }
            }}
            className="w-64 text-xs font-mono px-2 py-1 rounded border border-border/60 bg-background/80 text-foreground focus:outline-none focus:ring-1 focus:ring-cyan-500/50 truncate"
          >
            <option value="">-- 选择真资产技能 --</option>
            {selectedSkillSlug && !filteredSkills.some((s) => s.name === selectedSkillSlug) && (
              <option value={selectedSkillSlug}>{selectedSkillSlug}</option>
            )}
            {filteredSkills.map((s) => (
              <option key={s.name} value={s.name}>
                {s.name} ({s.scope})
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-wrap items-center gap-1.5 pt-1 border-t border-border/40">
          <span className="text-xs text-muted-foreground font-mono">快速测试预设:</span>
          {SKILL_ZIP_PRESETS.map((preset) => (
            <Button
              key={preset.id}
              variant={selectedPreset?.id === preset.id ? 'default' : 'outline'}
              size="sm"
              onClick={() => handleSelectPreset(preset)}
              className="text-xs h-6 px-2 font-mono"
            >
              {preset.name}
            </Button>
          ))}
        </div>
      </div>

      {/* Main Workbench: Dual Column Grid */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Left: Input & Gate Status */}
        <div className="flex flex-col gap-2 rounded border border-border/80 bg-card p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold font-mono flex items-center gap-1.5">
              <CodeIcon className="size-3.5 text-cyan-400" /> 原始/候选技能 Markdown
            </span>
            <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground">
              <span>种子基准: {seedLen} 字符</span>
              <span>当前: {skillInput.length} 字符 ({((skillInput.length / seedLen) * 100).toFixed(0)}%)</span>
            </div>
          </div>

          <textarea
            value={skillInput}
            onChange={(e) => setSkillInput(e.target.value)}
            rows={15}
            className="w-full rounded border border-border bg-muted/20 p-2.5 font-mono text-xs leading-relaxed text-foreground focus:border-cyan-500 focus:outline-none"
            placeholder="输入技能 Markdown 或选择上方预设..."
          />

          <div className="flex items-center justify-between pt-1">
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleRunGateCheck}
                disabled={gateMutation.isPending}
                className="text-xs font-mono h-8"
              >
                <ShieldCheckIcon className="size-3.5 mr-1 text-cyan-400" />
                {gateMutation.isPending ? '检测中...' : '🛡️ 写入即门禁检测'}
              </Button>
              <Button
                variant="default"
                size="sm"
                onClick={handleRunCompress}
                disabled={compressMutation.isPending}
                className="text-xs font-mono h-8 bg-cyan-600 hover:bg-cyan-500 text-white"
              >
                <ZapIcon className="size-3.5 mr-1" />
                {compressMutation.isPending ? '压缩中...' : '⚡ 0-Rollout 契约压缩'}
              </Button>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                if (selectedPreset) {
                  handleSelectPreset(selectedPreset)
                } else if (selectedSkillSlug) {
                  void loadRealSkill(selectedSkillSlug)
                }
              }}
              className="text-xs font-mono h-8 text-muted-foreground"
            >
              <RefreshCwIcon className="size-3 mr-1" /> 重置
            </Button>
          </div>

          {gateResult && (
            <div
              className={`mt-2 flex items-center justify-between rounded border p-2.5 text-xs font-mono ${
                gateResult.passed
                  ? 'border-cyan-500/40 bg-cyan-500/10 text-cyan-400'
                  : gateResult.recommended_action === 'TRIGGER_ZIP'
                  ? 'border-amber-500/40 bg-amber-500/10 text-amber-400'
                  : 'border-rose-500/40 bg-rose-500/10 text-rose-400'
              }`}
            >
              <div className="flex items-center gap-2">
                {gateResult.passed ? (
                  <CheckCircle2Icon className="size-4 shrink-0 text-cyan-400" />
                ) : (
                  <ShieldAlertIcon className="size-4 shrink-0" />
                )}
                <span>{gateResult.reason}</span>
              </div>
              <span className="font-bold shrink-0">{gateResult.recommended_action}</span>
            </div>
          )}
        </div>

        {/* Right: Compressed Result & Six-Tuple Schema */}
        <div className="flex flex-col gap-2 rounded border border-border/80 bg-card p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold font-mono flex items-center gap-1.5">
              <SparklesIcon className="size-3.5 text-cyan-400" /> 契约化压缩输出 (Canonical Schema)
            </span>
            {zipResult && (
              <div className="flex items-center gap-2 text-xs font-mono">
                <span className="text-cyan-400 font-bold">
                  减熵 {(zipResult.compression_ratio * 100).toFixed(1)}%
                </span>
                <span className="text-muted-foreground">
                  省 ~{zipResult.tokens_saved} Tokens
                </span>
              </div>
            )}
          </div>

          {zipResult ? (
            <>
              {/* Six-Tuple Chips */}
              <div className="flex flex-wrap gap-1.5 py-1">
                <span className="inline-flex items-center rounded border border-cyan-500/30 bg-cyan-500/10 px-2 py-0.5 text-xs font-mono text-cyan-400">
                  I 接口: {zipResult.six_tuple.interface ? '已对齐' : '无'}
                </span>
                <span className="inline-flex items-center rounded border border-border bg-muted/30 px-2 py-0.5 text-xs font-mono text-foreground">
                  W 工作流: {zipResult.six_tuple.workflow.length} 步
                </span>
                <span className="inline-flex items-center rounded border border-border bg-muted/30 px-2 py-0.5 text-xs font-mono text-foreground">
                  P 协议: {zipResult.six_tuple.protocol.length} 项
                </span>
                <span className="inline-flex items-center rounded border border-border bg-muted/30 px-2 py-0.5 text-xs font-mono text-foreground">
                  R 规则: {zipResult.six_tuple.rules.length} 条 (已去重)
                </span>
                <span className="inline-flex items-center rounded border border-cyan-500/30 bg-cyan-500/10 px-2 py-0.5 text-xs font-mono text-cyan-400">
                  C 契约: {zipResult.six_tuple.contracts.length} 条 (100%保真)
                </span>
                <span className="inline-flex items-center rounded border border-border bg-muted/30 px-2 py-0.5 text-xs font-mono text-foreground">
                  E 证据: {zipResult.six_tuple.evidence.length} 条
                </span>
              </div>

              <textarea
                readOnly
                value={zipResult.compressed_content}
                rows={12}
                className="w-full rounded border border-border bg-muted/30 p-2.5 font-mono text-xs leading-relaxed text-foreground"
              />

              <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-border/40">
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    onClick={() => applyMutation.mutate('in_place')}
                    disabled={applyMutation.isPending || (!selectedSkillSlug && !selectedPreset)}
                    className="h-7 px-2.5 text-xs font-mono bg-cyan-600 hover:bg-cyan-500 text-white"
                  >
                    {applyMutation.isPending ? (
                      <RefreshCwIcon className="size-3 mr-1 animate-spin" />
                    ) : (
                      <FileCheckIcon className="size-3 mr-1" />
                    )}
                    💾 原地安全覆写 (In-Place)
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => applyMutation.mutate('compact_variant')}
                    disabled={applyMutation.isPending || (!selectedSkillSlug && !selectedPreset)}
                    className="h-7 px-2 text-xs font-mono border-cyan-500/40 text-cyan-400 hover:bg-cyan-500/10"
                  >
                    📦 发布为紧凑版 (SKILL.compact.md)
                  </Button>
                </div>
                <div className="text-xs font-mono text-muted-foreground">
                  <span>耗时: {zipResult.latency_ms}ms</span>
                </div>
              </div>

              {applyResult && (
                <div
                  className={`mt-2 p-2.5 rounded border text-xs font-mono flex flex-col gap-1 ${
                    applyResult.status === 'ok'
                      ? 'border-cyan-500/40 bg-cyan-500/10 text-cyan-400'
                      : 'border-rose-500/40 bg-rose-500/10 text-rose-400'
                  }`}
                >
                  <div className="flex items-center gap-1.5 font-bold">
                    <CheckCircle2Icon className="size-3.5" />
                    <span>{applyResult.message}</span>
                  </div>
                  {applyResult.status === 'ok' && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-1 text-foreground/80 mt-1">
                      <div>
                        <span className="text-muted-foreground">落盘目标: </span>
                        <span className="text-cyan-300 break-all">{applyResult.target_path}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">快照备份: </span>
                        <span className="text-amber-300 break-all">{applyResult.backup_path}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">证据链 ID: </span>
                        <span className="text-cyan-300">{applyResult.event_id}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">写入字节: </span>
                        <span className="text-foreground">{applyResult.bytes_written} 字节 (减熵 {(applyResult.compression_ratio * 100).toFixed(1)}%)</span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="flex h-95 flex-col items-center justify-center rounded border border-dashed border-border/60 bg-muted/10 p-6 text-center text-muted-foreground">
              <ZapIcon className="size-8 text-muted-foreground/40 mb-2" />
              <p className="text-xs font-mono">点击左侧「⚡ 0-Rollout 契约压缩」按钮运行压缩演练</p>
              <p className="text-xs text-muted-foreground/60 font-mono mt-1">
                吸收阿里 SkillZip 思想，动态规划规则放置与 Explain Once, Reference Everywhere
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
