// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BookOpenIcon, FileTextIcon, SearchIcon } from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { ovClient } from '#/lib/ov-client'
import type { PromptTemplateItem } from '../-types/dspy-compiler'

interface PromptTemplatePickerProps {
  selectedPath?: string
  onSelectTemplate: (template: PromptTemplateItem) => void
}

const CATEGORIES = [
  { label: '全部', value: '' },
  { label: '压缩', value: 'compression' },
  { label: '检索', value: 'retrieval' },
  { label: '技能', value: 'skill' },
  { label: '记忆', value: 'memory' },
  { label: '视觉', value: 'vision' },
  { label: '解析', value: 'parsing' },
]

export function PromptTemplatePicker({
  selectedPath,
  onSelectTemplate,
}: PromptTemplatePickerProps) {
  const [search, setSearch] = useState('')
  const [selectedCat, setSelectedCat] = useState('')

  const { data: templates = [], isLoading } = useQuery<PromptTemplateItem[]>({
    queryKey: ['dspy', 'templates', search, selectedCat],
    queryFn: async () => {
      const res = await ovClient.instance.get<PromptTemplateItem[]>('/api/v1/dspy/templates', {
        params: {
          search: search.trim() || undefined,
          category: selectedCat || undefined,
          limit: 60,
        },
      })
      return res.data
    },
    staleTime: 30000,
  })

  return (
    <div className="flex flex-col gap-2 p-3 bg-card/60 border border-border/70 rounded-md text-xs font-mono">
      {/* Header & Controls */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/50 pb-2">
        <div className="flex items-center gap-2">
          <BookOpenIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
          <span className="font-semibold text-foreground">系统级 Prompt 模板真资产库</span>
          <Badge variant="outline" className="text-xs font-mono px-1.5 py-0 border-border">
            {templates.length} 个模板
          </Badge>
        </div>

        {/* Category Filter */}
        <div className="flex items-center gap-1">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.value}
              type="button"
              onClick={() => setSelectedCat(cat.value)}
              className={`px-2 py-0.5 rounded text-xs transition-colors ${
                selectedCat === cat.value
                  ? 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/40 font-semibold'
                  : 'text-muted-foreground hover:bg-muted/40 border border-transparent'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Search Input */}
      <div className="relative">
        <SearchIcon className="absolute left-2.5 top-2 size-3.5 text-muted-foreground" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="按名称、ID 或功能描述搜索 Prompt 模板..."
          className="w-full pl-8 pr-3 py-1.5 bg-muted/20 border border-border/60 rounded text-xs font-mono text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-cyan-500"
        />
      </div>

      {/* Template List */}
      <div className="max-h-48 overflow-y-auto space-y-1 pr-1">
        {isLoading ? (
          <div className="py-6 text-center text-muted-foreground">正在检索 Prompt 模板...</div>
        ) : templates.length === 0 ? (
          <div className="py-6 text-center text-muted-foreground">未找到匹配的 Prompt 模板</div>
        ) : (
          templates.map((tpl) => {
            const isSelected = selectedPath === tpl.rel_path
            return (
              <button
                key={tpl.rel_path}
                type="button"
                onClick={() => onSelectTemplate(tpl)}
                className={`w-full text-left p-2 rounded border transition-colors flex items-center justify-between gap-3 ${
                  isSelected
                    ? 'bg-cyan-500/10 border-cyan-500 text-foreground'
                    : 'bg-card/40 border-border/50 hover:bg-muted/30 text-muted-foreground'
                }`}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <FileTextIcon
                    className={`size-3.5 shrink-0 ${
                      isSelected ? 'text-cyan-600 dark:text-cyan-400' : 'text-muted-foreground'
                    }`}
                  />
                  <div className="min-w-0 truncate">
                    <span className="font-semibold text-foreground text-xs">{tpl.name}</span>
                    <span className="text-muted-foreground ml-2 text-xs truncate font-mono">
                      {tpl.id}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0 text-xs">
                  <Badge variant="outline" className="px-1 py-0 text-xs font-mono border-border">
                    {tpl.category}
                  </Badge>
                  <span className="tabular-nums text-muted-foreground">v{tpl.version}</span>
                  <span className="tabular-nums text-muted-foreground">
                    {tpl.template_chars} 字符
                  </span>
                </div>
              </button>
            )
          })
        )}
      </div>
    </div>
  )
}
