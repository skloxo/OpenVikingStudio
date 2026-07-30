import * as React from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { Share2Icon } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import type { GraphFilterCategory, GraphMode } from './-components/graph-toolbar'
import { GraphToolbar } from './-components/graph-toolbar'
import type { NodeData } from './-components/knowledge-graph-canvas'
import { KnowledgeGraphCanvas } from './-components/knowledge-graph-canvas'
import { NodeDetailsDrawer } from './-components/node-details-drawer'

class GraphErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex size-full flex-col items-center justify-center gap-3 bg-card/50 p-6 text-center">
          <div className="rounded-md border border-rose-500/30 bg-rose-500/10 p-4 text-rose-600 dark:text-rose-400 max-w-md font-mono text-xs">
            <h3 className="font-bold text-sm mb-1">WebGL / 3D 渲染器初始化异常</h3>
            <p className="text-[11px] opacity-90 leading-relaxed">
              {this.state.error?.message || '画布初始化失败，可能是由于 WebGL 上下文丢失或 GPU 硬件加速受限。'}
            </p>
            <button
              type="button"
              onClick={() => this.setState({ hasError: false, error: null })}
              className="mt-3 rounded bg-cyan-600 px-3 py-1 text-white hover:bg-cyan-700 text-xs transition-colors"
            >
              重新加载画布
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export const Route = createFileRoute('/graph')({
  component: GraphRouteComponent,
})

function GraphRouteComponent() {
  const { t } = useTranslation('monitoringPage')

  const [searchQuery, setSearchQuery] = React.useState('')
  const [activeFilter, setActiveFilter] = React.useState<GraphFilterCategory>('all')
  const [mode, setMode] = React.useState<GraphMode>('2d')
  const [nodeCount, setNodeCount] = React.useState(1458)
  const [selectedNode, setSelectedNode] = React.useState<NodeData | null>(null)

  const handleResetZoom = () => {
    setSearchQuery('')
    setActiveFilter('all')
  }

  return (
    <div className="relative h-[calc(100vh-4rem)] w-full overflow-hidden font-sans">
      {/* 2D / 3D Canvas Viewport */}
      <GraphErrorBoundary>
        <KnowledgeGraphCanvas
          searchQuery={searchQuery}
          filterCategory={activeFilter}
          mode={mode}
          selectedNode={selectedNode}
          onNodeSelect={setSelectedNode}
          onCountChange={setNodeCount}
        />
      </GraphErrorBoundary>

      {/* Floating Glassmorphism Toolbar */}
      <div className="absolute top-3 left-3 right-3 z-30 pointer-events-none">
        <div className="pointer-events-auto">
          <GraphToolbar
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            activeFilter={activeFilter}
            onFilterChange={setActiveFilter}
            mode={mode}
            onModeChange={setMode}
            onResetZoom={handleResetZoom}
          />
        </div>
      </div>

      {/* Floating Bottom Status Bar */}
      <div className="absolute bottom-3 left-3 z-30 flex items-center gap-2.5 rounded-md border border-border/70 bg-card/85 px-3.5 py-2 backdrop-blur-md shadow-md pointer-events-auto">
        <div className="flex size-7 items-center justify-center rounded bg-cyan-500/10 text-cyan-600 dark:text-cyan-400">
          <Share2Icon className="size-4" />
        </div>
        <div>
          <h1 className="text-xs font-bold tracking-tight text-foreground flex items-center gap-2">
            <span>{t('graphPage.title', { defaultValue: 'OpenViking 全量知识关系图谱' })}</span>
          </h1>
          <p className="text-[11px] text-muted-foreground font-mono">
            {nodeCount} 个全量 URI 知识节点与 3,890 条拓扑关联边
          </p>
        </div>
      </div>

      {/* Node Details Drawer */}
      <NodeDetailsDrawer
        node={selectedNode}
        onClose={() => setSelectedNode(null)}
      />
    </div>
  )
}
