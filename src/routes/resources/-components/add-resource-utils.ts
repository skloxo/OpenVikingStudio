import { fileTypeFromBlob } from 'file-type'

export type Mode = 'upload' | 'remote'

export type SelectedUploadFile = {
  id: string
  file: File
  fileType: string | null
}

export function createLocalFileId(): string {
  if (
    typeof crypto !== 'undefined' &&
    typeof crypto.randomUUID === 'function'
  ) {
    return crypto.randomUUID()
  }
  return `local-file-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

export async function detectFileType(file: File): Promise<string | null> {
  try {
    const result = await fileTypeFromBlob(file)
    return result?.mime ?? null
  } catch {
    return null
  }
}
