import { useEffect, useState } from 'react'
import hljs from 'highlight.js/lib/core'
import {
  ensureLanguage,
  detectCodeLanguage,
  escapeHtml,
} from '../../-lib/syntax-highlight'

interface CodeViewerProps {
  content: string
  filename: string
  needsHighlight?: boolean
  emptyText?: string
}

export function CodeViewer({
  content,
  filename,
  needsHighlight = true,
  emptyText = '',
}: CodeViewerProps) {
  const [highlightedCodeHtml, setHighlightedCodeHtml] = useState('')

  useEffect(() => {
    if (!needsHighlight || !content) {
      setHighlightedCodeHtml('')
      return
    }

    let cancelled = false
    const language = detectCodeLanguage(filename)

    const run = async () => {
      try {
        if (language) {
          await ensureLanguage(language)
          if (cancelled) return
          setHighlightedCodeHtml(hljs.highlight(content, { language }).value)
        } else {
          setHighlightedCodeHtml(hljs.highlightAuto(content).value)
        }
      } catch {
        if (!cancelled) setHighlightedCodeHtml(escapeHtml(content))
      }
    }

    void run()
    return () => {
      cancelled = true
    }
  }, [content, filename, needsHighlight])

  return (
    <pre className="overflow-auto rounded-md border bg-muted/20 p-3 text-xs leading-6">
      <code
        className="hljs block"
        dangerouslySetInnerHTML={{
          __html: highlightedCodeHtml || escapeHtml(content || emptyText),
        }}
      />
    </pre>
  )
}
