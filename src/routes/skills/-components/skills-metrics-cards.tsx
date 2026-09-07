import * as React from 'react'
import { Link } from '@tanstack/react-router'
import {
  ChevronRightIcon,
  ClockIcon,
  CpuIcon,
  LayersIcon,
  ShieldCheckIcon,
  TrendingUpIcon,
  ZapIcon,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Card } from '#/components/ui/card'
import type { SkillHarnessMetrics } from '../-lib/skill-types'

interface SkillsMetricsCardsProps {
  metrics: SkillHarnessMetrics
  totalSkills: number
}

export function SkillsMetricsCards({
  metrics,
  totalSkills,
}: SkillsMetricsCardsProps) {
  const {
    totalCalls,
    blockedCalls,
    findCalls,
    storeCalls,
    activeSkillsCount,
    activeUtilizationRatio,
    lessonsCount,
    builtinLessonsCount,
    autoWakeupRate,
    calculatedSuccessRate,
    calculatedCentralizedRatio,
    contextCompressionRatio,
  } = metrics

  const vkCentralizedCalls = findCalls + storeCalls

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {/* Card 1: 隐式自动唤醒率 */}
      <Card className="flex flex-col gap-1 p-2.5 shadow-none hover:border-border transition-colors">
        <div className="flex items-center justify-between text-xs text-muted-foreground font-sans">
          <span className="flex items-center gap-1.5 text-foreground font-medium">
            <ZapIcon className="size-3.5 text-muted-foreground" />
            隐式自动唤醒率
          </span>
          <Badge
            variant="outline"
            className="text-[11px] font-mono border-border bg-muted/40 text-foreground px-1 py-0"
          >
            意图感应
          </Badge>
        </div>
        <div className="font-mono text-lg font-bold tabular-nums text-foreground flex items-baseline gap-1">
          {autoWakeupRate !== null ? `${autoWakeupRate}%` : '--'}{' '}
          <span className="text-xs font-normal text-muted-foreground">
            {autoWakeupRate !== null ? '唤醒成功' : '暂无采样'}
          </span>
        </div>
        <p className="text-[11px] text-muted-foreground truncate">
          {autoWakeupRate !== null
            ? '零命令感应 · 意图静默触发'
            : '等待 Agent 意图唤醒采样...'}
        </p>
      </Card>

      {/* Card 2: 技能运行成功率 */}
      <Card
        className="flex flex-col gap-1 p-2.5 shadow-none hover:border-border transition-colors"
        title="监测近 24 小时技能被 Agent 唤醒后的执行成功率，反映技能运行情况与闭环质量"
      >
        <div className="flex items-center justify-between text-xs text-muted-foreground font-sans">
          <span className="flex items-center gap-1.5 text-foreground font-medium">
            <TrendingUpIcon className="size-3.5 text-muted-foreground" />
            技能运行成功率
          </span>
          <Badge
            variant="outline"
            className="text-[11px] font-mono border-border bg-muted/40 text-foreground px-1 py-0"
          >
            闭环质量
          </Badge>
        </div>
        <div className="font-mono text-lg font-bold tabular-nums text-foreground flex items-baseline gap-1">
          {calculatedSuccessRate !== null
            ? `${calculatedSuccessRate}%`
            : '--'}{' '}
          <span className="text-xs font-normal text-muted-foreground">
            {calculatedSuccessRate !== null ? '(物理闭环)' : '(暂无数据)'}
          </span>
        </div>
        <p className="text-[11px] text-muted-foreground truncate">
          {totalCalls > 0
            ? `近 24H ${totalCalls} 次执行${blockedCalls > 0 ? ` (${blockedCalls} 次阻断)` : '零挂起'}`
            : '近 24H 暂无物理执行采样'}
        </p>
      </Card>

      {/* Card 3: OpenViking 技能统一收敛率 */}
      <Card
        className="flex flex-col gap-1 p-2.5 shadow-none hover:border-border transition-colors"
        title="监测近 24 小时 Agent 调用走 OpenViking 技能中心 vs 私有渠道的比率"
      >
        <div className="flex items-center justify-between text-xs text-muted-foreground font-sans">
          <span className="flex items-center gap-1.5 text-foreground font-medium">
            <CpuIcon className="size-3.5 text-muted-foreground" />
            VK 技能统一收敛率
          </span>
          <Badge
            variant="outline"
            className="text-[11px] font-mono border-border bg-muted/40 text-foreground px-1 py-0"
          >
            踩坑演进飞轮
          </Badge>
        </div>
        <div className="font-mono text-lg font-bold tabular-nums text-foreground flex items-baseline gap-1">
          {calculatedCentralizedRatio !== null
            ? `${calculatedCentralizedRatio}%`
            : '--'}{' '}
          <span className="text-xs font-normal text-muted-foreground">
            {calculatedCentralizedRatio !== null
              ? '(走 VK 技能中心)'
              : '(暂无数据)'}
          </span>
        </div>
        <p className="text-[11px] text-muted-foreground truncate">
          {vkCentralizedCalls > 0
            ? `近 24H ${vkCentralizedCalls} 次 VK 集中调用`
            : '近 24H 暂无集中通道采样'}
        </p>
      </Card>

      {/* Card 4: 技能资产活跃复用率 */}
      <Card
        className="flex flex-col gap-1 p-2.5 shadow-none hover:border-border transition-colors"
        title="监测已装载的标准技能中，近 24H 真正被 Agent 命中调用的技能数量与活跃率"
      >
        <div className="flex items-center justify-between text-xs text-muted-foreground font-sans">
          <span className="flex items-center gap-1.5 text-foreground font-medium">
            <LayersIcon className="size-3.5 text-muted-foreground" />
            技能资产活跃复用率
          </span>
          <Badge
            variant="outline"
            className="text-[11px] font-mono border-border bg-muted/40 text-foreground px-1 py-0"
          >
            资产健康度
          </Badge>
        </div>
        <div className="font-mono text-lg font-bold tabular-nums text-foreground flex items-baseline gap-1">
          {activeUtilizationRatio !== null
            ? `${activeUtilizationRatio}%`
            : '--'}{' '}
          <span className="text-xs font-normal text-muted-foreground">
            ({activeSkillsCount}/{totalSkills} 项活跃)
          </span>
        </div>
        <p className="text-[11px] text-muted-foreground truncate">
          {totalSkills > 0
            ? `已装载 ${totalSkills} 项技能 · 防范僵尸技能`
            : '已接入标准化技能资产库'}
        </p>
      </Card>

      {/* Card 5: SOP 提示词 Context 压缩率 */}
      <Card
        className="flex flex-col gap-1 p-2.5 shadow-none hover:border-border transition-colors"
        title="监测通过 L0 意图按需唤醒 + L1 SOP 结构化注入，相比把全量 Prompt 塞给 Agent 节省的上下文 Token 比率"
      >
        <div className="flex items-center justify-between text-xs text-muted-foreground font-sans">
          <span className="flex items-center gap-1.5 text-foreground font-medium">
            <ShieldCheckIcon className="size-3.5 text-muted-foreground" />
            Context 提示词压缩率
          </span>
          <Badge
            variant="outline"
            className="text-[11px] font-mono border-border bg-muted/40 text-foreground px-1 py-0"
          >
            Token 降本
          </Badge>
        </div>
        <div className="font-mono text-lg font-bold tabular-nums text-foreground flex items-baseline gap-1">
          {contextCompressionRatio !== null
            ? `${contextCompressionRatio}%`
            : '--'}{' '}
          <span className="text-xs font-normal text-muted-foreground">
            {contextCompressionRatio !== null
              ? '(节省 Context)'
              : '(暂无采样)'}
          </span>
        </div>
        <p className="text-[11px] text-muted-foreground truncate">
          {contextCompressionRatio !== null
            ? '按需结构化注入 · 大幅降低 Token 冗余'
            : '等待按需 SOP 注入采样...'}
        </p>
      </Card>

      {/* Card 6: Harness 技能自演进 */}
      <Link
        to="/harness-logs"
        className="flex flex-col gap-1 rounded border border-border/60 bg-card p-2.5 hover:border-border transition-colors group cursor-pointer shadow-none"
        title="点击白盒查看 Harness 技能自动规范化与自演进审计日志"
      >
        <div className="flex items-center justify-between text-xs text-muted-foreground font-sans">
          <span className="flex items-center gap-1.5 text-foreground font-medium">
            <ClockIcon className="size-3.5 text-muted-foreground" />
            Harness 技能自演进
          </span>
          <Badge
            variant="outline"
            className="text-[11px] font-mono border-border bg-muted/40 text-foreground px-1 py-0"
          >
            白盒审计 ➔
          </Badge>
        </div>
        <div className="flex items-center gap-3 font-mono tabular-nums">
          <div className="flex flex-col">
            <span className="text-lg font-bold text-foreground">
              {builtinLessonsCount !== null ? builtinLessonsCount : '--'}
            </span>
            <span className="text-xs text-muted-foreground font-sans">
              预置规约
            </span>
          </div>
          <div className="text-muted-foreground/30 text-lg font-thin">|</div>
          <div className="flex flex-col">
            <span className="text-lg font-bold text-foreground">
              {lessonsCount !== null ? lessonsCount : '--'}
            </span>
            <span className="text-xs text-muted-foreground font-sans">
              动态演进
            </span>
          </div>
        </div>
        <p className="text-xs text-muted-foreground truncate flex items-center justify-between">
          <span>预置标准规约 + 动态踩坑演进双轨驱动</span>
          <ChevronRightIcon className="size-3.5 text-muted-foreground group-hover:translate-x-0.5 transition-transform" />
        </p>
      </Link>
    </div>
  )
}
