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
  role?: string
}

export interface RawTopologyEdge {
  source: string
  target: string
  link_type?: string
  description?: string
  weight?: number
}

export interface TopologyData {
  nodes: RawTopologyNode[]
  edges: RawTopologyEdge[]
}

export function useKnowledgeTopology() {
  return useQuery<TopologyData>({
    queryKey: ['knowledge-graph-topology'],
    queryFn: async () => {
      // 1. 优先调用后端单一真实真相源 (Card-20F SSOT)
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
        // 降级使用并行领域真实接口兜底
      }

      // 2. 兜底策略：从真实领域接口拉取（绝不使用硬编码假数据与随机生成）
      const nodes: RawTopologyNode[] = []
      const edges: RawTopologyEdge[] = []

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
        }
      }

      return { nodes, edges }
    },
    staleTime: 30_000,
  })
}
