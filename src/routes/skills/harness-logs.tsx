import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/skills/harness-logs')({
  beforeLoad: () => {
    throw redirect({
      to: '/request-logs',
      search: {
        tab: 'harness',
      },
    })
  },
  component: () => null,
})
