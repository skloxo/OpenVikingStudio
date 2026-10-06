import { describe, it, expect } from 'vitest'
import {
  TOOL_CATEGORIES,
  ALL_TOOL_IDS,
  SATELLITE_TOOL_IDS,
  CORE_MASTER_TOOL_IDS,
  isToolDisabledByRole,
} from '../-constants/agent-tools'

describe('FastMCP Tool ACL Scenario & Role Gating (Card-122)', () => {
  it('should have exactly 47 total tools across user-centric scenario categories', () => {
    expect(ALL_TOOL_IDS.length).toBe(47)

    const categoriesCount = TOOL_CATEGORIES.reduce((acc, cat) => acc + cat.tools.length, 0)
    expect(categoriesCount).toBe(47)

    // 确保 3 大用户使用场景定义完整
    const catKeys = TOOL_CATEGORIES.map((c) => c.id)
    expect(catKeys).toEqual(['satellite', 'core_master', 'cluster_ops'])
  })

  it('should categorize 15 tools into satellite scenario and 17 into core_master', () => {
    expect(SATELLITE_TOOL_IDS.length).toBe(15)
    expect(CORE_MASTER_TOOL_IDS.length).toBe(32) // satellite (15) + core_master (17)

    const satelliteCat = TOOL_CATEGORIES.find((c) => c.id === 'satellite')
    expect(satelliteCat?.tools.length).toBe(15)

    const coreCat = TOOL_CATEGORIES.find((c) => c.id === 'core_master')
    expect(coreCat?.tools.length).toBe(17)

    const opsCat = TOOL_CATEGORIES.find((c) => c.id === 'cluster_ops')
    expect(opsCat?.tools.length).toBe(15)
  })

  it('should preserve original technical modules as categoryBadge property', () => {
    for (const cat of TOOL_CATEGORIES) {
      for (const tool of cat.tools) {
        expect(tool.categoryBadge).toBeDefined()
        expect(tool.categoryBadge.length).toBeGreaterThan(0)
      }
    }
  })

  it('should disable system privileged tools when user role is regular user', () => {
    const opsCat = TOOL_CATEGORIES.find((c) => c.id === 'cluster_ops')!
    const adminTool = opsCat.tools.find((t) => t.id === 'list_watches')!
    expect(adminTool.requiredRole).toBe('admin')

    // 普通用户视角下超出权限的系统级特权工具置灰禁用
    expect(isToolDisabledByRole(adminTool, 'user')).toBe(true)

    // 管理员或 root 视角下系统特权工具可授权解锁
    expect(isToolDisabledByRole(adminTool, 'admin')).toBe(false)
    expect(isToolDisabledByRole(adminTool, 'root')).toBe(false)
  })

  it('should allow regular tools including forget and privacy_mask for all user roles', () => {
    const opsCat = TOOL_CATEGORIES.find((c) => c.id === 'cluster_ops')!
    const forgetTool = opsCat.tools.find((t) => t.id === 'forget')!
    expect(forgetTool.requiredRole).toBeUndefined()
    expect(isToolDisabledByRole(forgetTool, 'user')).toBe(false)

    const satelliteCat = TOOL_CATEGORIES.find((c) => c.id === 'satellite')!
    const findTool = satelliteCat.tools.find((t) => t.id === 'find')!
    expect(findTool.requiredRole).toBeUndefined()

    expect(isToolDisabledByRole(findTool, 'user')).toBe(false)
    expect(isToolDisabledByRole(findTool, 'admin')).toBe(false)
    expect(isToolDisabledByRole(findTool, 'root')).toBe(false)
  })
})
