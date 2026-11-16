import type { VikingFsEntry } from '#/routes/resources/-types/viking-fm'

export type JsonSchema = {
  $defs?: Record<string, JsonSchema>
  definitions?: Record<string, JsonSchema>
  $ref?: string
  type?: string | string[]
  title?: string
  description?: string
  default?: unknown
  enum?: unknown[]
  properties?: Record<string, JsonSchema>
  required?: string[]
  items?: JsonSchema | JsonSchema[]
  additionalProperties?: boolean | JsonSchema
  anyOf?: JsonSchema[]
  oneOf?: JsonSchema[]
  allOf?: JsonSchema[]
  minimum?: number
  maximum?: number
  minLength?: number
  maxLength?: number
}

export type McpServerInfo = {
  name: string
  root_uri: string
}

export type McpToolDefinition = {
  name: string
  title?: string
  description?: string
  inputSchema: JsonSchema
  annotations?: Record<string, unknown>
}

export type McpCatalogTool = {
  server: string
  uri: string
  revision: string
  input_revision: string
  tool: McpToolDefinition
}

export type McpCatalogServer = McpServerInfo & {
  tools: McpCatalogTool[]
}

export type McpCatalog = {
  complete: boolean
  error?: string
  servers: McpCatalogServer[]
  tools: McpCatalogTool[]
}

export type LiveContextMount = {
  node_uri: string
  tool_uri: string
  title: string
  description?: string | null
  timeout_seconds: number
  arguments: Record<string, unknown>
  tags?: string[]
  mcp?: string
  tool?: string
  updated_at?: string
}

export type LiveMountIndex = {
  complete: boolean
  error?: string
  mounts: Map<string, LiveContextMount>
}

export type MountInput = {
  node_uri: string
  tool_uri: string
  title: string
  description?: string
  timeout_seconds: number
  arguments: Record<string, unknown>
  tags?: string[]
}

export type LoadedDirectory = {
  entries: VikingFsEntry[]
  hasMore: boolean
  nextOffset: number
}

export type TextDocument = {
  bytes: Uint8Array
  content: string
  sha256: string
}

export type MutationKind = 'copy' | 'delete'

export type BatchLiveContextResult = {
  total: number
  succeeded: string[]
  failed: Array<{
    node_uri: string
    code: string
    message: string
    applied: boolean
  }>
  not_attempted: string[]
}
