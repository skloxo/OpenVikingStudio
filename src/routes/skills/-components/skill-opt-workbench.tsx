import * as React from 'react'
import { SparklesIcon, PlayIcon, RefreshCwIcon, CheckIcon, WrenchIcon, SaveIcon, ShieldCheckIcon, SearchIcon } from 'lucide-react'
import { Button } from '#/components/ui/button'
import { Badge } from '#/components/ui/badge'
import { Card } from '#/components/ui/card'
import type { SkillOptApplyResult, SkillOptAttemptResult, SkillOptOptimizeResult } from './skill-opt-types'

interface SkillOptWorkbenchProps {
  content: string
  onContentChange: (val: string) => void
  onAudit: () => void
  onAttempt: (query: string) => void
  onOptimize: () => void
  onApplyPatch: () => void
  attemptResult: SkillOptAttemptResult | null
  optimizeResult: SkillOptOptimizeResult | null
  applyResult: SkillOptApplyResult | null
  isAuditing?: boolean
  isAttempting?: boolean
  isOptimizing?: boolean
  isApplying?: boolean
  currentSkillSlug: string
  availableSkills?: Array<{ name: string; description: string; scope: string }>
  onSelectSkill?: (slug: string) => void
  isLoadingSkill?: boolean
}

export function SkillOptWorkbench({
  content,
  onContentChange,
  onAudit,
  onAttempt,
  onOptimize,
  onApplyPatch,
  attemptResult,
  optimizeResult,
  applyResult,
  isAuditing,
  isAttempting,
  isOptimizing,
  isApplying,
  currentSkillSlug,
  availableSkills = [],
  onSelectSkill,
  isLoadingSkill,
}: SkillOptWorkbenchProps) {
  const [testQuery, setTestQuery] = React.useState('出现死锁与性能下降时如何处理')
  const [skillSearch, setSkillSearch] = React.useState('')

  const filteredSkillOptions = React.useMemo(() => {
    if (!skillSearch.trim()) return availableSkills.slice(0, 50)
    const q = skillSearch.toLowerCase()
    return availableSkills.filter(
      (s) => s.name.toLowerCase().includes(q) || s.description.toLowerCase().includes(q)
    ).slice(0, 50)
  }, [availableSkills, skillSearch])

  return (
    <Card className="p-3.5 border-border/60 bg-card/60 flex flex-col gap-3">
      {/* Skill Selector Bar across 759 production skills */}
      <div className="flex flex-col gap-1.5 p-2 rounded-md border border-border/40 bg-muted/20">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <SearchIcon className="size-3.5 text-cyan-400" />
            <span className="text-xs font-semibold text-foreground">
              选择真资产技能 (共 {availableSkills.length} 个):
            </span>
            <Badge variant="outline" className="text-xs font-mono border-cyan-500/30 text-cyan-400 bg-cyan-500/10 px-1.5 py-0.2">
              当前: {currentSkillSlug || '未指定'}
            </Badge>
          </div>
          {isLoadingSkill && (
            <span className="text-xs font-mono text-cyan-400 flex items-center gap-1">
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
            value={currentSkillSlug}
            onChange={(e) => onSelectSkill && onSelectSkill(e.target.value)}
            className="w-56 text-xs font-mono px-2 py-1 rounded border border-border/60 bg-background/80 text-foreground focus:outline-none focus:ring-1 focus:ring-cyan-500/50 truncate"
          >
            {currentSkillSlug && !filteredSkillOptions.some(s => s.name === currentSkillSlug) && (
              <option value={currentSkillSlug}>{currentSkillSlug}</option>
            )}
            {filteredSkillOptions.map((s) => (
              <option key={s.name} value={s.name}>
                {s.name} ({s.scope})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Action Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/40 pb-2.5">
        <div className="flex items-center gap-1.5">
          <WrenchIcon className="size-3.5 text-cyan-400" />
          <span className="text-xs font-semibold">SkillOpt 交互调优工作台</span>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={onAudit}
            disabled={isAuditing || !content.trim()}
            className="h-7 text-xs font-mono bg-cyan-600 hover:bg-cyan-500 text-white"
          >
            {isAuditing ? <RefreshCwIcon className="size-3 mr-1 animate-spin" /> : <SparklesIcon className="size-3 mr-1" />}
            执行 SkillOpt 体检
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={onOptimize}
            disabled={isOptimizing || !content.trim()}
            className="h-7 text-xs font-mono border-cyan-500/40 text-cyan-400 hover:bg-cyan-500/10"
          >
            {isOptimizing ? <RefreshCwIcon className="size-3 mr-1 animate-spin" /> : <SparklesIcon className="size-3 mr-1" />}
            生成自动优化补丁
          </Button>
        </div>
      </div>

      {/* Editor text area */}
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between text-xs text-muted-foreground font-mono">
          <span>技能草稿文本 (SKILL.md)</span>
          <span>{content.split('\n').length} 行</span>
        </div>
        <textarea
          value={content}
          onChange={(e) => onContentChange(e.target.value)}
          placeholder="输入或选择技能 Markdown 文本 (需包含 YAML 标头)..."
          rows={10}
          className="w-full font-mono text-xs p-2.5 rounded-md border border-border/60 bg-background/80 text-foreground resize-y focus:outline-none focus:ring-1 focus:ring-cyan-500/50"
        />
      </div>

      {/* Attempt Simulator */}
      <div className="p-2.5 rounded-md border border-border/40 bg-muted/20 flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono font-medium text-foreground/90">🚀 Attempt 执行测试与 Judge 判据</span>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => onAttempt(testQuery)}
            disabled={isAttempting || !testQuery.trim() || !content.trim()}
            className="h-6 px-2 text-xs font-mono text-cyan-400 hover:bg-cyan-500/10"
          >
            {isAttempting ? <RefreshCwIcon className="size-3 mr-1 animate-spin" /> : <PlayIcon className="size-3 mr-1" />}
            运行 Attempt 场景
          </Button>
        </div>
        <input
          type="text"
          value={testQuery}
          onChange={(e) => setTestQuery(e.target.value)}
          placeholder="输入自然语言场景测试语句..."
          className="w-full text-xs font-mono px-2.5 py-1.5 rounded border border-border/40 bg-background/80 text-foreground focus:outline-none focus:ring-1 focus:ring-cyan-500/50"
        />

        {attemptResult && (
          <div className="mt-1 p-2 rounded bg-background/80 border border-border/40 flex flex-col gap-1 text-xs font-mono">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Judge 判据结果:</span>
              <Badge
                variant="outline"
                className={`text-xs font-mono px-1.5 py-0.5 ${
                  attemptResult.verdict === 'PASS'
                    ? 'border-cyan-500/40 text-cyan-400 bg-cyan-500/10'
                    : attemptResult.verdict === 'PARTIAL'
                    ? 'border-amber-500/40 text-amber-400 bg-amber-500/10'
                    : 'border-rose-500/40 text-rose-400 bg-rose-500/10'
                }`}
              >
                {attemptResult.verdict} ({(attemptResult.confidence * 100).toFixed(0)}%)
              </Badge>
            </div>
            <p className="text-muted-foreground">{attemptResult.judge_reason}</p>
          </div>
        )}
      </div>

      {/* Optimize Result Preview */}
      {optimizeResult && (
        <div className="p-2.5 rounded-md border border-cyan-500/40 bg-cyan-500/5 flex flex-col gap-2">
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
            <span className="text-cyan-400 font-medium">{optimizeResult.diff_summary}</span>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => onContentChange(optimizeResult.optimized_content)}
                className="h-6 px-2 text-xs font-mono border-cyan-500/40 text-cyan-400 hover:bg-cyan-500/10"
              >
                <CheckIcon className="size-3 mr-1" />
                采纳优化到草稿
              </Button>
              <Button
                size="sm"
                onClick={onApplyPatch}
                disabled={isApplying || !currentSkillSlug}
                className="h-6 px-2.5 text-xs font-mono bg-cyan-600 hover:bg-cyan-500 text-white font-medium"
              >
                {isApplying ? (
                  <RefreshCwIcon className="size-3 mr-1 animate-spin" />
                ) : (
                  <SaveIcon className="size-3 mr-1" />
                )}
                💾 物理保存回写到文件
              </Button>
            </div>
          </div>
          <ul className="text-xs font-mono text-muted-foreground space-y-0.5">
            {optimizeResult.applied_fixes.map((fix, idx) => (
              <li key={idx} className="flex items-center gap-1 text-foreground/80">
                <span className="text-cyan-400">✓</span> {fix}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Physical Apply & Snapshot Feedback */}
      {applyResult && (
        <div
          className={`p-2.5 rounded-md border text-xs font-mono flex flex-col gap-1.5 ${
            applyResult.status === 'ok'
              ? 'border-cyan-500/40 bg-cyan-500/10 text-cyan-400'
              : 'border-rose-500/40 bg-rose-500/10 text-rose-400'
          }`}
        >
          <div className="flex items-center gap-1.5 font-semibold">
            <ShieldCheckIcon className="size-4" />
            <span>{applyResult.message}</span>
          </div>
          {applyResult.status === 'ok' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-1 text-foreground/80 mt-0.5 text-xs">
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
                <span className="text-muted-foreground">物理写入: </span>
                <span className="text-foreground">{applyResult.bytes_written} 字节</span>
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  )
}
