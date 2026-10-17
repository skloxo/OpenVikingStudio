// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

import * as React from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  LinkIcon,
  UnlinkIcon,
  PlusIcon,
  CheckIcon,
  AlertCircleIcon,
  ArrowRightIcon,
  NetworkIcon,
} from 'lucide-react'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { ovClient } from '#/lib/ov-client'

export interface RelationItem {
  to_uri: string
  reason?: string
  link_type?: string
  weight?: number
  created_at?: number
}

interface NodeRelationsManagerProps {
  nodeId: string
  onRelationChange?: () => void
}

const LINK_TYPES = [
  { value: 'related_to', label: '相关联 (related_to)' },
  { value: 'depends_on', label: '依赖于 (depends_on)' },
  { value: 'derived_from', label: '派生自 (derived_from)' },
  { value: 'implements', label: '实现 (implements)' },
]

export function NodeRelationsManager({ nodeId, onRelationChange }: NodeRelationsManagerProps) {
  const queryClient = useQueryClient()
  const [targetUri, setTargetUri] = React.useState('')
  const [reason, setReason] = React.useState('')
  const [linkType, setLinkType] = React.useState('related_to')
  const [isAdding, setIsAdding] = React.useState(false)
  const [actionNotice, setActionNotice] = React.useState<string | null>(null)

  // 1. 查询当前节点所有出度关联
  const relationsQuery = useQuery<RelationItem[]>({
    queryKey: ['relations', nodeId],
    queryFn: async () => {
      const res = await ovClient.instance.get<{ status: string; result?: RelationItem[] }>(
        `/api/v1/relations?uri=${encodeURIComponent(nodeId)}`
      )
      return res.data.result ?? []
    },
    staleTime: 5_000,
    enabled: Boolean(nodeId),
  })

  const relations = relationsQuery.data ?? []

  // 2. 建立新关联 Mutation
  const linkMutation = useMutation({
    mutationFn: async () => {
      if (!targetUri.trim()) throw new Error('目标 URI 不能为空')
      const res = await ovClient.instance.post('/api/v1/relations/link', {
        from_uri: nodeId,
        to_uris: targetUri.trim(),
        reason: reason.trim(),
        link_type: linkType,
        weight: 1.0,
      })
      return res.data
    },
    onSuccess: () => {
      setTargetUri('')
      setReason('')
      setIsAdding(false)
      setActionNotice('关联已成功建立并物理落盘 relations.db')
      setTimeout(() => setActionNotice(null), 3000)
      void queryClient.invalidateQueries({ queryKey: ['relations', nodeId] })
      void queryClient.invalidateQueries({ queryKey: ['knowledge-topology'] })
      onRelationChange?.()
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : '建立关联失败'
      setActionNotice(`错误: ${msg}`)
      setTimeout(() => setActionNotice(null), 4000)
    },
  })

  // 3. 解除关联 Mutation
  const unlinkMutation = useMutation({
    mutationFn: async (toUri: string) => {
      const res = await ovClient.instance.post('/api/v1/relations/unlink', {
        from_uri: nodeId,
        to_uri: toUri,
      })
      return res.data
    },
    onSuccess: () => {
      setActionNotice('已成功解除实体关联')
      setTimeout(() => setActionNotice(null), 3000)
      void queryClient.invalidateQueries({ queryKey: ['relations', nodeId] })
      void queryClient.invalidateQueries({ queryKey: ['knowledge-topology'] })
      onRelationChange?.()
    },
  })

  return (
    <div className="flex flex-col gap-2 rounded-md border border-border/70 bg-card p-3 shadow-xs">
      <div className="flex items-center justify-between pb-1.5 border-b border-border/50">
        <span className="text-xs font-semibold text-foreground flex items-center gap-1.5 font-mono">
          <NetworkIcon className="size-3.5 text-cyan-500" />
          显式实体关联拓扑 ({relations.length})
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIsAdding(!isAdding)}
          className="h-6 px-2 text-xs gap-1 font-mono text-cyan-600 dark:text-cyan-400 border-cyan-500/30 hover:bg-cyan-500/10"
        >
          <PlusIcon className="size-3" />
          {isAdding ? '收起表单' : '新建关联'}
        </Button>
      </div>

      {actionNotice && (
        <div
          className={`px-2.5 py-1.5 rounded text-xs font-mono flex items-center gap-1.5 ${
            actionNotice.startsWith('错误')
              ? 'bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400'
              : 'bg-cyan-500/10 border border-cyan-500/30 text-cyan-600 dark:text-cyan-400'
          }`}
        >
          {actionNotice.startsWith('错误') ? (
            <AlertCircleIcon className="size-3.5 shrink-0" />
          ) : (
            <CheckIcon className="size-3.5 shrink-0" />
          )}
          <span>{actionNotice}</span>
        </div>
      )}

      {/* 新建关联表单折叠 */}
      {isAdding && (
        <div className="flex flex-col gap-2 rounded bg-muted/30 p-2.5 border border-border/60 text-xs">
          <div className="flex flex-col gap-1">
            <span className="text-muted-foreground font-mono">目标节点 URI (to_uri)</span>
            <Input
              value={targetUri}
              onChange={(e) => setTargetUri(e.target.value)}
              placeholder="viking://resources/... 或 viking://skills/..."
              className="h-7 text-xs font-mono"
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="flex flex-col gap-1">
              <span className="text-muted-foreground font-mono">关系类型</span>
              <select
                value={linkType}
                onChange={(e) => setLinkType(e.target.value)}
                className="h-7 rounded border border-border/60 bg-background px-2 text-xs font-mono text-foreground focus:outline-none focus:ring-1 focus:ring-cyan-500"
              >
                {LINK_TYPES.map((lt) => (
                  <option key={lt.value} value={lt.value}>
                    {lt.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <span className="text-muted-foreground font-mono">关联动因 (选填)</span>
              <Input
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="例如: 架构依赖/测试覆盖"
                className="h-7 text-xs font-mono"
              />
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-1">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsAdding(false)}
              className="h-7 px-2.5 text-xs font-mono"
            >
              取消
            </Button>
            <Button
              size="sm"
              disabled={linkMutation.isPending || !targetUri.trim()}
              onClick={() => linkMutation.mutate()}
              className="h-7 px-3 text-xs font-mono bg-cyan-600 hover:bg-cyan-700 text-white gap-1"
            >
              <LinkIcon className="size-3" />
              {linkMutation.isPending ? '建立中...' : '确认建立'}
            </Button>
          </div>
        </div>
      )}

      {/* 现有关系出度列表 */}
      <div className="flex flex-col gap-1.5 max-h-48 overflow-y-auto pr-1">
        {relationsQuery.isLoading ? (
          <div className="py-3 text-center text-xs text-muted-foreground font-mono">正在检索关联...</div>
        ) : relations.length === 0 ? (
          <div className="py-2 text-center text-xs text-muted-foreground font-mono">
            暂无显式出度关联边。点击上方「新建关联」建立实体互联。
          </div>
        ) : (
          relations.map((rel) => (
            <div
              key={rel.to_uri}
              className="flex items-center justify-between gap-1.5 rounded border border-border/40 bg-muted/20 px-2 py-1.5 text-xs font-mono"
            >
              <div className="flex items-center gap-1.5 overflow-hidden flex-1">
                <ArrowRightIcon className="size-3 text-cyan-500 shrink-0" />
                <div className="flex flex-col overflow-hidden">
                  <span className="text-foreground truncate font-medium" title={rel.to_uri}>
                    {rel.to_uri}
                  </span>
                  <div className="flex items-center gap-1.5 text-muted-foreground text-xs">
                    <span className="text-cyan-600 dark:text-cyan-400 font-semibold">
                      [{rel.link_type || 'related_to'}]
                    </span>
                    {rel.reason && <span className="truncate">· {rel.reason}</span>}
                  </div>
                </div>
              </div>

              <Button
                variant="ghost"
                size="sm"
                disabled={unlinkMutation.isPending}
                onClick={() => unlinkMutation.mutate(rel.to_uri)}
                className="h-6 px-1.5 text-xs text-muted-foreground hover:text-rose-500 hover:bg-rose-500/10 shrink-0 gap-1 font-mono"
                title="解除该实体关联"
              >
                <UnlinkIcon className="size-3 text-rose-500" />
                <span>解绑</span>
              </Button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
