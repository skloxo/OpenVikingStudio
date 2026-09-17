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
  { id: 'viking://peers/antigravity@2080ti', label: 'Peer: 2080Ti Antigravity', category: 'peers' },
  { id: 'viking://peers/antigravity@rtx3070', label: 'Peer: RTX3070 Antigravity', category: 'peers' },
  { id: 'viking://peers/openclaw@2080ti', label: 'Peer: 2080Ti OpenClaw', category: 'peers' },
  { id: 'viking://peers/workbuddy@rtx3070', label: 'Peer: RTX3070 WorkBuddy', category: 'peers' },
  { id: 'viking://peers/macstudio', label: 'Peer: Mac Studio M3', category: 'peers' },
  { id: 'viking://peers/xiaomimo@2080ti', label: 'Peer: 2080Ti XiaomiMo', category: 'peers' },
  { id: 'viking://peers/hermes@2080ti', label: 'Peer: 2080Ti Hermes', category: 'peers' },
]

function getPeerForSkill(skillName: string): string {
  const low = skillName.toLowerCase()
  if (low.includes('mac') || low.includes('studio') || low.includes('mlx') || low.includes('metal') || low.includes('llm')) {
    return 'viking://peers/macstudio'
  }
  if (low.includes('remote') || low.includes('3070') || low.includes('workbuddy')) {
    return 'viking://peers/antigravity@rtx3070'
  }
  if (low.includes('claw') || low.includes('bus') || low.includes('cluster') || low.includes('fleet')) {
    return 'viking://peers/openclaw@2080ti'
  }
  if (low.includes('gateway') || low.includes('hermes')) {
    return 'viking://peers/hermes@2080ti'
  }
  if (low.includes('mimo') || low.includes('xiaomi')) {
    return 'viking://peers/xiaomimo@2080ti'
  }
  return 'viking://peers/antigravity@2080ti'
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
          source: 'viking://peers/antigravity@2080ti',
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
