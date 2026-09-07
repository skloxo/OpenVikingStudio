import * as React from 'react'
import {
  AlignLeftIcon,
  CheckIcon,
  CopyIcon,
  FileCode2Icon,
  HashIcon,
  ListTreeIcon,
  UserRoundIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '#/components/ui/sheet'
import { cn } from '#/lib/utils'
import type { SkillDetail, SkillTocItem } from '../-lib/skill-types'
import { extractSkillToc, extractSopOverview } from '../-lib/skill-data'
import { getFallbackSkillContent } from '../-lib/skill-translations'

interface SkillDetailSheetProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  detail: SkillDetail | null
  isLoading: boolean
}

function DetailSection({
  title,
  children,
  className,
}: {
  title: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn('space-y-1.5', className)}>
      <h3 className="font-semibold text-foreground/80 tracking-wide font-sans text-xs">
        {title}
      </h3>
      {children}
    </div>
  )
}

function DetailTagList({
  title,
  values,
  empty,
}: {
  title: string
  values: string[]
  empty: string
}) {
  return (
    <DetailSection title={title}>
      {values.length === 0 ? (
        <p className="text-muted-foreground">{empty}</p>
      ) : (
        <div className="flex flex-wrap gap-1">
          {values.map((val) => (
            <Badge
              key={val}
              variant="outline"
              className="text-[11px] px-1.5 py-0 border-border/60 bg-muted/20 text-muted-foreground font-mono"
            >
              {val}
            </Badge>
          ))}
        </div>
      )}
    </DetailSection>
  )
}

function DetailMetric({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode
  label: string
  value: string
}) {
  return (
    <div className="flex items-center gap-2 rounded border border-border/50 bg-muted/20 px-2.5 py-1.5 font-sans">
      <span className="text-muted-foreground">{icon}</span>
      <span className="text-muted-foreground text-[11px]">{label}:</span>
      <span className="font-semibold text-foreground text-xs ml-auto font-mono">
        {value}
      </span>
    </div>
  )
}

function SkillSourceViewer({ content }: { content: string }) {
  const { t } = useTranslation('skillsPage')
  const [copied, setCopied] = React.useState(false)
  const [showToc, setShowToc] = React.useState(true)
  const [activeTocIdx, setActiveTocIdx] = React.useState<number | null>(null)
  const lines = React.useMemo(() => content.split('\n'), [content])
  const toc = React.useMemo(() => extractSkillToc(content), [content])
  const lineRefs = React.useRef<(HTMLDivElement | null)[]>([])

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation()
    void navigator.clipboard.writeText(content)
    setCopied(true)
    toast.success(t('skillsPage.toc.copied', { defaultValue: '源码已复制到剪贴板' }))
    setTimeout(() => setCopied(false), 2000)
  }

  const handleJumpToLine = (lineIdx: number) => {
    setActiveTocIdx(lineIdx)
    const el = lineRefs.current[lineIdx]
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }

  return (
    <div className="flex flex-col gap-2 flex-1 min-h-0">
      <div className="flex items-center justify-between gap-2 rounded border border-border/60 bg-muted/20 px-3 py-1.5 font-mono text-[11px]">
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1 font-semibold text-foreground">
            <FileCode2Icon className="size-3.5 text-cyan-500" />
            SKILL.md
          </span>
          <span className="text-muted-foreground/40">|</span>
          <span className="text-muted-foreground">{lines.length} 行代码</span>
          {toc.length > 0 && (
            <>
              <span className="text-muted-foreground/40">|</span>
              <button
                type="button"
                onClick={() => setShowToc((prev) => !prev)}
                className={cn(
                  'flex items-center gap-1 rounded px-1.5 py-0.5 transition-colors cursor-pointer',
                  showToc
                    ? 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 font-semibold'
                    : 'text-muted-foreground hover:text-foreground',
                )}
                title="切换 TOC 目录视图"
              >
                <ListTreeIcon className="size-3" />
                <span>{toc.length} 个章节</span>
              </button>
            </>
          )}
        </div>

        <Button
          size="sm"
          variant="outline"
          onClick={handleCopy}
          className="h-6 rounded px-2 text-[11px] font-mono gap-1 text-muted-foreground hover:text-foreground cursor-pointer"
        >
          {copied ? (
            <>
              <CheckIcon className="size-3 text-cyan-500" />
              <span>已复制</span>
            </>
          ) : (
            <>
              <CopyIcon className="size-3" />
              <span>复制源码</span>
            </>
          )}
        </Button>
      </div>

      {showToc && toc.length > 0 && (
        <div className="rounded border border-cyan-500/30 bg-cyan-500/5 p-2.5 space-y-1 font-mono text-[11px]">
          <div className="flex items-center justify-between text-cyan-600 dark:text-cyan-400 font-semibold border-b border-cyan-500/20 pb-1 mb-1.5 font-sans">
            <span className="flex items-center gap-1">
              <AlignLeftIcon className="size-3.5" />
              TOC 结构化章节索引
            </span>
            <span className="text-[11px] text-muted-foreground">{toc.length} 节</span>
          </div>
          <div className="max-h-36 overflow-y-auto space-y-0.5 pr-1">
            {toc.map((item, idx) => (
              <button
                key={`${item.id}-${idx}`}
                type="button"
                onClick={() => handleJumpToLine(item.lineIndex)}
                className={cn(
                  'w-full text-left flex items-center gap-1.5 rounded px-2 py-0.5 transition-colors truncate cursor-pointer',
                  activeTocIdx === item.lineIndex
                    ? 'bg-cyan-500/20 text-cyan-600 dark:text-cyan-400 font-bold'
                    : 'text-muted-foreground hover:bg-muted/40 hover:text-foreground',
                  item.level === 1 && 'font-semibold text-foreground',
                  item.level === 2 && 'pl-4',
                  item.level >= 3 && 'pl-7 text-muted-foreground/80',
                )}
                title={`跳转至第 ${item.lineIndex + 1} 行: ${item.title}`}
              >
                <HashIcon className="size-2.5 shrink-0 opacity-50" />
                <span className="truncate">{item.title}</span>
                <span className="ml-auto text-[11px] opacity-40 font-mono">L{item.lineIndex + 1}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="rounded border border-border/60 bg-muted/20 overflow-hidden flex flex-col">
        <div className="overflow-x-auto flex-1 font-mono text-[11px] leading-5 p-2 divide-y divide-border/10 max-h-[500px]">
          {lines.map((line, idx) => {
            const isHeading = line.startsWith('#')
            const isYaml = line.startsWith('---') || line.startsWith('name:') || line.startsWith('description:')
            const isCodeFence = line.startsWith('```')

            return (
              <div
                key={idx}
                ref={(el) => {
                  lineRefs.current[idx] = el
                }}
                className={cn(
                  'flex items-start gap-3 px-1.5 py-0.5 rounded transition-colors group',
                  activeTocIdx === idx && 'bg-cyan-500/10 border-l-2 border-cyan-500',
                  isHeading && 'font-semibold text-cyan-600 dark:text-cyan-400 bg-muted/30 my-0.5',
                  isYaml && 'text-amber-600 dark:text-amber-400',
                  isCodeFence && 'text-sky-600 dark:text-sky-400 bg-muted/40',
                )}
              >
                <span className="w-8 shrink-0 text-right text-muted-foreground/40 select-none text-[11px] group-hover:text-muted-foreground/70">
                  {idx + 1}
                </span>
                <span className="flex-1 whitespace-pre-wrap break-all text-foreground/90 font-mono">
                  {line || ' '}
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export function SkillDetailSheet({
  open,
  onOpenChange,
  detail,
  isLoading,
}: SkillDetailSheetProps) {
  const { t } = useTranslation('skillsPage')
  const [activeTab, setActiveTab] = React.useState<'L0' | 'L1' | 'L2'>('L0')

  if (!detail) return null

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-xl md:max-w-2xl overflow-y-auto flex flex-col gap-4 font-sans">
        <SheetHeader>
          <div className="flex items-center gap-2">
            <SheetTitle className="text-base font-semibold">
              {detail.cnName ? `${detail.cnName} (${detail.name})` : detail.name}
            </SheetTitle>
            <Badge variant="outline" className="text-[11px] font-mono">
              {detail.scope}
            </Badge>
          </div>
          <SheetDescription className="text-xs text-muted-foreground truncate font-mono">
            {detail.uri}
          </SheetDescription>
        </SheetHeader>

        <div className="flex items-center gap-1 rounded border border-border/60 bg-muted/20 p-1 font-mono text-xs">
          <button
            type="button"
            onClick={() => setActiveTab('L0')}
            className={cn(
              'flex-1 rounded-xs px-2.5 py-1 text-center font-medium transition-colors',
              activeTab === 'L0'
                ? 'bg-background text-cyan-500 shadow-xs border border-border/60'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            L0 (意图触发)
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('L1')}
            className={cn(
              'flex-1 rounded-xs px-2.5 py-1 text-center font-medium transition-colors',
              activeTab === 'L1'
                ? 'bg-background text-cyan-500 shadow-xs border border-border/60'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            L1 (SOP 流程)
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('L2')}
            className={cn(
              'flex-1 rounded-xs px-2.5 py-1 text-center font-medium transition-colors',
              activeTab === 'L2'
                ? 'bg-background text-cyan-500 shadow-xs border border-border/60'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            L2 (全量源码)
          </button>
        </div>

        {activeTab === 'L0' && (
          <div className="grid gap-3 text-xs">
            <DetailSection title="📌 技能自然语言触发描述 (Intent Description)">
              <p className="leading-5 text-muted-foreground bg-muted/20 p-2.5 rounded border border-border/40 font-sans">
                {detail.description ||
                  detail.overview ||
                  `用于触发与处理 ${detail.name} 的自动化专业技能。`}
              </p>
            </DetailSection>

            {detail.tags.length > 0 && (
              <DetailTagList
                title="🏷️ 语义关联标签 (Semantic Tags)"
                values={detail.tags}
                empty={t('none', { defaultValue: '无' })}
              />
            )}

            <div className="grid grid-cols-2 gap-2">
              <DetailMetric
                icon={<UserRoundIcon className="size-3.5" />}
                label={t('metrics.scope', { defaultValue: '作用域' })}
                value={detail.scope}
              />
              <DetailMetric
                icon={<FileCode2Icon className="size-3.5" />}
                label={t('metrics.files', { defaultValue: '关联文件' })}
                value={String(detail.files.length)}
              />
            </div>
          </div>
        )}

        {activeTab === 'L1' && (
          <div className="flex flex-col flex-1 min-h-0 gap-3 text-xs">
            <DetailSection
              title="📋 SOP 核心流程规范 (SOP Core Guidelines)"
              className="flex flex-col flex-1 min-h-0"
            >
              <pre className="overflow-y-auto flex-1 min-h-[350px] max-h-[500px] whitespace-pre-wrap rounded border border-border/60 bg-muted/20 p-3 font-sans text-xs leading-5 text-foreground/90">
                {detail.overview ||
                  extractSopOverview(detail.content, detail.description)}
              </pre>
            </DetailSection>

            {detail.allowedTools.length > 0 && (
              <DetailTagList
                title="🛠️ 允许调用的 MCP 工具 (Allowed Tools)"
                values={detail.allowedTools}
                empty={t('none', { defaultValue: '无' })}
              />
            )}
          </div>
        )}

        {activeTab === 'L2' && (
          <div className="flex flex-col flex-1 min-h-0 gap-3 text-xs">
            <DetailSection title="📁 关联源文件结构 (Associated Files)">
              {detail.files.length > 0 ? (
                <div className="overflow-hidden rounded border border-border/60 bg-card font-mono text-[11px]">
                  {detail.files.map((file) => (
                    <div
                      key={file.path}
                      className="flex items-center gap-2 border-b border-border/40 px-2.5 py-1.5 last:border-b-0"
                    >
                      <FileCode2Icon className="size-3.5 shrink-0 text-muted-foreground" />
                      <span className="min-w-0 flex-1 truncate text-foreground font-medium">
                        {file.name || file.path}
                      </span>
                      <Badge
                        variant="outline"
                        className="rounded-xs text-[11px] px-1 py-0 border-border bg-muted/40 text-foreground"
                      >
                        {file.isDir
                          ? '扩展子目录'
                          : file.name === 'SKILL.md'
                            ? '主规范说明书'
                            : '辅助脚本'}
                      </Badge>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="overflow-hidden rounded border border-border/60 bg-card p-2 font-mono text-[11px] text-foreground flex items-center justify-between">
                  <span className="flex items-center gap-1.5 font-bold">
                    <FileCode2Icon className="size-3.5 text-muted-foreground" />
                    SKILL.md
                  </span>
                  <Badge
                    variant="outline"
                    className="rounded-xs text-[11px] px-1.5 py-0 border-border bg-muted/40 text-foreground"
                  >
                    单文件精简规范
                  </Badge>
                </div>
              )}
            </DetailSection>

            <DetailSection title="📄 SKILL.md 全量源码与 TOC 结构索引 (Full Source & TOC)">
              <SkillSourceViewer
                content={detail.content || getFallbackSkillContent(detail.name, detail.description)}
              />
            </DetailSection>
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}
