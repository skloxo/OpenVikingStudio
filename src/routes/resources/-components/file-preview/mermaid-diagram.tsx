import { useEffect, useId, useState } from 'react'
import { useTheme } from 'next-themes'
import { useTranslation } from 'react-i18next'

let initializedTheme: string | null = null

export function MermaidDiagram({ code }: { code: string }) {
  const { t } = useTranslation('resources')
  const { resolvedTheme } = useTheme()
  const rawId = useId()
  const renderId = `mermaid-${rawId.replace(/[^a-zA-Z0-9_-]/g, '')}`
  const [svg, setSvg] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [showSource, setShowSource] = useState(false)

  useEffect(() => {
    let cancelled = false
    const theme = resolvedTheme === 'dark' ? 'dark' : 'default'

    const renderDiagram = async () => {
      try {
        const mod = await import('mermaid')
        const mermaid = mod.default
        if (initializedTheme !== theme) {
          mermaid.initialize({
            startOnLoad: false,
            securityLevel: 'strict',
            theme,
          })
          initializedTheme = theme
        }
        const { svg: renderedSvg } = await mermaid.render(renderId, code)
        if (!cancelled) {
          setSvg(renderedSvg)
          setErrorMsg(null)
        }
      } catch (err) {
        if (!cancelled) {
          setSvg(null)
          setErrorMsg(err instanceof Error ? err.message : String(err))
        }
      }
    }

    void renderDiagram()
    return () => {
      cancelled = true
    }
  }, [code, renderId, resolvedTheme])

  return (
    <div className="my-3 overflow-hidden rounded-md border border-border/70 bg-card/50">
      <div className="flex items-center justify-between border-b border-border/60 bg-muted/30 px-3 py-1.5 text-xs text-muted-foreground">
        <span className="font-mono font-medium">mermaid</span>
        <button
          type="button"
          className="rounded px-2 py-0.5 text-xs hover:bg-muted hover:text-foreground"
          onClick={() => setShowSource((v) => !v)}
        >
          {showSource
            ? t('filePreview.mermaidDiagram')
            : t('filePreview.mermaidSource')}
        </button>
      </div>
      {showSource || errorMsg || !svg ? (
        <div className="p-3">
          {errorMsg ? (
            <div className="mb-2 text-xs text-rose-500">
              {t('filePreview.mermaidRenderError')}: {errorMsg}
            </div>
          ) : null}
          <pre className="overflow-x-auto font-mono text-xs leading-6 text-foreground">
            <code>{code}</code>
          </pre>
        </div>
      ) : (
        <div
          className="flex justify-center overflow-x-auto p-4 [&_svg]:max-w-full"
          dangerouslySetInnerHTML={{ __html: svg }}
        />
      )}
    </div>
  )
}
