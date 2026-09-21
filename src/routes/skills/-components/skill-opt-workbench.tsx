import * as React from 'react'
import { SparklesIcon, PlayIcon, RefreshCwIcon, CheckIcon, WrenchIcon } from 'lucide-react'
import { Button } from '#/components/ui/button'
import { Badge } from '#/components/ui/badge'
import { Card } from '#/components/ui/card'
import type { SkillOptAttemptResult, SkillOptOptimizeResult } from './skill-opt-types'

interface SkillOptWorkbenchProps {
  content: string
  onContentChange: (val: string) => void
  onAudit: () => void
  onAttempt: (query: string) => void
  onOptimize: () => void
  attemptResult: SkillOptAttemptResult | null
  optimizeResult: SkillOptOptimizeResult | null
  isAuditing?: boolean
  isAttempting?: boolean
  isOptimizing?: boolean
}

export function SkillOptWorkbench({
  content,
  onContentChange,
  onAudit,
  onAttempt,
  onOptimize,
  attemptResult,
  optimizeResult,
  isAuditing,
  isAttempting,
  isOptimizing,
}: SkillOptWorkbenchProps) {
  const [testQuery, setTestQuery] = React.useState('出现死锁与性能下降时如何处理')

  return (
    <Card className="p-3.5 border-border/60 bg-card/60 flex flex-col gap-3">
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
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-cyan-400 font-medium">{optimizeResult.diff_summary}</span>
            <Button
              size="sm"
              onClick={() => onContentChange(optimizeResult.optimized_content)}
              className="h-6 px-2 text-xs font-mono bg-cyan-600 hover:bg-cyan-500 text-white"
            >
              <CheckIcon className="size-3 mr-1" />
              采纳此优化 Patch
            </Button>
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
    </Card>
  )
}
