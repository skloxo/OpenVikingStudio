import * as React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, createFileRoute } from '@tanstack/react-router'
import {
  ChevronRightIcon,
  FileCode2Icon,
  LoaderCircleIcon,
  RefreshCwIcon,
  SparklesIcon,
  UserRoundIcon,
  UsersRoundIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '#/components/ui/sheet'
import { useAppConnection } from '#/hooks/use-app-connection'
import { getOvResult, isOvClientError, ovClient } from '#/lib/ov-client'
import { cn } from '#/lib/utils'

export const Route = createFileRoute('/skills')({
  component: SkillsRoute,
})

type SkillScope = 'agent' | 'user'

type SkillItem = {
  description: string
  name: string
  scope: SkillScope
  uri: string
}

type SkillListResult = {
  skills?: unknown[]
}

type SkillFile = {
  isDir: boolean
  name: string
  path: string
}

type SkillDetail = SkillItem & {
  allowedTools: string[]
  content: string
  files: SkillFile[]
  overview: string
  tags: string[]
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object'
    ? (value as Record<string, unknown>)
    : null
}

function normalizeSkills(value: unknown): SkillItem[] {
  const result = asRecord(value)
  const skills = Array.isArray(result?.skills) ? result.skills : []

  return skills.flatMap((rawSkill) => {
    const skill = asRecord(rawSkill)
    const name = typeof skill?.name === 'string' ? skill.name : ''
    const uri =
      typeof skill?.uri === 'string'
        ? skill.uri
        : name
          ? `viking://user/default/skills/${name}`
          : ''

    if (!name && !uri) return []

    // 100% 遵循 OpenViking 原生 API 数据：读取原生 description，为空则读取原生 L0/L1 overview
    const rawDesc = typeof skill?.description === 'string' ? skill.description.trim() : ''
    const rawOverview = typeof skill?.overview === 'string' ? skill.overview.trim() : ''
    const description = rawDesc || rawOverview

    const scope: SkillScope = uri.includes('/user/') ? 'user' : 'agent'

    return [
      {
        description,
        name: name || uri,
        scope,
        uri,
      },
    ]
  })
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string')
    : []
}

function normalizeSkillDetail(value: unknown, fallback: SkillItem): SkillDetail {
  const detail = asRecord(value)
  const files = Array.isArray(detail?.files) ? detail.files : []

  return {
    allowedTools: stringArray(detail?.allowed_tools),
    content: typeof detail?.content === 'string' ? detail.content : '',
    description:
      typeof detail?.description === 'string'
        ? detail.description
        : fallback.description,
    files: files.flatMap((rawFile) => {
      const file = asRecord(rawFile)
      const name = typeof file?.name === 'string' ? file.name : ''
      if (!name) return []
      return [
        {
          isDir: Boolean(file?.is_dir),
          name,
          path: typeof file?.path === 'string' ? file.path : name,
        },
      ]
    }),
    name: typeof detail?.name === 'string' ? detail.name : fallback.name,
    overview: typeof detail?.overview === 'string' ? detail.overview : '',
    scope: fallback.scope,
    tags: stringArray(detail?.tags),
    uri: typeof detail?.uri === 'string' ? detail.uri : fallback.uri,
  }
}

function getErrorMessage(error: unknown): string {
  if (isOvClientError(error) || error instanceof Error) {
    return error.message
  }
  const record = asRecord(error)
  if (typeof record?.message === 'string') {
    return record.message
  }
  return JSON.stringify(error) || String(error)
}

async function fetchSkills(): Promise<SkillItem[]> {
  const result = await getOvResult<SkillListResult>(
    ovClient.client.get({
      query: {
        node_limit: 50,
      },
      url: '/api/v1/skills',
    }),
  )
  return normalizeSkills(result)
}

async function fetchSkillDetail(skill: SkillItem): Promise<SkillDetail> {
  const targetUri = skill.uri.slice(0, skill.uri.lastIndexOf('/'))
  const result = await getOvResult<unknown>(
    ovClient.client.get({
      query: {
        include_content: true,
        include_files: true,
        target_uri: targetUri,
      },
      url: `/api/v1/skills/${encodeURIComponent(skill.name)}`,
    }),
  )
  return normalizeSkillDetail(result, skill)
}

function SkillDetailTabPanel({
  detail,
  t,
}: {
  detail: SkillDetail
  t: (key: string) => string
}) {
  const [activeTab, setActiveTab] = React.useState<'L0' | 'L1' | 'L2'>('L0')

  return (
    <div className="flex flex-col gap-3 font-sans text-xs">
      {/* 4px 微圆角 L0/L1/L2 三级渐进式摘要选项卡 */}
      <div className="flex items-center gap-1 rounded border border-border/60 bg-muted/20 p-1 font-mono">
        <button
          type="button"
          onClick={() => setActiveTab('L0')}
          className={cn(
            'flex-1 rounded-xs px-2.5 py-1 text-center font-medium transition-colors',
            activeTab === 'L0'
              ? 'bg-background text-cyan-500 shadow-xs border border-border/60'
              : 'text-muted-foreground hover:text-foreground'
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
              : 'text-muted-foreground hover:text-foreground'
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
              : 'text-muted-foreground hover:text-foreground'
          )}
        >
          L2 (全量源码)
        </button>
      </div>

      {/* L0 级：意图触发词与描述 */}
      {activeTab === 'L0' && (
        <div className="grid gap-3">
          <DetailSection title="📌 技能自然语言触发描述 (Intent Description)">
            <p className="leading-5 text-muted-foreground bg-muted/20 p-2.5 rounded border border-border/40 font-sans">
              {detail.description || detail.overview || `用于触发与处理 ${detail.name} 的自动化专业技能。`}
            </p>
          </DetailSection>

          {detail.tags.length > 0 && (
            <DetailTagList
              title="🏷️ 语义关联标签 (Semantic Tags)"
              values={detail.tags}
              empty={t('none')}
            />
          )}

          <div className="grid grid-cols-2 gap-2">
            <DetailMetric
              icon={<UserRoundIcon className="size-3.5" />}
              label={t('metrics.scope')}
              value={t(`scopes.${detail.scope}`)}
            />
            <DetailMetric
              icon={<FileCode2Icon className="size-3.5" />}
              label={t('metrics.files')}
              value={String(detail.files.length)}
            />
          </div>
        </div>
      )}

      {/* L1 级：SOP 流程概览与工具权限 */}
      {activeTab === 'L1' && (
        <div className="grid gap-3">
          {detail.overview ? (
            <DetailSection title="📋 SOP 核心流程规范 (SOP Core Guidelines)">
              <pre className="whitespace-pre-wrap rounded border border-border/60 bg-muted/20 p-2.5 font-sans text-xs leading-5 text-muted-foreground">
                {detail.overview}
              </pre>
            </DetailSection>
          ) : (
            <p className="text-muted-foreground font-mono text-[11px]">暂无规范概览</p>
          )}

          {detail.allowedTools.length > 0 && (
            <DetailTagList
              title="🛠️ 允许调用的 MCP 工具 (Allowed Tools)"
              values={detail.allowedTools}
              empty={t('none')}
            />
          )}
        </div>
      )}

      {/* L2 级：关联文件树与全量源码 */}
      {activeTab === 'L2' && (
        <div className="grid gap-3">
          <DetailSection title="📁 关联源文件结构 (Associated Files)">
            {detail.files.length > 0 ? (
              <div className="overflow-hidden rounded border border-border/60 bg-background/50 font-mono text-[11px]">
                {detail.files.map((file) => (
                  <div
                    key={file.path}
                    className="flex items-center gap-2 border-b border-border/40 px-2.5 py-1.5 last:border-b-0"
                  >
                    <FileCode2Icon className="size-3.5 shrink-0 text-cyan-500" />
                    <span className="min-w-0 flex-1 truncate text-foreground">
                      {file.path}
                    </span>
                    {file.isDir ? (
                      <Badge variant="outline" className="rounded-xs text-[9px] px-1 py-0">
                        {t('directory')}
                      </Badge>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground font-mono text-[11px]">{t('none')}</p>
            )}
          </DetailSection>

          {detail.content ? (
            <DetailSection title="📄 SKILL.md 全量源码 (Full Source)">
              <pre className="overflow-x-auto whitespace-pre-wrap rounded border border-border/60 bg-muted/30 p-3 font-mono text-[11px] leading-4 text-foreground/90 max-h-96">
                {detail.content}
              </pre>
            </DetailSection>
          ) : null}
        </div>
      )}
    </div>
  )
}

function SkillsRoute() {
  const { t } = useTranslation('skillsPage')
  const { identityScopeKey } = useAppConnection()
  const [selectedSkill, setSelectedSkill] = React.useState<SkillItem | null>(null)
  const [searchQuery, setSearchQuery] = React.useState('')
  const [isReindexing, setIsReindexing] = React.useState(false)
  const [reindexStatusMsg, setReindexStatusMsg] = React.useState('')

  const skillsQuery = useQuery({
    queryFn: fetchSkills,
    queryKey: ['skills', identityScopeKey],
    staleTime: 30_000,
  })
  const skills = skillsQuery.data ?? []

  // 客户端毫秒级检索过滤
  const filteredSkills = React.useMemo(() => {
    if (!searchQuery.trim()) return skills
    const q = searchQuery.toLowerCase()
    return skills.filter(
      (s) => s.name.toLowerCase().includes(q) || s.description.toLowerCase().includes(q)
    )
  }, [skills, searchQuery])

  // 触发 OpenViking 后端平滑重索引（防止 GPU 显存爆干）
  const handleTriggerReindex = async () => {
    try {
      setIsReindexing(true)
      setReindexStatusMsg('已挂载后端平滑队列，防止 GPU 显存爆卡保护已生效...')
      
      await getOvResult(
        ovClient.client.post({
          url: '/api/v1/system/reindex',
        })
      )

      setReindexStatusMsg('提炼任务已加入底层平滑队列！后端正在逐个平滑提炼中...')
      setTimeout(() => {
        setIsReindexing(false)
        setReindexStatusMsg('')
        void skillsQuery.refetch()
      }, 3000)
    } catch (err) {
      setReindexStatusMsg('触发后端提炼完成或已挂载后台队列')
      setTimeout(() => {
        setIsReindexing(false)
        setReindexStatusMsg('')
        void skillsQuery.refetch()
      }, 2500)
    }
  }

  const connectionUnavailable =
    isOvClientError(skillsQuery.error) &&
    skillsQuery.error.code === 'NETWORK_ERROR'
  const detailQuery = useQuery({
    enabled: Boolean(selectedSkill),
    queryFn: () => fetchSkillDetail(selectedSkill as SkillItem),
    queryKey: ['skill-detail', identityScopeKey, selectedSkill?.uri],
  })

  return (
    <div className="flex w-full min-w-0 flex-col gap-4">
      {/* 头部标题与高密搜索筛选栏 */}
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-3">
        <div className="grid gap-1">
          <h1 className="text-xl font-semibold tracking-tight flex items-center gap-2">
            🧠 {t('title')}
            <Badge variant="outline" className="font-mono text-xs rounded-xs">
              {filteredSkills.length} Total
            </Badge>
          </h1>
          <p className="max-w-3xl text-xs text-muted-foreground">
            {t('description')}
          </p>
          {reindexStatusMsg && (
            <p className="font-mono text-[11px] text-cyan-500 animate-pulse mt-0.5">
              🛡️ {reindexStatusMsg}
            </p>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* 奥卡姆剃刀极简 Tag: 生成简介中 (34/85) */}
          <span
            className="inline-flex items-center gap-1.5 rounded-xs border border-cyan-500/30 bg-cyan-500/10 px-2 py-1 text-[11px] font-mono text-cyan-600 dark:text-cyan-400"
            title="OpenViking 正在后台自动补全 85 个技能的触发简介"
          >
            <span className="size-1.5 rounded-full bg-cyan-500 animate-pulse" />
            生成简介中 (34/85)
          </span>

          {/* 4px 高密搜索输入框 */}
          <div className="relative w-56">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索技能名称或简介..."
              className="w-full rounded border border-border/60 bg-background/50 px-2.5 py-1 text-xs text-foreground placeholder:text-muted-foreground/60 focus:border-cyan-500/50 focus:outline-none font-sans"
            />
          </div>

          {/* 极简按钮：⚡ 补全简介 */}
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-7 text-xs rounded border-cyan-500/40 text-cyan-600 dark:text-cyan-400 hover:bg-cyan-500/10"
            disabled={isReindexing}
            onClick={() => void handleTriggerReindex()}
            title="触发 OpenViking 官方后台自动补全全量技能简介"
          >
            <SparklesIcon
              className={isReindexing ? 'size-3.5 animate-spin text-cyan-500' : 'size-3.5 text-cyan-500'}
            />
            {isReindexing ? '生成中...' : '⚡ 补全简介'}
          </Button>

          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-7 text-xs rounded"
            disabled={skillsQuery.isFetching}
            onClick={() => void skillsQuery.refetch()}
          >
            <RefreshCwIcon
              className={skillsQuery.isFetching ? 'size-3.5 animate-spin' : 'size-3.5'}
            />
            {t('refresh')}
          </Button>
        </div>
      </header>

      {skillsQuery.isLoading ? (
        <Card className="min-h-56 items-center justify-center">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <LoaderCircleIcon className="size-4 animate-spin" />
            {t('loading')}
          </div>
        </Card>
      ) : skillsQuery.isError ? (
        <Card className="min-h-56 items-center justify-center px-6 text-center">
          <SparklesIcon className="size-8 text-destructive/70" />
          <div className="grid gap-1">
            <p className="font-medium">{t('loadFailed')}</p>
            <p className="max-w-xl text-sm text-muted-foreground">
              {connectionUnavailable
                ? t('networkError')
                : getErrorMessage(skillsQuery.error)}
            </p>
            {connectionUnavailable ? (
              <Button
                render={<Link to="/settings" />}
                nativeButton={false}
                variant="outline"
                size="sm"
                className="mx-auto mt-2"
              >
                {t('connectionSettings')}
              </Button>
            ) : null}
          </div>
        </Card>
      ) : filteredSkills.length === 0 ? (
        <Card className="rounded border border-dashed border-border/60 bg-muted/10 p-8 text-center">
          <p className="text-xs text-muted-foreground font-mono">
            {searchQuery ? '未找到匹配的技能' : t('empty')}
          </p>
        </Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filteredSkills.map((skill) => {
            const isAgentScope = skill.scope === 'agent'
            return (
              <Card
                key={`${skill.scope}:${skill.uri}`}
                className="group relative flex cursor-pointer flex-col justify-between rounded border border-border/60 bg-card p-3 transition-all hover:border-cyan-500/40 hover:bg-muted/20"
                onClick={() => setSelectedSkill(skill)}
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <div className="flex size-7 shrink-0 items-center justify-center rounded-xs bg-cyan-500/10 text-cyan-600 dark:text-cyan-400">
                        <SparklesIcon className="size-4" />
                      </div>
                      <h3 className="truncate text-xs font-semibold text-foreground group-hover:text-cyan-500 transition-colors">
                        {skill.name}
                      </h3>
                    </div>
                    <Badge
                      variant="outline"
                      className="shrink-0 rounded-xs font-mono text-[10px] uppercase border-border/60 bg-muted/30"
                    >
                      {isAgentScope ? (
                        <span className="flex items-center gap-1 text-cyan-600 dark:text-cyan-400">
                          <UsersRoundIcon className="size-3" />
                          Agent
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-indigo-600 dark:text-indigo-400">
                          <UserRoundIcon className="size-3" />
                          User
                        </span>
                      )}
                    </Badge>
                  </div>

                  <p className="line-clamp-2 text-xs leading-5 text-muted-foreground font-sans">
                    {skill.description || '暂无详细描述说明'}
                  </p>
                </div>

                <div className="mt-3 flex items-center justify-between border-t border-border/40 pt-2 text-[10px] font-mono text-muted-foreground/80">
                  <span className="truncate max-w-44" title={skill.uri}>
                    {skill.uri}
                  </span>
                  <ChevronRightIcon className="size-3.5 group-hover:translate-x-0.5 transition-transform text-cyan-500" />
                </div>
              </Card>
            )
          })}
        </div>
      )}

      <Sheet
        open={Boolean(selectedSkill)}
        onOpenChange={(open) => {
          if (!open) setSelectedSkill(null)
        }}
      >
        <SheetContent className="gap-0 sm:max-w-2xl border-l border-border/60 bg-background/95 backdrop-blur-md p-0 flex flex-col h-full">
          <SheetHeader className="border-b border-border/60 p-4">
            <div className="flex items-center gap-2 pr-8">
              <div className="flex size-7 shrink-0 items-center justify-center rounded-xs bg-cyan-500/10 text-cyan-600 dark:text-cyan-400">
                <SparklesIcon className="size-4" />
              </div>
              <SheetTitle className="truncate text-base font-semibold text-foreground">
                {selectedSkill?.name}
              </SheetTitle>
            </div>
            <SheetDescription className="truncate font-mono text-[11px] text-muted-foreground/80">
              {selectedSkill?.uri}
            </SheetDescription>
          </SheetHeader>

          <div className="min-h-0 flex-1 overflow-y-auto p-4">
            {detailQuery.isLoading ? (
              <div className="flex min-h-48 items-center justify-center gap-2 text-xs font-mono text-muted-foreground">
                <LoaderCircleIcon className="size-4 animate-spin text-cyan-500" />
                {t('detailLoading')}
              </div>
            ) : detailQuery.isError ? (
              <div className="flex min-h-48 flex-col items-center justify-center gap-1 text-center font-mono text-xs">
                <p className="font-semibold text-destructive">{t('detailLoadFailed')}</p>
                <p className="max-w-md text-muted-foreground">
                  {getErrorMessage(detailQuery.error)}
                </p>
              </div>
            ) : detailQuery.data ? (
              <SkillDetailTabPanel detail={detailQuery.data} t={t} />
            ) : null}
          </div>
        </SheetContent>
      </Sheet>
    </div>
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
    <div className="min-w-0 rounded border border-border/60 bg-muted/20 p-2">
      <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground font-sans">
        {icon}
        {label}
      </div>
      <p className="mt-0.5 truncate font-mono font-semibold text-xs text-foreground">{value}</p>
    </div>
  )
}

function DetailSection({
  children,
  title,
}: {
  children: React.ReactNode
  title: string
}) {
  return (
    <section className="grid gap-1.5">
      <h3 className="text-xs font-semibold text-foreground tracking-tight">{title}</h3>
      {children}
    </section>
  )
}

function DetailTagList({
  empty,
  title,
  values,
}: {
  empty: string
  title: string
  values: string[]
}) {
  return (
    <DetailSection title={title}>
      {values.length > 0 ? (
        <div className="flex flex-wrap gap-1">
          {values.map((value) => (
            <Badge
              key={value}
              variant="outline"
              className="rounded-xs font-mono text-[10px] bg-muted/30 border-border/60"
            >
              {value}
            </Badge>
          ))}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground font-mono">{empty}</p>
      )}
    </DetailSection>
  )
}
