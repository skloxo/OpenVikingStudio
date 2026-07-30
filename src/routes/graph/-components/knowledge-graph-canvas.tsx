import * as React from 'react'
import ForceGraph3D from 'react-force-graph-3d'
import ForceGraph2D from 'react-force-graph-2d'
import { useTheme } from 'next-themes'

import type { GraphFilterCategory, GraphMode } from './graph-toolbar'

export interface NodeData {
  id: string
  label: string
  category: 'peers' | 'sessions' | 'skills' | 'resources'
  color: string
  val: number
  degree: number
  x?: number
  y?: number
  z?: number
}

export interface LinkData {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  source: any
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  target: any
}

interface KnowledgeGraphCanvasProps {
  searchQuery: string
  filterCategory: GraphFilterCategory
  mode: GraphMode
  selectedNode: NodeData | null
  onNodeSelect?: (node: NodeData | null) => void
  onCountChange?: (count: number) => void
}

const PEERS_NODES: string[] = [
  'viking://peers/master_agent',
  'viking://peers/researcher_agent',
  'viking://peers/developer_agent',
  'viking://peers/designer_agent',
  'viking://peers/product_manager',
  'viking://peers/operator_agent',
  'viking://peers/planner_agent',
  'viking://peers/evaluator_agent',
  'viking://peers/test_agent',
]

const SKILLS_NODES: string[] = Array.from({ length: 85 }, (_, i) => `viking://skills/skill_${i + 1}`)
const SESSIONS_NODES: string[] = Array.from({ length: 120 }, (_, i) => `viking://sessions/session_${i + 1}`)
const RESOURCES_NODES: string[] = Array.from({ length: 1244 }, (_, i) => `viking://resources/doc_${i + 1}`)

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

  // ResizeObserver for dynamic full-container sizing
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

  // Generate All Raw Links
  const rawLinks = React.useMemo<LinkData[]>(() => {
    const links: LinkData[] = []
    const master = 'viking://peers/master_agent'

    PEERS_NODES.forEach((peer) => {
      if (peer !== master) {
        links.push({ source: master, target: peer })
      }
    })

    SKILLS_NODES.forEach((skill, idx) => {
      const peer = PEERS_NODES[idx % PEERS_NODES.length] || master
      links.push({ source: peer, target: skill })
    })

    SESSIONS_NODES.forEach((session, idx) => {
      const peer = PEERS_NODES[idx % PEERS_NODES.length] || master
      links.push({ source: peer, target: session })
    })

    RESOURCES_NODES.forEach((res, idx) => {
      if (idx % 3 === 0) {
        const skill = SKILLS_NODES[idx % SKILLS_NODES.length]
        if (skill) links.push({ source: skill, target: res })
      } else if (idx % 3 === 1) {
        const session = SESSIONS_NODES[idx % SESSIONS_NODES.length]
        if (session) links.push({ source: session, target: res })
      } else {
        const peer = PEERS_NODES[idx % PEERS_NODES.length]
        if (peer) links.push({ source: peer, target: res })
      }
    })

    return links
  }, [])

  // Calculate Node Degrees
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

  // Generate All Raw Nodes
  const allNodes = React.useMemo<NodeData[]>(() => {
    const nodes: NodeData[] = []

    PEERS_NODES.forEach((id) => {
      nodes.push({
        id,
        label: id.replace('viking://peers/', 'Peer: '),
        category: 'peers',
        color: isDark ? '#38bdf8' : '#0284c7', // Cyan
        val: 18,
        degree: nodeDegreesMap.get(id) || 0,
      })
    })

    SKILLS_NODES.forEach((id) => {
      nodes.push({
        id,
        label: id.replace('viking://skills/', 'Skill: '),
        category: 'skills',
        color: isDark ? '#f59e0b' : '#d97706', // Amber
        val: 10,
        degree: nodeDegreesMap.get(id) || 0,
      })
    })

    SESSIONS_NODES.forEach((id) => {
      nodes.push({
        id,
        label: id.replace('viking://sessions/', 'Session: '),
        category: 'sessions',
        color: isDark ? '#0ea5e9' : '#0284c7', // Sky Blue
        val: 8,
        degree: nodeDegreesMap.get(id) || 0,
      })
    })

    RESOURCES_NODES.forEach((id) => {
      nodes.push({
        id,
        label: id.replace('viking://resources/', 'Resource: '),
        category: 'resources',
        color: isDark ? '#64748b' : '#475569', // Slate
        val: 5,
        degree: nodeDegreesMap.get(id) || 0,
      })
    })

    return nodes
  }, [isDark, nodeDegreesMap])

  const allNodesMap = React.useMemo(() => {
    const map = new Map<string, NodeData>()
    allNodes.forEach((node) => map.set(node.id, node))
    return map
  }, [allNodes])

  // Slice & Filter Logic with 1-Hop Neighbor Preservation
  const graphData = React.useMemo(() => {
    let filteredNodes = allNodes

    if (filterCategory !== 'all') {
      const targetCategoryNodes = allNodes.filter((n) => n.category === filterCategory)
      const targetCategoryNodeIds = new Set(targetCategoryNodes.map((n) => n.id))

      const neighborNodeIds = new Set<string>()
      rawLinks.forEach((link) => {
        const sId = typeof link.source === 'object' ? link.source.id : link.source
        const tId = typeof link.target === 'object' ? link.target.id : link.target
        if (targetCategoryNodeIds.has(sId)) neighborNodeIds.add(tId)
        if (targetCategoryNodeIds.has(tId)) neighborNodeIds.add(sId)
      })

      filteredNodes = allNodes.filter(
        (n) => targetCategoryNodeIds.has(n.id) || neighborNodeIds.has(n.id)
      )
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      filteredNodes = filteredNodes.filter(
        (n) => n.id.toLowerCase().includes(q) || n.label.toLowerCase().includes(q)
      )
    }

    const nodeIds = new Set(filteredNodes.map((n) => n.id))
    const filteredLinks = rawLinks.filter((link) => {
      const sId = typeof link.source === 'object' ? link.source.id : link.source
      const tId = typeof link.target === 'object' ? link.target.id : link.target
      return nodeIds.has(sId) && nodeIds.has(tId)
    })

    return {
      nodes: filteredNodes,
      links: filteredLinks,
    }
  }, [allNodes, filterCategory, rawLinks, searchQuery])

  React.useEffect(() => {
    onCountChange?.(graphData.nodes.length)
  }, [graphData.nodes.length, onCountChange])

  // Handle Node Click: Highlight and smooth camera flight
  const handleNodeClick = React.useCallback(
    (node: NodeData) => {
      const fullNode = allNodesMap.get(node.id) || node
      onNodeSelect?.(fullNode)

      if (fgRef.current) {
        if (mode === '3d' && fgRef.current.cameraPosition && typeof node.x === 'number') {
          const distance = 40
          const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z || 1)
          fgRef.current.cameraPosition(
            { x: node.x * distRatio, y: node.y * distRatio, z: (node.z || 0) * distRatio },
            node,
            1200,
          )
        } else if (mode === '2d' && fgRef.current.centerAt && typeof node.x === 'number') {
          fgRef.current.centerAt(node.x, node.y, 1000)
          fgRef.current.zoom(2.5, 1000)
        }
      }
    },
    [allNodesMap, mode, onNodeSelect],
  )

  // Highlight links connected to selected node
  const selectedNodeId = selectedNode?.id
  const isLinkConnectedToSelected = (link: LinkData) => {
    if (!selectedNodeId) return false
    const sId = typeof link.source === 'object' ? link.source.id : link.source
    const tId = typeof link.target === 'object' ? link.target.id : link.target
    return sId === selectedNodeId || tId === selectedNodeId
  }

  return (
    <div
      ref={containerRef}
      className="relative size-full overflow-hidden bg-background transition-colors duration-200"
    >
      {mode === '2d' ? (
        <ForceGraph2D
          ref={fgRef}
          width={dimensions.width}
          height={dimensions.height}
          graphData={graphData}
          warmupTicks={150}
          cooldownTicks={30}
          d3VelocityDecay={0.8}
          d3AlphaDecay={0.08}
          nodeLabel="label"
          nodeColor={(node: NodeData) => {
            if (selectedNodeId && node.id === selectedNodeId) {
              return '#f59e0b'
            }
            return node.color
          }}
          nodeVal={(node: NodeData) => node.val * 0.8}
          nodeRelSize={3}
          linkWidth={(link: LinkData) => (isLinkConnectedToSelected(link) ? 3 : 0.8)}
          linkColor={(link: LinkData) => {
            if (isLinkConnectedToSelected(link)) {
              return '#f59e0b'
            }
            return isDark ? 'rgba(56, 189, 248, 0.3)' : 'rgba(2, 132, 199, 0.3)'
          }}
          linkDirectionalParticles={(link: LinkData) => (isLinkConnectedToSelected(link) ? 4 : 0)}
          linkDirectionalParticleWidth={(link: LinkData) => (isLinkConnectedToSelected(link) ? 3 : 0)}
          linkDirectionalParticleSpeed={(link: LinkData) => (isLinkConnectedToSelected(link) ? 0.015 : 0)}
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
          warmupTicks={200}
          cooldownTicks={15}
          d3VelocityDecay={0.9}
          d3AlphaDecay={0.1}
          nodeResolution={4}
          linkCurvature={0.12}
          nodeLabel="label"
          nodeColor={(node: NodeData) => {
            if (selectedNodeId && node.id === selectedNodeId) {
              return '#f59e0b'
            }
            return node.color
          }}
          nodeVal={(node: NodeData) => node.val}
          nodeRelSize={3.5}
          linkWidth={(link: LinkData) => (isLinkConnectedToSelected(link) ? 3 : 0.8)}
          linkColor={(link: LinkData) => {
            if (isLinkConnectedToSelected(link)) {
              return '#f59e0b'
            }
            return isDark ? 'rgba(56, 189, 248, 0.3)' : 'rgba(2, 132, 199, 0.3)'
          }}
          linkDirectionalParticles={(link: LinkData) => (isLinkConnectedToSelected(link) ? 5 : 0)}
          linkDirectionalParticleWidth={(link: LinkData) => (isLinkConnectedToSelected(link) ? 3 : 0)}
          linkDirectionalParticleSpeed={(link: LinkData) => (isLinkConnectedToSelected(link) ? 0.015 : 0)}
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
