import { createFileRoute, Outlet } from '@tanstack/react-router'

import { AdminConsoleShell } from './-components/admin-console-shell'

export const Route = createFileRoute('/admin')({
  component: AdminLayout,
})

function AdminLayout() {
  return (
    <AdminConsoleShell>
      <Outlet />
    </AdminConsoleShell>
  )
}
