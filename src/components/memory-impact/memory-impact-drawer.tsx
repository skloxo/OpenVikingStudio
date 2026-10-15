import { useState } from 'react'
import { BrainCircuitIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '#/components/ui/sheet'
import type { SessionMeta } from '@ov-server/api/v1/sessions'
import { UnifiedMemoryImpactView } from './memory-impact-view'
import type {
  UniversalMemoryDiff,
  UniversalMemoryDiffOperation,
} from './types'

export interface UnifiedMemoryImpactDrawerProps {
  /** 受控模式：外部传入的完整 Diff 列表 */
  diffs?: UniversalMemoryDiff[]
  /** 受控模式：外部直接传入扁平原子操作列表（自动包装为单一 Diff） */
  operations?: UniversalMemoryDiffOperation[]
  /** 异步查询模式：传入会话元数据，在抽屉打开时按需触发请求 */
  session?: SessionMeta
  /** 外部控制抽屉开关 */
  open?: boolean
  onOpenChange?: (open: boolean) => void
  /** 自定义触发器按钮节点，未传入受控 open 时有效 */
  trigger?: React.ReactNode
  /** 自定义标题与描述文案 */
  title?: string
  description?: string
}

export function UnifiedMemoryImpactDrawer({
  diffs,
  operations,
  session,
  open: externalOpen,
  onOpenChange: setExternalOpen,
  trigger,
  title: customTitle,
  description: customDescription,
}: UnifiedMemoryImpactDrawerProps) {
  const { t } = useTranslation('sessions')
  const [internalOpen, setInternalOpen] = useState(false)
  const isControlled = externalOpen !== undefined
  const isOpen = isControlled ? externalOpen : internalOpen
  const handleOpenChange = (nextOpen: boolean) => {
    if (isControlled) {
      setExternalOpen?.(nextOpen)
    } else {
      setInternalOpen(nextOpen)
    }
  }

  const titleText = customTitle || t('impact.title', '记忆增量影响')
  const descriptionText =
    customDescription ||
    t('impact.descriptionDefault', {
      defaultValue: '该次物理操作对系统知识库产生的变更快照',
    })

  return (
    <>
      {trigger ? (
        <span onClick={() => handleOpenChange(true)} className="inline-flex">
          {trigger}
        </span>
      ) : null}

      <Sheet open={isOpen} onOpenChange={handleOpenChange}>
        <SheetContent className="gap-0 data-[side=right]:sm:max-w-3xl flex flex-col">
          <SheetHeader className="border-b px-6 py-4 shrink-0">
            <div className="flex items-center gap-3 pr-10">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/15">
                <BrainCircuitIcon className="size-4.5" />
              </div>
              <div className="min-w-0">
                <SheetTitle className="text-base font-semibold text-foreground">
                  {titleText}
                </SheetTitle>
                <SheetDescription className="text-xs text-muted-foreground">
                  {descriptionText}
                </SheetDescription>
              </div>
            </div>
          </SheetHeader>

          <div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">
            <UnifiedMemoryImpactView
              diffs={diffs}
              operations={operations}
              session={session}
              isOpen={isOpen}
            />
          </div>
        </SheetContent>
      </Sheet>
    </>
  )
}
