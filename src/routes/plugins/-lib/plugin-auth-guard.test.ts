import { describe, expect, it } from 'vitest'
import {
  formatPlugin403Message,
  getPluginPrivilegeStatus,
  isPrivilegedPlugin,
  isPrivilegedTool,
} from './plugin-auth-guard'
import type { ToolItem } from './plugin-types'

describe('Plugin Auth Guard & 403 Privilege Interceptor (Card-144)', () => {
  it('should accurately identify privileged ops plugins', () => {
    expect(isPrivilegedPlugin('openviking-ops')).toBe(true)
    expect(isPrivilegedPlugin('openviking-memory')).toBe(false)
    expect(isPrivilegedPlugin('network-search')).toBe(false)
    expect(isPrivilegedPlugin('keepass-vault')).toBe(false)
    expect(isPrivilegedPlugin('dify')).toBe(false)
  })

  it('should identify privileged tools by category ops or dangerous flag', () => {
    const opsTool: ToolItem = {
      name: 'openviking_server_control',
      description: '服务器进程控制',
      category: 'ops',
      is_dangerous: true,
    }
    const safeTool: ToolItem = {
      name: 'openviking_find',
      description: '记忆检索',
      category: 'memory',
      is_dangerous: false,
    }
    const dangerousTool: ToolItem = {
      name: 'custom_delete',
      description: '高危删除',
      is_dangerous: true,
    }

    expect(isPrivilegedTool(opsTool)).toBe(true)
    expect(isPrivilegedTool(safeTool)).toBe(false)
    expect(isPrivilegedTool(dangerousTool)).toBe(true)
  })

  it('should grant full access to admin or root roles and restrict normal users', () => {
    // Admin 角色拥有全量特权
    const adminCheck = getPluginPrivilegeStatus('admin', 'openviking-ops')
    expect(adminCheck.isAllowed).toBe(true)
    expect(adminCheck.badgeText).toBe('特权已就绪')

    const rootCheck = getPluginPrivilegeStatus('root', 'openviking-ops')
    expect(rootCheck.isAllowed).toBe(true)

    // 普通用户访问普通插件允许，访问特权插件拦截并提示
    const userSafeCheck = getPluginPrivilegeStatus('user', 'openviking-memory')
    expect(userSafeCheck.isAllowed).toBe(true)

    const userOpsCheck = getPluginPrivilegeStatus('user', 'openviking-ops')
    expect(userOpsCheck.isAllowed).toBe(false)
    expect(userOpsCheck.badgeText).toBe('需 Admin 特权')
    expect(userOpsCheck.reason).toContain('当前为普通用户身份（user）')
  })

  it('should format helpful 403 error message with clear guidance', () => {
    const msg = formatPlugin403Message('user', '启停插件')
    expect(msg).toContain('403 特权不足')
    expect(msg).toContain('启停插件')
    expect(msg).toContain('管理员凭据')
  })
})
