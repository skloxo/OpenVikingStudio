import { useEffect, useMemo, useRef, useState, lazy, Suspense } from 'react'
import ReactMarkdown from 'react-markdown'
import rehypeRaw from 'rehype-raw'
import rehypeSanitize from 'rehype-sanitize'
import remarkGfm from 'remark-gfm'
import { X, Pencil, Save, XCircle, Loader2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '#/components/ui/button'
import { ScrollArea } from '#/components/ui/scroll-area'
import { parseOkfSidecarMarkdown } from '#/lib/okf-markdown'
import { formatSize } from '../-lib/normalize'
import { saveFileContent } from '../-lib/api'
import {
  useVikingFilePreview,
  useVikingFsStat,
  useInvalidateVikingFs,
} from '../-hooks/viking-fm'
import { useJsonFormat } from '../-hooks/use-json-format'
import { memoryFieldsDisplayContent } from '../-lib/syntax-highlight'
import type { VikingFsEntry } from '../-types/viking-fm'
import type { CodeEditorHandle } from './code-editor'
import { OkfMetadataPanel } from './okf-metadata-panel'

// ─── 子模块组件 ─────────────────────────────────────────────────────────────────
import {
  markdownComponents,
  MarkdownImage,
  MarkdownLink,
} from './file-preview/markdown-renderer'
import { JsonlPreview } from './file-preview/jsonl-preview'
import { DirectoryPreviewView } from './file-preview/directory-preview'
import { ImageViewer } from './file-preview/image-viewer'
import { CodeViewer } from './file-preview/code-viewer'
import { JsonViewer } from './file-preview/json-viewer'

// ─── 向后兼容 Re-exports (供单测及外部调用) ──────────────────────────────────────
export {
  parseJsonlRecords,
  normalizeJsonlDisplayText,
  hasJsonlToolPart,
  getJsonlMessage,
} from '../-lib/jsonl-parser'
export type {
  JsonlRecord,
  JsonlPart,
  JsonlMessage,
} from '../-lib/jsonl-parser'

const LazyCodeEditor = lazy(() =>
  import('./code-editor').then((m) => ({ default: m.CodeEditor })),
)

const LARGE_FILE_PREVIEW_BYTES = 2 * 1024 * 1024

export interface FilePreviewProps {
  file: VikingFsEntry | null
  hideDirectoryHeader?: boolean
  onClose: () => void
  onNavigate?: (uri: string) => void
  showCloseButton?: boolean
}

export function FilePreview({
  file,
  hideDirectoryHeader = false,
  onClose,
  onNavigate,
  showCloseButton = true,
}: FilePreviewProps) {
  const { t } = useTranslation('resources')
  const isJsonPath = Boolean(
    file && !file.isDir && file.name.toLowerCase().endsWith('.json'),
  )
  const needsMetadata = Boolean(
    isJsonPath && file && (file.sizeBytes === null || !file.modTime),
  )
  const statQuery = useVikingFsStat(needsMetadata ? file?.uri : undefined)
  const resolvedFile = useMemo(() => {
    if (!file || !statQuery.data || statQuery.data.uri !== file.uri) {
      return file
    }
    return {
      ...file,
      ...statQuery.data,
    }
  }, [file, statQuery.data])

  const isJsonFile = isJsonPath
  const previewQuery = useVikingFilePreview(
    resolvedFile,
    {
      maxAutoReadBytes: LARGE_FILE_PREVIEW_BYTES,
      defaultReadLimit: -1,
      requireKnownSize: isJsonFile,
    },
    { raw: true },
  )
  const preview = previewQuery.preview
  const metadataLoading = needsMetadata && statQuery.isPending
  const hasPreviewContent =
    Boolean(preview?.shouldAutoRead) || previewQuery.isContentLoaded
  const previewLoading = metadataLoading || previewQuery.isLoading
  const displayContent = useMemo(
    () => memoryFieldsDisplayContent(preview?.content || ''),
    [preview?.content],
  )
  const okfDocument = useMemo(
    () =>
      file && preview?.fileType === 'markdown'
        ? parseOkfSidecarMarkdown(file.uri, displayContent)
        : null,
    [displayContent, file, preview?.fileType],
  )
  const jsonFormat = useJsonFormat(
    displayContent,
    isJsonFile && hasPreviewContent,
  )

  const [markdownMode, setMarkdownMode] = useState<'preview' | 'source'>(
    'preview',
  )
  const [jsonMode, setJsonMode] = useState<'preview' | 'source'>('preview')
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const editorRef = useRef<CodeEditorHandle>(null)
  const { invalidatePreview } = useInvalidateVikingFs()

  const canEdit =
    !file?.isDir &&
    preview?.shouldAutoRead &&
    (preview.fileType === 'code' ||
      preview.fileType === 'markdown' ||
      preview.fileType === 'jsonl' ||
      preview.fileType === 'text')

  useEffect(() => {
    setMarkdownMode('preview')
    setJsonMode('preview')
    setEditing(false)
  }, [file?.uri])

  const handleSave = async () => {
    if (!file || !editorRef.current) return
    setSaving(true)
    try {
      await saveFileContent(file.uri, editorRef.current.getContent())
      invalidatePreview(file.uri)
      setEditing(false)
    } catch (err) {
      console.error('Save failed:', err)
    } finally {
      setSaving(false)
    }
  }

  if (!file) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        {t('filePreview.emptyPrompt')}
      </div>
    )
  }

  const isMarkdown = preview?.fileType === 'markdown'
  const isDark = document.documentElement.classList.contains('dark')
  const emptyFileText = t('filePreview.emptyFile')
  const showHeader = !(hideDirectoryHeader && file.isDir)
  const previewFile = resolvedFile || file
  const showJsonPreview =
    !editing &&
    !previewLoading &&
    preview?.fileType === 'code' &&
    hasPreviewContent &&
    isJsonFile

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      {showHeader ? (
        <div className="flex min-h-14 shrink-0 items-center justify-between border-b px-4">
          <div className="flex min-w-0 items-center gap-2">
            <div className="min-w-0">
              <div className="truncate text-sm font-medium leading-5">
                {file.name}
              </div>
              {!file.isDir ? (
                <div className="text-xs leading-5 text-muted-foreground">
                  {formatSize(previewFile.sizeBytes ?? previewFile.size)} ·{' '}
                  {previewFile.modTime || '-'}
                </div>
              ) : null}
            </div>
            {editing ? (
              <div className="flex items-center gap-1">
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={saving}
                  onClick={() => setEditing(false)}
                >
                  <XCircle className="mr-1 size-3.5" />
                  {t('filePreview.cancel')}
                </Button>
                <Button
                  size="sm"
                  className="active:scale-[0.96] transition-transform"
                  disabled={saving}
                  onClick={handleSave}
                >
                  {saving ? (
                    <Loader2 className="mr-1 size-3.5 animate-spin" />
                  ) : (
                    <Save className="mr-1 size-3.5" />
                  )}
                  {t('filePreview.save')}
                </Button>
              </div>
            ) : (
              canEdit && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setEditing(true)}
                >
                  <Pencil className="mr-1 size-3.5" />
                  {t('filePreview.edit')}
                </Button>
              )
            )}
          </div>
          {showCloseButton ? (
            <Button
              size="icon"
              variant="ghost"
              className="size-10"
              onClick={onClose}
            >
              <X className="size-4" />
            </Button>
          ) : null}
        </div>
      ) : null}

      {editing && preview?.content != null ? (
        <div className="min-h-0 flex-1 p-2">
          <Suspense
            fallback={
              <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                <Loader2 className="mr-2 size-4 animate-spin" />
                {t('filePreview.loadingEditor')}
              </div>
            }
          >
            <LazyCodeEditor
              ref={editorRef}
              initialContent={preview.content}
              filename={file.name}
              isDark={isDark}
            />
          </Suspense>
        </div>
      ) : showJsonPreview ? (
        <JsonViewer
          file={previewFile}
          displayContent={displayContent}
          jsonFormat={jsonFormat}
          jsonMode={jsonMode}
          onJsonModeChange={setJsonMode}
          isDark={isDark}
        />
      ) : (
        <ScrollArea className="min-h-0 flex-1">
          <div className="mx-auto min-h-full w-full max-w-5xl p-4">
            {isMarkdown && !editing ? (
              <div className="mb-3 inline-flex overflow-hidden rounded-md border">
                <button
                  type="button"
                  className={`px-3 py-1.5 text-xs ${markdownMode === 'preview' ? 'bg-muted font-medium text-foreground' : 'text-muted-foreground hover:bg-muted/60'}`}
                  onClick={() => setMarkdownMode('preview')}
                >
                  {t('filePreview.markdownPreview')}
                </button>
                <button
                  type="button"
                  className={`px-3 py-1.5 text-xs ${markdownMode === 'source' ? 'bg-muted font-medium text-foreground' : 'text-muted-foreground hover:bg-muted/60'}`}
                  onClick={() => setMarkdownMode('source')}
                >
                  {t('filePreview.markdownSource')}
                </button>
              </div>
            ) : null}

            {file.isDir ? (
              <DirectoryPreviewView file={file} onNavigate={onNavigate} />
            ) : null}

            {preview?.fileType === 'image' ? (
              <ImageViewer file={file} fileType={preview?.fileType} />
            ) : null}

            {previewLoading && preview?.fileType !== 'image' ? (
              <div className="text-sm text-muted-foreground">
                {t('filePreview.loadingContent')}
              </div>
            ) : null}

            {!previewLoading &&
            preview &&
            !file.isDir &&
            preview.fileType !== 'image' &&
            !hasPreviewContent ? (
              <div className="space-y-3 text-sm text-muted-foreground">
                <div>
                  {preview.reason === 'binary'
                    ? t('filePreview.unsupportedBinary')
                    : t('filePreview.largeFileSkipped')}
                </div>
                {previewQuery.canLoadContent && isJsonFile ? (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={previewQuery.isFetching}
                    onClick={() => void previewQuery.refetch()}
                  >
                    {previewQuery.isFetching ? (
                      <Loader2 className="mr-2 size-4 animate-spin" />
                    ) : null}
                    {t('filePreview.loadFile')}
                  </Button>
                ) : null}
              </div>
            ) : null}

            {!previewLoading &&
            preview?.fileType === 'markdown' &&
            hasPreviewContent &&
            markdownMode === 'preview' ? (
              <div className="space-y-5">
                {okfDocument ? (
                  <OkfMetadataPanel
                    metadata={okfDocument.metadata}
                    onNavigate={onNavigate}
                    rawFrontmatter={okfDocument.rawFrontmatter}
                  />
                ) : null}
                <article className="prose prose-sm max-w-none break-words dark:prose-invert dark:prose-pre:bg-muted-foreground/20">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    rehypePlugins={[rehypeRaw, rehypeSanitize]}
                    urlTransform={(url) => url}
                    components={{
                      ...markdownComponents,
                      img: ({ src, alt }) => (
                        <MarkdownImage
                          src={src ? String(src) : undefined}
                          alt={alt}
                          fileUri={file.uri}
                        />
                      ),
                      a: ({ href, children }) => (
                        <MarkdownLink
                          href={href}
                          fileUri={file.uri}
                          onNavigate={onNavigate}
                        >
                          {children}
                        </MarkdownLink>
                      ),
                    }}
                  >
                    {okfDocument
                      ? okfDocument.body || emptyFileText
                      : displayContent || emptyFileText}
                  </ReactMarkdown>
                </article>
              </div>
            ) : null}

            {!previewLoading &&
            preview?.fileType === 'markdown' &&
            hasPreviewContent &&
            markdownMode === 'source' ? (
              <CodeViewer
                content={displayContent}
                filename={file.name}
                emptyText={emptyFileText}
              />
            ) : null}

            {!previewLoading &&
            preview?.fileType === 'code' &&
            hasPreviewContent &&
            !isJsonFile ? (
              <CodeViewer
                content={displayContent}
                filename={file.name}
                emptyText={emptyFileText}
              />
            ) : null}

            {!previewLoading &&
            preview?.fileType === 'jsonl' &&
            hasPreviewContent ? (
              <JsonlPreview content={displayContent || ''} />
            ) : null}

            {!previewLoading &&
            preview &&
            preview.fileType !== 'image' &&
            preview.fileType !== 'markdown' &&
            preview.fileType !== 'jsonl' &&
            preview.fileType !== 'code' &&
            hasPreviewContent ? (
              <pre className="whitespace-pre-wrap break-words text-xs leading-6">
                {displayContent || emptyFileText}
              </pre>
            ) : null}
          </div>
        </ScrollArea>
      )}
    </div>
  )
}
