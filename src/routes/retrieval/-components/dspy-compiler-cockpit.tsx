// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import { useState, useEffect } from 'react'
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  Copy,
  Download,
  FileCode2,
  Save,
  Sparkles,
  Zap,
} from 'lucide-react'
import { ovClient } from '@/lib/ov-client'
import { DSPY_PRESETS, type DSPyPreset } from '../-constants/dspy-presets'
import { DSPyKpiTiles } from './dspy-kpi-tiles'
import { DSPySignatureInsightCard } from './dspy-signature-insight-card'
import { PromptTemplatePicker } from './prompt-template-picker'

import type {
  ApplyDSPyRequest,
  ApplyDSPyResult,
  DSPyCompileResult,
  DSPyCompilerStats,
  PromptTemplateItem,
} from '../-types/dspy-compiler'

export function DSPyCompilerCockpit() {
  const [selectedPreset, setSelectedPreset] = useState<DSPyPreset>(DSPY_PRESETS[0])
  const [rawPrompt, setRawPrompt] = useState<string>(DSPY_PRESETS[0].rawPrompt)
  const [signatureName, setSignatureName] = useState<string>(DSPY_PRESETS[0].signatureName)
  const [taskObjective, setTaskObjective] = useState<string>(DSPY_PRESETS[0].taskObjective)
  const [maxFewShot, setMaxFewShot] = useState<number>(2)
  const [strictTyping, setStrictTyping] = useState<boolean>(true)
  const [antiHallucination, setAntiHallucination] = useState<boolean>(true)

  // Real Prompt Template picking & persistence
  const [selectedTemplate, setSelectedTemplate] = useState<PromptTemplateItem | null>(null)
  const [showTemplatePicker, setShowTemplatePicker] = useState<boolean>(false)
  const [applyResult, setApplyResult] = useState<ApplyDSPyResult | null>(null)
  const [applyError, setApplyError] = useState<string | null>(null)
  const [applying, setApplying] = useState<boolean>(false)

  const [compiling, setCompiling] = useState<boolean>(false)
  const [result, setResult] = useState<DSPyCompileResult | null>(null)
  const [stats, setStats] = useState<DSPyCompilerStats | null>(null)
  const [copied, setCopied] = useState<boolean>(false)

  const fetchStats = async () => {
    try {
      const res = await ovClient.get<DSPyCompilerStats>('/api/v1/dspy/stats')
      if (res) setStats(res)
    } catch {
      // 优雅降级
    }
  }

  useEffect(() => {
    fetchStats()
  }, [])

  const handleApplyPreset = (preset: DSPyPreset) => {
    setSelectedPreset(preset)
    setSelectedTemplate(null)
    setRawPrompt(preset.rawPrompt)
    setSignatureName(preset.signatureName)
    setTaskObjective(preset.taskObjective)
    setResult(null)
    setApplyResult(null)
    setApplyError(null)
  }

  const handleSelectTemplate = async (tpl: PromptTemplateItem) => {
    setSelectedTemplate(tpl)
    try {
      const res = await ovClient.instance.get<{
        template: string
        name: string
        description: string
        id: string
      }>(`/api/v1/dspy/template?path=${encodeURIComponent(tpl.rel_path)}`)
      if (res.data) {
        setRawPrompt(res.data.template || '')
        setSignatureName(res.data.name || tpl.name)
        setTaskObjective(res.data.description || tpl.description)
      }
      setResult(null)
      setApplyResult(null)
      setApplyError(null)
    } catch (err: any) {
      setApplyError(`读取 Prompt 模板失败: ${err.message}`)
    }
  }

  const handleCompile = async () => {
    if (!rawPrompt.trim()) return
    setCompiling(true)
    try {
      const payload = {
        raw_prompt: rawPrompt,
        signature_name: signatureName || undefined,
        task_objective: taskObjective || undefined,
        candidate_examples: selectedPreset.candidateExamples,
        max_few_shot: maxFewShot,
        strict_typing: strictTyping,
        anti_hallucination_gate: antiHallucination,
      }
      const res = await ovClient.post<DSPyCompileResult>('/api/v1/dspy/compile', payload)
      if (res) {
        setResult(res)
        fetchStats()
      }
    } catch (err: any) {
      setApplyError(`DSPy 编译失败: ${err.message}`)
    } finally {
      setCompiling(false)
    }
  }

  const handleApply = async (saveMode: 'compiled_file' | 'in_place') => {
    if (!selectedTemplate) {
      setApplyError('请先从真实 Prompt 模板库中挑选一个模板进行回写')
      return
    }
    if (!result?.compiled_prompt) {
      setApplyError('请先执行 DSPy 编译生成强类型提示词')
      return
    }
    if (saveMode === 'in_place') {
      const confirmWrite = window.confirm(
        `确定要原地更新模板 ${selectedTemplate.name} 吗？系统将在隔离区自动生成时间戳快照以备秒级还原。`
      )
      if (!confirmWrite) return
    }

    setApplying(true)
    setApplyError(null)
    try {
      const payload: ApplyDSPyRequest = {
        rel_path: selectedTemplate.rel_path,
        compiled_prompt: result.compiled_prompt,
        signature_name: signatureName,
        task_objective: taskObjective,
        mode: saveMode,
      }
      const res = await ovClient.instance.post<ApplyDSPyResult>('/api/v1/dspy/apply', payload)
      if (res.data) {
        setApplyResult(res.data)
      }
    } catch (err: any) {
      setApplyError(`物理落盘失败: ${err.message}`)
    } finally {
      setApplying(false)
    }
  }

  const handleCopy = () => {
    if (!result?.compiled_prompt) return
    navigator.clipboard.writeText(result.compiled_prompt)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="space-y-4">
      {/* 顶部 4 大 KPI 瓦片 */}
      <DSPyKpiTiles result={result} stats={stats} />

      {/* Persistence Feedback Banner */}
      {applyResult && (
        <div className="p-3 bg-cyan-500/10 border border-cyan-500/30 rounded-md text-xs font-mono flex items-start justify-between gap-3 text-foreground">
          <div className="flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-cyan-500 shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-cyan-500">
                Prompt 物理落盘成功 ({applyResult.mode === 'in_place' ? '原地更新' : '编译版文件'})
              </div>
              <div className="text-muted-foreground mt-0.5">
                目标路径: <span className="text-foreground">{applyResult.target_path}</span> ｜ 编译后字符: {applyResult.compiled_chars}
              </div>
              <div className="text-muted-foreground truncate">
                安全快照: <span className="text-xs">{applyResult.snapshot_path}</span>
              </div>
            </div>
          </div>
          <button
            type="button"
            className="text-xs text-muted-foreground hover:text-foreground"
            onClick={() => setApplyResult(null)}
          >
            关闭
          </button>
        </div>
      )}

      {applyError && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-md text-xs font-mono flex items-center justify-between gap-3 text-rose-700 dark:text-rose-300">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{applyError}</span>
          </div>
          <button
            type="button"
            className="text-xs text-rose-500 hover:text-rose-400"
            onClick={() => setApplyError(null)}
          >
            关闭
          </button>
        </div>
      )}

      {/* 控制栏与预设 */}
      <div className="p-3.5 bg-card border border-border/70 rounded-md space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowTemplatePicker(!showTemplatePicker)}
              className={`flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-md border font-mono transition-colors ${
                showTemplatePicker
                  ? 'bg-cyan-500/10 border-cyan-500 text-cyan-500 font-semibold'
                  : 'border-border/60 hover:bg-muted/40 text-muted-foreground'
              }`}
            >
              <BookOpen className="w-3.5 h-3.5" />
              {selectedTemplate ? `已选: ${selectedTemplate.name}` : '挑选系统 Prompt 模板'}
            </button>

            <span className="text-xs font-medium text-muted-foreground ml-2">预设:</span>
            {DSPY_PRESETS.map((preset) => (
              <button
                key={preset.id}
                type="button"
                onClick={() => handleApplyPreset(preset)}
                className={`px-2 py-0.5 text-xs rounded-md border font-mono transition-colors ${
                  selectedPreset.id === preset.id && !selectedTemplate
                    ? 'bg-cyan-500/10 border-cyan-500 text-cyan-500 font-semibold'
                    : 'border-border/60 hover:bg-muted/40 text-muted-foreground'
                }`}
              >
                {preset.name.split(' ')[0]}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-3">
            <label className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer">
              <input
                type="checkbox"
                checked={strictTyping}
                onChange={(e) => setStrictTyping(e.target.checked)}
                className="rounded border-border accent-cyan-500"
              />
              <span>强类型规约</span>
            </label>

            <label className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer">
              <input
                type="checkbox"
                checked={antiHallucination}
                onChange={(e) => setAntiHallucination(e.target.checked)}
                className="rounded border-border accent-cyan-500"
              />
              <span>防幻觉硬门禁</span>
            </label>

            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <span>Few-Shot 样本:</span>
              <select
                value={maxFewShot}
                onChange={(e) => setMaxFewShot(Number(e.target.value))}
                className="bg-background border border-border/60 rounded px-1.5 py-0.5 text-xs font-mono"
              >
                <option value={0}>0 (Zero-Shot)</option>
                <option value={1}>1</option>
                <option value={2}>2 (推荐)</option>
                <option value={3}>3</option>
              </select>
            </div>

            <button
              type="button"
              onClick={handleCompile}
              disabled={compiling}
              className="flex items-center gap-1.5 px-3 py-1 bg-cyan-500 text-black font-semibold text-xs rounded-md hover:bg-cyan-400 disabled:opacity-50 transition-colors"
            >
              <Sparkles className="w-3.5 h-3.5" />
              {compiling ? '编译中...' : '一键执行 DSPy 编译'}
            </button>
          </div>
        </div>

        {/* Prompt Template Picker Tray */}
        {showTemplatePicker && (
          <div className="pt-2 border-t border-border/50">
            <PromptTemplatePicker
              selectedPath={selectedTemplate?.rel_path}
              onSelectTemplate={handleSelectTemplate}
            />
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
          <input
            type="text"
            value={signatureName}
            onChange={(e) => setSignatureName(e.target.value)}
            placeholder="强类型签名名称 (Signature Name)"
            className="w-full bg-background border border-border/60 rounded px-2.5 py-1 text-xs font-mono focus:border-cyan-500 outline-none"
          />
          <input
            type="text"
            value={taskObjective}
            onChange={(e) => setTaskObjective(e.target.value)}
            placeholder="任务核心目标说明 (Task Objective)"
            className="w-full bg-background border border-border/60 rounded px-2.5 py-1 text-xs focus:border-cyan-500 outline-none"
          />
        </div>
      </div>

      {/* 双栏实时对比编辑器 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* 左栏：原始松散 Prompt */}
        <div className="flex flex-col border border-border/70 rounded-md bg-card overflow-hidden">
          <div className="px-3.5 py-2 border-b border-border/60 bg-muted/20 flex items-center justify-between text-xs">
            <span className="font-semibold text-foreground flex items-center gap-1.5">
              <FileCode2 className="w-3.5 h-3.5 text-muted-foreground" />
              原始松散自然语言 Prompt
              {selectedTemplate && (
                <span className="ml-1 text-xs font-mono text-cyan-500 bg-cyan-500/10 px-1 rounded">
                  {selectedTemplate.id}
                </span>
              )}
            </span>
            <span className="text-muted-foreground font-mono text-xs">
              {rawPrompt.length} chars
            </span>
          </div>
          <textarea
            value={rawPrompt}
            onChange={(e) => setRawPrompt(e.target.value)}
            rows={14}
            className="w-full p-3 bg-transparent text-foreground text-xs font-mono leading-relaxed outline-none resize-none"
            placeholder="输入待编译的自然语言 Prompt，或从上方挑选系统 Prompt 模板..."
          />
        </div>

        {/* 右栏：编译后强类型 Prompt */}
        <div className="flex flex-col border border-border/70 rounded-md bg-card overflow-hidden">
          <div className="px-3.5 py-2 border-b border-border/60 bg-muted/20 flex items-center justify-between text-xs">
            <span className="font-semibold text-cyan-500 flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5" />
              DSPy MIPO 强类型编译产物
            </span>
            <div className="flex items-center gap-2">
              {result && (
                <>
                  <button
                    type="button"
                    onClick={handleCopy}
                    className="text-xs text-muted-foreground hover:text-cyan-500 flex items-center gap-1 transition-colors font-mono"
                  >
                    <Copy className="w-3 h-3" />
                    {copied ? '已复制' : '复制'}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleApply('compiled_file')}
                    disabled={applying}
                    className="text-xs text-cyan-500 hover:text-cyan-400 flex items-center gap-1 transition-colors font-mono border border-cyan-500/30 px-1.5 py-0.5 rounded"
                  >
                    <Download className="w-3 h-3" />
                    发布编译版 (.compiled)
                  </button>
                  <button
                    type="button"
                    onClick={() => handleApply('in_place')}
                    disabled={applying}
                    className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors font-mono border border-border/60 px-1.5 py-0.5 rounded"
                  >
                    <Save className="w-3 h-3" />
                    原地更新
                  </button>
                </>
              )}
              <span className="text-muted-foreground font-mono text-xs">
                {result ? `${result.compiled_prompt.length} chars` : '未编译'}
              </span>
            </div>
          </div>
          <div className="w-full p-3 bg-muted/5 text-foreground text-xs font-mono leading-relaxed h-full overflow-y-auto max-h-80">
            {result ? (
              <pre className="whitespace-pre-wrap">{result.compiled_prompt}</pre>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-muted-foreground gap-2 py-16">
                <Sparkles className="w-6 h-6 text-muted-foreground/40" />
                <span>点击上方「一键执行 DSPy 编译」生成高精纯强类型提示词</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 底部：提取契约与精选 Few-Shot 样本检查卡片 */}
      {result && <DSPySignatureInsightCard result={result} />}
    </div>
  )
}

