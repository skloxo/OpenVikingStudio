/**
 * hook-lifecycle-matrix.tsx
 * Agent Hook 核心生命周期与被动注入控制矩阵 (SSOT)。
 * 整组选用、一键装配，彻底切除细粒度单选复选框。
 * 遵循高密性冷淡设计规范 (字号 >= 12px, NO GREEN EVER)。
 */
import { ShieldCheckIcon, CheckIcon } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

export type HookLifecycleMatrixProps = {
  enabled?: boolean
  onToggleEnabled?: (enabled: boolean) => void
  disabled?: boolean
  // 兼容旧调用点，避免类型断言报错
  autoRecall?: boolean
  onToggleAutoRecall?: () => void
  autoCapture?: boolean
  onToggleAutoCapture?: () => void
  preToolGuard?: boolean
  onTogglePreToolGuard?: () => void
}

export function HookLifecycleMatrix({
  enabled = true,
  onToggleEnabled,
  disabled = false,
}: HookLifecycleMatrixProps) {
  const handleToggle = () => {
    if (disabled) return
    onToggleEnabled?.(!enabled)
  }

  return (
    <div className="space-y-2 pt-2 border-t border-border/40 font-sans text-xs">
      {/* 头部标题与整组选用开关 */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <ShieldCheckIcon className="size-3.5 text-cyan-500 shrink-0" />
          <span className="font-semibold text-foreground text-xs">
            Hook 核心生命周期与被动注入控制
          </span>
          <Badge variant="outline" className="text-xs font-mono font-normal">
            整组包含 3 项被动钩子
          </Badge>
        </div>

        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={disabled}
          onClick={handleToggle}
          className={`h-6 px-2 text-xs font-sans transition-all cursor-pointer ${
            enabled
              ? 'border-cyan-500/40 text-cyan-600 dark:text-cyan-400 bg-cyan-500/10 hover:bg-cyan-500/15'
              : 'border-border/60 text-muted-foreground hover:text-foreground hover:bg-muted/30'
          }`}
        >
          {enabled ? (
            <span className="flex items-center gap-1 font-medium">
              <CheckIcon className="size-3 stroke-2.5" />
              已整组装配
            </span>
          ) : (
            <span>点击整组选用 →</span>
          )}
        </Button>
      </div>

      {/* 整组套件所包含的三大神经反射弧卡片 (纯展示，不可拆分微操) */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        {/* 1. 先验记忆自动预取 */}
        <div
          className={`p-2.5 rounded-md border text-left transition-all select-none space-y-1 ${
            enabled
              ? 'border-cyan-500/30 bg-cyan-500/5 text-foreground'
              : 'border-border/40 bg-muted/10 opacity-60 text-muted-foreground'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="font-medium text-xs text-foreground">
              🧠 先验记忆自动预取
            </span>
            <Badge
              variant="outline"
              className={`text-xs font-mono h-4 px-1 ${
                enabled
                  ? 'border-cyan-500/30 text-cyan-600 dark:text-cyan-400'
                  : 'border-border/60 text-muted-foreground'
              }`}
            >
              Prompt 前置
            </Badge>
          </div>
          <div className="text-xs text-muted-foreground leading-relaxed">
            模型组装提示词前，自动从体外大脑检索相关经验注入 System Prompt
          </div>
        </div>

        {/* 2. 轮次经验自动沉淀 */}
        <div
          className={`p-2.5 rounded-md border text-left transition-all select-none space-y-1 ${
            enabled
              ? 'border-cyan-500/30 bg-cyan-500/5 text-foreground'
              : 'border-border/40 bg-muted/10 opacity-60 text-muted-foreground'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="font-medium text-xs text-foreground">
              📥 轮次经验自动沉淀
            </span>
            <Badge
              variant="outline"
              className={`text-xs font-mono h-4 px-1 ${
                enabled
                  ? 'border-cyan-500/30 text-cyan-600 dark:text-cyan-400'
                  : 'border-border/60 text-muted-foreground'
              }`}
            >
              对话后置
            </Badge>
          </div>
          <div className="text-xs text-muted-foreground leading-relaxed">
            单轮会话结束后，自动捕获助手输出的新结论与踩坑事实并入库
          </div>
        </div>

        {/* 3. 工具前置安全守卫 */}
        <div
          className={`p-2.5 rounded-md border text-left transition-all select-none space-y-1 ${
            enabled
              ? 'border-cyan-500/30 bg-cyan-500/5 text-foreground'
              : 'border-border/40 bg-muted/10 opacity-60 text-muted-foreground'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="font-medium text-xs text-foreground">
              🛡️ 工具前置安全守卫
            </span>
            <Badge
              variant="outline"
              className={`text-xs font-mono h-4 px-1 ${
                enabled
                  ? 'border-cyan-500/30 text-cyan-600 dark:text-cyan-400'
                  : 'border-border/60 text-muted-foreground'
              }`}
            >
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
