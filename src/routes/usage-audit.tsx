import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/usage-audit')({
  beforeLoad: () => {
    throw redirect({ to: '/request-logs' })
  },
  component: () => null,
})
