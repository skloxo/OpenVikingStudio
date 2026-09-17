import { Brain, FileText, Wrench } from 'lucide-react'
import type { FindContextType } from '#/lib/retrieval'

export const TYPE_META: Record<
  FindContextType,
  { icon: typeof Brain; color: string; bgColor: string }
> = {
  resource: {
    icon: FileText,
    color: 'text-cyan-600 dark:text-cyan-400',
    bgColor: 'bg-cyan-500/10 border-cyan-500/20',
  },
  memory: {
    icon: Brain,
    color: 'text-amber-600 dark:text-amber-400',
    bgColor: 'bg-amber-500/10 border-amber-500/20',
  },
  skill: {
    icon: Wrench,
    color: 'text-sky-600 dark:text-sky-400',
    bgColor: 'bg-sky-500/10 border-sky-500/20',
  },
}
