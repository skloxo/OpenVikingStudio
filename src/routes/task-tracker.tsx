import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/task-tracker')({
  beforeLoad: () => {
    throw redirect({ to: '/tasks' })
  },
  component: () => null,
})
