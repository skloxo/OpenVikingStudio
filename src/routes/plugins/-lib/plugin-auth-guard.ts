/**
 * plugin-auth-guard.ts
 * 插件中心权限守卫、非 Admin 特权拦截与 403 友好告警中枢 (Card-144)。
 *
 * 核心契约 (第一性原理)：
 * 1. 严格区隔普通业务身份 (user) 与平台特权身份 (admin/root)；
 * 2. 对特权插件 (openviking-ops) 与高危运维工具 (category === 'ops' | is_dangerous) 实施前置只读保护；
 * 3. 杜绝静默失败与死弹窗：统一拦截并输出友好气泡，明确引导用户切换管理账号；
 * 4. 严守黄金甜点区 (<= 150 行)。
 */

import { toast } from 'sonner'
import type { ConnectionRole } from '#/hooks/app-connection-types'
import type { ToolItem } from './plugin-types'

/**
 * 特权运维插件 ID 集合 (SSOT)
 */
export const PRIVILEGED_PLUGIN_IDS = new Set<string>([
  'openviking-ops',
])

/**
 * 判定目标插件是否属于特权运维插件
 */
export function isPrivilegedPlugin(pluginId: string): boolean {
  if (!pluginId) return false
  return PRIVILEGED_PLUGIN_IDS.has(pluginId.toLowerCase().trim())
}

/**
 * 判定目标工具是否属于特权运维或高危操作工具
 */
export function isPrivilegedTool(tool: ToolItem): boolean {
  if (!tool) return false
  return tool.category === 'ops' || Boolean(tool.is_dangerous)
}

export type PluginPrivilegeCheckResult = {
  isAllowed: boolean
  badgeText: string
  reason?: string
}

/**
 * 根据当前连接身份与目标插件，计算权限可用性与展示状态
 */
export function getPluginPrivilegeStatus(
  role: ConnectionRole,
  pluginId: string,
): PluginPrivilegeCheckResult {
  const isPrivileged = isPrivilegedPlugin(pluginId)

  // 管理员或根用户拥有全部特权
  if (role === 'admin' || role === 'root') {
    return {
      isAllowed: true,
      badgeText: isPrivileged ? '特权已就绪' : '可用',
    }
  }

  // 普通用户或未知身份访问特权插件：受限
  if (isPrivileged) {
    return {
      isAllowed: false,
      badgeText: '需 Admin 特权',
      reason: `当前为普通用户身份（${role || 'user'}），该插件属于平台特权运维能力（openviking-ops），需要管理员特权（Admin）方可配置或执行。`,
    }
  }

  // 普通插件对普通用户开放
  return {
    isAllowed: true,
    badgeText: '可用',
  }
}

/**
 * 格式化高密友好的 403 特权不足告警文案
 */
export function formatPlugin403Message(
  role: ConnectionRole,
  operation = '该操作',
): string {
  const roleName = role === 'user' ? '普通用户身份 (user)' : `身份 (${role || '未授权'})`
  return `403 特权不足：当前为${roleName}，无法执行${operation}。特权运维与高危指令受保护，请切换至管理员凭据或向管理员申请权限。`
}

/**
 * 统一触发 403 友好拦截气泡提示
 */
export function notifyPlugin403(
  role: ConnectionRole,
  operation = '特权操作',
): void {
  const message = formatPlugin403Message(role, operation)
  toast.warning(message, {
    duration: 5000,
    action: {
      label: '了解',
      onClick: () => {},
    },
  })
}
