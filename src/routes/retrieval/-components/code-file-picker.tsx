// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { FileCodeIcon, FolderIcon, SearchIcon } from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { ovClient } from '#/lib/ov-client'
import type { CodeFileItem } from '../-types/tokenshift'

interface CodeFilePickerProps {
  selectedPath?: string
  onSelectFile: (file: CodeFileItem) => void
}

const LANGUAGES = [
  { label: '全部', value: '' },
  { label: 'Python', value: 'python' },
  { label: 'TypeScript', value: 'typescript' },
  { label: 'JavaScript', value: 'javascript' },
]

export function CodeFilePicker({ selectedPath, onSelectFile }: CodeFilePickerProps) {
  const [search, setSearch] = useState('')
  const [selectedLang, setSelectedLang] = useState('')

  const { data: files = [], isLoading } = useQuery<CodeFileItem[]>({
    queryKey: ['tokenshift', 'files', search, selectedLang],
    queryFn: async () => {
      const res = await ovClient.instance.get<CodeFileItem[]>('/api/v1/tokenshift/files', {
        params: {
          search: search.trim() || undefined,
          language: selectedLang || undefined,
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
          <FolderIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
          <span className="font-semibold text-foreground">真实项目代码库拾取器</span>
          <Badge variant="outline" className="text-xs font-mono px-1.5 py-0 border-border">
            {files.length} 个源文件
          </Badge>
        </div>

        {/* Language Filter */}
        <div className="flex items-center gap-1">
          {LANGUAGES.map((lang) => (
            <button
              key={lang.value}
              type="button"
              onClick={() => setSelectedLang(lang.value)}
              className={`px-2 py-0.5 rounded text-xs transition-colors ${
                selectedLang === lang.value
                  ? 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/40 font-semibold'
                  : 'text-muted-foreground hover:bg-muted/40 border border-transparent'
              }`}
            >
              {lang.label}
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
          placeholder="按文件名或相对路径模糊搜索代码 (如 router, service, index)..."
          className="w-full pl-8 pr-3 py-1.5 bg-muted/20 border border-border/60 rounded text-xs font-mono text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-cyan-500"
        />
      </div>

      {/* File List Grid */}
      <div className="max-h-48 overflow-y-auto space-y-1 pr-1">
        {isLoading ? (
          <div className="py-6 text-center text-muted-foreground">正在检索工程源码...</div>
        ) : files.length === 0 ? (
          <div className="py-6 text-center text-muted-foreground">未找到匹配的源码文件</div>
        ) : (
          files.map((file) => {
            const isSelected = selectedPath === file.rel_path
            return (
              <button
                key={file.rel_path}
                type="button"
                onClick={() => onSelectFile(file)}
                className={`w-full text-left p-2 rounded border transition-colors flex items-center justify-between gap-3 ${
                  isSelected
                    ? 'bg-cyan-500/10 border-cyan-500 text-foreground'
                    : 'bg-card/40 border-border/50 hover:bg-muted/30 text-muted-foreground'
                }`}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <FileCodeIcon
                    className={`size-3.5 shrink-0 ${
                      isSelected ? 'text-cyan-600 dark:text-cyan-400' : 'text-muted-foreground'
                    }`}
                  />
                  <div className="min-w-0 truncate">
                    <span className="font-semibold text-foreground text-xs">{file.filename}</span>
                    <span className="text-muted-foreground ml-2 text-xs truncate">
                      {file.rel_path}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0 text-xs">
                  <Badge variant="outline" className="px-1 py-0 text-xs font-mono border-border">
                    {file.language}
                  </Badge>
                  <span className="tabular-nums text-muted-foreground">{file.line_count} 行</span>
                  <span className="tabular-nums text-muted-foreground">
                    {(file.size_bytes / 1024).toFixed(1)} KB
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
