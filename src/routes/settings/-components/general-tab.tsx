import * as React from 'react'
import { useQuery } from '@tanstack/react-query'

import { useAppConnection } from '#/hooks/use-app-connection'
import { ovClient } from '#/lib/ov-client'
import { parseObserverModelsTable } from '../-lib/settings-types'
import { ConnectionCard } from './general/connection-card'
import { ModelsPanoramaCard } from './general/models-panorama-card'
import { WorkspaceStorageCard } from './general/workspace-storage-card'

export function GeneralTab() {
  const { connection } = useAppConnection()

  const modelsQuery = useQuery({
    enabled: Boolean(connection.baseUrl),
    queryFn: async () => {
      try {
        const res = await ovClient.instance.get<{
          status: string
          result?: {
            name: string
            is_healthy: boolean
            status: string
          }
        }>('/api/v1/observer/models')
        return res.data?.result ?? null
      } catch {
        return null
      }
    },
    queryKey: [
      'system-observer-models',
      connection.baseUrl,
      connection.adminApiKey,
      connection.apiKey,
    ],
    staleTime: 15_000,
  })

  const workspaceQuery = useQuery({
    enabled: Boolean(connection.baseUrl),
    queryFn: async () => {
      try {
        const res = await ovClient.instance.get<{
          status: string
          result?: {
            effective?: {
              resource_uri?: string
              skill_uri?: string
            }
          }
        }>('/api/v1/user-settings/add-locations')
        return res.data?.result ?? null
      } catch {
        return null
      }
    },
    queryKey: [
      'user-settings-add-locations',
      connection.baseUrl,
      connection.adminApiKey,
      connection.apiKey,
    ],
    staleTime: 30_000,
  })

  const parsedModels = React.useMemo(
    () => parseObserverModelsTable(modelsQuery.data?.status),
    [modelsQuery.data?.status],
  )

  const activeVlm =
    parsedModels.vlm.find((m) => m.model === 'qwen3.8-flash-next') ||
    parsedModels.vlm.find((m) => Number(m.calls) > 0) ||
    parsedModels.vlm[0]

  const activeEmbedding =
    parsedModels.embedding.find((m) => Number(m.calls) > 0) ||
    parsedModels.embedding[0]

  const activeRerank =
    parsedModels.rerank.find((m) => Number(m.calls) > 0) ||
    parsedModels.rerank[0]

  const activeCompressor = parsedModels.compressor[0]

  const handleRecheckAll = () => {
    void modelsQuery.refetch()
    void workspaceQuery.refetch()
  }

  return (
    <div className="space-y-4">
      <ConnectionCard
        onRecheckAll={handleRecheckAll}
        isRechecking={modelsQuery.isFetching || workspaceQuery.isFetching}
      />
      <ModelsPanoramaCard
        activeVlm={activeVlm}
        activeEmbedding={activeEmbedding}
        activeRerank={activeRerank}
        activeCompressor={activeCompressor}
      />
      <WorkspaceStorageCard
        resourceUri={workspaceQuery.data?.effective?.resource_uri}
        skillUri={workspaceQuery.data?.effective?.skill_uri}
      />
    </div>
  )
}
