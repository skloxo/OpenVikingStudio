import * as React from 'react'
import {
  DatabaseIcon,
  HardDriveIcon,
  LockKeyholeIcon,
  SearchIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '#/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '#/components/ui/table'
import { postContentReindex } from '#/gen/ov-client'
import { cn } from '#/lib/utils'
import { parseObserverStatus } from '../-lib/parse-status'

export type ObserverComponent = {
  has_errors: boolean
  is_healthy: boolean
  name: string
  status: string
}

const MONITOR_TYPES = [
  ['vikingdb', DatabaseIcon],
  ['filesystem', HardDriveIcon],
  ['lock', LockKeyholeIcon],
  ['retrieval', SearchIcon],
] as const

const HEADER_TRANSLATIONS: Record<string, string> = {
  'Queue': '队列名称',
  'Pending': '等待中',
  'In Progress': '进行中',
  'Processed': '已处理',
  'Requeued': '重新入队',
  'Errors': '异常数',
  'Total': '总数',
  'Collection': '集合',
  'Index Count': '索引数',
  'Vector Count': '向量数',
  'Status': '状态',
  'Model': '模型名称',
  'Provider': '提供方',
  'Calls': '调用次数',
  'Prompt': '输入 Token (Prompt)',
  'Completion': '输出 Token (Completion)',
  'Last Updated': '最后更新时间',
  'Metric': '监控指标',
  'Value': '当前数值',
  'Operation': '操作类型',
  'Count': '操作次数',
  'Avg (ms)': '均耗时 (ms)',
  'Min (ms)': '最小耗时 (ms)',
  'Max (ms)': '最大耗时 (ms)',
  'Context Type': '上下文类别',
  'Queries': '检索次数',
}

const CELL_TRANSLATIONS: Record<string, string> = {
  'OK': '正常',
  'ERROR': '异常',
  'TOTAL': '总计',
  'context': '上下文主集合',
  'mkdir': '创建目录',
  'read': '读取数据',
  'write': '写入数据',
  'read_dir': '列出目录',
  'stat': '查询状态',
  'rmdir': '删除目录',
  'delete': '删除文件',
  'unlink': '解除链接',
  'rename': '文件重命名',
  'copy': '复制数据',
  'move': '移动路径',
  'open': '打开句柄',
  'close': '关闭句柄',
  'flush': '刷盘同步',
  'lock': '申请互斥锁',
  'unlock': '释放互斥锁',
  'ensure_parent_dir': '确保父级目录',
  'tree_dir': '遍历目录树',
  'ls': '列出清单',
  'cat': '读取文件',
  'rm': '删除路径',
  'mv': '移动路径',
  'grep': '内容匹配',
  'glob_directory': '模式匹配',
  'copy_within_mount': '卷内复制',
  'system_sync_status': '同步状态检查',
  'system_sync_retry': '同步重试',
  'Total Operations': '总操作执行数',
  'Total Time (s)': '总耗时 (秒)',
  'Overall Avg (ms)': '综合均耗时 (ms)',
  'Total Queries': '总检索请求次数',
  'Total Results': '总召回条目数',
  'Avg Results/Query': '单次平均召回数',
  'Zero-Result Queries': '零召回查询数',
  'Zero-Result Rate': '零召回率',
  'Avg Score': '平均语义相似度',
  'Score Range': '相似度区间',
  'Rerank Used': '重排引擎调用数',
  'Rerank Fallback': '重排降级回退数',
  'Avg Latency (ms)': '平均检索延迟 (ms)',
  'Max Latency (ms)': '最大峰值延迟 (ms)',
  'unknown': '未分类类别',
  'resource': '知识资源',
  'memory': '长期记忆',
  'skill': '技能协议',
  'file': '本地文件',
  'web': '网页抓取',
  'code': '代码仓库',
  'session': '会话上下文',
}

function translateHeader(header: string, isZh: boolean): string {
  if (!isZh) return header
  const trimmed = header.trim()
  return HEADER_TRANSLATIONS[trimmed] || HEADER_TRANSLATIONS[trimmed.toLowerCase()] || header
}

function translateCell(cell: string, isZh: boolean): string {
  if (!isZh) return cell
  const trimmed = cell.trim()
  return CELL_TRANSLATIONS[trimmed] || CELL_TRANSLATIONS[trimmed.toLowerCase()] || cell
}

function translateText(text: string, isZh: boolean): string {
  if (!isZh) return text
  const trimmed = text.trim()
  const unreadyMatch = trimmed.match(/^Unready Directories:\s*(\d+)$/i)
  if (unreadyMatch) return `未就绪目录数: ${unreadyMatch[1]}`
  const activeLocksMatch = trimmed.match(/^Active locks:\s*(\d+)$/i)
  if (activeLocksMatch) return `活跃互斥锁: ${activeLocksMatch[1]}`
  const waitingLocksMatch = trimmed.match(/^Waiting locks:\s*(\d+)$/i)
  if (waitingLocksMatch) return `等待队列锁: ${waitingLocksMatch[1]}`
  const staleLocksMatch = trimmed.match(/^Stale locks removed:\s*(\d+)$/i)
  if (staleLocksMatch) return `已清理过期锁: ${staleLocksMatch[1]}`
  const conflictsMatch = trimmed.match(/^Conflicts:\s*(\d+)$/i)
  if (conflictsMatch) return `锁冲突次数: ${conflictsMatch[1]}`
  const mountMatch = trimmed.match(/^Mount:\s*([^\s]+)\s*\(plugin:\s*([^)]+)\)$/i)
  if (mountMatch) return `挂载路径: ${mountMatch[1]} (驱动插件: ${mountMatch[2]})`
  if (/^No operation statistics recorded yet\.?$/i.test(trimmed)) return '暂无文件系统操作统计记录。'
  if (/^No filesystem statistics available\.?$/i.test(trimmed)) return '暂无可用文件系统统计数据。'
  if (/^No retrieval queries recorded\.?$/i.test(trimmed)) return '暂无检索查询记录。'
  if (/^No collections found\.?$/i.test(trimmed)) return '暂无可用向量集合。'
  if (/^VikingDB manager not initialized\.?$/i.test(trimmed)) return 'VikingDB 向量数据库管理器尚未初始化。'
  if (/^Not initialized\.?$/i.test(trimmed)) return '服务尚未初始化。'
  if (trimmed.startsWith('Error retrieving filesystem statistics:')) {
    return trimmed.replace(/^Error retrieving filesystem statistics:/i, '获取文件系统统计异常:')
  }
  return text
}

export function ObserverStatusContent({ status }: { status: string }) {
  const { i18n, t } = useTranslation('monitoringPage')
  const isZh = i18n.language.startsWith('zh')
  const blocks = React.useMemo(() => parseObserverStatus(status), [status])
  const [isReindexing, setIsReindexing] = React.useState(false)
  const [reindexSuccessMsg, setReindexSuccessMsg] = React.useState<string | null>(null)

  const handleTriggerReindex = async () => {
    setIsReindexing(true)
    setReindexSuccessMsg(null)
    try {
      await postContentReindex({
        body: {
          uri: 'viking://resources',
          mode: 'prune_orphans',
          wait: false,
        },
      })
      setReindexSuccessMsg(t('vikingdb.reindexSuccess', { defaultValue: '已触发全量重新索引' }))
    } catch (e) {
      console.error('Failed to trigger reindex:', e)
    } finally {
      setIsReindexing(false)
    }
  }

  if (blocks.length === 0) {
    return <p className="text-xs text-muted-foreground">{t('detail.noData', { defaultValue: '暂无组件运行数据' })}</p>
  }

  return (
    <div className="grid gap-2.5">
      {blocks.map((block, blockIndex) => {
        if (block.kind === 'text') {
          const trimmed = block.value.trim()
          const unreadyMatch = trimmed.match(/^Unready Directories:\s*(\d+)$/i)
          if (unreadyMatch) {
            const count = unreadyMatch[1]
            return (
              <div
                key={`${block.value}-${blockIndex}`}
                className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border/60 bg-muted/20 px-3 py-2 text-xs font-mono text-muted-foreground"
              >
                <div className="flex items-center gap-2">
                  <span>{isZh ? `未就绪目录数: ${count}` : `Unready Directories: ${count}`}</span>
                  {reindexSuccessMsg && (
                    <span className="text-cyan-500 font-sans text-xs">({reindexSuccessMsg})</span>
                  )}
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-6 px-2.5 text-xs font-sans hover:bg-background"
                  onClick={handleTriggerReindex}
                  disabled={isReindexing}
                >
                  {isReindexing ? t('vikingdb.reindexing', { defaultValue: '索引中...' }) : t('vikingdb.triggerReindex', { defaultValue: '立即索引' })}
                </Button>
              </div>
            )
          }

          return (
            <p
              key={`${block.value}-${blockIndex}`}
              className="rounded-md border border-border/60 bg-muted/20 px-3 py-2 text-xs font-mono text-muted-foreground"
            >
              {translateText(block.value, isZh)}
            </p>
          )
        }

        return (
          <div
            key={`table-${blockIndex}`}
            className="overflow-x-auto rounded-md border border-border/60"
          >
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/20 hover:bg-muted/20">
                  {block.headers.map((header, headerIndex) => (
                    <TableHead
                      key={`${header}-${headerIndex}`}
                      className="whitespace-nowrap font-medium text-xs py-2 px-3"
                    >
                      {translateHeader(header, isZh)}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {block.rows.map((row, rowIndex) => (
                  <TableRow key={`row-${rowIndex}`} className="hover:bg-muted/10">
                    {row.map((cell, cellIndex) => (
                      <TableCell
                        key={`${cell}-${cellIndex}`}
                        className="whitespace-nowrap font-mono text-xs py-1.5 px-3"
                      >
                        {translateCell(cell, isZh)}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )
      })}
    </div>
  )
}

export function ObserverComponentsSection({
  components,
}: {
  components?: Record<string, ObserverComponent | undefined>
}) {
  const { t } = useTranslation('monitoringPage')

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      {MONITOR_TYPES.map(([name, Icon]) => {
        const component = components?.[name]
        const healthy = component?.is_healthy === true && !component.has_errors
        return (
          <Card key={name} className="gap-0 overflow-hidden py-0 border-border/60 bg-card/60">
            <CardHeader className="border-b px-4 py-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <Icon className="size-4 text-muted-foreground" />
                  <div>
                    <CardTitle className="text-xs font-semibold tracking-tight">{t(`tabs.${name}`, { defaultValue: name.toUpperCase() })}</CardTitle>
                    <p className="text-xs text-muted-foreground">
                      {t(`detail.descriptions.${name}`, { defaultValue: `${name} 核心引擎运行状态` })}
                    </p>
                  </div>
                </div>
                <Badge
                  variant="outline"
                  className={cn(
                    'gap-1.5 font-normal text-xs',
                    healthy
                      ? 'border-cyan-500/30 text-cyan-600 dark:text-cyan-400'
                      : 'border-destructive/30 text-destructive',
                  )}
                >
                  <span
                    className={cn(
                      'size-1.5 rounded-full',
                      healthy ? 'bg-cyan-500' : 'bg-destructive',
                    )}
                  />
                  {healthy
                    ? t('health.healthy', { defaultValue: '正常' })
                    : t('health.unhealthy', { defaultValue: '异常' })}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="px-4 py-4">
              <ObserverStatusContent status={component?.status ?? ''} />
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
