/**
 * hook-lifecycle-matrix.tsx
 * Agent Hook 核心生命周期与被动注入控制矩阵 (SSOT)。
 * 涵盖先验记忆自动预取、轮次经验自动沉淀与工具前置安全守卫三大神经反射弧。
 * 遵循高密性冷淡设计规范 (字号 >= 12px, NO GREEN EVER)。
 */
import { CheckSquareIcon, ShieldCheckIcon, SquareIcon } from 'lucide-react'
import { Badge } from '#/components/ui/badge'

export type HookLifecycleMatrixProps = {
  autoRecall: boolean
  onToggleAutoRecall: () => void
  autoCapture: boolean
  onToggleAutoCapture: () => void
  preToolGuard: boolean
  onTogglePreToolGuard: () => void
  disabled?: boolean
}

export function HookLifecycleMatrix({
  autoRecall,
  onToggleAutoRecall,
  autoCapture,
  onToggleAutoCapture,
  preToolGuard,
  onTogglePreToolGuard,
  disabled = false,
}: HookLifecycleMatrixProps) {
  const activeCount = [autoRecall, autoCapture, preToolGuard].filter(Boolean).length

  return (
    <div className="space-y-2 pt-2 border-t border-border/40 font-sans text-xs">
      <div className="flex items-center justify-between">
        <span className="font-semibold text-foreground flex items-center gap-1.5">
          <ShieldCheckIcon className="size-3.5 text-cyan-500" />
          Hook 核心生命周期与被动注入控制
        </span>
        <span className="text-xs text-muted-foreground font-mono">
          已启用 {activeCount} / 3 项被动钩子
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        {/* 1. 先验记忆自动预取 */}
        <div
          onClick={() => !disabled && onToggleAutoRecall()}
          className={`p-2.5 rounded-md border text-left transition-all select-none space-y-1 ${
            disabled ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'
          } ${
            autoRecall
              ? 'border-cyan-500/60 bg-cyan-500/10 text-foreground'
              : 'border-border/60 bg-muted/10 text-muted-foreground hover:bg-muted/20'
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 font-medium text-xs">
              {autoRecall ? (
                <CheckSquareIcon className="size-3.5 text-cyan-500" />
              ) : (
                <SquareIcon className="size-3.5 text-muted-foreground" />
              )}
              <span>🧠 先验记忆自动预取</span>
            </div>
            <Badge variant="outline" className="text-xs font-mono h-4 px-1 border-border/60">
              Prompt 前置
            </Badge>
          </div>
          <div className="text-xs text-muted-foreground leading-relaxed">
            模型组装提示词前，自动从体外大脑检索相关经验注入 System Prompt
          </div>
        </div>

        {/* 2. 轮次经验自动沉淀 */}
        <div
          onClick={() => !disabled && onToggleAutoCapture()}
          className={`p-2.5 rounded-md border text-left transition-all select-none space-y-1 ${
            disabled ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'
          } ${
            autoCapture
              ? 'border-cyan-500/60 bg-cyan-500/10 text-foreground'
              : 'border-border/60 bg-muted/10 text-muted-foreground hover:bg-muted/20'
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 font-medium text-xs">
              {autoCapture ? (
                <CheckSquareIcon className="size-3.5 text-cyan-500" />
              ) : (
                <SquareIcon className="size-3.5 text-muted-foreground" />
              )}
              <span>📥 轮次经验自动沉淀</span>
            </div>
            <Badge variant="outline" className="text-xs font-mono h-4 px-1 border-border/60">
              对话后置
            </Badge>
          </div>
          <div className="text-xs text-muted-foreground leading-relaxed">
            单轮会话结束后，自动捕获助手输出的新结论与踩坑事实并入库
          </div>
        </div>

        {/* 3. 工具前置安全守卫 */}
        <div
          onClick={() => !disabled && onTogglePreToolGuard()}
          className={`p-2.5 rounded-md border text-left transition-all select-none space-y-1 ${
            disabled ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'
          } ${
            preToolGuard
              ? 'border-cyan-500/60 bg-cyan-500/10 text-foreground'
              : 'border-border/60 bg-muted/10 text-muted-foreground hover:bg-muted/20'
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 font-medium text-xs">
              {preToolGuard ? (
                <CheckSquareIcon className="size-3.5 text-cyan-500" />
              ) : (
                <SquareIcon className="size-3.5 text-muted-foreground" />
              )}
              <span>🛡️ 工具前置安全守卫</span>
            </div>
            <Badge variant="outline" className="text-xs font-mono h-4 px-1 border-border/60">
              工具拦截
            </Badge>
          </div>
          <div className="text-xs text-muted-foreground leading-relaxed">
            工具执行前拦截敏感 Key 泄露、检测目标路径越权，确保安全沙箱
          </div>
        </div>
      </div>
    </div>
  )
}
