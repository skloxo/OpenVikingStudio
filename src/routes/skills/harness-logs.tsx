import { createFileRoute } from '@tanstack/react-router'
import { HarnessLogsPage } from '#/routes/harness-logs'

export const Route = createFileRoute('/skills/harness-logs')({
  component: HarnessLogsPage,
})
