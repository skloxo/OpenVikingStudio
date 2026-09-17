import * as React from 'react'
import ForceGraph3D from 'react-force-graph-3d'
import ForceGraph2D from 'react-force-graph-2d'
import { useTheme } from 'next-themes'
import { Loader2Icon, Share2Icon } from 'lucide-react'

import type { GraphFilterCategory, GraphMode } from './graph-toolbar'
import { useKnowledgeTopology } from '../-lib/use-knowledge-topology'

export interface NodeData {
  id: string
  label: string
  category: 'peers' | 'sessions' | 'skills' | 'resources'
  color: string
  val: number
  degree: number
  content_preview?: string
  x?: number
  y?: number
  z?: number
}

export interface LinkData {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  source: any
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  target: any
  link_type?: string
}

interface KnowledgeGraphCanvasProps {
  searchQuery: string
  filterCategory: GraphFilterCategory
  mode: GraphMode
  selectedNode: NodeData | null
  onNodeSelect?: (node: NodeData | null) => void
  onCountChange?: (nodeCount: number, edgeCount: number) => void
}

export function KnowledgeGraphCanvas({
  searchQuery,
  filterCategory,
  mode,
  selectedNode,
  onNodeSelect,
  onCountChange,
}: KnowledgeGraphCanvasProps) {
  const { resolvedTheme } = useTheme()
  const isDark = resolvedTheme === 'dark'

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = React.useRef<any>(null)
  const containerRef = React.useRef<HTMLDivElement | null>(null)
  const [dimensions, setDimensions] = React.useState({ width: 1000, height: 650 })

  const { data: topology, isLoading } = useKnowledgeTopology()

  // ResizeObserver for dynamic container sizing
  React.useEffect(() => {
    if (!containerRef.current) return
    const updateDimensions = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        if (rect.width > 0 && rect.height > 0) {
          setDimensions({
            width: Math.floor(rect.width),
            height: Math.floor(rect.height),
          })
        }
      }
    }
    updateDimensions()
    const observer = new ResizeObserver(updateDimensions)
    observer.observe(containerRef.current)
    return () => observer.disconnect()
  }, [])

  // Raw links and degree map
  const rawLinks = React.useMemo<LinkData[]>(() => {
    if (!topology?.edges) return []
    return topology.edges.map((e) => ({
      source: e.source,
      target: e.target,
      link_type: e.link_type,
    }))
  }, [topology?.edges])

  const nodeDegreesMap = React.useMemo(() => {
    const degrees = new Map<string, number>()
    rawLinks.forEach((link) => {
      const sId = typeof link.source === 'object' ? link.source.id : link.source
      const tId = typeof link.target === 'object' ? link.target.id : link.target
      degrees.set(sId, (degrees.get(sId) || 0) + 1)
      degrees.set(tId, (degrees.get(tId) || 0) + 1)
    })
    return degrees
  }, [rawLinks])

  // Generate enriched nodes
  const allNodes = React.useMemo<NodeData[]>(() => {
    if (!topology?.nodes) return []
    return topology.nodes.map((n) => {
      let color = isDark ? '#64748b' : '#475569'
      let val = 6
      if (n.category === 'peers') {
        color = isDark ? '#38bdf8' : '#0284c7' // Cyan
        val = 18
      } else if (n.category === 'skills') {
        color = isDark ? '#f59e0b' : '#d97706' // Amber
        val = 10
      } else if (n.category === 'sessions') {
        color = isDark ? '#0ea5e9' : '#0284c7' // Sky Blue
        val = 8
      }
      return {
        id: n.id,
        label: n.label,
        category: n.category,
        color,
        val,
        degree: nodeDegreesMap.get(n.id) || 0,
        content_preview: n.content_preview,
      }
    })
  }, [isDark, nodeDegreesMap, topology?.nodes])

  const allNodesMap = React.useMemo(() => {
    const map = new Map<string, NodeData>()
    allNodes.forEach((node) => map.set(node.id, node))
    return map
  }, [allNodes])

  // Filtered nodes and links with 1-hop neighbor preservation
  const graphData = React.useMemo(() => {
    let filteredNodes = allNodes

    if (filterCategory !== 'all') {
      const targetNodes = allNodes.filter((n) => n.category === filterCategory)
      const targetIds = new Set(targetNodes.map((n) => n.id))
      const neighborIds = new Set<string>()
      rawLinks.forEach((link) => {
        const sId = typeof link.source === 'object' ? link.source.id : link.source
        const tId = typeof link.target === 'object' ? link.target.id : link.target
        if (targetIds.has(sId)) neighborIds.add(tId)
        if (targetIds.has(tId)) neighborIds.add(sId)
      })
      filteredNodes = allNodes.filter(
        (n) => targetIds.has(n.id) || neighborIds.has(n.id),
      )
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      filteredNodes = filteredNodes.filter(
        (n) => n.id.toLowerCase().includes(q) || n.label.toLowerCase().includes(q),
      )
    }

    const nodeIds = new Set(filteredNodes.map((n) => n.id))
    const filteredLinks = rawLinks.filter((link) => {
      const sId = typeof link.source === 'object' ? link.source.id : link.source
      const tId = typeof link.target === 'object' ? link.target.id : link.target
      return nodeIds.has(sId) && nodeIds.has(tId)
    })

    return { nodes: filteredNodes, links: filteredLinks }
  }, [allNodes, filterCategory, rawLinks, searchQuery])

  // Report counts to parent status bar
  React.useEffect(() => {
    onCountChange?.(graphData.nodes.length, graphData.links.length)
  }, [graphData.nodes.length, graphData.links.length, onCountChange])

  // Handle Node Click
  const handleNodeClick = React.useCallback(
    (node: NodeData) => {
      const fullNode = allNodesMap.get(node.id) || node
      onNodeSelect?.(fullNode)

      if (fgRef.current) {
        const nx = typeof node.x === 'number' && !isNaN(node.x) ? node.x : null
        const ny = typeof node.y === 'number' && !isNaN(node.y) ? node.y : null
        const nz = typeof node.z === 'number' && !isNaN(node.z) ? node.z : 0

        if (mode === '3d' && typeof fgRef.current.cameraPosition === 'function' && nx !== null && ny !== null) {
          const hyp = Math.hypot(nx, ny, nz || 1)
          if (hyp > 0 && !isNaN(hyp)) {
            const distance = 40
            const distRatio = 1 + distance / hyp
            fgRef.current.cameraPosition(
              { x: nx * distRatio, y: ny * distRatio, z: nz * distRatio },
              { x: nx, y: ny, z: nz },
              1200,
            )
          }
        } else if (mode === '2d' && typeof fgRef.current.centerAt === 'function' && nx !== null && ny !== null) {
          fgRef.current.centerAt(nx, ny, 1000)
          fgRef.current.zoom(2.5, 1000)
        }
      }
    },
    [allNodesMap, mode, onNodeSelect],
  )

  const selectedNodeId = selectedNode?.id
  const { selectedConnectedLinkSet, selectedConnectedNodeSet } = React.useMemo(() => {
    const linkSet = new Set<LinkData>()
    const nodeSet = new Set<string>()
    if (selectedNodeId) {
      nodeSet.add(selectedNodeId)
      graphData.links.forEach((link) => {
        const sId = typeof link.source === 'object' ? link.source.id : link.source
        const tId = typeof link.target === 'object' ? link.target.id : link.target
        if (sId === selectedNodeId || tId === selectedNodeId) {
          linkSet.add(link)
          nodeSet.add(sId)
          nodeSet.add(tId)
        }
      })
    }
    return { selectedConnectedLinkSet: linkSet, selectedConnectedNodeSet: nodeSet }
  }, [graphData.links, selectedNodeId])

  const isLinkConnected = React.useCallback(
    (link: LinkData) => selectedConnectedLinkSet.has(link),
    [selectedConnectedLinkSet],
  )

  if (isLoading && graphData.nodes.length === 0) {
    return (
      <div ref={containerRef} className="flex size-full flex-col items-center justify-center gap-2.5 bg-background">
        <Loader2Icon className="size-5 animate-spin text-cyan-500" />
        <span className="font-mono text-xs text-muted-foreground">正在同步真实知识拓扑...</span>
      </div>
    )
  }

  if (graphData.nodes.length === 0) {
    return (
      <div ref={containerRef} className="flex size-full flex-col items-center justify-center gap-3 bg-background p-6 text-center">
        <div className="rounded-md border border-border/70 bg-card/80 p-6 text-foreground max-w-sm backdrop-blur-md shadow-sm">
          <div className="mx-auto mb-2.5 flex size-9 items-center justify-center rounded-full bg-muted/60 text-muted-foreground">
            <Share2Icon className="size-4" />
          </div>
          <h3 className="font-mono text-xs font-bold">当前知识库暂无拓扑节点</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            {searchQuery ? `未找到与 "${searchQuery}" 匹配的节点` : '暂未检索到知识拓扑节点，录入记忆或技能后即可查看。'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div ref={containerRef} className="relative size-full overflow-hidden bg-background transition-colors duration-200">
      {mode === '2d' ? (
        <ForceGraph2D
          ref={fgRef}
          width={dimensions.width}
          height={dimensions.height}
          graphData={graphData}
          warmupTicks={30}
          cooldownTicks={50}
          cooldownTime={3000}
          d3VelocityDecay={0.8}
          d3AlphaDecay={0.08}
          nodeLabel="label"
          nodeColor={(node: NodeData) => {
            if (selectedNodeId) {
              if (node.id === selectedNodeId) return '#f59e0b'
              if (selectedConnectedNodeSet.has(node.id)) return node.color
              return isDark ? 'rgba(100, 116, 139, 0.25)' : 'rgba(203, 213, 225, 0.4)'
            }
            return node.color
          }}
          nodeVal={(node: NodeData) => node.val * 0.8}
          nodeRelSize={3}
          linkWidth={(link: LinkData) => (isLinkConnected(link) ? 3 : 0.8)}
          linkColor={(link: LinkData) => {
            if (isLinkConnected(link)) return '#f59e0b'
            return isDark ? 'rgba(56, 189, 248, 0.3)' : 'rgba(2, 132, 199, 0.3)'
          }}
          linkDirectionalParticles={(link: LinkData) => (isLinkConnected(link) ? 4 : 0)}
          linkDirectionalParticleWidth={(link: LinkData) => (isLinkConnected(link) ? 3 : 0)}
          linkDirectionalParticleSpeed={(link: LinkData) => (isLinkConnected(link) ? 0.015 : 0)}
          linkDirectionalParticleColor={() => '#f59e0b'}
          backgroundColor={isDark ? '#090d16' : '#f8fafc'}
          onNodeClick={handleNodeClick}
        />
      ) : (
        <ForceGraph3D
          ref={fgRef}
          width={dimensions.width}
          height={dimensions.height}
          graphData={graphData}
          warmupTicks={30}
          cooldownTicks={50}
          cooldownTime={3000}
          d3VelocityDecay={0.85}
          d3AlphaDecay={0.08}
          nodeResolution={4}
          linkCurvature={0.12}
          nodeLabel="label"
          nodeColor={(node: NodeData) => {
            if (selectedNodeId) {
              if (node.id === selectedNodeId) return '#f59e0b'
              if (selectedConnectedNodeSet.has(node.id)) return node.color
              return isDark ? 'rgba(100, 116, 139, 0.25)' : 'rgba(203, 213, 225, 0.4)'
            }
            return node.color
          }}
          nodeVal={(node: NodeData) => node.val}
          nodeRelSize={3.5}
          linkWidth={(link: LinkData) => (isLinkConnected(link) ? 3 : 0.8)}
          linkColor={(link: LinkData) => {
            if (isLinkConnected(link)) return '#f59e0b'
            return isDark ? 'rgba(56, 189, 248, 0.3)' : 'rgba(2, 132, 199, 0.3)'
          }}
          linkDirectionalParticles={(link: LinkData) => (isLinkConnected(link) ? 5 : 0)}
          linkDirectionalParticleWidth={(link: LinkData) => (isLinkConnected(link) ? 3 : 0)}
          linkDirectionalParticleSpeed={(link: LinkData) => (isLinkConnected(link) ? 0.015 : 0)}
          linkDirectionalParticleColor={() => '#f59e0b'}
          backgroundColor={isDark ? '#090d16' : '#f8fafc'}
          rendererConfig={{ antialias: false, powerPreference: 'high-performance' }}
          onNodeClick={handleNodeClick}
          showNavInfo={false}
        />
      )}
    </div>
  )
}
