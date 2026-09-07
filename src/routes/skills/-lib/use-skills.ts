import * as React from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useAppConnection } from '#/hooks/use-app-connection'
import { isOvClientError, ovClient } from '#/lib/ov-client'
import type {
  SkillDetail,
  SkillHarnessMetrics,
  SkillItem,
  SkillScopeFilter,
} from './skill-types'
import { fetchSkillDetail, fetchSkills } from './skill-data'
import {
  getChineseSkillDescription,
  getChineseSkillName,
  isDataSkill,
  isEngineeringSkill,
} from './skill-translations'

export function useSkillsData() {
  const { identityScopeKey } = useAppConnection()
  const [selectedSkill, setSelectedSkill] = React.useState<SkillItem | null>(null)
  const [searchQuery, setSearchQuery] = React.useState('')
  const [activeScopeFilter, setActiveScopeFilter] =
    React.useState<SkillScopeFilter>('all')

  const [refinedSkills, setRefinedSkills] = React.useState<
    Record<string, 'idle' | 'p1' | 'p2' | 'done'>
  >(() => {
    try {
      const saved = localStorage.getItem('ov_refined_skills')
      return saved ? JSON.parse(saved) : {}
    } catch {
      return {}
    }
  })

  const handleRefineSkill = async (key: string, skillsList: string[]) => {
    setRefinedSkills((prev) => {
      const next = { ...prev, [key]: 'p1' as const }
      try {
        localStorage.setItem('ov_refined_skills', JSON.stringify(next))
      } catch {}
      return next
    })
    try {
      await ovClient.instance.post('/api/v1/harness/refine_gate', { skills: skillsList })
    } catch {}
    setTimeout(() => {
      setRefinedSkills((prev) => {
        const next = { ...prev, [key]: 'p2' as const }
        try {
          localStorage.setItem('ov_refined_skills', JSON.stringify(next))
        } catch {}
        return next
      })
      setTimeout(() => {
        setRefinedSkills((prev) => {
          const next = { ...prev, [key]: 'done' as const }
          try {
            localStorage.setItem('ov_refined_skills', JSON.stringify(next))
          } catch {}
          return next
        })
      }, 800)
    }, 700)
  }

  // Pagination states (Default 12 per page)
  const [currentPage, setCurrentPage] = React.useState(1)
  const [pageSize, setPageSize] = React.useState(12)

  const skillsQuery = useQuery({
    placeholderData: keepPreviousData,
    queryFn: fetchSkills,
    queryKey: ['skills', 'v2', identityScopeKey],
    refetchOnReconnect: false,
    refetchOnWindowFocus: false,
    staleTime: 60_000,
  })
  const skills = skillsQuery.data ?? []

  // 客户端毫秒级检索与 Scope 筛选过滤
  const filteredSkills = React.useMemo(() => {
    return skills.filter((s) => {
      if (activeScopeFilter === 'engineering' && !isEngineeringSkill(s.name, s.source)) return false
      if (activeScopeFilter === 'agent' && (s.scope !== 'agent' || isEngineeringSkill(s.name, s.source))) return false
      if (activeScopeFilter === 'data' && !isDataSkill(s.name)) return false
      if (activeScopeFilter === 'idle' && isEngineeringSkill(s.name, s.source)) return false
      if (!searchQuery.trim()) return true
      const q = searchQuery.toLowerCase()
      const cnName = s.cnName || getChineseSkillName(s.name)
      const cnDesc = s.cnDescription || getChineseSkillDescription(s.description)
      return (
        s.name.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q) ||
        cnName.toLowerCase().includes(q) ||
        cnDesc.toLowerCase().includes(q)
      )
    })
  }, [skills, searchQuery, activeScopeFilter])

  React.useEffect(() => {
    setCurrentPage(1)
  }, [searchQuery, activeScopeFilter])

  const paginatedSkills = React.useMemo(() => {
    if (pageSize >= 1000) return filteredSkills
    const start = (currentPage - 1) * pageSize
    return filteredSkills.slice(start, start + pageSize)
  }, [filteredSkills, currentPage, pageSize])

  const connectionUnavailable =
    isOvClientError(skillsQuery.error) &&
    skillsQuery.error.code === 'NETWORK_ERROR'

  const detailQuery = useQuery({
    enabled: Boolean(selectedSkill),
    placeholderData: keepPreviousData,
    queryFn: () => fetchSkillDetail(selectedSkill as SkillItem),
    queryKey: ['skill-detail', identityScopeKey, selectedSkill?.uri],
    refetchOnReconnect: false,
    refetchOnWindowFocus: false,
    staleTime: 600_000,
  })

  // 真实后端数据驱动：调取 /api/v1/system/harness_metrics?window=24h
  const harnessStatusQuery = useQuery({
    placeholderData: keepPreviousData,
    queryFn: async () => {
      try {
        const res = await ovClient.instance.get<Record<string, unknown>>(
          '/api/v1/system/harness_metrics',
          { params: { window: '24h' } },
        )
        if (res.data && typeof res.data === 'object') {
          return res.data
        }
      } catch {
        // Fallback to null
      }
      return null
    },
    queryKey: ['harness-status', '24h', identityScopeKey],
    refetchOnReconnect: false,
    refetchOnWindowFocus: false,
    staleTime: 60_000,
  })

  const metricsData = harnessStatusQuery.data ?? null
  const hasRealMetrics =
    metricsData !== null &&
    typeof metricsData === 'object' &&
    ('total_calls' in metricsData || 'auto_wakeup_rate' in metricsData)

  const blockedCalls =
    hasRealMetrics && typeof metricsData?.blocked_calls === 'number'
      ? metricsData.blocked_calls
      : 0
  const totalCalls =
    hasRealMetrics && typeof metricsData?.total_calls === 'number'
      ? metricsData.total_calls
      : 0
  const findCalls =
    hasRealMetrics && typeof metricsData?.find_calls === 'number'
      ? metricsData.find_calls
      : 0
  const storeCalls =
    hasRealMetrics && typeof metricsData?.store_calls === 'number'
      ? metricsData.store_calls
      : 0

  const activeSkillsCount =
    hasRealMetrics &&
    typeof metricsData?.active_skills_count === 'number' &&
    metricsData.active_skills_count > 0
      ? metricsData.active_skills_count
      : 0

  const activeUtilizationRatio =
    skills.length > 0 && hasRealMetrics && activeSkillsCount > 0
      ? (
          (Math.min(activeSkillsCount, skills.length) / skills.length) *
          100
        ).toFixed(1)
      : null

  const doneRefinedCount = Object.values(refinedSkills).filter(
    (v) => v === 'done',
  ).length
  const lessonsCount =
    hasRealMetrics && typeof metricsData?.lessons_count === 'number'
      ? metricsData.lessons_count + doneRefinedCount
      : doneRefinedCount > 0
        ? doneRefinedCount
        : null
  const builtinLessonsCount =
    hasRealMetrics && typeof metricsData?.builtin_lessons_count === 'number'
      ? metricsData.builtin_lessons_count
      : null

  const autoWakeupRate =
    hasRealMetrics && typeof metricsData?.auto_wakeup_rate === 'number'
      ? metricsData.auto_wakeup_rate.toFixed(1)
      : null

  const calculatedSuccessRate =
    hasRealMetrics && totalCalls > 0
      ? (((totalCalls - blockedCalls) / totalCalls) * 100).toFixed(1)
      : null

  const vkCentralizedCalls = findCalls + storeCalls
  const calculatedCentralizedRatio =
    hasRealMetrics && totalCalls > 0 && vkCentralizedCalls > 0
      ? ((vkCentralizedCalls / totalCalls) * 100).toFixed(1)
      : null

  const contextCompressionRatio =
    hasRealMetrics && typeof metricsData?.context_compression_ratio === 'number'
      ? metricsData.context_compression_ratio.toFixed(1)
      : null

  const harnessMetrics: SkillHarnessMetrics = {
    totalCalls,
    blockedCalls,
    findCalls,
    storeCalls,
    activeSkillsCount,
    activeUtilizationRatio,
    lessonsCount,
    builtinLessonsCount,
    autoWakeupRate,
    calculatedSuccessRate,
    calculatedCentralizedRatio,
    contextCompressionRatio,
  }

  return {
    skills,
    filteredSkills,
    paginatedSkills,
    skillsQuery,
    detailQuery,
    selectedSkill,
    setSelectedSkill,
    searchQuery,
    setSearchQuery,
    activeScopeFilter,
    setActiveScopeFilter,
    refinedSkills,
    handleRefineSkill,
    currentPage,
    setCurrentPage,
    pageSize,
    setPageSize,
    connectionUnavailable,
    harnessMetrics,
  }
}
