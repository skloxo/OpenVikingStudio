import { createFileRoute, Navigate } from '@tanstack/react-router'

export const Route = createFileRoute('/task-tracker')({
  component: () => <Navigate to="/tasks" replace />,
})
