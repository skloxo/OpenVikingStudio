import * as React from 'react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Textarea } from '#/components/ui/textarea'
import { ovClient } from '#/lib/ov-client'
import {
  CheckCircle2Icon,
  Code2Icon,
  PlayIcon,
  RotateCcwIcon,
  ShieldAlertIcon,
  TerminalIcon,
} from 'lucide-react'

export function HarnessLivePlayground() {
  // Anti-Lazy Guard State
  const [sampleCode, setSampleCode] = React.useState<string>(
    'def calculate_score(metrics: dict) -> float:\n    pass # TODO: implement score logic\n'
  )
  const [isTestingGuard, setIsTestingGuard] = React.useState(false)
  const [guardResult, setGuardResult] = React.useState<{
    passed: boolean
    blocked: boolean
    matched_pattern?: string | null
    reason: string
    rule: string
  } | null>(null)

  // Physical Probe State
  const [diffText, setDiffText] = React.useState<string>('')
  const [testCmd, setTestCmd] = React.useState<string>('pytest -o addopts="" tests/unit/test_harness_invariants.py')
  const [isProbing, setIsProbing] = React.useState(false)
  const [probeResult, setProbeResult] = React.useState<any>(null)

  const handleTestGuard = async () => {
    setIsTestingGuard(true)
    try {
      const res = await ovClient.instance.post('/api/v1/harness/test_guard', {
        code: sampleCode,
      })
      setGuardResult(res.data)
    } catch (err: any) {
      setGuardResult({
        passed: false,
        blocked: true,
        reason: `调用失败: ${err?.message ?? '网络或服务异常'}`,
        rule: 'AntiLazyCodeGuard',
      })
    } finally {
      setIsTestingGuard(false)
    }
  }

  const handleRunProbe = async () => {
    setIsProbing(true)
    try {
      const res = await ovClient.instance.post('/api/v1/harness/verify_probe', {
        diff_text: diffText.trim() ? diffText : null,
        test_command: testCmd.trim() ? testCmd : null,
      })
      setProbeResult(res.data)
    } catch (err: any) {
      setProbeResult({
        passed: false,
        summary: `探针执行失败: ${err?.message ?? '异常'}`,
        rejection_reasons: [err?.message ?? '执行异常'],
      })
    } finally {
      setIsProbing(false)
    }
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      {/* 1. Anti-Lazy Code Guard Playground */}
      <div className="flex flex-col justify-between rounded-md border border-border/70 bg-card/60 p-3.5">
        <div>
          <div className="flex items-center justify-between gap-2 border-b border-border/40 pb-2.5">
            <div className="flex items-center gap-2">
              <Code2Icon className="size-4 text-cyan-400" />
              <h4 className="text-xs font-semibold">防偷懒护栏实验台 (Anti-Lazy Guard)</h4>
            </div>
            <Badge variant="outline" className="border-cyan-500/30 bg-cyan-500/10 text-xs text-cyan-300">
              毫秒级 AST/正则扫描
            </Badge>
          </div>

          <div className="mt-2.5 flex flex-wrap gap-1.5">
            {[
              { label: '偷懒 1: pass 占位', code: 'def run_agent():\n    pass # TODO: implement\n' },
              { label: '偷懒 2: 省略号 ...', code: 'class InvariantVerifier:\n    ...\n' },
              { label: '偷懒 3: NotImplemented', code: 'def compile_spec():\n    raise NotImplementedError("to do")\n' },
              { label: '合规示例: 完整实现', code: 'def add(a: int, b: int) -> int:\n    result = a + b\n    return result\n', clean: true },
            ].map((btn, i) => (
              <Button
                key={i}
                type="button"
                variant="outline"
                size="sm"
                className={`h-6 text-xs px-2 ${btn.clean ? 'border-cyan-500/40 text-cyan-300 hover:bg-cyan-950/20' : ''}`}
                onClick={() => setSampleCode(btn.code)}
              >
                {btn.label}
              </Button>
            ))}
          </div>

          <div className="mt-2.5">
            <Textarea
              value={sampleCode}
              onChange={(e) => setSampleCode(e.target.value)}
              rows={4}
              className="font-mono text-xs bg-background/80"
              placeholder="输入待扫描的 Python 或 TypeScript 代码段..."
            />
          </div>

          <div className="mt-2.5 flex items-center justify-between">
            <Button
              type="button"
              size="sm"
              disabled={isTestingGuard || !sampleCode.trim()}
              onClick={handleTestGuard}
              className="h-7 text-xs bg-cyan-600 hover:bg-cyan-500 text-white"
            >
              <PlayIcon className="mr-1.5 size-3" />
              {isTestingGuard ? '扫描中...' : '实时检测代码门禁'}
            </Button>
            {guardResult && (
              <span className="font-mono text-xs text-muted-foreground">
                {guardResult.rule}
              </span>
            )}
          </div>

          {/* Result Feedback Banner */}
          {guardResult && (
            <div
              className={`mt-3 rounded-md border p-2.5 text-xs transition-all ${
                guardResult.blocked
                  ? 'border-rose-500/50 bg-rose-500/10 text-rose-300'
                  : 'border-cyan-500/50 bg-cyan-500/10 text-cyan-200'
              }`}
            >
              <div className="flex items-center gap-2">
                {guardResult.blocked ? (
                  <ShieldAlertIcon className="size-4 text-rose-400 shrink-0" />
                ) : (
                  <CheckCircle2Icon className="size-4 text-cyan-400 shrink-0" />
                )}
                <span className="font-semibold">
                  {guardResult.blocked ? '🚨 物理阻断 (Prohibited Write Blocked)' : '✅ 校验通过 (Clean Code Approved)'}
                </span>
              </div>
              <p className="mt-1 text-xs text-foreground/90">{guardResult.reason}</p>
              {guardResult.matched_pattern && (
                <div className="mt-1.5 rounded bg-background/80 px-2 py-1 font-mono text-xs text-rose-400">
                  捕获违规特征: {guardResult.matched_pattern}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 2. Physical Verification Probe */}
      <div className="flex flex-col justify-between rounded-md border border-border/70 bg-card/60 p-3.5">
        <div>
          <div className="flex items-center justify-between gap-2 border-b border-border/40 pb-2.5">
            <div className="flex items-center gap-2">
              <TerminalIcon className="size-4 text-cyan-400" />
              <h4 className="text-xs font-semibold">物理验真探针 (Physical Diff & Test Retina)</h4>
            </div>
            <Badge variant="outline" className="border-cyan-500/30 bg-cyan-500/10 text-xs text-cyan-300">
              真实工作区执行
            </Badge>
          </div>

          <div className="mt-2.5 flex flex-wrap gap-1.5">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-6 text-xs px-2"
              onClick={() => {
                setDiffText('')
                setTestCmd('pytest -o addopts="" tests/unit/test_harness_invariants.py')
              }}
            >
              默认: 检验当前 Git 仓库
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-6 text-xs px-2"
              onClick={() => {
                setDiffText('--- a/doc.py\n+++ b/doc.py\n@@ -1,1 +1,2 @@\n # header\n+# comment only\n')
                setTestCmd('')
              }}
            >
              模拟: 纯注释变更 (应阻断)
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-6 text-xs px-2"
              onClick={() => {
                setDiffText('--- a/lib.py\n+++ b/lib.py\n@@ -1,1 +1,3 @@\n-old\n+new_code = True\n')
                setTestCmd('')
              }}
            >
              模拟: 有效代码变更 (应通过)
            </Button>
          </div>

          <div className="mt-2.5">
            <Textarea
              value={diffText}
              onChange={(e) => setDiffText(e.target.value)}
              rows={4}
              className="font-mono text-xs bg-background/80"
              placeholder="留空则实时校验当前 Git 工作区 Diff；或在此粘贴 unified diff..."
            />
          </div>

          <div className="mt-2.5 flex items-center justify-between">
            <Button
              type="button"
              size="sm"
              disabled={isProbing}
              onClick={handleRunProbe}
              className="h-7 text-xs bg-cyan-600 hover:bg-cyan-500 text-white"
            >
              <RotateCcwIcon className={`mr-1.5 size-3 ${isProbing ? 'animate-spin' : ''}`} />
              {isProbing ? '验真探针执行中...' : '一键执行物理验真探针'}
            </Button>
          </div>

          {/* Probe Report Feedback */}
          {probeResult && (
            <div className="mt-3 rounded-md border border-border/80 bg-background/90 p-2.5 font-mono text-xs">
              <div className="flex items-center justify-between border-b border-border/40 pb-1.5">
                <span className="font-semibold text-foreground">
                  验真报告: {probeResult.passed ? '✅ 门禁全部通过' : '🚨 门禁拦截拒收'}
                </span>
                <Badge
                  variant="outline"
                  className={`text-xs ${
                    probeResult.passed
                      ? 'border-cyan-500/40 text-cyan-300'
                      : 'border-rose-500/40 text-rose-300'
                  }`}
                >
                  {probeResult.passed ? 'PASS' : 'REJECTED'}
                </Badge>
              </div>

              {probeResult.diff_result && (
                <div className="mt-1.5 grid grid-cols-2 gap-1 text-muted-foreground">
                  <div>有效改动行: <span className="text-foreground">{probeResult.diff_result.effective_diff_lines}</span></div>
                  <div>纯注释过滤: <span className="text-foreground">{probeResult.diff_result.comment_lines_filtered ?? 0}</span></div>
                  <div>空改动状态: <span className="text-foreground">{String(probeResult.diff_result.is_empty)}</span></div>
                  <div>改动文件数: <span className="text-foreground">{probeResult.diff_result.files_changed?.length ?? 0}</span></div>
                </div>
              )}

              {probeResult.test_result && (
                <div className="mt-1.5 border-t border-border/30 pt-1 text-muted-foreground">
                  测试视网膜: passed={probeResult.test_result.passed_count}, failed={probeResult.test_result.failed_count}, exit={probeResult.test_result.exit_code} (欺诈防御={String(probeResult.test_result.is_false_exit_zero)})
                </div>
              )}

              {probeResult.rejection_reasons?.length > 0 && (
                <div className="mt-1.5 border-t border-rose-500/30 pt-1 text-rose-400">
                  拒收原因: {probeResult.rejection_reasons.join('; ')}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
