import React, { useState, useEffect } from "react";
import {
  FileCode2,
  Sparkles,
  ShieldCheck,
  Zap,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  Copy,
  Layers,
  ArrowRight,
  Database,
  Binary,
} from "lucide-react";
import { ovClient } from "@/lib/ov-client";
import { DSPY_PRESETS, type DSPyPreset } from "../-constants/dspy-presets";
import type {
  DSPyCompileResult,
  DSPyCompilerStats,
  BootstrapExample,
} from "../-types/dspy-compiler";

export function DSPyCompilerCockpit() {
  const [selectedPreset, setSelectedPreset] = useState<DSPyPreset>(DSPY_PRESETS[0]);
  const [rawPrompt, setRawPrompt] = useState<string>(DSPY_PRESETS[0].rawPrompt);
  const [signatureName, setSignatureName] = useState<string>(DSPY_PRESETS[0].signatureName);
  const [taskObjective, setTaskObjective] = useState<string>(DSPY_PRESETS[0].taskObjective);
  const [maxFewShot, setMaxFewShot] = useState<number>(2);
  const [strictTyping, setStrictTyping] = useState<boolean>(true);
  const [antiHallucination, setAntiHallucination] = useState<boolean>(true);

  const [compiling, setCompiling] = useState<boolean>(false);
  const [result, setResult] = useState<DSPyCompileResult | null>(null);
  const [stats, setStats] = useState<DSPyCompilerStats | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  const fetchStats = async () => {
    try {
      const res = await ovClient.get<DSPyCompilerStats>("/api/v1/dspy/stats");
      if (res) setStats(res);
    } catch {
      // 优雅降级
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const handleApplyPreset = (preset: DSPyPreset) => {
    setSelectedPreset(preset);
    setRawPrompt(preset.rawPrompt);
    setSignatureName(preset.signatureName);
    setTaskObjective(preset.taskObjective);
    setResult(null);
  };

  const handleCompile = async () => {
    if (!rawPrompt.trim()) return;
    setCompiling(true);
    try {
      const payload = {
        raw_prompt: rawPrompt,
        signature_name: signatureName || undefined,
        task_objective: taskObjective || undefined,
        candidate_examples: selectedPreset.candidateExamples,
        max_few_shot: maxFewShot,
        strict_typing: strictTyping,
        anti_hallucination_gate: antiHallucination,
      };
      const res = await ovClient.post<DSPyCompileResult>("/api/v1/dspy/compile", payload);
      if (res) {
        setResult(res);
        fetchStats();
      }
    } catch (err) {
      console.error("DSPy Compile Failed:", err);
    } finally {
      setCompiling(false);
    }
  };

  const handleCopy = () => {
    if (!result?.compiled_prompt) return;
    navigator.clipboard.writeText(result.compiled_prompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-4">
      {/* 顶部 4 大 KPI 瓦片 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-3.5 bg-card border border-border/70 rounded-md">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-mono">
            <span>ORIGINAL TOKENS</span>
            <Database className="w-3.5 h-3.5 text-muted-foreground" />
          </div>
          <div className="text-xl font-bold font-mono text-foreground mt-1 tabular-nums">
            {result ? result.original_token_count : "--"}
          </div>
          <div className="text-xs text-muted-foreground mt-0.5">原始松散提示词估算</div>
        </div>

        <div className="p-3.5 bg-card border border-border/70 rounded-md">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-mono">
            <span>COMPILED TOKENS</span>
            <Zap className="w-3.5 h-3.5 text-cyan-500" />
          </div>
          <div className="text-xl font-bold font-mono text-cyan-500 mt-1 tabular-nums">
            {result ? result.compiled_token_count : "--"}
          </div>
          <div className="text-xs text-muted-foreground mt-0.5">
            {result ? `Token 比率: ${(result.compression_ratio * 100).toFixed(1)}%` : "强类型规约合成"}
          </div>
        </div>

        <div className="p-3.5 bg-card border border-border/70 rounded-md">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-mono">
            <span>CONTRACT STATUS</span>
            <ShieldCheck className="w-3.5 h-3.5 text-cyan-500" />
          </div>
          <div className="text-xl font-bold font-mono mt-1 flex items-center gap-1.5">
            {result ? (
              <span className="text-cyan-500 flex items-center gap-1">
                <CheckCircle2 className="w-4 h-4" /> {result.contract_status}
              </span>
            ) : (
              <span className="text-muted-foreground">READY</span>
            )}
          </div>
          <div className="text-xs text-muted-foreground mt-0.5">
            {result?.anti_hallucination_injected ? "零幻觉护栏已激活" : "Schema 强类型门禁"}
          </div>
        </div>

        <div className="p-3.5 bg-card border border-border/70 rounded-md">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-mono">
            <span>LATENCY & CALLS</span>
            <Binary className="w-3.5 h-3.5 text-cyan-500" />
          </div>
          <div className="text-xl font-bold font-mono text-foreground mt-1 tabular-nums">
            {result ? `${result.elapsed_ms}ms` : stats ? `${stats.average_latency_ms}ms` : "--"}
          </div>
          <div className="text-xs text-muted-foreground mt-0.5">
            累计编译: {stats ? stats.total_compilations : 0} 次
          </div>
        </div>
      </div>

      {/* 控制栏与预设 */}
      <div className="p-3.5 bg-card border border-border/70 rounded-md space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-muted-foreground">工业级预设:</span>
            {DSPY_PRESETS.map((preset) => (
              <button
                key={preset.id}
                type="button"
                onClick={() => handleApplyPreset(preset)}
                className={`px-2.5 py-1 text-xs rounded-md border font-mono transition-colors ${
                  selectedPreset.id === preset.id
                    ? "bg-cyan-500/10 border-cyan-500 text-cyan-400 font-semibold"
                    : "border-border/60 hover:bg-muted/40 text-muted-foreground"
                }`}
              >
                {preset.name.split(" ")[0]}
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
              {compiling ? "编译中..." : "一键执行 DSPy 编译"}
            </button>
          </div>
        </div>

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
            placeholder="输入待编译的自然语言 Prompt..."
          />
        </div>

        {/* 右栏：编译后强类型 Prompt */}
        <div className="flex flex-col border border-border/70 rounded-md bg-card overflow-hidden">
          <div className="px-3.5 py-2 border-b border-border/60 bg-muted/20 flex items-center justify-between text-xs">
            <span className="font-semibold text-cyan-400 flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5" />
              DSPy MIPO 强类型编译产物
            </span>
            <div className="flex items-center gap-2">
              {result && (
                <button
                  type="button"
                  onClick={handleCopy}
                  className="text-xs text-muted-foreground hover:text-cyan-400 flex items-center gap-1 transition-colors font-mono"
                >
                  <Copy className="w-3 h-3" />
                  {copied ? "已复制" : "复制"}
                </button>
              )}
              <span className="text-muted-foreground font-mono text-xs">
                {result ? `${result.compiled_prompt.length} chars` : "未编译"}
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
      {result && (
        <div className="p-3.5 bg-card border border-border/70 rounded-md space-y-2">
          <div className="flex items-center justify-between text-xs font-semibold text-foreground">
            <span className="flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-cyan-500" />
              强类型签名与样本洞察 ({result.signature.name})
            </span>
            <span className="text-muted-foreground font-mono text-xs">
              输入字段: {result.signature.input_fields.length} ｜ 输出字段: {result.signature.output_fields.length} ｜ Few-Shot: {result.selected_few_shot.length}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            <div className="bg-muted/10 border border-border/40 rounded p-2.5">
              <div className="text-muted-foreground font-mono text-xs mb-1">输入/输出类型契约:</div>
              <div className="space-y-1 font-mono text-xs">
                {result.signature.input_fields.map((f) => (
                  <div key={f.name} className="flex items-center gap-1 text-foreground">
                    <span className="text-cyan-500">IN</span>
                    <span className="font-semibold">{f.name}</span>:
                    <span className="text-muted-foreground">{f.field_type}</span>
                  </div>
                ))}
                {result.signature.output_fields.map((f) => (
                  <div key={f.name} className="flex items-center gap-1 text-foreground">
                    <span className="text-cyan-400">OUT</span>
                    <span className="font-semibold">{f.name}</span>:
                    <span className="text-muted-foreground">{f.field_type}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-muted/10 border border-border/40 rounded p-2.5">
              <div className="text-muted-foreground font-mono text-xs mb-1">精选注入的 Bootstrap 样本:</div>
              {result.selected_few_shot.length > 0 ? (
                <div className="space-y-1 text-xs">
                  {result.selected_few_shot.map((ex) => (
                    <div key={ex.example_id} className="flex items-center justify-between">
                      <span className="font-mono text-foreground">{ex.example_id}</span>
                      <span className="text-cyan-500 font-mono">
                        得分: {ex.quality_score.toFixed(2)} ({ex.source})
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-muted-foreground text-xs">当前为 Zero-Shot 纯规约模式</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
