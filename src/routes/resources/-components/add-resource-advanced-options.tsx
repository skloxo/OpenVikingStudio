import { ChevronRight, Info } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Checkbox } from '#/components/ui/checkbox'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '#/components/ui/collapsible'
import { Input } from '#/components/ui/input'
import { Label } from '#/components/ui/label'
import { Textarea } from '#/components/ui/textarea'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '#/components/ui/tooltip'

export interface AddResourceAdvancedOptionsProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  strict: boolean
  onStrictChange: (val: boolean) => void
  createParent: boolean
  onCreateParentChange: (val: boolean) => void
  directlyUploadMedia: boolean
  onDirectlyUploadMediaChange: (val: boolean) => void
  isRemote: boolean
  ignoreDirs: string
  onIgnoreDirsChange: (val: string) => void
  include: string
  onIncludeChange: (val: string) => void
  exclude: string
  onExcludeChange: (val: string) => void
  reason: string
  onReasonChange: (val: string) => void
  instruction: string
  onInstructionChange: (val: string) => void
}

export function AddResourceAdvancedOptions({
  open,
  onOpenChange,
  strict,
  onStrictChange,
  createParent,
  onCreateParentChange,
  directlyUploadMedia,
  onDirectlyUploadMediaChange,
  isRemote,
  ignoreDirs,
  onIgnoreDirsChange,
  include,
  onIncludeChange,
  exclude,
  onExcludeChange,
  reason,
  onReasonChange,
  instruction,
  onInstructionChange,
}: AddResourceAdvancedOptionsProps) {
  const { t } = useTranslation('addResource')

  return (
    <Collapsible open={open} onOpenChange={onOpenChange}>
      <CollapsibleTrigger className="flex items-center gap-1 text-sm font-medium text-muted-foreground hover:text-foreground">
        <ChevronRight
          className={`size-4 transition-transform ${open ? 'rotate-90' : ''}`}
        />
        {t('advancedOptions')}
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="mt-3 space-y-4 rounded-lg border border-border/50 bg-muted/10 p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
            <Label className="flex items-center gap-2">
              <Checkbox
                checked={strict}
                onCheckedChange={(checked) => onStrictChange(Boolean(checked))}
              />
              <span>{t('strict')}</span>
              <Tooltip>
                <TooltipTrigger
                  render={
                    <Info className="size-3.5 text-muted-foreground" />
                  }
                />
                <TooltipContent>{t('strict.hint')}</TooltipContent>
              </Tooltip>
            </Label>
            <Label className="flex items-center gap-2">
              <Checkbox
                checked={createParent}
                onCheckedChange={(checked) =>
                  onCreateParentChange(Boolean(checked))
                }
              />
              <span>{t('createParent')}</span>
              <Tooltip>
                <TooltipTrigger
                  render={
                    <Info className="size-3.5 text-muted-foreground" />
                  }
                />
                <TooltipContent>{t('createParent.hint')}</TooltipContent>
              </Tooltip>
            </Label>
            <Label className="flex items-center gap-2">
              <Checkbox
                checked={directlyUploadMedia}
                onCheckedChange={(checked) =>
                  onDirectlyUploadMediaChange(Boolean(checked))
                }
              />
              <span>{t('directlyUploadMedia')}</span>
              <Tooltip>
                <TooltipTrigger
                  render={
                    <Info className="size-3.5 text-muted-foreground" />
                  }
                />
                <TooltipContent>
                  {t('directlyUploadMedia.hint')}
                </TooltipContent>
              </Tooltip>
            </Label>
          </div>

          {isRemote && (
            <div className="space-y-4 border-t border-border/50 pt-4">
              <div className="space-y-2">
                <Label htmlFor="add-resource-ignore-dirs">
                  {t('directoryScan.ignoreDirs')}
                </Label>
                <Input
                  id="add-resource-ignore-dirs"
                  placeholder={t('directoryScan.ignoreDirs.placeholder')}
                  value={ignoreDirs}
                  onChange={(e) => onIgnoreDirsChange(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="add-resource-include">
                  {t('directoryScan.include')}
                </Label>
                <Input
                  id="add-resource-include"
                  placeholder={t('directoryScan.include.placeholder')}
                  value={include}
                  onChange={(e) => onIncludeChange(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="add-resource-exclude">
                  {t('directoryScan.exclude')}
                </Label>
                <Input
                  id="add-resource-exclude"
                  placeholder={t('directoryScan.exclude.placeholder')}
                  value={exclude}
                  onChange={(e) => onExcludeChange(e.target.value)}
                />
              </div>
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="add-resource-reason">{t('reason')}</Label>
            <Textarea
              id="add-resource-reason"
              placeholder={t('reason.placeholder')}
              value={reason}
              onChange={(e) => onReasonChange(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="add-resource-instruction">
              {t('instruction')}
            </Label>
            <Textarea
              id="add-resource-instruction"
              placeholder={t('instruction.placeholder')}
              value={instruction}
              onChange={(e) => onInstructionChange(e.target.value)}
            />
          </div>
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}
