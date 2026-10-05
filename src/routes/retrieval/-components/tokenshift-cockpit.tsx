// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  AlertCircleIcon,
  CheckCircle2Icon,
  CodeIcon,
  CopyIcon,
  DownloadIcon,
  FolderOpenIcon,
  PlayIcon,
  SaveIcon,
  ShieldCheckIcon,
  SparklesIcon,
} from 'lucide-react'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import { ovClient } from '#/lib/ov-client'
import { CodeFilePicker } from './code-file-picker'
import { TokenShiftKpiTiles } from './tokenshift-kpi-tiles'
import { TOKENSHIFT_PRESETS } from '../-constants/tokenshift-presets'
import type {
  ApplyTokenShiftRequest,
  ApplyTokenShiftResult,
  CodeFileItem,
  TokenShiftLanguage,
  TokenShiftMode,
  TokenShiftProtectResult,
  TokenShiftRequest,
  TokenShiftResult,
  TokenShiftStats,
} from '../-types/tokenshift'

export function TokenShiftCockpit() {
  const [code, setCode] = useState<string>(TOKENSHIFT_PRESETS[0].code)
  const [mode, setMode] = useState<TokenShiftMode>('skeleton')
  const [language, setLanguage] = useState<TokenShiftLanguage>('auto')
  const [preserveDocstrings, setPreserveDocstrings] = useState<boolean>(true)
  const [stripComments, setStripComments] = useState<boolean>(true)
  const [copied, setCopied] = useState<boolean>(false)

  // Real codebase file picking & persistence
  const [selectedFile, setSelectedFile] = useState<CodeFileItem | null>(null)
  const [showFilePicker, setShowFilePicker] = useState<boolean>(false)
  const [applyResult, setApplyResult] = useState<ApplyTokenShiftResult | null>(null)
  const [applyError, setApplyError] = useState<string | null>(null)

  // Query global stats
  const { data: stats, refetch: refetchStats } = useQuery<TokenShiftStats>({
    queryKey: ['tokenshift', 'stats'],
    queryFn: async () => {
      const res = await ovClient.instance.get<TokenShiftStats>('/api/v1/tokenshift/stats')
      return res.data
    },
    refetchInterval: 15000,
  })

  // Compress mutation
  const compressMutation = useMutation<TokenShiftResult, Error, TokenShiftRequest>({
    mutationFn: async (req) => {
      const res = await ovClient.instance.post<TokenShiftResult>('/api/v1/tokenshift/compress', req)
      return res.data
    },
    onSuccess: () => {
      refetchStats()
      setApplyResult(null)
      setApplyError(null)
    },
  })

  // Protect symbols mutation
  const protectMutation = useMutation<TokenShiftProtectResult, Error, { code: string; language: TokenShiftLanguage }>({
    mutationFn: async (body) => {
      const res = await ovClient.instance.post<TokenShiftProtectResult>('/api/v1/tokenshift/protect', body)
      return res.data
    },
  })

  // Physical persistence mutation
  const applyMutation = useMutation<ApplyTokenShiftResult, Error, ApplyTokenShiftRequest>({
    mutationFn: async (body) => {
      const res = await ovClient.instance.post<ApplyTokenShiftResult>('/api/v1/tokenshift/apply', body)
      return res.data
    },
    onSuccess: (data) => {
      setApplyResult(data)
      setApplyError(null)
    },
    onError: (err) => {
      setApplyError(err.message)
    },
  })

  const handleSelectFile = async (file: CodeFileItem) => {
    setSelectedFile(file)
    try {
      const res = await ovClient.instance.get<{ content: string; language: string }>(
        `/api/v1/tokenshift/file?path=${encodeURIComponent(file.rel_path)}`
      )
      if (res.data?.content) {
        setCode(res.data.content)
        if (['python', 'typescript', 'javascript', 'json'].includes(res.data.language)) {
          setLanguage(res.data.language as TokenShiftLanguage)
        }
      }
      setApplyResult(null)
      setApplyError(null)
    } catch (err: any) {
      setApplyError(`读取源码文件失败: ${err.message}`)
    }
  }

  const handleCompress = () => {
    compressMutation.mutate({
      code,
      mode,
      language,
      preserve_docstrings: preserveDocstrings,
      strip_comments: stripComments,
    })
  }

  const handleProtect = () => {
    protectMutation.mutate({ code, language })
  }

  const handleApply = (saveMode: 'skeleton_file' | 'in_place') => {
    if (!selectedFile) {
      setApplyError('请先从项目代码树中挑选一个目标文件进行回写')
      return
    }
    const compressedCode = compressMutation.data?.compressed_code
    if (!compressedCode) {
      setApplyError('请先执行 AST 压缩生成优化代码')
      return
    }
    if (saveMode === 'in_place') {
      const confirmWrite = window.confirm(
        `确定要原地覆写文件 ${selectedFile.rel_path} 吗？系统将在隔离区自动生成时间戳快照以备秒级还原。`
      )
      if (!confirmWrite) return
    }
    applyMutation.mutate({
      rel_path: selectedFile.rel_path,
      compressed_code: compressedCode,
      mode: saveMode,
    })
  }

  const handleCopy = () => {
    const textToCopy = compressMutation.data?.compressed_code || ''
    if (textToCopy) {
      navigator.clipboard.writeText(textToCopy)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const result = compressMutation.data

  return (
    <div className="flex flex-col gap-4">
      {/* 4 High-Density Metrics Tiles */}
      <TokenShiftKpiTiles result={result} stats={stats} />


      {/* Persistence Feedback Banner */}
      {applyResult && (
        <div className="p-3 bg-cyan-500/10 border border-cyan-500/30 rounded-md text-xs font-mono flex items-start justify-between gap-3 text-foreground">
          <div className="flex items-start gap-2">
            <CheckCircle2Icon className="size-4 text-cyan-600 dark:text-cyan-400 shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-cyan-600 dark:text-cyan-400">
                物理落盘成功 ({applyResult.mode === 'in_place' ? '原地覆写' : '骨架文件'})
              </div>
              <div className="text-muted-foreground mt-0.5">
                目标路径: <span className="text-foreground">{applyResult.target_path}</span> ｜ 节省: {applyResult.saved_chars} 字符
              </div>
              <div className="text-muted-foreground truncate">
                安全快照: <span className="text-xs">{applyResult.snapshot_path}</span>
              </div>
            </div>
          </div>
          <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={() => setApplyResult(null)}>
            关闭
          </Button>
        </div>
      )}

      {applyError && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-md text-xs font-mono flex items-center justify-between gap-3 text-rose-700 dark:text-rose-300">
          <div className="flex items-center gap-2">
            <AlertCircleIcon className="size-4 shrink-0" />
            <span>{applyError}</span>
          </div>
          <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={() => setApplyError(null)}>
            关闭
          </Button>
        </div>
      )}

      {/* Control Bar & Mode / File Picker Header */}
      <Card className="p-3 bg-card/60 border-border/70 flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className={`h-7 text-xs font-mono ${showFilePicker ? 'border-cyan-500 text-cyan-600 dark:text-cyan-400' : 'border-border/70'}`}
              onClick={() => setShowFilePicker(!showFilePicker)}
            >
              <FolderOpenIcon className="size-3.5 mr-1" />
              {selectedFile ? `已选: ${selectedFile.filename}` : '浏览工程源码'}
            </Button>

            <span className="text-xs text-muted-foreground font-mono ml-2">预设:</span>
            {TOKENSHIFT_PRESETS.map((p) => (
              <Button
                key={p.id}
                variant="outline"
                size="sm"
                className="h-7 text-xs font-mono border-border/70"
                onClick={() => {
                  setCode(p.code)
                  setLanguage(p.language)
                  setSelectedFile(null)
                  setApplyResult(null)
                }}
              >
                {p.label}
              </Button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs font-mono border-border/70"
              onClick={handleProtect}
              disabled={protectMutation.isPending}
            >
              <ShieldCheckIcon className="size-3.5 mr-1 text-cyan-600 dark:text-cyan-400" />
              {protectMutation.isPending ? '分析中...' : '提取保护符号'}
            </Button>
            <Button
              variant="default"
              size="sm"
              className="h-7 text-xs font-mono bg-primary text-primary-foreground"
              onClick={handleCompress}
              disabled={compressMutation.isPending}
            >
              <PlayIcon className="size-3.5 mr-1" />
              {compressMutation.isPending ? '压缩中...' : '执行 AST 压缩'}
            </Button>
          </div>
        </div>

        {/* Real Codebase Picker Dropdown Tray */}
        {showFilePicker && (
          <div className="pt-2 border-t border-border/50">
            <CodeFilePicker selectedPath={selectedFile?.rel_path} onSelectFile={handleSelectFile} />
          </div>
        )}

        {/* Modes & Options */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-border/50 text-xs font-mono">
          <div className="flex items-center gap-1.5">
            <span className="text-muted-foreground">压缩阶梯:</span>
            {(['outline', 'skeleton', 'compact'] as TokenShiftMode[]).map((m) => (
              <Button
                key={m}
                variant={mode === m ? 'secondary' : 'ghost'}
                size="sm"
                className={`h-6 text-xs font-mono px-2 ${mode === m ? 'border border-cyan-500/40 text-cyan-600 dark:text-cyan-400' : ''}`}
                onClick={() => setMode(m)}
              >
                {m === 'outline' && 'L0 大纲 (~70%)'}
                {m === 'skeleton' && 'L1 骨架 (~50%)'}
                {m === 'compact' && 'L2 紧凑 (~25%)'}
              </Button>
            ))}
          </div>

          <div className="flex items-center gap-4 text-muted-foreground">
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={preserveDocstrings}
                onChange={(e) => setPreserveDocstrings(e.target.checked)}
                className="rounded border-border size-3.5 accent-cyan-500"
              />
              保留 Docstring
            </label>
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={stripComments}
                onChange={(e) => setStripComments(e.target.checked)}
                className="rounded border-border size-3.5 accent-cyan-500"
              />
              剔除冗余注释
            </label>
          </div>
        </div>
      </Card>

      {/* Protected Symbols Tray (if extracted) */}
      {protectMutation.data && (
        <Card className="p-3 bg-muted/20 border-border/70 flex flex-col gap-2">
          <div className="flex items-center justify-between text-xs font-mono text-muted-foreground">
            <span>🛡️ 语法树受保护符号与签名 ({protectMutation.data.total_symbols} 个)</span>
            <span>语言: {protectMutation.data.language}</span>
          </div>
          <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
            {protectMutation.data.frozen_signatures.map((sig, idx) => (
              <Badge
                key={idx}
                variant="outline"
                className="text-xs font-mono px-1.5 py-0.5 border-border bg-card/60 text-foreground"
              >
                {sig}
              </Badge>
            ))}
          </div>
        </Card>
      )}

      {/* Two-Column Code Workbench */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 min-h-105">
        {/* Left Column: Raw Source */}
        <Card className="p-3 bg-card/60 border-border/70 flex flex-col gap-2">
          <div className="flex items-center justify-between text-xs font-mono text-muted-foreground border-b border-border/50 pb-2">
            <span className="flex items-center gap-1.5 font-semibold text-foreground">
              <CodeIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
              原始源代码 (Source Input)
              {selectedFile && (
                <Badge variant="outline" className="text-xs font-mono px-1 py-0 border-cyan-500/40 text-cyan-600 dark:text-cyan-400">
                  {selectedFile.rel_path}
                </Badge>
              )}
            </span>
            <span>{code.split('\n').length} 行 ｜ {code.length} 字符</span>
          </div>
          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="flex-1 w-full p-2.5 font-mono text-xs bg-muted/20 border border-border/60 rounded-md focus:outline-none focus:ring-1 focus:ring-cyan-500 min-h-90 resize-y"
            placeholder="粘贴待压缩代码，或从上方「浏览工程源码」挑选代码文件..."
          />
        </Card>

        {/* Right Column: Compressed Output */}
        <Card className="p-3 bg-card/60 border-border/70 flex flex-col gap-2">
          <div className="flex items-center justify-between text-xs font-mono text-muted-foreground border-b border-border/50 pb-2">
            <span className="flex items-center gap-1.5 font-semibold text-cyan-600 dark:text-cyan-400">
              <SparklesIcon className="size-3.5" />
              TokenShift 压缩代码 (AST-Protected)
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="h-6 text-xs font-mono px-2 border-border/70"
                onClick={handleCopy}
                disabled={!result?.compressed_code}
              >
                <CopyIcon className="size-3 mr-1" />
                {copied ? '已复制' : '复制'}
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-6 text-xs font-mono px-2 border-cyan-500/40 text-cyan-600 dark:text-cyan-400 hover:bg-cyan-500/10"
                onClick={() => handleApply('skeleton_file')}
                disabled={!result?.compressed_code || applyMutation.isPending}
              >
                <DownloadIcon className="size-3 mr-1" />
                保存骨架 (.skeleton)
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-6 text-xs font-mono px-2 border-border/70 text-muted-foreground hover:text-foreground"
                onClick={() => handleApply('in_place')}
                disabled={!result?.compressed_code || applyMutation.isPending}
              >
                <SaveIcon className="size-3 mr-1" />
                原地覆写
              </Button>
            </div>
          </div>
          <textarea
            readOnly
            value={result?.compressed_code || ''}
            className="flex-1 w-full p-2.5 font-mono text-xs bg-muted/10 border border-border/60 rounded-md focus:outline-none text-foreground min-h-90 resize-y"
            placeholder="执行压缩后将在此高密呈现语法树保护代码..."
          />
        </Card>
      </div>
    </div>
  )
}
