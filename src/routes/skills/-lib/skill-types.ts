export type SkillScope = 'agent' | 'user'

export type SkillScopeFilter = 'all' | 'engineering' | 'agent' | 'data' | 'idle'

export type SkillFile = {
  isDir: boolean
  name: string
  path: string
}

export type SkillItem = {
  description: string
  name: string
  scope: SkillScope
  uri: string
  path?: string
  source?: string
  cnName?: string
  cnDescription?: string
  content?: string
  files?: SkillFile[]
  file_count?: number
}

export type SkillListResult = {
  skills?: unknown[]
}

export type SkillDetail = SkillItem & {
  allowedTools: string[]
  content: string
  files: SkillFile[]
  overview: string
  tags: string[]
}

export interface SkillTocItem {
  level: number
  title: string
  lineIndex: number
  id: string
}

export interface SkillHarnessMetrics {
  totalCalls: number
  blockedCalls: number
  findCalls: number
  storeCalls: number
  activeSkillsCount: number
  activeUtilizationRatio: string | null
  lessonsCount: number | null
  builtinLessonsCount: number | null
  autoWakeupRate: string | null
  calculatedSuccessRate: string | null
  calculatedCentralizedRatio: string | null
  contextCompressionRatio: string | null
}
