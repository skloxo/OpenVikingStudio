import { createFileRoute } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  FlaskConicalIcon,
  ShieldCheckIcon,
  DatabaseIcon,
  MoonIcon,
  LayersIcon,
  GitForkIcon,
  RefreshCwIcon,
  DnaIcon,
  SplitIcon,
  TerminalIcon,
} from 'lucide-react'

import { SkillEvalCockpit } from '../retrieval/-components/skill-eval-cockpit'
import { AHECockpit } from '../retrieval/-components/ahe-cockpit'
import { HermesEvolveCockpit } from '../retrieval/-components/hermes-evolve-cockpit'
import { RSIDayNightCockpit } from '../retrieval/-components/rsi-daynight-cockpit'
import { CapabilityPagesCockpit } from '../retrieval/-components/capability-pages-cockpit'
import { SkillKDCockpit } from '../retrieval/-components/skill-kd-cockpit'
import { EvolutionCICDCockpit } from '../retrieval/-components/evolution-cicd-cockpit'
import { EvolutionLessonsCockpit } from './-components/evolution-lessons-cockpit'
import { HarnessBisectionHealCockpit } from '../harness-logs/-components/harness-bisection-heal-cockpit'
import { HarnessLivePlayground } from '../harness-logs/-components/harness-live-playground'

export type EvolutionTab =
  | 'evolutionCicd'
  | 'lessons'
  | 'hermes'
  | 'bisectionHeal'
  | 'playground'
  | 'skillEval'
  | 'ahe'
  | 'rsi'
  | 'capabilityPages'
  | 'skillKd'

interface EvolutionSearch {
  tab?: EvolutionTab
}

export const Route = createFileRoute('/evolution')({
  validateSearch: (search: Record<string, unknown>): EvolutionSearch => {
    return {
      tab: typeof search.tab === 'string' ? (search.tab as EvolutionTab) : undefined,
    }
  },
  component: EvolutionPage,
})

const TABS: Array<{
  id: EvolutionTab
  label: string
  icon: React.ReactNode
}> = [
  {
    id: 'evolutionCicd',
    label: '🔄 七阶流水线 & Dreaming',
    icon: <RefreshCwIcon className="size-3.5 mr-1 text-cyan-600 dark:text-cyan-400" />,
  },
  {
    id: 'lessons',
    label: '📋 演进教训档案',
    icon: <LayersIcon className="size-3.5 mr-1 text-cyan-600 dark:text-cyan-400" />,
  },
  {
    id: 'hermes',
    label: '🧬 Hermes 经历与微补丁',
    icon: <DatabaseIcon className="size-3.5 mr-1 text-cyan-600 dark:text-cyan-400" />,
  },
  {
    id: 'bisectionHeal',
    label: '⚡ 故障二分自愈',
    icon: <SplitIcon className="size-3.5 mr-1 text-cyan-600 dark:text-cyan-400" />,
  },
  {
    id: 'playground',
    label: '🧪 交互实验场',
    icon: <TerminalIcon className="size-3.5 mr-1 text-cyan-600 dark:text-cyan-400" />,
  },
  {
    id: 'skillEval',
    label: '🧪 技能视网膜',
    icon: <FlaskConicalIcon className="size-3.5 mr-1 text-cyan-600 dark:text-cyan-400" />,
  },
  {
    id: 'ahe',
    label: '🛡️ AHE 自演进',
    icon: <ShieldCheckIcon className="size-3.5 mr-1 text-cyan-600 dark:text-cyan-400" />,
  },
  {
    id: 'rsi',
    label: '🌓 RSI 昼夜策略',
    icon: <MoonIcon className="size-3.5 mr-1 text-cyan-600 dark:text-cyan-400" />,
  },
  {
    id: 'capabilityPages',
    label: '📑 腾讯能力档案',
    icon: <LayersIcon className="size-3.5 mr-1 text-cyan-600 dark:text-cyan-400" />,
  },
  {
    id: 'skillKd',
    label: '🎯 SKILL-KD 蒸馏',
    icon: <GitForkIcon className="size-3.5 mr-1 text-cyan-600 dark:text-cyan-400" />,
  },
]

function EvolutionPage() {
  const { t } = useTranslation('retrieval')
  const [activeTab, setActiveTab] = useState<EvolutionTab>('evolutionCicd')

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search)
      const tabParam = params.get('tab') as EvolutionTab | null
      if (tabParam && TABS.some((tabItem) => tabItem.id === tabParam)) {
        setActiveTab(tabParam)
      }
    }
  }, [])

  return (
    <div className="flex w-full min-w-0 flex-col gap-4">
      {/* 顶部座舱微横幅：定位与态势 */}
      <div className="flex items-center justify-between px-3 py-2 rounded-md border border-border/60 bg-muted/40">
        <div className="flex items-center gap-2">
          <div className="flex items-center justify-center size-6 rounded bg-cyan-100/80 dark:bg-cyan-950/40 text-cyan-700 dark:text-cyan-400 border border-cyan-300 dark:border-cyan-800/40">
            <DnaIcon className="size-3.5" />
          </div>
          <div>
            <div className="text-xs font-semibold text-foreground tracking-tight flex items-center gap-1.5">
              <span>智能体技能演进与生命周期中心</span>
              <span className="text-[12px] font-mono px-1.5 py-0.2 rounded border border-cyan-300 dark:border-cyan-800/40 bg-cyan-100/70 dark:bg-cyan-950/30 text-cyan-800 dark:text-cyan-300">
                7-Tier Cycle Ready
              </span>
            </div>
            <div className="text-[12px] text-muted-foreground">
              承载技能视网膜评测、AHE 沙盒拓扑、Hermes 经历提纯与昼夜 RSI 自进化。
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3 text-[12px] font-mono text-muted-foreground tabular-nums">
          <span>门禁状态: <strong className="text-cyan-600 dark:text-cyan-400 font-semibold">Active</strong></span>
          <span>昼夜节律: <strong className="text-foreground">自驱动</strong></span>
        </div>
      </div>

      {/* 座舱 Tab 导航 */}
      <div className="flex items-center gap-1.5 border-b border-border/60 pb-1 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center rounded-t-md px-3 py-1.5 text-xs font-medium transition-all cursor-pointer whitespace-nowrap ${
              activeTab === tab.id
                ? 'border-b-2 border-cyan-600 dark:border-cyan-400 bg-card text-foreground font-semibold'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted/40'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* 各 Tab 内容渲染 */}
      {activeTab === 'evolutionCicd' && <EvolutionCICDCockpit />}
      {activeTab === 'lessons' && <EvolutionLessonsCockpit />}
      {activeTab === 'hermes' && <HermesEvolveCockpit />}
      {activeTab === 'bisectionHeal' && <HarnessBisectionHealCockpit />}
      {activeTab === 'playground' && <HarnessLivePlayground />}
      {activeTab === 'skillEval' && <SkillEvalCockpit />}
      {activeTab === 'ahe' && <AHECockpit />}
      {activeTab === 'rsi' && <RSIDayNightCockpit />}
      {activeTab === 'capabilityPages' && <CapabilityPagesCockpit />}
      {activeTab === 'skillKd' && <SkillKDCockpit />}
    </div>
  )
}
