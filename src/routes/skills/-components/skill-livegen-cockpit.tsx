// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  PlayIcon,
  ShieldCheckIcon,
  SparklesIcon,
  UploadCloudIcon,
  Wand2Icon,
} from 'lucide-react'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import { ovClient } from '#/lib/ov-client'
import { SKILL_LIVEGEN_PRESETS } from '../-constants/skill-livegen-presets'
import type { SkillLiveGenPreset } from '../-constants/skill-livegen-presets'
import { SkillLiveGenEditor } from './skill-livegen-editor'
import { SkillLiveGenSandbox } from './skill-livegen-sandbox'
import type {
  LiveGenStats,
  PublishResult,
  SimulationResult,
  ValidationResult,
} from './skill-livegen-types'

export function SkillLiveGenCockpit() {
  const [selectedPreset, setSelectedPreset] = React.useState<SkillLiveGenPreset>(SKILL_LIVEGEN_PRESETS[0])
  const [skillName, setSkillName] = React.useState(selectedPreset.name)
  const [skillDescription, setSkillDescription] = React.useState(selectedPreset.description)
  const [templateType, setTemplateType] = React.useState(selectedPreset.templateType)
  const [allowedToolsStr, setAllowedToolsStr] = React.useState(selectedPreset.allowedTools.join(', '))
  const [draftContent, setDraftContent] = React.useState('')
  const [testQueriesText, setTestQueriesText] = React.useState(selectedPreset.sampleQueries.join('\n'))

  const [validationData, setValidationData] = React.useState<ValidationResult | null>(null)
  const [simulationData, setSimulationData] = React.useState<SimulationResult | null>(null)
  const [publishFeedback, setPublishFeedback] = React.useState<PublishResult | null>(null)

  // 1. Stats Query
  const { data: stats, refetch: refetchStats } = useQuery<LiveGenStats>({
    queryKey: ['skill-livegen-stats'],
    queryFn: async () => {
      return (await ovClient.instance.get<LiveGenStats>('/api/v1/skills/livegen/stats')).data
    },
    refetchInterval: false,
    staleTime: 15_000,
  })

  // 2. Scaffold Mutation
  const scaffoldMutation = useMutation({
    mutationFn: async () => {
      const tools = allowedToolsStr.split(/[, ]+/).filter(Boolean)
      const res = await ovClient.instance.post<{ content: string }>('/api/v1/skills/livegen/scaffold', {
        name: skillName,
        description: skillDescription,
        allowed_tools: tools,
        template_type: templateType,
      })
      return res.data
    },
    onSuccess: (data) => {
      setDraftContent(data.content)
      setPublishFeedback(null)
      refetchStats()
      validateMutation.mutate(data.content)
    },
  })

  // 3. Validation Mutation
  const validateMutation = useMutation({
    mutationFn: async (content: string) => {
      const res = await ovClient.instance.post<ValidationResult>('/api/v1/skills/livegen/validate', {
        content,
        strict: true,
      })
      return res.data
    },
    onSuccess: (data) => {
      setValidationData(data)
      refetchStats()
    },
  })

  // 4. Simulate Mutation
  const simulateMutation = useMutation({
    mutationFn: async () => {
      const queries = testQueriesText.split('\n').map((q) => q.trim()).filter(Boolean)
      const res = await ovClient.instance.post<SimulationResult>('/api/v1/skills/livegen/simulate', {
        content: draftContent,
        queries,
      })
      return res.data
    },
    onSuccess: (data) => {
      setSimulationData(data)
      refetchStats()
    },
  })

  // 5. Publish Mutation
  const publishMutation = useMutation({
    mutationFn: async () => {
      const res = await ovClient.instance.post<PublishResult>('/api/v1/skills/livegen/publish', {
        skill_name: skillName,
        content: draftContent,
      })
      return res.data
    },
    onSuccess: (data) => {
      setPublishFeedback(data)
      refetchStats()
    },
  })

  // Load default preset on mount
  React.useEffect(() => {
    handleLoadPreset(SKILL_LIVEGEN_PRESETS[0])
  }, [])

  const handleLoadPreset = (preset: SkillLiveGenPreset) => {
    setSelectedPreset(preset)
    setSkillName(preset.name)
    setSkillDescription(preset.description)
    setTemplateType(preset.templateType)
    setAllowedToolsStr(preset.allowedTools.join(', '))
    setTestQueriesText(preset.sampleQueries.join('\n'))

    const tools = preset.allowedTools
    ovClient.instance.post<{ content: string }>('/api/v1/skills/livegen/scaffold', {
      name: preset.name,
      description: preset.description,
      allowed_tools: tools,
      template_type: preset.templateType,
    }).then((res) => {
      setDraftContent(res.data.content)
      validateMutation.mutate(res.data.content)
    })
  }

  return (
    <div className="flex flex-col gap-4">
      {/* 顶部指标瓦片 */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card className="p-3 bg-card/60 border-border/70 flex flex-col justify-between">
          <div className="text-xs font-mono text-muted-foreground flex items-center gap-1">
            <Wand2Icon className="size-3 text-cyan-400" /> 创生草稿数
          </div>
          <div className="text-lg font-mono font-semibold tabular-nums text-foreground mt-1">
            {stats?.total_scaffolds ?? 0}
          </div>
        </Card>
        <Card className="p-3 bg-card/60 border-border/70 flex flex-col justify-between">
          <div className="text-xs font-mono text-muted-foreground flex items-center gap-1">
            <ShieldCheckIcon className="size-3 text-cyan-400" /> 规范静态门禁
          </div>
          <div className="text-lg font-mono font-semibold tabular-nums text-foreground mt-1">
            {stats?.total_validations ?? 0}
          </div>
        </Card>
        <Card className="p-3 bg-card/60 border-border/70 flex flex-col justify-between">
          <div className="text-xs font-mono text-muted-foreground flex items-center gap-1">
            <PlayIcon className="size-3 text-cyan-400" /> 沙盒演练次数
          </div>
          <div className="text-lg font-mono font-semibold tabular-nums text-foreground mt-1">
            {stats?.total_simulations ?? 0}
          </div>
        </Card>
        <Card className="p-3 bg-card/60 border-border/70 flex flex-col justify-between">
          <div className="text-xs font-mono text-muted-foreground flex items-center gap-1">
            <UploadCloudIcon className="size-3 text-cyan-400" /> 成功上架中枢
          </div>
          <div className="text-lg font-mono font-semibold tabular-nums text-cyan-400 mt-1">
            {stats?.total_published ?? 0}
          </div>
        </Card>
      </div>

      {/* 预设快速载入 */}
      <div className="flex flex-wrap items-center gap-2 p-2.5 rounded-md border border-border/60 bg-muted/20">
        <span className="text-xs font-mono text-muted-foreground flex items-center gap-1">
          <SparklesIcon className="size-3.5 text-cyan-400" /> 预设脚手架:
        </span>
        {SKILL_LIVEGEN_PRESETS.map((preset) => (
          <Button
            key={preset.id}
            variant={selectedPreset.id === preset.id ? 'default' : 'outline'}
            size="sm"
            className={`text-xs h-6 px-2 font-mono ${selectedPreset.id === preset.id ? 'bg-cyan-600 text-white' : 'text-foreground'}`}
            onClick={() => handleLoadPreset(preset)}
          >
            {preset.title}
          </Button>
        ))}
      </div>

      {/* 主工作台: 双栏布局 */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* 左栏: 脚手架配置与 Markdown 编辑器 (7 cols) */}
        <div className="lg:col-span-7">
          <SkillLiveGenEditor
            skillName={skillName}
            setSkillName={setSkillName}
            skillDescription={skillDescription}
            setSkillDescription={setSkillDescription}
            allowedToolsStr={allowedToolsStr}
            setAllowedToolsStr={setAllowedToolsStr}
            draftContent={draftContent}
            setDraftContent={(val) => {
              setDraftContent(val)
              validateMutation.mutate(val)
            }}
            onGenerateScaffold={() => scaffoldMutation.mutate()}
            onValidate={() => validateMutation.mutate(draftContent)}
            isScaffolding={scaffoldMutation.isPending}
            isValidating={validateMutation.isPending}
          />
        </div>

        {/* 右栏: 门禁体检报告与沙盒测试 (5 cols) */}
        <div className="lg:col-span-5">
          <SkillLiveGenSandbox
            validationData={validationData}
            simulationData={simulationData}
            publishFeedback={publishFeedback}
            testQueriesText={testQueriesText}
            setTestQueriesText={setTestQueriesText}
            draftContent={draftContent}
            onRunSimulation={() => simulateMutation.mutate()}
            onPublish={() => publishMutation.mutate()}
            isSimulating={simulateMutation.isPending}
            isPublishing={publishMutation.isPending}
          />
        </div>
      </div>
    </div>
  )
}
