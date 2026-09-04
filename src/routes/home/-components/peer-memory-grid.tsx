import { useTranslation } from 'react-i18next'
import {
  Brain,
  Code2,
  Cpu,
  Database,
  Network,
  Share2,
  ShieldCheck,
  Terminal,
  Wrench,
  Zap,
} from 'lucide-react'

export interface PeerAgentItem {
  id: string
  nameKey: string
  messagesCount: number
  uriNode: string
  connectionModeKey: 'realtimeApi' | 'apiClient' | 'primaryEngine'
  lastSync: string
  status: 'running' | 'ready' | 'standby'
  icon: 'brain' | 'terminal' | 'database' | 'zap' | 'cpu' | 'code' | 'wrench' | 'network'
  role?: string
}

interface PeerMemoryGridProps {
  isLoading?: boolean
  peerList?: PeerAgentItem[]
}

export function PeerMemoryGrid({
  isLoading = false,
  peerList,
}: PeerMemoryGridProps) {
  const { t } = useTranslation('home')

  const peers = peerList && peerList.length > 0 ? peerList : []

  const renderIcon = (type: PeerAgentItem['icon']) => {
    const iconClass = 'size-4 text-cyan-600 dark:text-cyan-400'
    switch (type) {
      case 'brain':
        return <Brain className={iconClass} />
      case 'terminal':
        return <Terminal className={iconClass} />
      case 'database':
        return <Database className={iconClass} />
      case 'zap':
        return <Zap className={iconClass} />
      case 'cpu':
        return <Cpu className={iconClass} />
      case 'code':
        return <Code2 className={iconClass} />
      case 'wrench':
        return <Wrench className={iconClass} />
      case 'network':
      default:
        return <Network className={iconClass} />
    }
  }

  const renderStatusBadge = (status: PeerAgentItem['status']) => {
    switch (status) {
      case 'running':
        return (
          <span className="inline-flex items-center gap-1 rounded-xs border border-cyan-500/30 bg-cyan-500/10 px-1.5 py-0.5 text-[11px] font-mono font-medium text-cyan-600 dark:bg-cyan-500/20 dark:text-cyan-400">
            <span className="size-1.5 rounded-full bg-cyan-500 animate-pulse" />
            {t('peerAgents.statusRunning')}
          </span>
        )
      case 'ready':
        return (
          <span className="inline-flex items-center gap-1 rounded-xs border border-sky-500/30 bg-sky-500/10 px-1.5 py-0.5 text-[11px] font-mono font-medium text-sky-600 dark:bg-sky-500/20 dark:text-sky-400">
            <span className="size-1.5 rounded-full bg-sky-500" />
            {t('peerAgents.statusReady')}
          </span>
        )
      case 'standby':
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-xs border border-slate-500/30 bg-slate-500/10 px-1.5 py-0.5 text-[11px] font-mono font-medium text-slate-500 dark:bg-slate-500/20 dark:text-slate-400">
            <span className="size-1.5 rounded-full bg-slate-400" />
            {t('peerAgents.statusStandby')}
          </span>
        )
    }
  }

  return (
    <div className="rounded border border-border/60 bg-card p-3.5 transition-colors">
      {/* 头部标题 */}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex size-7 items-center justify-center rounded-sm bg-cyan-500/10 text-cyan-600 dark:bg-cyan-500/20 dark:text-cyan-400">
            <Share2 className="size-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground tracking-tight">
              🧠 {t('peerAgents.title')}
            </h3>
            <p className="text-[11px] text-muted-foreground font-mono">
              {t('peerAgents.subtitle')}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 rounded-xs border border-border/60 bg-muted/40 px-2 py-0.5 text-[11px] font-mono tabular-nums text-muted-foreground">
            <ShieldCheck className="size-3 text-cyan-500" />
            {t('peerAgents.agfsMesh')}
          </span>
        </div>
      </div>

      {/* 精准 Agent Peer 矩阵 */}
      {isLoading ? (
        <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, idx) => (
            <div
              key={idx}
              className="h-28 animate-pulse rounded border border-border/40 bg-muted/20"
            />
          ))}
        </div>
      ) : peers.length === 0 ? (
        <div className="flex h-24 items-center justify-center rounded border border-dashed border-border/60 text-xs text-muted-foreground">
          {t('common.noData', { defaultValue: '暂无感知到的 Agent 对等节点' })}
        </div>
      ) : (
        <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
          {peers.map((peer) => (
            <div
              key={peer.id}
              className="group flex flex-col justify-between rounded border border-border/60 bg-background/50 p-2.5 transition-all hover:border-cyan-500/40 hover:bg-background"
            >
              <div>
                <div className="flex items-start justify-between gap-1.5 mb-1.5">
                  <div className="flex items-center gap-2 min-w-0">
                    <div className="flex size-6 shrink-0 items-center justify-center rounded-xs bg-muted/60">
                      {renderIcon(peer.icon)}
                    </div>
                    <div className="truncate">
                      <h4 className="truncate text-xs font-semibold text-foreground group-hover:text-cyan-600 dark:group-hover:text-cyan-400">
                        {t(`peerAgents.agents.${peer.nameKey}`, { defaultValue: peer.id })}
                      </h4>
                      <p className="truncate text-[11px] text-muted-foreground font-sans">
                        {peer.role || t(`peerAgents.roles.${peer.nameKey}`, { defaultValue: peer.id })}
                      </p>
                    </div>
                  </div>
                  {renderStatusBadge(peer.status)}
                </div>

                {/* 消息/调用沉淀数量 */}
                <div className="mt-2 flex items-center justify-between text-[11px] border-t border-border/40 pt-1.5">
                  <span className="text-muted-foreground font-sans">
                    {t('peerAgents.messagesCount')}:
                  </span>
                  <span className="font-mono font-bold tabular-nums text-cyan-500">
                    {peer.messagesCount.toLocaleString()}
                  </span>
                </div>

                {/* 对接通道 */}
                <div className="mt-1 flex items-center justify-between text-[11px]">
                  <span className="text-muted-foreground font-sans">
                    {t('peerAgents.connectionType')}:
                  </span>
                  <span className="font-mono text-cyan-600 dark:text-cyan-400 bg-cyan-500/10 px-1 py-0.5 rounded-xs">
                    {t(`peerAgents.${peer.connectionModeKey}`, { defaultValue: peer.connectionModeKey })}
                  </span>
                </div>
              </div>

              {/* 节点 URI 路径与时间 */}
              <div className="mt-2.5 flex items-center justify-between text-[11px] font-mono text-muted-foreground/80 bg-muted/30 px-1.5 py-0.5 rounded-xs">
                <span className="truncate max-w-42.5" title={peer.uriNode}>
                  {peer.uriNode}
                </span>
                <span className="shrink-0">{peer.lastSync}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
