import * as React from 'react'
import { useTranslation } from 'react-i18next'
import { PlayIcon, CopyIcon, CheckIcon, LayersIcon } from 'lucide-react'
import { Card } from '#/components/ui/card'
import { Button } from '#/components/ui/button'
import { Badge } from '#/components/ui/badge'
import { ovClient } from '#/lib/ov-client'

export interface ActionPreset {
  id: string
  category: string
  title: string
  desc: string
  method: 'GET' | 'POST'
  endpoint: string
  defaultPayload: string
}

export const ACTION_PRESETS: ActionPreset[] = [
  {
    id: 'db-health-run',
    category: '系统与诊断',
    title: 'SQLite 与 FTS5 数据库完整性自检',
    desc: '对全部 SQLite 数据库执行 PRAGMA quick_check 与 FTS5 全文索引自检修复。',
    method: 'POST',
    endpoint: '/api/v1/rsi/bootstrap/health/run',
    defaultPayload: '{}',
  },
  {
    id: 'queue-sync-metrics',
    category: '队列与存储',
    title: '向量队列同步与死信指标透视',
    desc: '获取向量化处理进度、滞留失联数与死信队列统计信息。',
    method: 'GET',
    endpoint: '/api/v1/queue/sync-metrics',
    defaultPayload: '{}',
  },
  {
    id: 'queue-sync-heal',
    category: '队列与存储',
    title: '未索引滞留文件自动重试扫描',
    desc: '自动扫描未及时向量化同步的文件并触发重新排队自愈。',
    method: 'POST',
    endpoint: '/api/v1/queue/sync-heal',
    defaultPayload: '{\n  "max_age_seconds": 300.0,\n  "limit": 50\n}',
  },
  {
    id: 'snapshot-log',
    category: '版本与灾备',
    title: '工作区快照时间轴日志查询',
    desc: '查询工作区历史提交快照、创建人、时间戳与不可篡改 Git Commit Hash。',
    method: 'GET',
    endpoint: '/api/v1/snapshot/log?limit=10',
    defaultPayload: '{}',
  },
  {
    id: 'system-consistency',
    category: '系统与诊断',
    title: '多写文件与向量索引一致性体检',
    desc: '探测 VikingFS 文件系统与底层向量索引是否存在孤岛或失联。',
    method: 'POST',
    endpoint: '/api/v1/system/consistency',
    defaultPayload: '{\n  "uri": "viking:///",\n  "prune": false\n}',
  },
]

export function VisualActionLauncher() {
  const { t } = useTranslation('playground')
  const [selectedId, setSelectedId] = React.useState<string>(ACTION_PRESETS[0].id)
  const [payloadText, setPayloadText] = React.useState<string>(ACTION_PRESETS[0].defaultPayload)
  const [isRunning, setIsRunning] = React.useState(false)
  const [result, setResult] = React.useState<{ status: number; durationMs: number; data: unknown } | null>(null)
  const [copied, setCopied] = React.useState(false)

  const activePreset = ACTION_PRESETS.find((p) => p.id === selectedId) || ACTION_PRESETS[0]

  const handleSelectPreset = (preset: ActionPreset) => {
    setSelectedId(preset.id)
    setPayloadText(preset.defaultPayload)
    setResult(null)
  }

  const handleExecute = async () => {
    try {
      setIsRunning(true)
      const start = performance.now()
      let parsedPayload = {}
      if (activePreset.method === 'POST') {
        try {
          parsedPayload = JSON.parse(payloadText)
        } catch {
          parsedPayload = {}
        }
      }

      let res
      if (activePreset.method === 'GET') {
        res = await ovClient.instance.get(activePreset.endpoint)
      } else {
        res = await ovClient.instance.post(activePreset.endpoint, parsedPayload)
      }
      const durationMs = Math.round(performance.now() - start)
      setResult({ status: res.status, durationMs, data: res.data })
    } catch (err: any) {
      setResult({
        status: err?.response?.status || 500,
        durationMs: 0,
        data: err?.response?.data || { error: String(err) },
      })
    } finally {
      setIsRunning(false)
    }
  }

  const handleCopy = () => {
    if (!result) return
    void navigator.clipboard.writeText(JSON.stringify(result.data, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 p-3 overflow-y-auto">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/40 pb-2">
        <div className="flex items-center gap-2">
          <LayersIcon className="size-4 text-cyan-500" />
          <span className="text-xs font-semibold tracking-wide text-foreground">
            {t('visualLauncher.title')}
          </span>
          <Badge variant="outline" className="h-5 px-1.5 text-xs font-mono text-cyan-500 border-cyan-500/30 bg-cyan-500/5">
            {t('visualLauncher.badge')}
          </Badge>
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="text-xs font-medium text-muted-foreground">{t('visualLauncher.selectPrompt')}</span>
        <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2 lg:grid-cols-3">
          {ACTION_PRESETS.map((preset) => {
            const isSelected = preset.id === selectedId
            return (
              <button
                key={preset.id}
                type="button"
                onClick={() => handleSelectPreset(preset)}
                className={`flex flex-col gap-1 rounded-md border p-2 text-left transition-colors ${
                  isSelected
                    ? 'border-cyan-500/60 bg-cyan-500/10'
                    : 'border-border/40 bg-muted/10 hover:border-border/80 hover:bg-muted/20'
                }`}
              >
                <div className="flex items-center justify-between gap-1">
                  <span className="text-xs font-medium text-foreground truncate">{preset.title}</span>
                  <Badge variant="outline" className="h-4 px-1 text-[11px] font-mono shrink-0">
                    {preset.method}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground line-clamp-1">{preset.desc}</p>
              </button>
            )
          })}
        </div>
      </div>

      <Card className="flex flex-col gap-2.5 p-3 shadow-none border border-border/60">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Badge
              variant="outline"
              className={`h-5 px-1.5 text-xs font-mono font-bold ${
                activePreset.method === 'POST' ? 'text-cyan-500 border-cyan-500/40' : 'text-amber-400 border-amber-400/40'
              }`}
            >
              {activePreset.method}
            </Badge>
            <span className="text-xs font-mono text-foreground font-semibold">{activePreset.endpoint}</span>
          </div>

          <Button
            size="sm"
            disabled={isRunning}
            onClick={() => { void handleExecute() }}
            className="h-7 px-3 text-xs font-mono bg-cyan-600 hover:bg-cyan-700 text-white"
          >
            <PlayIcon className={`mr-1 size-3.5 ${isRunning ? 'animate-spin' : ''}`} />
            {isRunning ? t('visualLauncher.running') : t('visualLauncher.btnRun')}
          </Button>
        </div>

        {activePreset.method === 'POST' && (
          <div className="flex flex-col gap-1">
            <span className="text-xs text-muted-foreground font-mono">{t('visualLauncher.reqPayload')}</span>
            <textarea
              value={payloadText}
              onChange={(e) => setPayloadText(e.target.value)}
              className="w-full h-20 rounded-md border border-border/60 bg-muted/20 p-2 font-mono text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-cyan-500"
              placeholder="{}"
            />
          </div>
        )}
      </Card>

      {result && (
        <Card className="flex flex-col gap-2 p-3 shadow-none border border-border/60 bg-muted/10">
          <div className="flex items-center justify-between border-b border-border/40 pb-2">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-muted-foreground">{t('visualLauncher.resultTitle')}</span>
              <Badge
                variant="outline"
                className={`h-5 px-1.5 text-xs font-mono font-bold ${
                  result.status >= 200 && result.status < 300
                    ? 'text-cyan-500 border-cyan-500/40 bg-cyan-500/5'
                    : 'text-rose-500 border-rose-500/40 bg-rose-500/5'
                }`}
              >
                {result.status}
              </Badge>
              <span className="text-xs font-mono text-muted-foreground tabular-nums">
                {t('visualLauncher.duration', { ms: result.durationMs })}
              </span>
            </div>

            <Button
              size="sm"
              variant="outline"
              onClick={handleCopy}
              className="h-6 px-2 text-xs font-mono"
            >
              {copied ? <CheckIcon className="size-3 mr-1 text-cyan-500" /> : <CopyIcon className="size-3 mr-1" />}
              {copied ? t('visualLauncher.copied') : t('visualLauncher.btnCopy')}
            </Button>
          </div>

          <pre className="max-h-56 overflow-auto rounded-md bg-muted/30 p-2.5 font-mono text-xs text-foreground leading-relaxed">
            {JSON.stringify(result.data, null, 2)}
          </pre>
        </Card>
      )}
    </div>
  )
}
