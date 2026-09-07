import { getOvResult, isOvClientError, ovClient } from '#/lib/ov-client'
import { fileNameFromUri } from '#/lib/viking-uri'
import type {
  SkillDetail,
  SkillFile,
  SkillItem,
  SkillListResult,
  SkillScope,
  SkillTocItem,
} from './skill-types'
import {
  getChineseSkillDescription,
  getChineseSkillName,
} from './skill-translations'

export function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object'
    ? (value as Record<string, unknown>)
    : null
}

export function stringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string')
    : []
}

export function parseSkillFiles(rawFiles: unknown[]): SkillFile[] {
  return rawFiles.flatMap((rawFile) => {
    if (typeof rawFile === 'string' && rawFile.trim()) {
      const cleanPath = rawFile.trim()
      const cleanName = fileNameFromUri(cleanPath)
      return [
        {
          isDir: false,
          name: cleanName,
          path: cleanPath,
        },
      ]
    }
    const file = asRecord(rawFile)
    const fileName =
      typeof file?.name === 'string'
        ? file.name
        : typeof file?.path === 'string'
          ? fileNameFromUri(file.path)
          : ''
    if (!fileName) return []
    return [
      {
        isDir: Boolean(file?.is_dir || file?.isDir),
        name: fileName,
        path: typeof file?.path === 'string' ? file.path : fileName,
      },
    ]
  })
}

export function cleanSkillText(source: string): string {
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
    if (cleaned.length >= 3 && /[a-zA-Z0-9\u4e00-\u9fa5]/.test(cleaned)) {
      return cleaned
    }
  }
  return ''
}

export function normalizeSkills(value: unknown): SkillItem[] {
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
    if (name.startsWith('.') || /^\d{4}-\d{2}-\d{2}/.test(name) || name.toLowerCase().includes('curator')) {
      return []
    }

    const rawDesc =
      typeof skill?.description === 'string' ? skill.description.trim() : ''
    const rawAbstract =
      typeof skill?.abstract === 'string' ? skill.abstract.trim() : ''
    const rawOverview =
      typeof skill?.overview === 'string' ? skill.overview.trim() : ''
    const rawContent =
      typeof skill?.content === 'string' ? skill.content.trim() : ''

    let description = rawDesc || rawOverview || rawAbstract
    if (!description && rawContent) {
      description = cleanSkillText(rawContent.slice(0, 1000))
    }
    if (!description || description === '|' || description === '>') {
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
    const parsedFiles = parseSkillFiles(rawFiles)

    const fileCount =
      typeof skill?.file_count === 'number'
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

export function extractSopOverview(content: string, description: string): string {
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

export function extractSkillToc(content: string): SkillTocItem[] {
  const lines = content.split('\n')
  const toc: SkillTocItem[] = []
  lines.forEach((line, idx) => {
    const match = line.match(/^(#{1,4})\s+(.+)$/)
    if (match) {
      const level = match[1].length
      const title = match[2].trim()
      toc.push({
        level,
        title,
        lineIndex: idx,
        id: `toc-line-${idx}`,
      })
    }
  })
  return toc
}

export function normalizeSkillDetail(
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

  const parsedFiles = parseSkillFiles(rawFiles)
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

export function getErrorMessage(error: unknown): string {
  if (isOvClientError(error) || error instanceof Error) {
    return error.message
  }
  const record = asRecord(error)
  if (typeof record?.message === 'string') {
    return record.message
  }
  return JSON.stringify(error) || String(error)
}

export async function fetchSkills(): Promise<SkillItem[]> {
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

export async function fetchSkillDetail(skill: SkillItem): Promise<SkillDetail> {
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
