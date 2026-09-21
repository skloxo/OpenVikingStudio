import { createFileRoute, Navigate } from '@tanstack/react-router'

export const Route = createFileRoute('/usage-audit')({
  component: () => <Navigate to="/request-logs" replace />,
})
