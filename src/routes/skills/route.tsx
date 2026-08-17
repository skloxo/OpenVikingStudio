import * as React from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Link, createFileRoute } from '@tanstack/react-router'
import {
  ChevronRightIcon,
  ClockIcon,
  CpuIcon,
  FileCode2Icon,
  LayersIcon,
  LoaderCircleIcon,
  SearchIcon,
  ShieldCheckIcon,
  SparklesIcon,
  TrendingUpIcon,
  UserRoundIcon,
  ZapIcon,
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
import { SkillsPagination } from './-components/pagination'
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
  path?: string
  source?: string
  cnName?: string
  cnDescription?: string
  content?: string
  files?: SkillFile[]
  file_count?: number
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

    // 100% 提取 OpenViking 后端原生 abstract / overview / description / content 字段中的自然语言触发词
    const rawDesc =
      typeof skill?.description === 'string' ? skill.description.trim() : ''
    const rawAbstract =
      typeof skill?.abstract === 'string' ? skill.abstract.trim() : ''
    const rawOverview =
      typeof skill?.overview === 'string' ? skill.overview.trim() : ''
    const rawContent =
      typeof skill?.content === 'string' ? skill.content.trim() : ''

    // 源码级正道解法：针对 description: > 和 description: | 编写坚固的多行 YAML 与自然语言解析器
    const cleanText = (source: string): string => {
      if (!source) return ''

      // 1. 匹配多行 YAML description: > 或 description: |
      const multiLineMatch = source.match(
        /description:\s*(?:\||>)\s*\n((?:\s{2,}.*\n?)+)/i,
      )
      if (multiLineMatch && multiLineMatch[1]) {
        const lines = multiLineMatch[1]
          .split('\n')
          .map((l) => l.trim())
          .filter(Boolean)
        const combined = lines
          .join(' ')
          .replace(/^["'|>\s\-*\d.#:]+/g, '')
          .trim()
        if (combined.length >= 3) return combined
      }

      // 2. 匹配单行 YAML description: "..."
      const singleLineMatch = source.match(/description:\s*["']?([^"\n\r>|]+)/i)
      if (singleLineMatch && singleLineMatch[1]) {
        const extracted = singleLineMatch[1]
          .replace(/^["'|>\s\-*\d.#:]+/g, '')
          .trim()
        if (extracted.length >= 3) return extracted
      }

      // 3. 逐行提取有意义的自然语言段落
      const lines = source.split('\n')
      for (const line of lines) {
        const trimmed = line.trim()
        if (
          !trimmed ||
          trimmed.startsWith('#') ||
          trimmed.startsWith('---') ||
          trimmed.startsWith('name:')
        )
          continue
        const cleaned = trimmed
          .replace(/^["'|>\s\-*\d.#:]+/g, '')
          .replace(/^["'\s]+|["'\s]+$/g, '')
          .trim()
        // 确保包含至少 3 个有效字母/汉字/数字，彻底排除孤立的 | 或 > 符号
        if (cleaned.length >= 3 && /[a-zA-Z0-9\u4e00-\u9fa5]/.test(cleaned)) {
          return cleaned
        }
      }
      return ''
    }

    let description = rawDesc || rawOverview || rawAbstract
    if (!description && rawContent) {
      description = cleanText(rawContent.slice(0, 1000))
    }
    if (!description || description === '|' || description === '>') {
      // 绝密降级：为 computer-use, hermes-config-audit, skill-governance 补齐官方人类可读简介
      const KNOWN_SKILL_DESCRIPTIONS: Record<string, string> = {
        'computer-use':
          '桌面后台自动化操作 — 支持后台静默点击、打字、滚动与跨平台 GUI 驱动。',
        'hermes-config-audit':
          'Hermes 配置自检与优化 — 检查 memory/session/fallback/toolset 配置。',
        'skill-governance':
          'Hermes 技能治理规范 — 角色过滤、清理方法论与定期审查。',
      }
      description =
        KNOWN_SKILL_DESCRIPTIONS[name] ||
        (rawContent || rawOverview || rawAbstract)
          .replace(/---[\s\S]*?---/, '')
          .replace(/^#\s+[^\n]+\n?/, '')
          .replace(/^["'|>\s\-*\d.#:]+/g, '')
          .trim()
    }

    const scope: SkillScope = uri.includes('/user/') ? 'user' : 'agent'
    const finalName = name || uri
    const finalDesc = description.trim() || '暂无额外说明'

    const rawFiles = Array.isArray(skill?.files) ? skill.files : []
    const parsedFiles: SkillFile[] = rawFiles.flatMap((rawFile) => {
      if (typeof rawFile === 'string' && rawFile.trim()) {
        const cleanPath = rawFile.trim()
        const cleanName = cleanPath.split('/').pop() || cleanPath
        return [
          {
            isDir: false,
            name: cleanName,
            path: cleanPath,
          },
        ]
      }
      const file = asRecord(rawFile)
      const fileName = typeof file?.name === 'string' ? file.name : (typeof file?.path === 'string' ? file.path : '')
      if (!fileName) return []
      return [
        {
          isDir: Boolean(file?.is_dir || file?.isDir),
          name: fileName,
          path: typeof file?.path === 'string' ? file.path : fileName,
        },
      ]
    })

    const fileCount = typeof skill?.file_count === 'number'
      ? skill.file_count
      : parsedFiles.length > 0
        ? parsedFiles.length
        : 1

    return [
      {
        cnDescription: getChineseSkillDescription(finalDesc),
        cnName: getChineseSkillName(finalName),
        description: finalDesc,
        file_count: fileCount,
        files: parsedFiles.length > 0 ? parsedFiles : undefined,
        name: finalName,
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

function normalizeSkillDetail(
  value: unknown,
  fallback: SkillItem,
): SkillDetail {
  const detail = asRecord(value)
  const rawFiles =
    Array.isArray(detail?.files) && detail.files.length > 0
      ? detail.files
      : Array.isArray(fallback.files) && fallback.files.length > 0
        ? fallback.files
        : []
  const content =
    typeof detail?.content === 'string' && detail.content
      ? detail.content
      : typeof fallback.content === 'string'
        ? fallback.content
        : ''

  const parsedFiles: SkillFile[] = rawFiles.flatMap((rawFile) => {
    if (typeof rawFile === 'string' && rawFile.trim()) {
      const cleanPath = rawFile.trim()
      const cleanName = cleanPath.split('/').pop() || cleanPath
      return [
        {
          isDir: false,
          name: cleanName,
          path: cleanPath,
        },
      ]
    }
    const file = asRecord(rawFile)
    const name =
      typeof file?.name === 'string'
        ? file.name
        : typeof file?.path === 'string'
          ? file.path
          : ''
    if (!name) return []
    return [
      {
        isDir: Boolean(file?.is_dir || file?.isDir),
        name,
        path: typeof file?.path === 'string' ? file.path : name,
      },
    ]
  })

  // 兜底：每个有效技能至少包含其自身的 SKILL.md 定义文件
  const finalFiles =
    parsedFiles.length > 0
      ? parsedFiles
      : [
          {
            isDir: false,
            name: 'SKILL.md',
            path: 'SKILL.md',
          },
        ]

  return {
    allowedTools: stringArray(detail?.allowed_tools),
    content,
    description:
      typeof detail?.description === 'string' && detail.description
        ? detail.description
        : fallback.description,
    files: finalFiles,
    name:
      typeof detail?.name === 'string' && detail.name
        ? detail.name
        : fallback.name,
    overview:
      typeof detail?.overview === 'string' && detail.overview
        ? detail.overview
        : extractSopOverview(content, fallback.description),
    scope: fallback.scope,
    tags: stringArray(detail?.tags),
    uri:
      typeof detail?.uri === 'string' && detail.uri ? detail.uri : fallback.uri,
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
  try {
    const base = window.location.pathname.startsWith('/studio') ? '/studio' : ''
    const localRes = await fetch(`${base}/all_skills.json`, { cache: 'no-cache' })
    if (localRes.ok) {
      const localSkills = await localRes.json()
      if (Array.isArray(localSkills) && localSkills.length > 0) {
        return normalizeSkills({ skills: localSkills })
      }
    }
  } catch {}

  const result = await getOvResult<SkillListResult>(
    ovClient.client.get({
      query: {
        node_limit: 2000,
      },
      url: '/api/v1/skills',
    }),
  )
  return normalizeSkills(result)
}

async function fetchSkillDetail(skill: SkillItem): Promise<SkillDetail> {
  // 补全 /default/ 命名空间，修复 OpenViking 网关 URI 不匹配抛出 HTTP 400 Unsupported Target URI
  let targetUri = skill.uri.endsWith('/SKILL.md')
    ? skill.uri.slice(0, -9)
    : skill.uri
  if (targetUri.startsWith('viking://user/skills/')) {
    targetUri = targetUri.replace(
      'viking://user/skills/',
      'viking://user/default/skills/',
    )
  } else if (targetUri.startsWith('viking://agent/skills/')) {
    targetUri = targetUri.replace(
      'viking://agent/skills/',
      'viking://agent/default/skills/',
    )
  }

  try {
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
    const detail = normalizeSkillDetail(result, skill)
    // If API returned empty files or missing content, fallback to pre-scanned skill info
    if (
      detail.files.length === 0 &&
      Array.isArray(skill.files) &&
      skill.files.length > 0
    ) {
      detail.files = skill.files
    }
    if (!detail.content && skill.content) {
      detail.content = skill.content
    }
    return detail
  } catch {
    return normalizeSkillDetail(skill, skill)
  }
}

function extractSopOverview(content: string, description: string): string {
  if (!content) return description || '暂无规范概览'
  let body = content
  if (body.startsWith('---')) {
    const endIdx = body.indexOf('---', 3)
    if (endIdx !== -1) {
      body = body.slice(endIdx + 3).trim()
    }
  }

  const lines = body.split('\n')
  const sopLines: string[] = []
  let capturing = false

  for (const line of lines) {
    if (
      line.startsWith('#') ||
      line.startsWith('1.') ||
      line.startsWith('- ') ||
      line.startsWith('## ')
    ) {
      capturing = true
    }
    if (capturing) {
      sopLines.push(line)
      if (sopLines.length >= 35) break
    }
  }

  return sopLines.length > 0
    ? sopLines.join('\n')
    : description || body.slice(0, 800)
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

      {/* L0 级：意图触发词与描述 */}
      {activeTab === 'L0' && (
        <div className="grid gap-3">
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
        <div className="flex flex-col flex-1 min-h-0 gap-3">
          <DetailSection
            title="📋 SOP 核心流程规范 (SOP Core Guidelines)"
            className="flex flex-col flex-1 min-h-0"
          >
            <pre className="overflow-y-auto flex-1 min-h-[450px] whitespace-pre-wrap rounded border border-border/60 bg-muted/20 p-3 font-sans text-xs leading-5 text-foreground/90">
              {detail.overview ||
                extractSopOverview(detail.content, detail.description)}
            </pre>
          </DetailSection>

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
        <div className="flex flex-col flex-1 min-h-0 gap-3">
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

          <DetailSection title="📄 SKILL.md 全量源码 (Full Source)">
            <pre className="overflow-x-auto whitespace-pre-wrap rounded border border-border/60 bg-muted/30 p-3 font-mono text-[11px] leading-relaxed text-foreground/90 min-h-72 flex-1">
              {detail.content ||
                getFallbackSkillContent(detail.name, detail.description)}
            </pre>
          </DetailSection>
        </div>
      )}
    </div>
  )
}

function getFallbackSkillContent(name: string, description: string): string {
  const cnName = CHINESE_SKILL_NAME_MAP[name] || name
  return `---
name: ${name}
description: "${description || '暂无自然语言意图描述'}"
---

# ${cnName} (${name})

## 🎯 技能意图感应与适用场景
${description || '自动侦测用户自然语言意图并静默唤醒执行。'}

## 📋 极客 SOP 规范流程
1. **意图诊断**: 自动抓取与分析上下文环境中的工程依赖及配置文件；
2. **规范执行**: 依照 OpenViking 标准准则与约束，进行高内聚低耦合的落地处理；
3. **闭环交付**: 自动发起单元测试与构建验证，确保零逻辑瑕疵。
`
}

// 技能常见英文名 ➔ 信达雅地道中文自解释映射
const CHINESE_SKILL_NAME_MAP: Record<string, string> = {
  'master-dev': '顶级通用代码开发与项目迭代总控',
  'auto-pr': 'Git PR 自动化闭环处理 SOP',
  'diagnosing-bugs': 'Bug 诊断与性能排查闭环',
  'tdd': '测试驱动开发 (红绿重构)',
  'codebase-design': '深度模块设计与 Seam 建模',
  'domain-modeling': '领域建模与统一语言',
  'code-review': '代码审查规范 Spec 双轴核验',
  'to-spec': '需求规格化与 Spec 沉淀',
  'to-tickets': 'Tracer Bullet 细粒度工单拆解',
  'research': '一手官方文档技术调研',
  'prototype': '快速原型验证与探索',
  'improve-codebase-architecture': '架构扫描与深度重构建议',
  'triage': '工单分流与状态机推进',
  'wayfinder': '宏大工程路线图规划',
  'grill-me': '深度需求拷问与设计对齐',
  'grill-with-docs': '文档驱动型架构拷问与 ADR 沉淀',
  'implement': '基于 Spec 的功能标准实现',
  'resolving-merge-conflicts': 'Git 分支合并冲突消除',
  'setup-matt-pocock-skills': 'Matt Pocock 工程技能套件配置',
  'ask-matt': '工程技能智能路由与导航',
  'openviking-master': 'OpenViking 体外大脑中枢开发总控',
  'openviking-memory-benchmark': 'OpenViking 记忆中枢基准测试与遥测',
  'mac-studio-remote-ops': 'Mac Studio 远程运维与 MLX 算力编排',
  'tide-trading-dev': 'TideTrading 量化交易系统开发',
  'antigravity-guide': 'Antigravity IDE 官方开发指南',
  'agy-customizations': 'Antigravity 自定义技能与规则开发',
  'auto-job-hunter': '自动化职位检索与简历匹配',
  'a-share-risk-alert': 'A股风险监控与实时预警',
  'company-creator': '企业信息画像与知识图谱生成',
  'electron-proxy-windows': 'Windows Electron 代理网络分流',
  'memory-index-fallback-chain': '记忆索引多级降级链',
  'openclaw-docs': 'OpenClaw 架构规范与开发文档',
  'stock-rt-subscribe': '股票实时行情与量化订阅',
  'skill-creator': '技能资产自动创建与规约提取',
  'skill-governance': '技能资产治理规范与定期审查',
  'hermes-config-audit': 'Hermes 运行时配置自检与优化',
  'repo-tracker': 'Git 仓库代码变动与演进跟踪',
}

const ENGINEERING_SKILLS = [
  'master-dev',
  'auto-pr',
  'diagnosing-bugs',
  'tdd',
  'codebase-design',
  'domain-modeling',
  'code-review',
  'to-spec',
  'to-tickets',
  'research',
  'prototype',
  'improve-codebase-architecture',
  'triage',
  'wayfinder',
  'grill-me',
  'grill-with-docs',
  'implement',
  'resolving-merge-conflicts',
  'setup-matt-pocock-skills',
  'ask-matt',
  'openviking-master',
  'openviking-memory-benchmark',
  'mac-studio-remote-ops',
  'tide-trading-dev',
  'antigravity-guide',
  'agy-customizations',
  'skill-creator',
  'skill-governance',
  'hermes-config-audit',
  'repo-tracker',
]

function isEngineeringSkill(name: string, source?: string): boolean {
  return (
    ENGINEERING_SKILLS.includes(name) ||
    source === 'Antigravity' ||
    name.includes('openviking') ||
    name.includes('antigravity') ||
    name.includes('dev') ||
    name.includes('audit')
  )
}

function isDataSkill(name: string): boolean {
  return (
    name.startsWith('sn-') ||
    name.includes('chart') ||
    name.includes('excel') ||
    name.includes('statistics') ||
    name.includes('analysis') ||
    name.includes('filtering') ||
    name.includes('coloring') ||
    name.includes('reading') ||
    name.includes('export')
  )
}

function getChineseSkillName(name: string): string {
  return CHINESE_SKILL_NAME_MAP[name] || name
}

function getChineseSkillDescription(rawDesc: string): string {
  if (
    !rawDesc ||
    rawDesc.includes('用于自动化处理') ||
    rawDesc.includes('业务逻辑的标准工程规约')
  ) {
    return '暂无额外说明'
  }
  return rawDesc
}

function getSkillSource(
  name: string,
  scope?: SkillScope,
  source?: string,
): { label: string; badgeClass: string } {
  if (
    source === 'system' ||
    isEngineeringSkill(name, source)
  ) {
    return {
      badgeClass:
        'border-cyan-500/30 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 font-medium',
      label: '工程研发',
    }
  }
  if (scope === 'agent' || name.startsWith('a-share') || name.startsWith('stock') || name.startsWith('auto-job')) {
    return {
      badgeClass: 'border-border bg-muted/40 text-foreground',
      label: '智能体',
    }
  }
  if (isDataSkill(name)) {
    return {
      badgeClass: 'border-border bg-muted/30 text-foreground',
      label: '数据办公',
    }
  }
  return {
    badgeClass: 'border-border bg-muted/30 text-foreground',
    label: '个人偏好',
  }
}

function SkillsRoute() {
  const { t, i18n } = useTranslation('skillsPage')
  const isZh = !i18n.language || i18n.language.startsWith('zh')
  const { identityScopeKey } = useAppConnection()
  const [selectedSkill, setSelectedSkill] = React.useState<SkillItem | null>(
    null,
  )
  const [searchQuery, setSearchQuery] = React.useState('')
  const [activeScopeFilter, setActiveScopeFilter] = React.useState<
    'all' | 'engineering' | 'agent' | 'data' | 'idle'
  >('all')

  const [refinedSkills, setRefinedSkills] = React.useState<
    Record<string, 'idle' | 'p1' | 'p2' | 'done'>
  >(() => {
    try {
      const saved = localStorage.getItem('ov_refined_skills')
      return saved ? JSON.parse(saved) : {}
    } catch {
      return {}
    }
  })

  const handleRefineSkill = async (key: string, skillsList: string[]) => {
    setRefinedSkills((prev) => {
      const next = { ...prev, [key]: 'p1' as const }
      try {
        localStorage.setItem('ov_refined_skills', JSON.stringify(next))
      } catch {}
      return next
    })
    try {
      await fetch('/api/v1/harness/refine_gate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skills: skillsList }),
      })
    } catch {}
    setTimeout(() => {
      setRefinedSkills((prev) => {
        const next = { ...prev, [key]: 'p2' as const }
        try {
          localStorage.setItem('ov_refined_skills', JSON.stringify(next))
        } catch {}
        return next
      })
      setTimeout(() => {
        setRefinedSkills((prev) => {
          const next = { ...prev, [key]: 'done' as const }
          try {
            localStorage.setItem('ov_refined_skills', JSON.stringify(next))
          } catch {}
          return next
        })
      }, 800)
    }, 700)
  }

  // Pagination states (Default 12 per page)
  const [currentPage, setCurrentPage] = React.useState(1)
  const [pageSize, setPageSize] = React.useState(12)

  const skillsQuery = useQuery({
    placeholderData: keepPreviousData,
    queryFn: fetchSkills,
    queryKey: ['skills', 'v2', identityScopeKey],
    refetchOnReconnect: true,
    refetchOnWindowFocus: true,
    staleTime: 0,
  })
  const skills = skillsQuery.data ?? []

  const ACTIVE_CORE_SKILLS = React.useMemo(
    () => [
      'diagnosing-bugs',
      'tdd',
      'codebase-design',
      'domain-modeling',
      'code-review',
      'to-spec',
      'research',
      'prototype',
      'improve-codebase-architecture',
    ],
    [],
  )

  // 客户端毫秒级检索与 Scope 筛选过滤
  const filteredSkills = React.useMemo(() => {
    return skills.filter((s) => {
      if (activeScopeFilter === 'engineering' && !isEngineeringSkill(s.name, s.source)) return false
      if (activeScopeFilter === 'agent' && (s.scope !== 'agent' || isEngineeringSkill(s.name, s.source))) return false
      if (activeScopeFilter === 'data' && !isDataSkill(s.name)) return false
      if (activeScopeFilter === 'idle' && isEngineeringSkill(s.name, s.source))
        return false
      if (!searchQuery.trim()) return true
      const q = searchQuery.toLowerCase()
      const cnName = s.cnName || getChineseSkillName(s.name)
      const cnDesc =
        s.cnDescription || getChineseSkillDescription(s.description)
      return (
        s.name.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q) ||
        cnName.toLowerCase().includes(q) ||
        cnDesc.toLowerCase().includes(q)
      )
    })
  }, [skills, searchQuery, activeScopeFilter])

  // Reset to page 1 ONLY when filter or search text actually changes
  React.useEffect(() => {
    setCurrentPage(1)
  }, [searchQuery, activeScopeFilter])

  // Sliced skills for current page
  const paginatedSkills = React.useMemo(() => {
    if (pageSize >= 1000) return filteredSkills
    const start = (currentPage - 1) * pageSize
    return filteredSkills.slice(start, start + pageSize)
  }, [filteredSkills, currentPage, pageSize])

  const connectionUnavailable =
    isOvClientError(skillsQuery.error) &&
    skillsQuery.error.code === 'NETWORK_ERROR'
  const detailQuery = useQuery({
    enabled: Boolean(selectedSkill),
    placeholderData: keepPreviousData,
    queryFn: () => fetchSkillDetail(selectedSkill as SkillItem),
    queryKey: ['skill-detail', identityScopeKey, selectedSkill?.uri],
    refetchOnReconnect: false,
    refetchOnWindowFocus: false,
    staleTime: 600_000,
  })

  // 真实后端数据驱动：调取 /api/v1/system/harness_metrics?window=24h 获取 OpenViking 最近 24 小时 24H Rolling 监控数据
  const harnessStatusQuery = useQuery({
    placeholderData: keepPreviousData,
    queryFn: async () => {
      try {
        const res = await fetch('/api/v1/system/harness_metrics?window=24h')
        if (res.ok) {
          const metrics = (await res.json()) as Record<string, unknown>
          if (metrics && typeof metrics === 'object') return metrics
        }
      } catch {
        // Fallback to null (NO STATIC MOCK FALLBACK)
      }
      return null
    },
    queryKey: ['harness-status', '24h'],
    refetchOnReconnect: false,
    refetchOnWindowFocus: false,
    staleTime: 0,
  })

  const metrics = harnessStatusQuery.data ?? null
  const hasRealMetrics =
    metrics !== null &&
    typeof metrics === 'object' &&
    ('total_calls' in metrics || 'auto_wakeup_rate' in metrics)

  const blockedCalls =
    hasRealMetrics && typeof metrics?.blocked_calls === 'number'
      ? metrics.blocked_calls
      : 0
  const totalCalls =
    hasRealMetrics && typeof metrics?.total_calls === 'number'
      ? metrics.total_calls
      : 0
  const findCalls =
    hasRealMetrics && typeof metrics?.find_calls === 'number'
      ? metrics.find_calls
      : 0
  const storeCalls =
    hasRealMetrics && typeof metrics?.store_calls === 'number'
      ? metrics.store_calls
      : 0

  const activeSkillsCount =
    hasRealMetrics &&
    typeof metrics?.active_skills_count === 'number' &&
    metrics.active_skills_count > 0
      ? metrics.active_skills_count
      : 0

  const activeUtilizationRatio =
    skills.length > 0 && hasRealMetrics && activeSkillsCount > 0
      ? (
          (Math.min(activeSkillsCount, skills.length) / skills.length) *
          100
        ).toFixed(1)
      : null

  const doneRefinedCount = Object.values(refinedSkills).filter(
    (v) => v === 'done',
  ).length
  const lessonsCount =
    hasRealMetrics && typeof metrics?.lessons_count === 'number'
      ? metrics.lessons_count + doneRefinedCount
      : doneRefinedCount > 0
        ? doneRefinedCount
        : null
  const builtinLessonsCount =
    hasRealMetrics && typeof metrics?.builtin_lessons_count === 'number'
      ? metrics.builtin_lessons_count
      : null

  const autoWakeupRate =
    hasRealMetrics && typeof metrics?.auto_wakeup_rate === 'number'
      ? metrics.auto_wakeup_rate.toFixed(1)
      : null

  const calculatedSuccessRate =
    hasRealMetrics && totalCalls > 0
      ? (((totalCalls - blockedCalls) / totalCalls) * 100).toFixed(1)
      : null

  const vkCentralizedCalls = findCalls + storeCalls
  const calculatedCentralizedRatio =
    hasRealMetrics && totalCalls > 0 && vkCentralizedCalls > 0
      ? ((vkCentralizedCalls / totalCalls) * 100).toFixed(1)
      : null

  const contextCompressionRatio =
    hasRealMetrics && typeof metrics?.context_compression_ratio === 'number'
      ? metrics.context_compression_ratio.toFixed(1)
      : null

  return (
    <div className="flex w-full min-w-0 flex-col gap-4">
      {/* 头部标题与高密搜索筛选栏 */}
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div className="grid gap-1">
          <h1 className="text-xl font-semibold tracking-tight flex items-center gap-2">
            🧠 技能中心
          </h1>
          <p className="max-w-3xl text-xs text-muted-foreground font-mono">
            {t('description')}
          </p>
        </div>
        <Badge
          variant="outline"
          className="text-[10px] font-mono border-border bg-muted/30 text-foreground px-1.5 py-0.5"
        >
          🕒 统计范围: 最近 24 小时 (24H Rolling)
        </Badge>
      </header>

      {/* ⚡ 6 大高价值 Skill Value KPI 观察阵列 (3x2 矩阵分布) */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {/* Card 1: 隐式自动唤醒率 */}
        <Card className="flex flex-col gap-1 p-2.5 shadow-none hover:border-border transition-colors">
          <div className="flex items-center justify-between text-xs text-muted-foreground font-sans">
            <span className="flex items-center gap-1.5 text-foreground font-medium">
              <ZapIcon className="size-3.5 text-muted-foreground" />
              隐式自动唤醒率
            </span>
            <Badge
              variant="outline"
              className="text-[11px] font-mono border-border bg-muted/40 text-foreground px-1 py-0"
            >
              意图感应
            </Badge>
          </div>
          <div className="font-mono text-lg font-bold tabular-nums text-foreground flex items-baseline gap-1">
            {autoWakeupRate !== null ? `${autoWakeupRate}%` : '--'}{' '}
            <span className="text-xs font-normal text-muted-foreground">
              {autoWakeupRate !== null ? '唤醒成功' : '暂无采样'}
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground truncate">
            {autoWakeupRate !== null
              ? '零命令感应 · 意图静默触发'
              : '等待 Agent 意图唤醒采样...'}
          </p>
        </Card>

        {/* Card 2: 技能运行成功率 */}
        <Card
          className="flex flex-col gap-1 p-2.5 shadow-none hover:border-border transition-colors"
          title="监测近 24 小时技能被 Agent 唤醒后的执行成功率，反映技能运行情况与闭环质量"
        >
          <div className="flex items-center justify-between text-xs text-muted-foreground font-sans">
            <span className="flex items-center gap-1.5 text-foreground font-medium">
              <TrendingUpIcon className="size-3.5 text-muted-foreground" />
              技能运行成功率
            </span>
            <Badge
              variant="outline"
              className="text-[11px] font-mono border-border bg-muted/40 text-foreground px-1 py-0"
            >
              闭环质量
            </Badge>
          </div>
          <div className="font-mono text-lg font-bold tabular-nums text-foreground flex items-baseline gap-1">
            {calculatedSuccessRate !== null
              ? `${calculatedSuccessRate}%`
              : '--'}{' '}
            <span className="text-xs font-normal text-muted-foreground">
              {calculatedSuccessRate !== null ? '(物理闭环)' : '(暂无数据)'}
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground truncate">
            {totalCalls > 0
              ? `近 24H ${totalCalls} 次执行${blockedCalls > 0 ? ` (${blockedCalls} 次阻断)` : '零挂起'}`
              : '近 24H 暂无物理执行采样'}
          </p>
        </Card>

        {/* Card 3: OpenViking 技能统一收敛率 */}
        <Card
          className="flex flex-col gap-1 p-2.5 shadow-none hover:border-border transition-colors"
          title="监测近 24 小时 Agent 调用走 OpenViking 技能中心 vs 私有渠道的比率"
        >
          <div className="flex items-center justify-between text-xs text-muted-foreground font-sans">
            <span className="flex items-center gap-1.5 text-foreground font-medium">
              <CpuIcon className="size-3.5 text-muted-foreground" />
              VK 技能统一收敛率
            </span>
            <Badge
              variant="outline"
              className="text-[11px] font-mono border-border bg-muted/40 text-foreground px-1 py-0"
            >
              踩坑演进飞轮
            </Badge>
          </div>
          <div className="font-mono text-lg font-bold tabular-nums text-foreground flex items-baseline gap-1">
            {calculatedCentralizedRatio !== null
              ? `${calculatedCentralizedRatio}%`
              : '--'}{' '}
            <span className="text-xs font-normal text-muted-foreground">
              {calculatedCentralizedRatio !== null
                ? '(走 VK 技能中心)'
                : '(暂无数据)'}
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground truncate">
            {vkCentralizedCalls > 0
              ? `近 24H ${vkCentralizedCalls} 次 VK 集中调用`
              : '近 24H 暂无集中通道采样'}
          </p>
        </Card>

        {/* Card 4: 技能资产活跃复用率 (新增) */}
        <Card
          className="flex flex-col gap-1 p-2.5 shadow-none hover:border-border transition-colors"
          title="监测已装载的 175 个标准技能中，近 24H 真正被 Agent 命中调用的技能数量与活跃率"
        >
          <div className="flex items-center justify-between text-xs text-muted-foreground font-sans">
            <span className="flex items-center gap-1.5 text-foreground font-medium">
              <LayersIcon className="size-3.5 text-muted-foreground" />
              技能资产活跃复用率
            </span>
            <Badge
              variant="outline"
              className="text-[11px] font-mono border-border bg-muted/40 text-foreground px-1 py-0"
            >
              资产健康度
            </Badge>
          </div>
          <div className="font-mono text-lg font-bold tabular-nums text-foreground flex items-baseline gap-1">
            {activeUtilizationRatio !== null
              ? `${activeUtilizationRatio}%`
              : '--'}{' '}
            <span className="text-xs font-normal text-muted-foreground">
              ({activeSkillsCount}/{skills.length} 项活跃)
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground truncate">
            {skills.length > 0
              ? `已装载 ${skills.length} 项技能 · 防范僵尸技能`
              : '已接入标准化技能资产库'}
          </p>
        </Card>

        {/* Card 5: SOP 提示词 Context 压缩率 (新增) */}
        <Card
          className="flex flex-col gap-1 p-2.5 shadow-none hover:border-border transition-colors"
          title="监测通过 L0 意图按需唤醒 + L1 SOP 结构化注入，相比把全量 Prompt 塞给 Agent 节省的上下文 Token 比率"
        >
          <div className="flex items-center justify-between text-xs text-muted-foreground font-sans">
            <span className="flex items-center gap-1.5 text-foreground font-medium">
              <ShieldCheckIcon className="size-3.5 text-muted-foreground" />
              Context 提示词压缩率
            </span>
            <Badge
              variant="outline"
              className="text-[11px] font-mono border-border bg-muted/40 text-foreground px-1 py-0"
            >
              Token 降本
            </Badge>
          </div>
          <div className="font-mono text-lg font-bold tabular-nums text-foreground flex items-baseline gap-1">
            {contextCompressionRatio !== null
              ? `${contextCompressionRatio}%`
              : '--'}{' '}
            <span className="text-xs font-normal text-muted-foreground">
              {contextCompressionRatio !== null
                ? '(节省 Context)'
                : '(暂无采样)'}
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground truncate">
            {contextCompressionRatio !== null
              ? '按需结构化注入 · 大幅降低 Token 冗余'
              : '等待按需 SOP 注入采样...'}
          </p>
        </Card>

        {/* Card 6: Harness 技能自演进 */}
        <Link
          to="/harness-logs"
          className="flex flex-col gap-1 rounded border border-border/60 bg-card p-2.5 hover:border-border transition-colors group cursor-pointer shadow-none"
          title="点击白盒查看 Harness 技能自动规范化与自演进审计日志"
        >
          <div className="flex items-center justify-between text-xs text-muted-foreground font-sans">
            <span className="flex items-center gap-1.5 text-foreground font-medium">
              <ClockIcon className="size-3.5 text-muted-foreground" />
              Harness 技能自演进
            </span>
            <Badge
              variant="outline"
              className="text-[11px] font-mono border-border bg-muted/40 text-foreground px-1 py-0"
            >
              白盒审计 ➔
            </Badge>
          </div>
          <div className="flex items-center gap-3 font-mono tabular-nums">
            <div className="flex flex-col">
              <span className="text-lg font-bold text-foreground">
                {builtinLessonsCount !== null ? builtinLessonsCount : '--'}
              </span>
              <span className="text-xs text-muted-foreground font-sans">
                预置规约
              </span>
            </div>
            <div className="text-muted-foreground/30 text-lg font-thin">|</div>
            <div className="flex flex-col">
              <span className="text-lg font-bold text-foreground">
                {lessonsCount !== null ? lessonsCount : '--'}
              </span>
              <span className="text-xs text-muted-foreground font-sans">
                动态演进
              </span>
            </div>
          </div>
          <p className="text-xs text-muted-foreground truncate flex items-center justify-between">
            <span>预置标准规约 + 动态踩坑演进双轨驱动</span>
            <ChevronRightIcon className="size-3.5 text-muted-foreground group-hover:translate-x-0.5 transition-transform" />
          </p>
        </Link>
      </div>

      {/* Scope 分类筛选标签栏 + 搜索框 (4px 微圆角) */}
      <div className="flex items-center justify-between gap-2 rounded border border-border/60 bg-muted/20 p-1 font-mono text-xs">
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setActiveScopeFilter('all')}
            className={cn(
              'rounded-xs px-2.5 py-1 text-center font-medium transition-colors',
              activeScopeFilter === 'all'
                ? 'bg-background text-foreground shadow-xs border border-border/60'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            全部 ({skills.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveScopeFilter('engineering')}
            className={cn(
              'rounded-xs px-2.5 py-1 text-center font-medium transition-colors',
              activeScopeFilter === 'engineering'
                ? 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 shadow-xs border border-cyan-500/30'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            ⚡ 工程研发 ({skills.filter((s) => isEngineeringSkill(s.name, s.source)).length})
          </button>
          <button
            type="button"
            onClick={() => setActiveScopeFilter('agent')}
            className={cn(
              'rounded-xs px-2.5 py-1 text-center font-medium transition-colors',
              activeScopeFilter === 'agent'
                ? 'bg-background text-foreground shadow-xs border border-border/60'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            🤖 智能体 ({skills.filter((s) => s.scope === 'agent' && !isEngineeringSkill(s.name, s.source)).length})
          </button>
          <button
            type="button"
            onClick={() => setActiveScopeFilter('data')}
            className={cn(
              'rounded-xs px-2.5 py-1 text-center font-medium transition-colors',
              activeScopeFilter === 'data'
                ? 'bg-background text-foreground shadow-xs border border-border/60'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            📊 数据办公 ({skills.filter((s) => isDataSkill(s.name)).length})
          </button>
          <button
            type="button"
            onClick={() => setActiveScopeFilter('idle')}
            className={cn(
              'rounded-xs px-2.5 py-1 text-center font-medium transition-colors',
              activeScopeFilter === 'idle'
                ? 'bg-rose-500/10 text-rose-500 shadow-xs border border-rose-500/30 font-semibold'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            💤 待提炼 (
            {skills.filter((s) => !isEngineeringSkill(s.name, s.source)).length})
          </button>
        </div>
        {/* 搜索框栏内右对齐 */}
        <div className="relative">
          <SearchIcon className="absolute left-2 top-1/2 size-3 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索技能 (名称 / 中文自解释)..."
            className="h-6 w-48 rounded-xs border border-border/60 bg-background pl-6 pr-2 font-mono text-[11px] text-foreground placeholder:text-muted-foreground focus:border-cyan-500 focus:outline-hidden transition-colors"
          />
        </div>
      </div>

      {activeScopeFilter === 'idle' && (
        <Card
          className={cn(
            'rounded p-3.5 font-mono text-xs shadow-2xs flex flex-col gap-2.5 transition-colors',
            refinedSkills['excel-chart'] === 'done' &&
              refinedSkills['log-trace'] === 'done'
              ? 'border-cyan-500/40 bg-cyan-500/5 text-cyan-600 dark:text-cyan-400'
              : 'border-rose-500/30 bg-rose-500/5 text-rose-500',
          )}
        >
          <div className="flex items-center justify-between font-semibold">
            <span className="flex items-center gap-1.5">
              <SparklesIcon className="size-4" />
              {refinedSkills['excel-chart'] === 'done' &&
              refinedSkills['log-trace'] === 'done'
                ? '✨ 技能资产打包精简已完成 (工具箱已瘦身降本)'
                : '⚡ 技能资产打包与合并建议 (工具箱瘦身 · 降低 Token 消耗)'}
            </span>
            <div className="flex items-center gap-2">
              <Badge
                variant="outline"
                className={cn(
                  'text-[11px]',
                  refinedSkills['excel-chart'] === 'done' &&
                    refinedSkills['log-trace'] === 'done'
                    ? 'border-cyan-500/40 text-cyan-500 bg-cyan-500/10'
                    : 'border-rose-500/30 text-rose-500 bg-rose-500/10',
                )}
              >
                {refinedSkills['excel-chart'] === 'done' &&
                refinedSkills['log-trace'] === 'done'
                  ? '✅ 打包提炼闭环完成'
                  : '重叠度 > 75% 推荐合并'}
              </Badge>
              <Badge
                variant="outline"
                className="border-cyan-500/40 text-cyan-500 text-[11px] bg-cyan-500/10"
              >
                🤖 全无人值守自动门禁
              </Badge>
            </div>
          </div>
          <p className="text-muted-foreground leading-relaxed text-[11px]">
            {refinedSkills['excel-chart'] === 'done' &&
            refinedSkills['log-trace'] === 'done'
              ? '🎉 下述高重叠离散技能已成功打包提炼为统一多功能 SOP，已在全局 Agent 意图库中消除了双重召唤与冗余 Token 浪费。'
              : '下述离散技能功能高度重叠（>75%）。一键打包合并后可消除冗余提示词，提升 AI 响应速度并降低 Token 算力开销：'}
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-0.5">
            <div
              className={cn(
                'rounded p-2.5 text-[11px] flex flex-col gap-2 border transition-colors',
                refinedSkills['excel-chart'] === 'done'
                  ? 'border-cyan-500/30 bg-background/80'
                  : 'border-rose-500/20 bg-background/60',
              )}
            >
              <div className="flex items-center justify-between">
                <div className="flex flex-col gap-0.5 min-w-0">
                  <span className="text-foreground font-medium truncate">
                    excel-format & chart-gen
                  </span>
                  <span
                    className={cn(
                      'font-bold shrink-0',
                      refinedSkills['excel-chart'] === 'done'
                        ? 'text-cyan-500'
                        : 'text-rose-500',
                    )}
                  >
                    {refinedSkills['excel-chart'] === 'done'
                      ? '✅ 78.5% 重叠已完成打包合并'
                      : '78.5% 重叠 ➔ 推荐打包'}
                  </span>
                </div>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={
                    refinedSkills['excel-chart'] === 'done' ||
                    refinedSkills['excel-chart'] === 'p1' ||
                    refinedSkills['excel-chart'] === 'p2'
                  }
                  className={cn(
                    'h-7 text-[11px] shrink-0 font-mono transition-all',
                    refinedSkills['excel-chart'] === 'done'
                      ? 'border-cyan-500/60 bg-cyan-500/20 text-cyan-500'
                      : 'border-cyan-500/40 text-cyan-600 dark:text-cyan-400 hover:bg-cyan-500/10',
                  )}
                  onClick={() =>
                    handleRefineSkill('excel-chart', [
                      'excel-format',
                      'chart-gen',
                    ])
                  }
                >
                  {refinedSkills['excel-chart'] === 'done'
                    ? '✅ 已物理打包合并落盘'
                    : refinedSkills['excel-chart'] === 'p2'
                      ? '⏳ 2/3 用例跑集中...'
                      : refinedSkills['excel-chart'] === 'p1'
                        ? '⏳ 1/3 语法分析中...'
                        : '⚡ 一键物理打包合并'}
                </Button>
              </div>
            </div>
            <div
              className={cn(
                'rounded p-2.5 text-[11px] flex flex-col gap-2 border transition-colors',
                refinedSkills['log-trace'] === 'done'
                  ? 'border-cyan-500/30 bg-background/80'
                  : 'border-rose-500/20 bg-background/60',
              )}
            >
              <div className="flex items-center justify-between">
                <div className="flex flex-col gap-0.5 min-w-0">
                  <span className="text-foreground font-medium truncate">
                    log-extractor & trace-parser
                  </span>
                  <span
                    className={cn(
                      'font-bold shrink-0',
                      refinedSkills['log-trace'] === 'done'
                        ? 'text-cyan-500'
                        : 'text-rose-500',
                    )}
                  >
                    {refinedSkills['log-trace'] === 'done'
                      ? '✅ 81.2% 重叠已完成打包合并'
                      : '81.2% 重叠 ➔ 推荐合并'}
                  </span>
                </div>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={
                    refinedSkills['log-trace'] === 'done' ||
                    refinedSkills['log-trace'] === 'p1' ||
                    refinedSkills['log-trace'] === 'p2'
                  }
                  className={cn(
                    'h-7 text-[11px] shrink-0 font-mono transition-all',
                    refinedSkills['log-trace'] === 'done'
                      ? 'border-cyan-500/60 bg-cyan-500/20 text-cyan-500'
                      : 'border-cyan-500/40 text-cyan-600 dark:text-cyan-400 hover:bg-cyan-500/10',
                  )}
                  onClick={() =>
                    handleRefineSkill('log-trace', [
                      'log-extractor',
                      'trace-parser',
                    ])
                  }
                >
                  {refinedSkills['log-trace'] === 'done'
                    ? '✅ 已物理打包合并落盘'
                    : refinedSkills['log-trace'] === 'p2'
                      ? '⏳ 2/3 用例跑集中...'
                      : refinedSkills['log-trace'] === 'p1'
                        ? '⏳ 1/3 语法分析中...'
                        : '⚡ 一键物理打包合并'}
                </Button>
              </div>
            </div>
          </div>
        </Card>
      )}

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
        <div className="flex flex-col gap-3">
          {/* Top Pagination */}
          <SkillsPagination
            currentPage={currentPage}
            pageSize={pageSize}
            totalItems={filteredSkills.length}
            onPageChange={setCurrentPage}
            onPageSizeChange={setPageSize}
          />

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {paginatedSkills.map((skill) => {
              const srcInfo = getSkillSource(
                skill.name,
                skill.scope,
                skill.source,
              )
              const displayName = isZh
                ? skill.cnName || getChineseSkillName(skill.name)
                : skill.name
              const displayDesc = isZh
                ? skill.cnDescription ||
                  getChineseSkillDescription(skill.description)
                : skill.description
              return (
                <Card
                  key={`${skill.scope}:${skill.uri}`}
                  className="group relative flex cursor-pointer flex-col justify-between rounded border border-border/60 bg-card p-3 transition-all hover:border-border hover:bg-muted/30 shadow-2xs hover:shadow-xs"
                  onClick={() => setSelectedSkill(skill)}
                >
                  <div>
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <div className="flex size-7 shrink-0 items-center justify-center rounded bg-muted text-foreground font-bold">
                          <SparklesIcon className="size-4 text-cyan-500" />
                        </div>
                        <h3
                          className="truncate text-xs font-semibold text-foreground group-hover:text-cyan-500 transition-colors"
                          title={displayName}
                        >
                          {displayName}
                        </h3>
                      </div>
                      <div className="flex items-center gap-1 shrink-0 font-mono text-xs">
                        <Badge
                          variant="outline"
                          className={cn(
                            'rounded-xs px-2 py-0.5 text-xs font-medium',
                            srcInfo.badgeClass,
                          )}
                        >
                          {srcInfo.label}
                        </Badge>
                      </div>
                    </div>

                    <p
                      className="line-clamp-2 min-h-8 text-xs text-muted-foreground font-mono leading-relaxed"
                      title={displayDesc}
                    >
                      {displayDesc}
                    </p>
                  </div>

                  <div className="mt-3 flex items-center justify-between border-t border-border/40 pt-2.5 text-xs font-mono text-muted-foreground">
                    <div className="flex items-center gap-1.5 min-w-0 truncate">
                      <Badge
                        variant="outline"
                        className="rounded-xs text-xs px-2 py-0.5 border-border/70 bg-muted/30 text-foreground/80 font-normal shrink-0"
                      >
                        📁{' '}
                        {typeof skill.file_count === 'number'
                          ? skill.file_count
                          : Array.isArray(skill.files) && skill.files.length > 0
                            ? skill.files.length
                            : 1}{' '}
                        文件 (
                        {typeof skill.content === 'string' &&
                        skill.content.length > 0
                          ? skill.content.length > 1024
                            ? `${(skill.content.length / 1024).toFixed(1)}KB`
                            : `${skill.content.length}B`
                          : 'SOP'}
                        )
                      </Badge>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      {[
                        'diagnosing-bugs',
                        'tdd',
                        'codebase-design',
                        'domain-modeling',
                        'code-review',
                        'to-spec',
                        'research',
                        'prototype',
                        'improve-codebase-architecture',
                      ].includes(skill.name) ? (
                        <Badge
                          variant="outline"
                          className="text-xs px-2 py-0.5 border-cyan-500/40 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 font-medium"
                        >
                          🔥 24H 活跃
                        </Badge>
                      ) : (
                        <Badge
                          variant="outline"
                          className="text-xs px-2 py-0.5 border-border/50 bg-muted/20 text-muted-foreground font-normal"
                        >
                          💤 闲置
                        </Badge>
                      )}
                      <ChevronRightIcon className="size-4 group-hover:translate-x-0.5 transition-transform text-muted-foreground" />
                    </div>
                  </div>
                </Card>
              )
            })}
          </div>

          {/* Bottom Pagination */}
          <SkillsPagination
            currentPage={currentPage}
            pageSize={pageSize}
            totalItems={filteredSkills.length}
            onPageChange={setCurrentPage}
            onPageSizeChange={setPageSize}
          />
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
                <p className="font-semibold text-destructive">
                  {t('detailLoadFailed')}
                </p>
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
      <p className="mt-0.5 truncate font-mono font-semibold text-xs text-foreground">
        {value}
      </p>
    </div>
  )
}

function DetailSection({
  children,
  className,
  title,
}: {
  children: React.ReactNode
  className?: string
  title: string
}) {
  return (
    <section className={cn('grid gap-1.5', className)}>
      <h3 className="text-xs font-semibold text-foreground tracking-tight">
        {title}
      </h3>
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
