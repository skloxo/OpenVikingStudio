import { useQuery } from '@tanstack/react-query'
import { ovClient } from '#/lib/ov-client'
import { fetchSessions } from '#/lib/sessions/api'
import { fetchFsList } from '#/routes/resources/-lib/api'
import { fetchSkills } from '#/routes/skills/-lib/skill-data'

export interface RawTopologyNode {
  id: string
  label: string
  category: 'peers' | 'sessions' | 'skills' | 'resources'
  content_preview?: string
}

export interface RawTopologyEdge {
  source: string
  target: string
  link_type?: string
}

export interface TopologyData {
  nodes: RawTopologyNode[]
  edges: RawTopologyEdge[]
}

const PEERS_NODES: RawTopologyNode[] = [
  { id: 'viking://peers/master_agent', label: 'Peer: master_agent', category: 'peers' },
  { id: 'viking://peers/researcher_agent', label: 'Peer: researcher_agent', category: 'peers' },
  { id: 'viking://peers/developer_agent', label: 'Peer: developer_agent', category: 'peers' },
  { id: 'viking://peers/designer_agent', label: 'Peer: designer_agent', category: 'peers' },
  { id: 'viking://peers/product_manager', label: 'Peer: product_manager', category: 'peers' },
  { id: 'viking://peers/operator_agent', label: 'Peer: operator_agent', category: 'peers' },
  { id: 'viking://peers/planner_agent', label: 'Peer: planner_agent', category: 'peers' },
  { id: 'viking://peers/evaluator_agent', label: 'Peer: evaluator_agent', category: 'peers' },
  { id: 'viking://peers/test_agent', label: 'Peer: test_agent', category: 'peers' },
]

function getPeerForSkill(skillName: string): string {
  const low = skillName.toLowerCase()
  if (low.includes('test') || low.includes('tdd') || low.includes('debug') || low.includes('code') || low.includes('dev')) {
    return 'viking://peers/developer_agent'
  }
  if (low.includes('research') || low.includes('search') || low.includes('retrieval') || low.includes('scrapling')) {
    return 'viking://peers/researcher_agent'
  }
  if (low.includes('ops') || low.includes('satellite') || low.includes('docker') || low.includes('fleet')) {
    return 'viking://peers/operator_agent'
  }
  if (low.includes('ui') || low.includes('cockpit') || low.includes('design') || low.includes('style')) {
    return 'viking://peers/designer_agent'
  }
  if (low.includes('eval') || low.includes('radar') || low.includes('benchmark') || low.includes('audit')) {
    return 'viking://peers/evaluator_agent'
  }
  if (low.includes('ticket') || low.includes('spec') || low.includes('plan')) {
    return 'viking://peers/planner_agent'
  }
  return 'viking://peers/master_agent'
}

export function useKnowledgeTopology() {
  return useQuery<TopologyData>({
    queryKey: ['knowledge-graph-topology'],
    queryFn: async () => {
      // 1. Try unified backend topology endpoint first
      try {
        const resp = await ovClient.instance.get('/api/v1/relations/topology')
        const result = resp.data?.result
        if (result?.nodes && Array.isArray(result.nodes) && result.nodes.length > 0) {
          return {
            nodes: result.nodes,
            edges: Array.isArray(result.edges) ? result.edges : [],
          }
        }
      } catch {
        // Fall back to parallel resource collection
      }

      // 2. Parallel truthful retrieval from primary domain endpoints
      const nodes: RawTopologyNode[] = [...PEERS_NODES]
      const edges: RawTopologyEdge[] = []

      for (const peer of PEERS_NODES.slice(1)) {
        edges.push({
          source: 'viking://peers/master_agent',
          target: peer.id,
          link_type: 'orchestrates',
        })
      }

      const [skillsResult, sessionsResult, resourcesResult] = await Promise.allSettled([
        fetchSkills(),
        fetchSessions(),
        fetchFsList('viking://resources', { nodeLimit: 80 }),
      ])

      if (skillsResult.status === 'fulfilled' && Array.isArray(skillsResult.value)) {
        for (const skill of skillsResult.value.slice(0, 100)) {
          if (!skill.name || skill.name.startsWith('.')) continue
          const skillId = skill.uri || `viking://skills/${skill.name}`
          nodes.push({
            id: skillId,
            label: `Skill: ${skill.name}`,
            category: 'skills',
            content_preview: skill.description,
          })
          edges.push({
            source: getPeerForSkill(skill.name),
            target: skillId,
            link_type: 'applies',
          })
        }
      }

      if (sessionsResult.status === 'fulfilled' && Array.isArray(sessionsResult.value)) {
        for (const session of sessionsResult.value.slice(0, 80)) {
          if (!session.session_id) continue
          const sessId = `viking://sessions/${session.session_id}`
          nodes.push({
            id: sessId,
            label: `Session: ${session.session_id.slice(0, 8)}`,
            category: 'sessions',
          })
          edges.push({
            source: 'viking://peers/master_agent',
            target: sessId,
            link_type: 'interacts',
          })
        }
      }

      if (resourcesResult.status === 'fulfilled' && Array.isArray(resourcesResult.value?.entries)) {
        for (const res of resourcesResult.value.entries.slice(0, 80)) {
          if (!res.uri) continue
          const name = res.name || res.uri.split('/').pop() || 'resource'
          nodes.push({
            id: res.uri,
            label: `Resource: ${name}`,
            category: 'resources',
            content_preview: res.abstract,
          })
          edges.push({
            source: 'viking://peers/master_agent',
            target: res.uri,
            link_type: 'indexes',
          })
        }
      }

      return { nodes, edges }
    },
    staleTime: 60_000,
  })
}
