import hljs from 'highlight.js/lib/core'

export const languageLoaders: Partial<
  Record<
    string,
    () => Promise<{ default: Parameters<typeof hljs.registerLanguage>[1] }>
  >
> = {
  bash: () => import('highlight.js/lib/languages/bash'),
  c: () => import('highlight.js/lib/languages/c'),
  cpp: () => import('highlight.js/lib/languages/cpp'),
  csharp: () => import('highlight.js/lib/languages/csharp'),
  css: () => import('highlight.js/lib/languages/css'),
  dart: () => import('highlight.js/lib/languages/dart'),
  diff: () => import('highlight.js/lib/languages/diff'),
  dockerfile: () => import('highlight.js/lib/languages/dockerfile'),
  elixir: () => import('highlight.js/lib/languages/elixir'),
  erlang: () => import('highlight.js/lib/languages/erlang'),
  go: () => import('highlight.js/lib/languages/go'),
  graphql: () => import('highlight.js/lib/languages/graphql'),
  haskell: () => import('highlight.js/lib/languages/haskell'),
  ini: () => import('highlight.js/lib/languages/ini'),
  java: () => import('highlight.js/lib/languages/java'),
  javascript: () => import('highlight.js/lib/languages/javascript'),
  json: () => import('highlight.js/lib/languages/json'),
  kotlin: () => import('highlight.js/lib/languages/kotlin'),
  latex: () => import('highlight.js/lib/languages/latex'),
  less: () => import('highlight.js/lib/languages/less'),
  lua: () => import('highlight.js/lib/languages/lua'),
  makefile: () => import('highlight.js/lib/languages/makefile'),
  markdown: () => import('highlight.js/lib/languages/markdown'),
  nginx: () => import('highlight.js/lib/languages/nginx'),
  objectivec: () => import('highlight.js/lib/languages/objectivec'),
  perl: () => import('highlight.js/lib/languages/perl'),
  php: () => import('highlight.js/lib/languages/php'),
  plaintext: () => import('highlight.js/lib/languages/plaintext'),
  protobuf: () => import('highlight.js/lib/languages/protobuf'),
  python: () => import('highlight.js/lib/languages/python'),
  r: () => import('highlight.js/lib/languages/r'),
  ruby: () => import('highlight.js/lib/languages/ruby'),
  rust: () => import('highlight.js/lib/languages/rust'),
  scala: () => import('highlight.js/lib/languages/scala'),
  scss: () => import('highlight.js/lib/languages/scss'),
  shell: () => import('highlight.js/lib/languages/shell'),
  sql: () => import('highlight.js/lib/languages/sql'),
  swift: () => import('highlight.js/lib/languages/swift'),
  typescript: () => import('highlight.js/lib/languages/typescript'),
  wasm: () => import('highlight.js/lib/languages/wasm'),
  xml: () => import('highlight.js/lib/languages/xml'),
  yaml: () => import('highlight.js/lib/languages/yaml'),
}

export const loadedLanguages = new Set<string>()
export const markdownLanguageAliases: Record<string, string> = {
  cjs: 'javascript',
  js: 'javascript',
  jsx: 'javascript',
  mjs: 'javascript',
  sh: 'bash',
  ts: 'typescript',
  tsx: 'typescript',
  yml: 'yaml',
  zsh: 'bash',
}

export async function ensureLanguage(lang: string): Promise<void> {
  if (loadedLanguages.has(lang)) return
  const loader = languageLoaders[lang]
  if (!loader) return
  const mod = await loader()
  hljs.registerLanguage(lang, mod.default)
  loadedLanguages.add(lang)
}

export function detectCodeLanguage(filename: string): string | null {
  const lower = filename.toLowerCase()
  const ext = lower.includes('.') ? lower.split('.').pop() || '' : ''

  const extMap: Record<string, string> = {
    ts: 'typescript',
    tsx: 'typescript',
    js: 'javascript',
    jsx: 'javascript',
    mjs: 'javascript',
    cjs: 'javascript',
    py: 'python',
    pyw: 'python',
    go: 'go',
    rs: 'rust',
    java: 'java',
    c: 'c',
    h: 'c',
    cpp: 'cpp',
    cc: 'cpp',
    cxx: 'cpp',
    hpp: 'cpp',
    hxx: 'cpp',
    cs: 'csharp',
    json: 'json',
    yml: 'yaml',
    yaml: 'yaml',
    md: 'markdown',
    markdown: 'markdown',
    html: 'xml',
    xml: 'xml',
    svg: 'xml',
    xhtml: 'xml',
    css: 'css',
    scss: 'scss',
    less: 'less',
    sql: 'sql',
    sh: 'bash',
    bash: 'bash',
    zsh: 'bash',
    toml: 'ini',
    ini: 'ini',
    cfg: 'ini',
    conf: 'ini',
    dockerfile: 'dockerfile',
    dart: 'dart',
    kt: 'kotlin',
    kts: 'kotlin',
    swift: 'swift',
    rb: 'ruby',
    rake: 'ruby',
    gemspec: 'ruby',
    php: 'php',
    lua: 'lua',
    r: 'r',
    rmd: 'r',
    scala: 'scala',
    ex: 'elixir',
    exs: 'elixir',
    erl: 'erlang',
    hrl: 'erlang',
    hs: 'haskell',
    lhs: 'haskell',
    m: 'objectivec',
    mm: 'objectivec',
    pl: 'perl',
    pm: 'perl',
    proto: 'protobuf',
    graphql: 'graphql',
    gql: 'graphql',
    tex: 'latex',
    latex: 'latex',
    makefile: 'makefile',
    nginx: 'nginx',
    wasm: 'wasm',
    wat: 'wasm',
    diff: 'diff',
    patch: 'diff',
  }

  if (ext && extMap[ext]) return extMap[ext]

  const basename = lower.split('/').pop() || ''
  if (basename === 'dockerfile' || basename.startsWith('dockerfile.'))
    return 'dockerfile'
  if (basename === 'makefile' || basename === 'gnumakefile') return 'makefile'
  if (
    basename === '.bashrc' ||
    basename === '.zshrc' ||
    basename === '.bash_profile'
  )
    return 'bash'

  return null
}

export function escapeHtml(raw: string): string {
  return raw.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

export const MEMORY_FIELDS_RE = /<!--\s*MEMORY_FIELDS\s*([\s\S]*?)\s*-->/

export function parseMemoryFields(
  content: string,
): Record<string, unknown> | null {
  const match = MEMORY_FIELDS_RE.exec(content)
  if (!match?.[1]) return null

  try {
    const parsed = JSON.parse(match[1].trim()) as unknown
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : null
  } catch {
    return null
  }
}

export function stripMemoryFields(content: string): string {
  return content.replace(MEMORY_FIELDS_RE, '').trim()
}

export function memoryFieldsDisplayContent(content: string): string {
  const fields = parseMemoryFields(content)
  if (!fields) return content

  const body = stripMemoryFields(content)
  if (body) return body

  const fieldContent = fields.content
  if (typeof fieldContent === 'string' && fieldContent.trim()) {
    return fieldContent.trim()
  }

  return JSON.stringify(fields, null, 2)
}

export function normalizeMarkdownLanguage(
  className: string | undefined,
): string {
  const match = /language-([\w-]+)/.exec(className || '')
  const raw = match?.[1]?.toLowerCase() || ''
  return markdownLanguageAliases[raw] ?? raw
}
