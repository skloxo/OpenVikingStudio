import { FolderTreeIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Card, CardContent, CardHeader, CardTitle } from '#/components/ui/card'

interface WorkspaceStorageCardProps {
  resourceUri?: string
  skillUri?: string
}

export function WorkspaceStorageCard({
  resourceUri,
  skillUri,
}: WorkspaceStorageCardProps) {
  const { t } = useTranslation('settings')

  return (
    <Card className="gap-0 overflow-hidden border-border/80 bg-card py-0 shadow-sm">
      <CardHeader className="gap-2 border-b border-border/60 bg-muted/20 px-5 py-3.5">
        <div className="flex items-center gap-2">
          <div className="flex size-7 items-center justify-center rounded-md bg-cyan-500/10 text-cyan-500 border border-cyan-500/30">
            <FolderTreeIcon className="size-4" />
          </div>
          <div>
            <CardTitle className="text-sm font-semibold">
              {t('hub.workspace.title')}
            </CardTitle>
            <p className="text-[11px] text-muted-foreground">
              {t('hub.workspace.description')}
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="grid gap-3 px-5 py-4 sm:grid-cols-3">
        <div className="flex flex-col rounded-md border bg-muted/20 p-3 space-y-1">
          <span className="text-[11px] text-muted-foreground font-medium">
            {t('hub.workspace.rootUri')}
          </span>
          <span className="font-mono text-xs font-bold text-foreground">
            viking://
          </span>
          <span className="text-[11px] text-muted-foreground">
            AGFS Root Mount
          </span>
        </div>
        <div className="flex flex-col rounded-md border bg-muted/20 p-3 space-y-1">
          <span className="text-[11px] text-muted-foreground font-medium">
            {t('hub.workspace.defaultResourceTarget')}
          </span>
          <span className="font-mono text-xs font-bold text-foreground">
            {resourceUri || 'viking://resources/'}
          </span>
          <span className="text-[11px] text-muted-foreground">
            Auto Ingest Namespace
          </span>
        </div>
        <div className="flex flex-col rounded-md border bg-muted/20 p-3 space-y-1">
          <span className="text-[11px] text-muted-foreground font-medium">
            {t('hub.workspace.defaultSkillTarget')}
          </span>
          <span className="font-mono text-xs font-bold text-foreground">
            {skillUri || 'viking://skills/'}
          </span>
          <span className="text-[11px] text-muted-foreground">
            Skill Protocol Storage
          </span>
        </div>
      </CardContent>
    </Card>
  )
}
