import { Badge } from '#/components/ui/badge'
import {
  Code2Icon,
  EyeIcon,
  GitBranchIcon,
  ShieldCheckIcon,
  SparklesIcon,
  UsersIcon,
} from 'lucide-react'

export interface GateSpec {
  name: string
  status: string
  badge: string
  description: string
  rules: string[]
}

export interface GateDashboardProps {
  gates?: Record<string, GateSpec>
}

export function HarnessGateDashboard({ gates }: GateDashboardProps) {
  const defaultGates: Record<string, GateSpec> = {
    physical_diff: {
      name: '物理增量代码门禁 (Physical Diff Gate)',
      status: 'active',
      badge: 'Active Invariant',
      description: '严格剔除纯空格与纯注释伪变更，断言物理有效改动行 > 0',
      rules: ['min_effective_lines >= 1', 'comment_only_filtered', 'whitespace_filtered', 'git_tree_asserted'],
    },
    test_retina: {
      name: '测试视网膜反欺诈门禁 (Anti-Cheat Retina)',
      status: 'active',
      badge: 'Active Invariant',
      description: '拦截 false exit 0 假绿灯，真实校验 passed > 0 且 failed == 0',
      rules: ['real_process_execution', 'test_report_parsed', 'false_exit_zero_blocked', 'duration_tracked'],
    },
    anti_lazy: {
      name: '防偷懒代码省略占位符护栏 (Anti-Lazy Code Guard)',
      status: 'active',
      badge: 'Active Invariant',
      description: 'AST 与正则实时扫描，物理封杀 pass、# TODO、...、NotImplementedError',
      rules: ['prohibit_pass_stub', 'prohibit_todo_stub', 'prohibit_ellipsis', 'zero_omission_tolerance'],
    },
    role_separation: {
      name: '生成与评估角色隔离 (Role Separation)',
      status: 'active',
      badge: 'Active Invariant',
      description: '物理隔离生成者与评估者，防止智能体自问自答自批改作弊',
      rules: ['generator_not_evaluator', 'checkpoint_sha256_verified', 'dual_axis_standards_spec'],
    },
    cpa_teacher_guard: {
      name: 'CPA 教师模型守卫拦截器 (CPA Teacher Model Guard)',
      status: 'active',
      badge: 'Active Invariant',
      description: '毫秒级物理拦截工兵任务/批量并发滥用昂贵教师模型 (GPT/Claude)，确保教师零泄漏、工兵高吞吐',
      rules: [
        'teacher_models_restricted_to_deadlock_and_tradeoff',
        'worker_pool_unlimited_throughput',
        'pre_tool_interception_sub_2ms',
        'discovery_to_card_proposal_enforced',
      ],
    },
  }

  const activeGates = gates && Object.keys(gates).length > 0 ? gates : defaultGates

  const gateIcons: Record<string, React.ReactNode> = {
    physical_diff: <GitBranchIcon className="size-4 text-cyan-400" />,
    test_retina: <EyeIcon className="size-4 text-cyan-400" />,
    anti_lazy: <Code2Icon className="size-4 text-cyan-400" />,
    role_separation: <UsersIcon className="size-4 text-cyan-400" />,
    cpa_teacher_guard: <SparklesIcon className="size-4 text-cyan-400" />,
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-3">
        <div className="flex items-center gap-2">
          <ShieldCheckIcon className="size-4 text-cyan-400" />
          <h3 className="text-sm font-semibold tracking-wide">
            五大物理贯彻执行门禁 (Five Invariant Enforcement Gates)
          </h3>
          <Badge variant="outline" className="border-cyan-500/30 bg-cyan-500/10 text-xs text-cyan-300">
            100% 物理拦截闭环
          </Badge>
        </div>
        <div className="text-xs text-muted-foreground">
          保障交付真实性，切除合成回路与虚假绿灯
        </div>
      </div>

      {/* 4 Invariant Cards */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {Object.entries(activeGates).map(([key, gate]) => {
          const icon = gateIcons[key] ?? <ShieldCheckIcon className="size-4 text-cyan-400" />
          return (
            <div
              key={key}
              className="flex flex-col justify-between rounded-md border border-border/70 bg-card/60 p-3.5 transition-colors hover:border-cyan-500/40"
            >
              <div>
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    {icon}
                    <h4 className="text-xs font-semibold text-foreground">{gate.name}</h4>
                  </div>
                  <Badge
                    variant="outline"
                    className="border-cyan-500/30 bg-cyan-500/10 text-xs text-cyan-300 font-mono"
                  >
                    {gate.badge}
                  </Badge>
                </div>
                <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
                  {gate.description}
                </p>
              </div>

              <div className="mt-3 border-t border-border/40 pt-2.5">
                <div className="mb-1.5 text-xs font-medium text-muted-foreground">
                  物理契约与生效规则 (Enforced Invariant Rules):
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {gate.rules.map((rule, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center rounded border border-border/60 bg-muted/40 px-1.5 py-0.5 font-mono text-xs text-muted-foreground"
                    >
                      {rule}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
