// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { AlertCircleIcon, CheckCircle2Icon, CopyIcon, RefreshCwIcon, TerminalIcon } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '#/components/ui/sheet'
import { ovClient } from '#/lib/ov-client'

export interface DeadLetterRecord {
  id: number
  queue_name: string
  msg_id?: string
  uri?: string
  account_id?: string
  payload?: Record<string, unknown>
  error_type: string
  error_message: string
  stack_trace?: string
  retry_count: number
  resolved: number // 0: pending, 1: resolved, 2: retried
  resolution_note?: string
  created_at: number
  updated_at: number
}

interface DeadLetterDrawerProps {
  item: DeadLetterRecord | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onActionSuccess?: () => void
}

export function DeadLetterDrawer({
  item,
  open,
  onOpenChange,
  onActionSuccess,
}: DeadLetterDrawerProps) {
  const [detail, setDetail] = React.useState<DeadLetterRecord | null>(null)
  const [isLoadingDetail, setIsLoadingDetail] = React.useState(false)
  const [isRetrying, setIsRetrying] = React.useState(false)
  const [isResolving, setIsResolving] = React.useState(false)
  const [noteInput, setNoteInput] = React.useState('')
  const [showNoteInput, setShowNoteInput] = React.useState(false)

  React.useEffect(() => {
    if (!open || !item) {
      setDetail(null)
      setShowNoteInput(false)
      setNoteInput('')
      return
    }

    setDetail(item)
    const fetchFullDetail = async () => {
      try {
        setIsLoadingDetail(true)
        const res = await ovClient.instance.get<{ status: string; item: DeadLetterRecord }>(
          `/api/v1/queue/dlq/${item.id}`
        )
        if (res.data?.status === 'success' && res.data.item) {
          setDetail(res.data.item)
        }
      } catch (err) {
        console.error('[DeadLetterDrawer] Failed to fetch dead letter detail:', err)
      } finally {
        setIsLoadingDetail(false)
      }
    }
    fetchFullDetail()
  }, [open, item])

  if (!item) return null
  const current = detail || item

  const formatTimestamp = (ts?: number) => {
    if (!ts) return '--'
    const date = new Date(ts > 1e11 ? ts : ts * 1000)
    return date.toLocaleString('zh-CN', {
      hour12: false,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  const handleCopyText = (text: string, label: string) => {
    navigator.clipboard.writeText(text)
    toast.success(`已复制 ${label} 到剪贴板`)
  }

  const handleRetry = async () => {
    try {
      setIsRetrying(true)
      const res = await ovClient.instance.post<{ status: string; re_enqueued?: boolean }>(
        `/api/v1/queue/dlq/${current.id}/retry`
      )
      if (res.data?.status === 'success') {
        toast.success(`死信 #${current.id} 已重投入队，触发单条自愈`)
        setDetail((prev) => (prev ? { ...prev, resolved: 2, retry_count: prev.retry_count + 1 } : null))
        onActionSuccess?.()
      } else {
        toast.error(`重试失败: ${res.data?.status}`)
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      toast.error(`单条重试异常: ${msg}`)
    } finally {
      setIsRetrying(false)
    }
  }

  const handleResolve = async () => {
    try {
      setIsResolving(true)
      const res = await ovClient.instance.post<{ status: string }>(
        `/api/v1/queue/dlq/${current.id}/resolve`,
        {
          resolution_note: noteInput || 'Manual resolution in Studio cockpit',
          status: 1,
        }
      )
      if (res.data?.status === 'success') {
        toast.success(`死信 #${current.id} 已标记为已解决`)
        setDetail((prev) => (prev ? { ...prev, resolved: 1, resolution_note: noteInput } : null))
        setShowNoteInput(false)
        onActionSuccess?.()
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      toast.error(`解决处理异常: ${msg}`)
    } finally {
      setIsResolving(false)
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-[90vw] sm:max-w-xl flex flex-col gap-4 p-4 overflow-y-auto">
        <SheetHeader className="border-b pb-3 border-border/60">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="font-mono text-xs px-2 py-0.5 rounded-md">
                #{current.id}
              </Badge>
              <Badge variant="outline" className="font-mono text-xs px-2 py-0.5 rounded-md border-border/60">
                {current.queue_name}
              </Badge>
              {current.resolved === 0 && (
                <Badge variant="outline" className="text-xs px-2 py-0.5 rounded-md border-rose-500/40 text-rose-500 bg-rose-500/5">
                  待决死信
                </Badge>
              )}
              {current.resolved === 1 && (
                <Badge variant="outline" className="text-xs px-2 py-0.5 rounded-md border-cyan-500/40 text-cyan-500 bg-cyan-500/5">
                  已人工解决
                </Badge>
              )}
              {current.resolved === 2 && (
                <Badge variant="outline" className="text-xs px-2 py-0.5 rounded-md border-cyan-500/40 text-cyan-500 bg-cyan-500/5">
                  已重试入队
                </Badge>
              )}
            </div>
            {isLoadingDetail && (
              <span className="text-xs text-muted-foreground animate-pulse font-mono">加载中...</span>
            )}
          </div>
          <SheetTitle className="text-sm font-semibold tracking-tight text-foreground truncate mt-1">
            {current.uri || `Message #${current.id}`}
          </SheetTitle>
          <SheetDescription className="text-xs text-muted-foreground font-mono">
            入管时间: {formatTimestamp(current.created_at)} ｜ 重试次数: {current.retry_count}
          </SheetDescription>
        </SheetHeader>

        {/* 基础元数据网格 */}
        <div className="grid grid-cols-2 gap-2 text-xs font-mono bg-muted/20 p-2.5 rounded-md border border-border/60">
          <div>
            <span className="text-muted-foreground">消息 ID: </span>
            <span className="text-foreground select-all">{current.msg_id || '--'}</span>
          </div>
          <div>
            <span className="text-muted-foreground">所属账户: </span>
            <span className="text-foreground">{current.account_id || 'default'}</span>
          </div>
          <div className="col-span-2 truncate">
            <span className="text-muted-foreground">目标 URI: </span>
            <span className="text-foreground select-all">{current.uri || '--'}</span>
          </div>
          <div>
            <span className="text-muted-foreground">最后更新: </span>
            <span className="text-foreground">{formatTimestamp(current.updated_at)}</span>
          </div>
          <div>
            <span className="text-muted-foreground">重试计数: </span>
            <span className="text-foreground tabular-nums">{current.retry_count} 次</span>
          </div>
        </div>

        {/* 异常诊断面板 */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-rose-500">
              <AlertCircleIcon className="size-3.5" />
              <span>异常类型: {current.error_type}</span>
            </div>
            <Button
              size="sm"
              variant="ghost"
              className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground"
              onClick={() => handleCopyText(current.error_message, '错误原因')}
            >
              <CopyIcon className="size-3 mr-1" />
              复制原因
            </Button>
          </div>
          <div className="text-xs font-mono text-rose-500 bg-rose-500/5 p-2.5 rounded-md border border-rose-500/20 whitespace-pre-wrap break-all max-h-36 overflow-y-auto">
            {current.error_message || '--'}
          </div>
        </div>

        {/* 异常堆栈信息（如果有） */}
        {current.stack_trace && (
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground">
              <div className="flex items-center gap-1.5">
                <TerminalIcon className="size-3.5 text-amber-400" />
                <span>调用栈轨迹 (Stack Trace)</span>
              </div>
              <Button
                size="sm"
                variant="ghost"
                className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground"
                onClick={() => handleCopyText(current.stack_trace || '', '调用栈')}
              >
                <CopyIcon className="size-3 mr-1" />
                复制堆栈
              </Button>
            </div>
            <pre className="text-xs font-mono bg-muted/40 p-2.5 rounded-md border border-border/60 text-muted-foreground overflow-x-auto max-h-44 text-[12px] leading-relaxed">
              {current.stack_trace}
            </pre>
          </div>
        )}

        {/* 原始消息体 Payload */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground">
            <span>原始载荷 (Message Payload)</span>
            <Button
              size="sm"
              variant="ghost"
              className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground"
              onClick={() => handleCopyText(JSON.stringify(current.payload || {}, null, 2), 'Payload')}
            >
              <CopyIcon className="size-3 mr-1" />
              复制 JSON
            </Button>
          </div>
          <pre className="text-xs font-mono bg-muted/30 p-2.5 rounded-md border border-border/60 text-foreground overflow-x-auto max-h-48 text-[12px] leading-relaxed">
            {JSON.stringify(current.payload || {}, null, 2)}
          </pre>
        </div>

        {/* 历史解决备注 */}
        {current.resolution_note && (
          <div className="flex flex-col gap-1 text-xs bg-muted/20 p-2.5 rounded-md border border-border/60">
            <span className="font-semibold text-muted-foreground">解决备注:</span>
            <span className="text-foreground font-mono">{current.resolution_note}</span>
          </div>
        )}

        {/* 底部操作工具栏 */}
        <div className="mt-auto border-t pt-3 flex flex-col gap-2 border-border/60">
          {showNoteInput && current.resolved === 0 && (
            <div className="flex flex-col gap-1.5">
              <input
                type="text"
                placeholder="请输入解决备注（如：已修正数据源，忽略本次死信）"
                value={noteInput}
                onChange={(e) => setNoteInput(e.target.value)}
                className="w-full text-xs font-mono px-2.5 py-1.5 rounded-md border border-border bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <div className="flex justify-end gap-1.5">
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-6 px-2 text-xs"
                  onClick={() => setShowNoteInput(false)}
                >
                  取消
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={isResolving}
                  onClick={handleResolve}
                  className="h-6 px-2.5 text-xs font-mono border-cyan-500/40 text-cyan-500 hover:bg-cyan-500/10"
                >
                  {isResolving ? '提交中...' : '确认解决'}
                </Button>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {current.resolved === 0 && !showNoteInput && (
                <>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={isRetrying}
                    onClick={handleRetry}
                    className="h-7 px-3 text-xs font-mono border-cyan-500/40 text-cyan-500 hover:bg-cyan-500/10"
                  >
                    <RefreshCwIcon className={`size-3 mr-1.5 ${isRetrying ? 'animate-spin' : ''}`} />
                    {isRetrying ? '重试入队中...' : '单条自愈重试'}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setShowNoteInput(true)}
                    className="h-7 px-2.5 text-xs font-mono"
                  >
                    <CheckCircle2Icon className="size-3 mr-1 text-muted-foreground" />
                    标记解决
                  </Button>
                </>
              )}
            </div>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => onOpenChange(false)}
              className="h-7 px-3 text-xs font-mono"
            >
              关闭
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
