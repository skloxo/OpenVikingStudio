import { useQuery } from '@tanstack/react-query'
import type { TFunction } from 'i18next'
import { useAppConnection } from '#/hooks/use-app-connection'
import {
  BUILTIN_SKILLS_ROOT,
  fetchCompileSkills,
  type CompileSkill,
} from './api'

const BUILTIN_GUIDE_KEYS = new Set([
  'llm-wiki',
  'knowledge-distillation',
  'daily-report',
  'knowledge-graph',
  'ov-session-report',
])

export function skillScope(uri: string) {
  if (uri.startsWith(`${BUILTIN_SKILLS_ROOT}/`)) return 'builtinSkills'
  if (uri.startsWith('viking://user/')) return 'mySkills'
  if (uri.startsWith('viking://agent/skills/')) return 'sharedSkills'
  return 'otherSkills'
}

export function skillGuide(skill: CompileSkill, t: TFunction<'compile'>) {
  if (skillScope(skill.uri) !== 'builtinSkills') return null
  const key = skill.uri.replace(/\/$/, '').split('/').pop()
  if (!key || !BUILTIN_GUIDE_KEYS.has(key)) return null
  return {
    name: t(`builtin.${key}.name` as never),
    description: t(`builtin.${key}.description` as never),
    inputs: t(`builtin.${key}.inputs` as never),
    outputs: t(`builtin.${key}.outputs` as never),
    limits: t(`builtin.${key}.limits` as never),
    specialized: key === 'ov-session-report',
  }
}

export function useCompileSkills() {
  const { identityScopeKey, connection } = useAppConnection()
  const mine = useQuery({
    queryKey: ['compile-skills', identityScopeKey, 'mine'],
    queryFn: ({ signal }) =>
      fetchCompileSkills(
        signal,
        `viking://user/${connection.userId || 'default'}/skills`,
      ),
    staleTime: 30_000,
  })
  const shared = useQuery({
    queryKey: ['compile-skills', identityScopeKey, 'shared'],
    queryFn: ({ signal }) => fetchCompileSkills(signal, 'viking://agent/skills'),
    staleTime: 30_000,
  })
  const builtin = useQuery({
    queryKey: ['compile-skills', identityScopeKey, 'builtin'],
    queryFn: ({ signal }) => fetchCompileSkills(signal, BUILTIN_SKILLS_ROOT),
    staleTime: 30_000,
  })
  return {
    mine,
    shared,
    builtin,
    data: [
      ...(builtin.data ?? []),
      ...(mine.data ?? []),
      ...(shared.data ?? []),
    ],
  }
}
