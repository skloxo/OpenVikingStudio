// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import { TerminalIcon } from 'lucide-react'
import * as React from 'react'
import { Badge } from '#/components/ui/badge'
import { SkillCompressionBench } from './skill-compression-bench'
import { SkillHitTester } from './skill-hit-tester'
import { SkillLiveGenCockpit } from './skill-livegen-cockpit'
import { SkillOptCockpit } from './skill-opt-cockpit'
import { SkillScaffoldGenerator } from './skill-scaffold-generator'

const DEFAULT_DRAFT = `---
name: sample-ops
domain: observability
description: Inspect runtime service logs and verify health endpoints
triggers:
  - inspect service logs
---

## 1. Interface
- Inputs: target service URL and timeout

## 2. Workflow
1. Probe /health endpoint with 5s timeout
2. Report observed status code

## 3. Protocol
- Fail fast on repeated transport errors

## 4. Rules
- NO GREEN EVER: use cyan-500 for healthy state

## 5. Contracts
- Never dump raw API keys into logs

## 6. Evidence
- Attach live HTTP status output
`

export function SkillPlaygroundCockpit() {
  const [skillDraft, setSkillDraft] = React.useState(DEFAULT_DRAFT)
  const [playgroundTab, setPlaygroundTab] = React.useState<'sandbox' | 'livegen' | 'optimizer'>('sandbox')

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-cyan-500/30 bg-cyan-950/15 px-3.5 py-2 text-xs font-mono">
        <div className="flex items-center gap-2 text-foreground">
          <TerminalIcon className="size-4 text-cyan-400" />
          <span className="font-semibold">🧪 技能大盘交互测试沙箱与意图试算器 (Skill Playground)</span>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {[
            { id: 'sandbox', label: '意图试算与压缩' },
            { id: 'livegen', label: 'LiveGen 在线生成' },
            { id: 'optimizer', label: 'SkillOpt 审计调优' },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setPlaygroundTab(tab.id as 'sandbox' | 'livegen' | 'optimizer')}
              className={`rounded px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer ${
                playgroundTab === tab.id
                  ? 'bg-cyan-500 text-slate-950 font-semibold'
                  : 'border border-border/60 bg-background/60 text-muted-foreground hover:text-foreground'
              }`}
            >
              {tab.label}
            </button>
          ))}
          <Badge variant="outline" className="text-xs font-mono border-cyan-500/40 text-cyan-400">
            零副作用在线试算
          </Badge>
        </div>
      </div>

      {playgroundTab === 'sandbox' && (
        <>
          <SkillHitTester draftContent={skillDraft} />
          <SkillCompressionBench skillContent={skillDraft} setSkillContent={setSkillDraft} />
          <SkillScaffoldGenerator onSendToCompression={(content) => setSkillDraft(content)} />
        </>
      )}
      {playgroundTab === 'livegen' && <SkillLiveGenCockpit />}
      {playgroundTab === 'optimizer' && <SkillOptCockpit />}
    </div>
  )
}
