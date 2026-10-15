import {
  AlertCircleIcon,
  CheckCircle2Icon,
  ChevronDownIcon,
  ClockIcon,
  PlayIcon,
  ShieldAlertIcon,
  ShieldCheckIcon,
  TerminalIcon,
  UploadCloudIcon,
} from 'lucide-react'
import * as React from 'react'
import { Button } from '#/components/ui/button'
import { Badge } from '#/components/ui/badge'
import { Card } from '#/components/ui/card'
import type { PublishResult, SimulationResult, ValidationResult } from './skill-livegen-types'

interface SkillLiveGenSandboxProps {
  validationData: ValidationResult | null
  simulationData: SimulationResult | null
  publishFeedback: PublishResult | null
  testQueriesText: string
  setTestQueriesText: (val: string) => void
  draftContent: string
  onRunSimulation: () => void
  onPublish: () => void
  isSimulating: boolean
  isPublishing: boolean
}

export function SkillLiveGenSandbox({
  validationData,
  simulationData,
  publishFeedback,
  testQueriesText,
  setTestQueriesText,
  draftContent,
  onRunSimulation,
  onPublish,
  isSimulating,
  isPublishing,
}: SkillLiveGenSandboxProps) {
  const [showLogDrawer, setShowLogDrawer] = React.useState(false)

  // 严格数据安全准入判定：静态规范合规 + 沙箱执行通过 + 零高危拦截
  const isPublishAllowed =
    Boolean(validationData?.valid) &&
    Boolean(simulationData?.sandbox_passed) &&
    (simulationData?.security_blocked_count ?? 0) === 0

  return (
    <div className="flex flex-col gap-3">
      {/* 静态门禁体检报告 */}
      <Card className="p-3.5 bg-card/60 border-border/70 flex flex-col gap-2.5">
        <div className="flex items-center justify-between">
          <div className="text-xs font-semibold font-mono flex items-center gap-1.5 text-foreground">
            <ShieldCheckIcon className="size-3.5 text-cyan-400" /> 规范合规门禁
          </div>
          {validationData?.valid ? (
            <Badge variant="outline" className="text-xs font-mono text-cyan-400 border-cyan-500/40">
              <CheckCircle2Icon className="size-3 mr-1" /> 合规准入
            </Badge>
          ) : (
            <Badge variant="outline" className="text-xs font-mono text-rose-400 border-rose-500/40">
              <AlertCircleIcon className="size-3 mr-1" /> 存在阻断项
            </Badge>
          )}
        </div>

        {validationData?.errors && validationData.errors.length > 0 && (
          <div className="p-2 bg-rose-950/20 border border-rose-500/30 rounded text-xs font-mono text-rose-300 flex flex-col gap-1">
            {validationData.errors.map((err, i) => (
              <div key={i}>• [{err.field}]: {err.message}</div>
            ))}
          </div>
        )}

        <div className="grid grid-cols-2 gap-2 text-xs font-mono text-muted-foreground pt-1">
          <div>名称: <span className="text-foreground">{validationData?.name || '--'}</span></div>
          <div>声明工具: <span className="text-foreground">{validationData?.allowed_tools?.length || 0} 个</span></div>
          <div>正文行数: <span className="text-foreground">{validationData?.body_lines || 0} 行</span></div>
          <div>标签数: <span className="text-foreground">{validationData?.tags?.length || 0} 个</span></div>
        </div>
      </Card>

      {/* 真实受限沙箱与契约演练台 (Card-89 闭环) */}
      <Card className="p-3.5 bg-card/60 border-border/70 flex flex-col gap-2.5">
        <div className="flex items-center justify-between">
          <div className="text-xs font-semibold font-mono flex items-center gap-1.5 text-foreground">
            <PlayIcon className="size-3.5 text-cyan-400" /> 沙箱受限试跑与契约演练台
          </div>
          {simulationData && (
            <div className="flex items-center gap-1.5">
              <Badge variant="outline" className={`text-xs font-mono ${simulationData.sandbox_passed ? 'text-cyan-400 border-cyan-500/40' : 'text-rose-400 border-rose-500/40'}`}>
                {simulationData.sandbox_passed ? '沙箱通过' : '沙箱异常/阻断'}
              </Badge>
              <Badge variant="outline" className="text-xs font-mono text-muted-foreground border-border">
                命中率: {(simulationData.pass_rate * 100).toFixed(0)}%
              </Badge>
            </div>
          )}
        </div>

        {/* 沙箱执行客观物理指标瓦片 */}
        {simulationData && (
          <div className="grid grid-cols-3 gap-2 p-2 bg-muted/20 border border-border/60 rounded text-xs font-mono">
            <div className="flex flex-col">
              <span className="text-muted-foreground flex items-center gap-1">
                <ClockIcon className="size-3 text-cyan-400" /> 真实耗时
              </span>
              <span className="text-foreground font-semibold tabular-nums mt-0.5">
                {simulationData.sandbox_duration_ms?.toFixed(1) || '0.0'} ms
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-muted-foreground flex items-center gap-1">
                <ShieldAlertIcon className="size-3 text-rose-400" /> 安全拦截
              </span>
              <span className={`font-semibold tabular-nums mt-0.5 ${(simulationData.security_blocked_count ?? 0) > 0 ? 'text-rose-400' : 'text-cyan-400'}`}>
                {simulationData.security_blocked_count ?? 0} 项高危
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-muted-foreground flex items-center gap-1">
                <TerminalIcon className="size-3 text-muted-foreground" /> 进程输出
              </span>
              <span className="text-foreground font-semibold tabular-nums mt-0.5">
                {simulationData.stdout ? '有输出' : '纯文本契约'}
              </span>
            </div>
          </div>
        )}

        <div>
          <label className="text-xs font-mono text-muted-foreground">测试 Query 样本 (每行一条):</label>
          <textarea
            value={testQueriesText}
            onChange={(e) => setTestQueriesText(e.target.value)}
            rows={3}
            className="w-full mt-1 p-2 text-xs font-mono bg-background border border-border rounded text-foreground focus:outline-none focus:border-cyan-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="text-xs h-7 font-mono"
            onClick={onRunSimulation}
            disabled={isSimulating || !draftContent}
          >
            <PlayIcon className="size-3.5 mr-1 text-cyan-400" />
            {isSimulating ? '沙箱试跑中...' : '启动沙箱受限试跑'}
          </Button>

          {simulationData && (simulationData.stdout || simulationData.stderr) && (
            <Button
              variant="ghost"
              size="sm"
              className="text-xs h-7 font-mono text-muted-foreground hover:text-foreground"
              onClick={() => setShowLogDrawer(!showLogDrawer)}
            >
              <TerminalIcon className="size-3 mr-1" />
              {showLogDrawer ? '收起终端' : '查看沙箱输出'}
              <ChevronDownIcon className={`size-3 ml-0.5 transition-transform ${showLogDrawer ? 'rotate-180' : ''}`} />
            </Button>
          )}
        </div>

        {/* 白盒输出终端抽屉 */}
        {showLogDrawer && simulationData && (
          <div className="p-2 bg-black/80 border border-border/80 rounded text-xs font-mono text-slate-200 flex flex-col gap-1 max-h-40 overflow-y-auto">
            {simulationData.stdout && (
              <div>
                <span className="text-cyan-400">[STDOUT]</span> {simulationData.stdout}
              </div>
            )}
            {simulationData.stderr && (
              <div className="text-rose-400">
                <span className="text-rose-400">[STDERR]</span> {simulationData.stderr}
              </div>
            )}
          </div>
        )}

        {simulationData?.results && (
          <div className="flex flex-col gap-1.5 max-h-44 overflow-y-auto pt-1">
            {simulationData.results.map((res, idx) => (
              <div key={idx} className="p-2 bg-muted/20 border border-border/60 rounded flex flex-col gap-1">
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="truncate max-w-50 text-foreground">{res.query}</span>
                  {res.matched ? (
                    <span className="text-cyan-400 font-semibold">PASS ({(res.confidence * 100).toFixed(0)}%)</span>
                  ) : (
                    <span className="text-rose-400 font-semibold">MISS ({(res.confidence * 100).toFixed(0)}%)</span>
                  )}
                </div>
                <div className="text-xs font-mono text-muted-foreground">{res.explanation}</div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* 一键发布上架与数据安全防线 */}
      <Card className="p-3.5 bg-card/60 border-border/70 flex flex-col gap-2.5">
        <Button
          variant="default"
          size="sm"
          className="text-xs h-8 font-mono bg-cyan-600 hover:bg-cyan-500 text-white w-full disabled:opacity-50"
          onClick={onPublish}
          disabled={isPublishing || !isPublishAllowed}
        >
          <UploadCloudIcon className="size-3.5 mr-1.5" />
          {isPublishing ? '持久化上架中...' : '一键上架至 Viking 记忆中枢'}
        </Button>

        {/* 数据安全准入状态提示 */}
        {!isPublishAllowed && (
          <div className="text-xs font-mono text-muted-foreground flex items-center gap-1">
            <AlertCircleIcon className="size-3 text-amber-400 shrink-0" />
            {!validationData?.valid
              ? '请先修复规范门禁阻断项'
              : !simulationData
              ? '数据安全防线: 须先启动沙箱受限试跑并通过后方可上架'
              : !simulationData.sandbox_passed
              ? '沙箱试跑未通过或检测到高危系统调用，已物理阻断上架'
              : '准备就绪'}
          </div>
        )}

        {publishFeedback && (
          <div className={`p-2 rounded text-xs font-mono border ${publishFeedback.success ? 'bg-cyan-950/20 border-cyan-500/30 text-cyan-300' : 'bg-rose-950/20 border-rose-500/30 text-rose-300'}`}>
            {publishFeedback.success ? (
              <>
                <div>✅ {publishFeedback.message}</div>
                <div className="text-muted-foreground mt-0.5">指纹: {publishFeedback.content_hash} ｜ 路径: {publishFeedback.target_path}</div>
              </>
            ) : (
              <div>❌ {publishFeedback.message}</div>
            )}
          </div>
        )}
      </Card>
    </div>
  )
}
