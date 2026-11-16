import { createFileRoute } from '@tanstack/react-router'
import { useAppConnection } from '#/hooks/use-app-connection'
import { CompileForm } from './-components/compile-form'

export const Route = createFileRoute('/compile/new')({
  validateSearch: (
    s: Record<string, unknown>,
  ): { fromTask?: string; from?: string; target?: string } => ({
    target:
      typeof s.target === 'string' && s.target.startsWith('viking://')
        ? s.target
        : undefined,
    fromTask: typeof s.fromTask === 'string' ? s.fromTask : undefined,
    from:
      typeof s.from === 'string' && s.from.startsWith('viking://')
        ? s.from
        : undefined,
  }),
  component: NewCompilePage,
})

function NewCompilePage() {
  const { identityScopeKey } = useAppConnection()
  const { fromTask, from, target } = Route.useSearch()
  return (
    <CompileForm
      key={`${identityScopeKey}:${target || ''}:${fromTask || ''}:${from || ''}`}
      fromTask={target ? undefined : fromTask}
      sourceUri={target ? undefined : from}
      target={target}
    />
  )
}
