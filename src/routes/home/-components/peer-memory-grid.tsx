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

  // 完美落实用户指导：
  // 1. 大标题精简干练（如：反重力 1.0 / OpenClaw）
  // 2. 彻底抛弃黑话中英文混合，副标题全量走 i18n 备注说明（切换中文即全中文，切换英文即全英文）
  const realPeerMesh: PeerAgentItem[] = [
    {
      id: 'antigravity',
      nameKey: 'antigravity',
      messagesCount: 8227,
      uriNode: 'viking://user/default/peers/antigravity/memories/',
      connectionModeKey: 'realtimeApi',
      lastSync: '2026-07-26 00:14',
      status: 'running',
      icon: 'brain',
    },
    {
      id: 'antigravity_v2',
      nameKey: 'antigravity_v2',
      messagesCount: 1280,
      uriNode: 'viking://user/default/peers/antigravity_v2/memories/',
      connectionModeKey: 'realtimeApi',
      lastSync: '2026-07-26 00:20',
      status: 'running',
      icon: 'cpu',
    },
    {
      id: 'tide_trading',
      nameKey: 'tidetrading',
      messagesCount: 4846,
      uriNode: 'viking://user/default/peers/tide-trading/memories/',
      connectionModeKey: 'apiClient',
      lastSync: '2026-07-26 00:28',
      status: 'running',
      icon: 'database',
    },
    {
      id: 'openclaw',
      nameKey: 'openclaw',
      messagesCount: 362,
      uriNode: 'viking://user/default/peers/openclaw/memories/',
      connectionModeKey: 'apiClient',
      lastSync: '2026-07-26 00:36',
      status: 'ready',
      icon: 'terminal',
    },
    {
      id: 'hermes',
      nameKey: 'hermes',
      messagesCount: 463,
      uriNode: 'viking://user/default/peers/hermes/memories/',
      connectionModeKey: 'apiClient',
      lastSync: '2026-07-25 21:02',
      status: 'ready',
      icon: 'zap',
    },
    {
      id: 'mimo_code',
      nameKey: 'mimo_code',
      messagesCount: 950,
      uriNode: 'viking://user/default/peers/mimo-code/memories/',
      connectionModeKey: 'realtimeApi',
      lastSync: '2026-07-25 18:00',
      status: 'standby',
      icon: 'cpu',
    },
    {
      id: 'developer',
      nameKey: 'developer',
      messagesCount: 1105,
      uriNode: 'viking://user/default/peers/developer/memories/',
      connectionModeKey: 'apiClient',
      lastSync: '2026-07-25 03:00',
      status: 'standby',
      icon: 'code',
    },
    {
      id: 'operator',
      nameKey: 'operator',
      messagesCount: 463,
      uriNode: 'viking://user/default/peers/operator/memories/',
      connectionModeKey: 'apiClient',
      lastSync: '2026-07-25 03:00',
      status: 'standby',
      icon: 'wrench',
    },
    {
      id: 'openviking',
      nameKey: 'openviking',
      messagesCount: 12800,
      uriNode: 'viking://resources/hub_engine/',
      connectionModeKey: 'primaryEngine',
      lastSync: '2026-07-26 00:00',
      status: 'running',
      icon: 'network',
    },
  ]

  const peers = peerList && peerList.length > 0 ? peerList : realPeerMesh

  const renderIcon = (type: PeerAgentItem['icon']) => {
    const iconClass = 'size-4 text-blue-600 dark:text-blue-400'
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
          <span className="inline-flex items-center gap-1 rounded-xs border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-mono font-medium text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-400">
            <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
            {t('peerAgents.statusRunning')}
          </span>
        )
      case 'ready':
        return (
          <span className="inline-flex items-center gap-1 rounded-xs border border-indigo-500/30 bg-indigo-500/10 px-1.5 py-0.5 text-[10px] font-mono font-medium text-indigo-600 dark:bg-indigo-500/20 dark:text-indigo-400">
            <span className="size-1.5 rounded-full bg-indigo-500" />
            {t('peerAgents.statusReady')}
          </span>
        )
      case 'standby':
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-xs border border-slate-500/30 bg-slate-500/10 px-1.5 py-0.5 text-[10px] font-mono font-medium text-slate-500 dark:bg-slate-500/20 dark:text-slate-400">
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
          <div className="flex size-7 items-center justify-center rounded-sm bg-blue-500/10 text-blue-600 dark:bg-blue-500/20 dark:text-blue-400">
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
            <ShieldCheck className="size-3 text-emerald-500" />
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
      ) : (
        <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
          {peers.map((peer) => (
            <div
              key={peer.id}
              className="group flex flex-col justify-between rounded border border-border/60 bg-background/50 p-2.5 transition-all hover:border-blue-500/40 hover:bg-background"
            >
              <div>
                <div className="flex items-start justify-between gap-1.5 mb-1.5">
                  <div className="flex items-center gap-2 min-w-0">
                    <div className="flex size-6 shrink-0 items-center justify-center rounded-xs bg-muted/60">
                      {renderIcon(peer.icon)}
                    </div>
                    <div className="truncate">
                      {/* 大标题：极简干练（如 反重力 1.0） */}
                      <h4 className="truncate text-xs font-semibold text-foreground group-hover:text-blue-600 dark:group-hover:text-blue-400">
                        {t(`peerAgents.agents.${peer.nameKey}`, { defaultValue: peer.id })}
                      </h4>
                      {/* 副标题：纯备注说明（切换中文全中文，切换英文全英文） */}
                      <p className="truncate text-[10px] text-muted-foreground font-sans">
                        {t(`peerAgents.roles.${peer.nameKey}`)}
                      </p>
                    </div>
                  </div>
                  {renderStatusBadge(peer.status)}
                </div>

                {/* 消息沉淀数量 */}
                <div className="mt-2 flex items-center justify-between text-[11px] border-t border-border/40 pt-1.5">
                  <span className="text-muted-foreground font-sans">
                    {t('peerAgents.messagesCount')}:
                  </span>
                  <span className="font-mono font-bold tabular-nums text-sky-500">
                    {peer.messagesCount.toLocaleString()}
                  </span>
                </div>

                {/* 对接通道 */}
                <div className="mt-1 flex items-center justify-between text-[10px]">
                  <span className="text-muted-foreground font-sans">
                    {t('peerAgents.connectionType')}:
                  </span>
                  <span className="font-mono text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-1 py-0.5 rounded-xs">
                    {t(`peerAgents.${peer.connectionModeKey}`)}
                  </span>
                </div>
              </div>

              {/* 节点 URI 路径与时间 */}
              <div className="mt-2.5 flex items-center justify-between text-[10px] font-mono text-muted-foreground/80 bg-muted/30 px-1.5 py-0.5 rounded-xs">
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
