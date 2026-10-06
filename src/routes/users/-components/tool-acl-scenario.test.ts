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

  it('should categorize 21 tools into satellite scenario, 13 into core_master, and 13 into cluster_ops', () => {
    expect(SATELLITE_TOOL_IDS.length).toBe(21)
    expect(CORE_MASTER_TOOL_IDS.length).toBe(34) // satellite (21) + core_master (13)

    const satelliteCat = TOOL_CATEGORIES.find((c) => c.id === 'satellite')
    expect(satelliteCat?.tools.length).toBe(21)
    // 验证新纳入卫星组的一线战地核心工具
    const satIds = satelliteCat?.tools.map((t) => t.id) ?? []
    expect(satIds).toContain('openviking_code_impact')
    expect(satIds).toContain('openviking_tokenshift_compress')
    expect(satIds).toContain('openviking_context_route')
    expect(satIds).toContain('openviking_skill_validate')
    expect(satIds).toContain('openviking_skill_publish')
    expect(satIds).toContain('openviking_privacy_mask')

    const coreCat = TOOL_CATEGORIES.find((c) => c.id === 'core_master')
    expect(coreCat?.tools.length).toBe(13)

    const opsCat = TOOL_CATEGORIES.find((c) => c.id === 'cluster_ops')
    expect(opsCat?.tools.length).toBe(13)
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

    const maskTool = satelliteCat.tools.find((t) => t.id === 'openviking_privacy_mask')!
    expect(maskTool.requiredRole).toBeUndefined()
    expect(isToolDisabledByRole(maskTool, 'user')).toBe(false)
    expect(isToolDisabledByRole(maskTool, 'admin')).toBe(false)
    expect(isToolDisabledByRole(maskTool, 'root')).toBe(false)
  })
})
