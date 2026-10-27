/**
 * plugin-types.ts
 * 插件中心强类型 DTO 与视图类型定义 (SSOT)。
 */

export type ToolItem = {
  name: string
  description: string
  category: string
  is_dangerous: boolean
}

export type HookItem = {
  hook_id: string
  name: string
  trigger_event: string
  description: string
}

export type SkillItem = {
  skill_id: string
  name: string
  description: string
  sop_summary: string
  rules: string[]
}

export type GuiSchema = {
  settings_fields: Record<string, any>
  dashboard_route: string
}

export type PluginHealth = {
  status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown'
  latency_ms: number
  message: string
  checked_at: number
}

export type RuleItem = {
  name: string
  description?: string
  content: string
}

export type QuadPluginItem = {
  plugin_id: string
  name: string
  version: string
  category: 'platform' | 'user' | 'custom'
  archetype?: 'local-offline' | 'server-backed' | 'hybrid-gateway'
  description: string
  readme_content?: string
  author?: string
  homepage?: string
  license?: string
  tags?: string[]
  suggested_prompts?: string[]
  skill: SkillItem
  skills?: SkillItem[]
  rules?: RuleItem[]
  hooks: HookItem[]
  tools: ToolItem[]
  gui: GuiSchema
  health: PluginHealth
  integration?: IntegrationDefinition
}

export type IntegrationChannel = {
  id: string
  name: string
  install_cmd?: string
  config_snippet?: string
  docs_markdown?: string
  agent_prompt?: string
}

export type IntegrationDefinition = {
  channels: IntegrationChannel[]
}



export type PluginsHealthSummary = {
  total_count: number
  healthy_count: number
  healthy_rate: number
  average_latency_ms: number
  overall_status: 'healthy' | 'degraded' | 'down' | 'unhealthy'
  probes: Record<string, PluginHealth>
}

export type DshPluginBridgeInfo = {
  pkg: string
  ver: string
}

export type DshPackageMapping = Record<string, DshPluginBridgeInfo>

export type QuickstartCommandItem = {
  id: string
  title: string
  command: string
  copyLabel: string
  iconType?: 'laptop' | 'terminal' | 'cube'
  badge?: string
}
