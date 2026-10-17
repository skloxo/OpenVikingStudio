/**
 * upload-processors.ts
 * 负责本地文件临时切片上传与远程 Git / URL 资源提交的底层网络请求执行器。
 */
import {
  getOvResult,
  postResources,
  postResourcesTempUpload,
} from '#/lib/ov-client'
import type {
  AddResourceResult,
  TempUploadResult,
} from '@ov-server/api/v1/resources'
import type { UploadBatchItem } from './resource-upload-types'
import { isRecord } from './resource-upload-utils'

export type UploadExecutionResult = {
  rootUri: string | null
  serverTaskId: string | null
}

export type RemoteExecutionResult = {
  rootUri: string | null
  serverTaskId: string | null
  warnings: string[]
}

export async function executeTempFileUpload(
  item: UploadBatchItem,
  commonBody: Record<string, unknown>,
  onProgress?: (progress: number) => void,
): Promise<UploadExecutionResult> {
  const uploadResult = await getOvResult<TempUploadResult>(
    postResourcesTempUpload({
      body: {
        file: item.file,
        telemetry: true,
      },
      onUploadProgress: (event: { loaded: number; total?: number }) => {
        const total = event.total
        if (!total) return
        onProgress?.(Math.round((event.loaded / total) * 100))
      },
    }),
  )

  const tempFileId = isRecord(uploadResult)
    ? uploadResult.temp_file_id
    : undefined
  if (typeof tempFileId !== 'string' || !tempFileId.trim()) {
    throw new Error('Temp upload did not return temp_file_id.')
  }

  const addResult = await getOvResult<AddResourceResult>(
    postResources({
      body: {
        ...commonBody,
        temp_file_id: tempFileId,
        source_name: item.file.name,
      } as Parameters<typeof postResources>[0]['body'],
    }),
  )

  if (addResult.status === 'error') {
    const errors = Array.isArray(addResult.errors) ? addResult.errors : []
    throw new Error(errors.join('; ') || 'Processing failed')
  }

  const rootUri =
    typeof addResult.root_uri === 'string' ? addResult.root_uri : null
  const serverTaskId =
    typeof addResult.task_id === 'string' && addResult.task_id.trim()
      ? addResult.task_id
      : null

  return { rootUri, serverTaskId }
}

export async function executeRemoteUpload(
  url: string,
  commonBody: Record<string, unknown>,
  signal: AbortSignal,
): Promise<RemoteExecutionResult> {
  const result = await getOvResult<AddResourceResult>(
    postResources({
      body: {
        ...commonBody,
        path: url,
      } as Parameters<typeof postResources>[0]['body'],
      signal,
    }),
  )

  if (result.status === 'error') {
    const errors = Array.isArray(result.errors) ? result.errors : []
    throw new Error(errors.join('; ') || 'Processing failed')
  }

  const warnings = Array.isArray(result.warnings) ? result.warnings : []
  const rootUri = typeof result.root_uri === 'string' ? result.root_uri : null
  const serverTaskId =
    typeof result.task_id === 'string' && result.task_id.trim()
      ? result.task_id
      : null

  return { rootUri, serverTaskId, warnings }
}
