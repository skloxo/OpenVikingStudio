import * as React from 'react'

import { ExportBackupCard } from './data-ops/export-backup-card'
import { ImportRestoreCard } from './data-ops/import-restore-card'

export function DataOpsTab() {
  return (
    <div className="space-y-4">
      <ExportBackupCard />
      <ImportRestoreCard />
    </div>
  )
}
