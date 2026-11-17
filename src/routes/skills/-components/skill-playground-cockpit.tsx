// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import { TerminalIcon } from 'lucide-react'
import * as React from 'react'
import { Badge } from '#/components/ui/badge'
import { SkillCompressionBench } from './skill-compression-bench'
import { SkillHitTester } from './skill-hit-tester'
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

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-cyan-500/30 bg-cyan-950/15 px-3.5 py-2 text-xs font-mono">
        <div className="flex items-center gap-2 text-foreground">
          <TerminalIcon className="size-4 text-cyan-400" />
          <span className="font-semibold">🧪 技能大盘交互测试沙箱与意图试算器 (Skill Playground)</span>
        </div>
        <Badge variant="outline" className="text-xs font-mono border-cyan-500/40 text-cyan-400">
          零副作用在线试算
        </Badge>
      </div>

      <SkillHitTester draftContent={skillDraft} />
      <SkillCompressionBench skillContent={skillDraft} setSkillContent={setSkillDraft} />
      <SkillScaffoldGenerator onSendToCompression={(content) => setSkillDraft(content)} />
    </div>
  )
}
