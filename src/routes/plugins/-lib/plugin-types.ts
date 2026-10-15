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

export type QuadPluginItem = {
  plugin_id: string
  name: string
  version: string
  category: 'platform' | 'user' | 'custom'
  description: string
  skill: SkillItem
  hooks: HookItem[]
  tools: ToolItem[]
  gui: GuiSchema
  health: PluginHealth
}

export type PluginsHealthSummary = {
  total_plugins: number
  healthy_count: number
  degraded_count: number
  unhealthy_count: number
  average_latency_ms: number
  checked_at: number
  overall_status: 'healthy' | 'degraded' | 'unhealthy'
}
