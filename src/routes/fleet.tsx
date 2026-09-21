import { createFileRoute, Navigate } from '@tanstack/react-router'

export const Route = createFileRoute('/fleet')({
  component: () => <Navigate to="/monitoring" replace />,
})
