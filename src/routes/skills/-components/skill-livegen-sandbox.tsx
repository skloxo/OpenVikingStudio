import {
  AlertCircleIcon,
  CheckCircle2Icon,
  PlayIcon,
  ShieldCheckIcon,
  UploadCloudIcon,
} from 'lucide-react'
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

      {/* 自然语言沙盒演练台 */}
      <Card className="p-3.5 bg-card/60 border-border/70 flex flex-col gap-2.5">
        <div className="flex items-center justify-between">
          <div className="text-xs font-semibold font-mono flex items-center gap-1.5 text-foreground">
            <PlayIcon className="size-3.5 text-cyan-400" /> 触发沙盒演练台
          </div>
          {simulationData && (
            <Badge variant="outline" className="text-xs font-mono text-cyan-400 border-cyan-500/40">
              命中率: {(simulationData.pass_rate * 100).toFixed(0)}% ({simulationData.passed_queries}/{simulationData.total_queries})
            </Badge>
          )}
        </div>

        <div>
          <label className="text-xs font-mono text-muted-foreground">测试 Query 样本 (每行一条):</label>
          <textarea
            value={testQueriesText}
            onChange={(e) => setTestQueriesText(e.target.value)}
            rows={3}
            className="w-full mt-1 p-2 text-xs font-mono bg-background border border-border rounded text-foreground focus:outline-none focus:border-cyan-500"
          />
        </div>

        <Button
          variant="outline"
          size="sm"
          className="text-xs h-7 font-mono self-start"
          onClick={onRunSimulation}
          disabled={isSimulating || !draftContent}
        >
          <PlayIcon className="size-3.5 mr-1 text-cyan-400" />
          运行沙盒测试
        </Button>

        {simulationData?.results && (
          <div className="flex flex-col gap-1.5 max-h-48 overflow-y-auto pt-1">
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

      {/* 一键发布上架 */}
      <Card className="p-3.5 bg-card/60 border-border/70 flex flex-col gap-2.5">
        <Button
          variant="default"
          size="sm"
          className="text-xs h-8 font-mono bg-cyan-600 hover:bg-cyan-500 text-white w-full"
          onClick={onPublish}
          disabled={isPublishing || !validationData?.valid}
        >
          <UploadCloudIcon className="size-3.5 mr-1.5" />
          一键上架至 Viking 记忆中枢
        </Button>

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
