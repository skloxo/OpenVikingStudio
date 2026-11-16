import katex from 'katex'
import 'katex/dist/katex.min.css'

type MathToken = {
  displayMode: boolean
  raw: string
  value: string
}

const MATH_SEGMENT_RE =
  /(\$\$[\s\S]+?\$\$|\$(?!\s)(?:\\.|[^$\n])+?(?<!\s)\$)/g

export function extractMathSegments(text: string): Array<string | MathToken> {
  const parts: Array<string | MathToken> = []
  let lastIndex = 0

  for (const match of text.matchAll(MATH_SEGMENT_RE)) {
    const idx = match.index ?? 0
    if (idx > lastIndex) {
      parts.push(text.slice(lastIndex, idx))
    }
    const raw = match[0]
    const displayMode = raw.startsWith('$$') && raw.endsWith('$$')
    const value = (displayMode ? raw.slice(2, -2) : raw.slice(1, -1)).trim()
    if (value) {
      parts.push({ displayMode, raw, value })
    } else {
      parts.push(raw)
    }
    lastIndex = idx + raw.length
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex))
  }
  return parts
}

type MdastNode = {
  type: string
  value?: string
  children?: MdastNode[]
  data?: Record<string, unknown>
}

const SKIP_MATH_PARENTS = new Set(['code', 'inlineCode', 'link', 'linkReference'])

function transformTextNodes(node: MdastNode): void {
  if (SKIP_MATH_PARENTS.has(node.type) || !Array.isArray(node.children)) {
    return
  }

  const nextChildren: MdastNode[] = []
  for (const child of node.children) {
    if (
      child.type === 'text' &&
      typeof child.value === 'string' &&
      child.value.includes('$')
    ) {
      for (const seg of extractMathSegments(child.value)) {
        if (typeof seg === 'string') {
          nextChildren.push({ type: 'text', value: seg })
        } else {
          nextChildren.push({
            type: 'ovKatex',
            data: {
              hName: 'span',
              hProperties: {
                className: 'ov-katex',
                'data-latex': seg.value,
                'data-display': seg.displayMode ? 'true' : 'false',
              },
            },
            children: [],
          })
        }
      }
    } else {
      transformTextNodes(child)
      nextChildren.push(child)
    }
  }
  node.children = nextChildren
}

/** Lightweight remark plugin emitting safe KaTeX placeholder spans for ReactMarkdown. */
export function remarkKatex() {
  return (tree: MdastNode) => {
    transformTextNodes(tree)
  }
}

export function KatexFormula({
  latex,
  displayMode = false,
}: {
  latex: string
  displayMode?: boolean
}) {
  const html = katex.renderToString(latex, {
    displayMode,
    throwOnError: false,
    output: 'htmlAndMathml',
  })
  return displayMode ? (
    <span
      className="my-3 block overflow-x-auto text-center"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  ) : (
    <span
      className="ov-katex-inline"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}
