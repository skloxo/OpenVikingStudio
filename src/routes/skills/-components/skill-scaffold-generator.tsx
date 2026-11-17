// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import { useMutation } from '@tanstack/react-query'
import { CheckCircle2Icon, CopyIcon, FileCode2Icon, LoaderCircleIcon, ShieldAlertIcon, Wand2Icon } from 'lucide-react'
import * as React from 'react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import { copyTextToClipboard } from '#/lib/clipboard'
import { generatePlaygroundScaffold, type ScaffoldResponse } from '../-lib/playground-api'

interface SkillScaffoldGeneratorProps {
  onSendToCompression: (content: string) => void
}

export function SkillScaffoldGenerator({ onSendToCompression }: SkillScaffoldGeneratorProps) {
  const [name, setName] = React.useState('incident-triage')
  const [domain, setDomain] = React.useState('observability')
  const [description, setDescription] = React.useState('诊断线上服务异常并生成结构化修复证据')
  const [triggersText, setTriggersText] = React.useState('排查线上告警, incident triage')
  const [role, setRole] = React.useState('On-Call Diagnostics Specialist')
  const [constraintsText, setConstraintsText] = React.useState('所有外网探针强制设定 5s 超时\n单文件严格控制在 300 行以内')
  const [result, setResult] = React.useState<ScaffoldResponse | null>(null)
  const [copied, setCopied] = React.useState(false)
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: generatePlaygroundScaffold,
    onSuccess: (data) => {
      setErrorMsg(null)
      setResult(data)
    },
    onError: (err: unknown) => {
      setErrorMsg(err instanceof Error ? err.message : '脚手架生成失败')
    },
  })

  const handleGenerate = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || !description.trim()) return
    mutation.mutate({
      name: name.trim(),
      description: description.trim(),
      domain: domain.trim() || 'general',
      triggers: triggersText.split(/[,，\n]/).map((s) => s.trim()).filter(Boolean),
      role: role.trim() || 'Autonomous Engineering Specialist',
      constraints: constraintsText.split('\n').map((s) => s.trim()).filter(Boolean),
    })
  }

  const handleCopy = async () => {
    if (!result?.content) return
    await copyTextToClipboard(result.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <Card className="p-4 border-border/80 bg-card flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-semibold font-mono text-foreground">
          <FileCode2Icon className="size-4 text-cyan-500" />
          <span>标准 6 章节 Six-Tuple 技能脚手架生成器</span>
        </div>
        {result && (
          <Badge
            variant="outline"
            className={`text-xs font-mono ${result.validation.valid ? 'border-cyan-500/50 text-cyan-400' : 'border-rose-500/50 text-rose-400'}`}
          >
            {result.validation.valid ? (
              <CheckCircle2Icon className="size-3 mr-1" />
            ) : (
              <ShieldAlertIcon className="size-3 mr-1" />
            )}
            {result.validation.valid ? '格式门禁通过' : '存在格式错误'}
          </Badge>
        )}
      </div>

      <form onSubmit={handleGenerate} className="grid gap-2.5 md:grid-cols-2">
        <label className="grid gap-1 text-xs font-mono text-muted-foreground">
          <span>技能标识 (kebab-case)</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="h-8 rounded-md border border-border bg-background px-2.5 text-xs text-foreground outline-none focus:border-cyan-500"
          />
        </label>
        <label className="grid gap-1 text-xs font-mono text-muted-foreground">
          <span>所属领域 (domain)</span>
          <input
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            className="h-8 rounded-md border border-border bg-background px-2.5 text-xs text-foreground outline-none focus:border-cyan-500"
          />
        </label>
        <label className="grid gap-1 text-xs font-mono text-muted-foreground">
          <span>功能简述</span>
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="h-8 rounded-md border border-border bg-background px-2.5 text-xs text-foreground outline-none focus:border-cyan-500"
          />
        </label>
        <label className="grid gap-1 text-xs font-mono text-muted-foreground">
          <span>触发关键词 (逗号分隔)</span>
          <input
            value={triggersText}
            onChange={(e) => setTriggersText(e.target.value)}
            className="h-8 rounded-md border border-border bg-background px-2.5 text-xs text-foreground outline-none focus:border-cyan-500"
          />
        </label>
        <label className="grid gap-1 text-xs font-mono text-muted-foreground">
          <span>角色定位</span>
          <input
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="h-8 rounded-md border border-border bg-background px-2.5 text-xs text-foreground outline-none focus:border-cyan-500"
          />
        </label>
        <label className="grid gap-1 text-xs font-mono text-muted-foreground">
          <span>核心红线约束 (每行一条)</span>
          <textarea
            value={constraintsText}
            onChange={(e) => setConstraintsText(e.target.value)}
            rows={2}
            className="rounded-md border border-border bg-background p-2 text-xs text-foreground outline-none focus:border-cyan-500"
          />
        </label>
        <div className="md:col-span-2 flex flex-wrap items-center gap-2">
          <Button
            type="submit"
            disabled={mutation.isPending || !name.trim() || !description.trim()}
            className="h-8 text-xs font-mono bg-cyan-600 hover:bg-cyan-500 text-white"
          >
            {mutation.isPending ? (
              <LoaderCircleIcon className="size-3.5 mr-1.5 animate-spin" />
            ) : (
              <Wand2Icon className="size-3.5 mr-1.5" />
            )}
            生成 6 章节脚手架
          </Button>
          {result && (
            <>
              <Button type="button" variant="outline" size="sm" onClick={handleCopy} className="h-8 text-xs font-mono">
                <CopyIcon className="size-3.5 mr-1.5" />
                {copied ? '已复制 Markdown' : '复制脚手架'}
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => onSendToCompression(result.content)}
                className="h-8 text-xs font-mono border-cyan-500/40 text-cyan-400"
              >
                送入注脑压缩台 ➔
              </Button>
            </>
          )}
        </div>
      </form>

      {errorMsg && (
        <div className="rounded border border-rose-500/40 bg-rose-950/20 px-3 py-2 text-xs font-mono text-rose-300">
          {errorMsg}
        </div>
      )}

      {result && (
        <pre className="max-h-64 overflow-auto rounded border border-border/70 bg-background/80 p-2.5 text-xs font-mono text-foreground whitespace-pre-wrap">
          {result.content}
        </pre>
      )}
    </Card>
  )
}
