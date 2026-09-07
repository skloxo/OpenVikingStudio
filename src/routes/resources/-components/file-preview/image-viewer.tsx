import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getContentDownload } from '#/lib/ov-client'
import type { VikingFsEntry } from '../../-types/viking-fm'
import { toDownloadUrl, withCacheBust } from './markdown-renderer'

interface ImageViewerProps {
  file: VikingFsEntry
  fileType?: string
}

export function ImageViewer({ file, fileType }: ImageViewerProps) {
  const { t } = useTranslation('resources')
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [imageLoading, setImageLoading] = useState(false)
  const [imageError, setImageError] = useState<string | null>(null)

  const imageSrc = useMemo(() => {
    if (fileType !== 'image') return null
    return withCacheBust(
      toDownloadUrl(file.uri),
      file.modTime || Date.now().toString(),
    )
  }, [file.uri, file.modTime, fileType])

  useEffect(() => {
    let alive = true

    const loadWithAuthClient = async () => {
      if (fileType !== 'image') {
        setImageUrl(null)
        setImageError(null)
        setImageLoading(false)
        return
      }

      setImageLoading(true)
      setImageError(null)

      try {
        const response = await getContentDownload({
          query: { uri: file.uri },
          responseType: 'blob',
          throwOnError: true,
        })

        if (!alive) return

        const blob = response.data as Blob
        if (blob.size === 0) throw new Error('empty blob')

        const nextUrl = URL.createObjectURL(blob)
        setImageUrl((prev) => {
          if (prev) URL.revokeObjectURL(prev)
          return nextUrl
        })
        setImageLoading(false)
      } catch (error) {
        if (!alive) return
        setImageLoading(false)
        setImageError(String(error))
      }
    }

    if (fileType === 'image') {
      void loadWithAuthClient()
    }

    return () => {
      alive = false
    }
  }, [file.uri, fileType])

  if (imageLoading) {
    return (
      <div className="text-sm text-muted-foreground">
        {t('filePreview.imageLoading')}
      </div>
    )
  }

  if (imageUrl) {
    return (
      <img
        src={imageUrl}
        alt={file.name}
        className="max-h-[70vh] max-w-full rounded-md object-contain outline outline-1 -outline-offset-1 outline-black/10 dark:outline-white/10"
      />
    )
  }

  if (imageSrc) {
    return (
      <div className="space-y-3">
        <img
          src={imageSrc}
          alt={file.name}
          className="max-h-[70vh] max-w-full rounded-md object-contain outline outline-1 -outline-offset-1 outline-black/10 dark:outline-white/10"
          onError={() => setImageError('direct img failed')}
        />
        {imageError ? (
          <div className="text-xs text-muted-foreground">{imageError}</div>
        ) : null}
      </div>
    )
  }

  return (
    <div className="space-y-1 text-sm text-muted-foreground">
      <div>{t('filePreview.imageFailed')}</div>
      {imageError ? <div className="text-xs">{imageError}</div> : null}
    </div>
  )
}
