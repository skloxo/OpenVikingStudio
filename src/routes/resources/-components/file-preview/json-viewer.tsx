import { Suspense, lazy } from 'react'
import { Loader2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { VikingFsEntry } from '../../-types/viking-fm'

const LazyCodeEditor = lazy(() =>
  import('../code-editor').then((m) => ({ default: m.CodeEditor })),
)

const LARGE_FILE_PREVIEW_BYTES = 2 * 1024 * 1024

interface JsonViewerProps {
  file: VikingFsEntry
  displayContent: string
  jsonFormat: {
    content: string
    error: string | null
    isFormatting: boolean
  }
  jsonMode: 'preview' | 'source'
  onJsonModeChange: (mode: 'preview' | 'source') => void
  isDark: boolean
}

export function JsonViewer({
  file,
  displayContent,
  jsonFormat,
  jsonMode,
  onJsonModeChange,
  isDark,
}: JsonViewerProps) {
  const { t } = useTranslation('resources')

  return (
    <div className="min-h-0 flex-1 p-2">
      <div className="flex h-full min-h-0 flex-col">
        <div className="mb-2 inline-flex shrink-0 self-start overflow-hidden rounded-md border">
          <button
            type="button"
            className={`px-3 py-1.5 text-xs ${
              jsonMode === 'preview'
                ? 'bg-muted font-medium text-foreground'
                : 'text-muted-foreground hover:bg-muted/60'
            }`}
            onClick={() => onJsonModeChange('preview')}
          >
            {t('filePreview.markdownPreview')}
          </button>
          <button
            type="button"
            className={`px-3 py-1.5 text-xs ${
              jsonMode === 'source'
                ? 'bg-muted font-medium text-foreground'
                : 'text-muted-foreground hover:bg-muted/60'
            }`}
            onClick={() => onJsonModeChange('source')}
          >
            {t('filePreview.markdownSource')}
          </button>
        </div>

        {jsonMode === 'preview' && jsonFormat.isFormatting ? (
          <div className="flex min-h-0 flex-1 items-center justify-center text-sm text-muted-foreground">
            <Loader2 className="mr-2 size-4 animate-spin" />
            {t('filePreview.formattingJson')}
          </div>
        ) : (
          <div className="flex min-h-0 flex-1 flex-col gap-2">
            {jsonMode === 'preview' && jsonFormat.error ? (
              <div className="shrink-0 text-xs text-destructive">
                {t('filePreview.jsonFormatFailed')}
              </div>
            ) : null}
            <div className="min-h-0 flex-1">
              <Suspense
                fallback={
                  <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                    <Loader2 className="mr-2 size-4 animate-spin" />
                    {t('filePreview.loadingEditor')}
                  </div>
                }
              >
                <LazyCodeEditor
                  initialContent={
                    jsonMode === 'preview'
                      ? jsonFormat.content
                      : displayContent
                  }
                  filename={file.name}
                  isDark={isDark}
                  readOnly
                  appearance={jsonMode === 'preview' ? 'plain' : 'editor'}
                  enableLanguageSupport={
                    (file.sizeBytes ?? 0) <= LARGE_FILE_PREVIEW_BYTES
                  }
                  lineWrapping={
                    jsonMode === 'source' || Boolean(jsonFormat.error)
                  }
                />
              </Suspense>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
