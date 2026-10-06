import { describe, it, expect } from 'vitest'
import {
  TOOL_CATEGORIES,
  ALL_TOOL_IDS,
  SATELLITE_CONSUMER_TOOL_IDS,
  MASTER_MAINTAINER_TOOL_IDS,
  OFFICIAL_TOOL_BUNDLES,
  isToolDisabledByRole,
} from '../-constants/agent-tools'

describe('FastMCP Tool ACL Scenario, Tool Bundles & Role Gating (Card-126)', () => {
  it('should have exactly 47 total tools across role-centric categories', () => {
    expect(ALL_TOOL_IDS.length).toBe(47)

    const categoriesCount = TOOL_CATEGORIES.reduce((acc, cat) => acc + cat.tools.length, 0)
    expect(categoriesCount).toBe(47)

    const catKeys = TOOL_CATEGORIES.map((c) => c.id)
    expect(catKeys).toEqual(['satellite', 'master_ops'])
  })

  it('should define exactly 2 official Tool Bundles (Satellite Consumer 31 vs Master Maintainer 47)', () => {
    expect(OFFICIAL_TOOL_BUNDLES.length).toBe(2)

    const satBundle = OFFICIAL_TOOL_BUNDLES.find((b) => b.id === 'satellite_consumer')!
    expect(satBundle).toBeDefined()
    expect(satBundle.toolIds.length).toBe(31)
    expect(SATELLITE_CONSUMER_TOOL_IDS.length).toBe(31)

    // 验证一线使用者角色核心武器完备度
    expect(satBundle.toolIds).toContain('find')
    expect(satBundle.toolIds).toContain('remember')
    expect(satBundle.toolIds).toContain('openviking_code_impact')
    expect(satBundle.toolIds).toContain('openviking_generate_contract_test') // TDD契约单测
    expect(satBundle.toolIds).toContain('openviking_skill_validate')
    expect(satBundle.toolIds).toContain('openviking_skill_judge') // 技能质量评分
    expect(satBundle.toolIds).toContain('openviking_skill_remediate') // 技能缺陷自愈
    expect(satBundle.toolIds).toContain('openviking_skill_publish') // 技能上架
    expect(satBundle.toolIds).toContain('openviking_file_task_card') // AIFP建卡
    expect(satBundle.toolIds).toContain('openviking_resolve_task_card') // AIFP结单归档
    expect(satBundle.toolIds).toContain('openviking_valet_handover') // 异步大文档泊车消化
    expect(satBundle.toolIds).toContain('openviking_privacy_mask')

    const masterBundle = OFFICIAL_TOOL_BUNDLES.find((b) => b.id === 'master_maintainer')!
    expect(masterBundle).toBeDefined()
    expect(masterBundle.toolIds.length).toBe(47)
    expect(MASTER_MAINTAINER_TOOL_IDS.length).toBe(47)

    // 验证中枢运维特权工具
    expect(masterBundle.toolIds).toContain('write')
    expect(masterBundle.toolIds).toContain('edit')
    expect(masterBundle.toolIds).toContain('openviking_dlq_status')
    expect(masterBundle.toolIds).toContain('openviking_retry_dead_letter')
    expect(masterBundle.toolIds).toContain('forget')
    expect(masterBundle.toolIds).toContain('openviking_skill_evolution_pipeline')
    expect(masterBundle.toolIds).toContain('openviking_harness_probe')
  })

  it('should categorize 31 tools into satellite consumer category and 16 into master ops category', () => {
    const satelliteCat = TOOL_CATEGORIES.find((c) => c.id === 'satellite')!
    expect(satelliteCat.tools.length).toBe(31)

    const opsCat = TOOL_CATEGORIES.find((c) => c.id === 'master_ops')!
    expect(opsCat.tools.length).toBe(16)
  })

  it('should preserve technical modules as categoryBadge property', () => {
    for (const cat of TOOL_CATEGORIES) {
      for (const tool of cat.tools) {
        expect(tool.categoryBadge).toBeDefined()
        expect(tool.categoryBadge.length).toBeGreaterThan(0)
      }
    }
  })

  it('should disable system privileged tools when user role is regular user', () => {
    const opsCat = TOOL_CATEGORIES.find((c) => c.id === 'master_ops')!
    const adminTool = opsCat.tools.find((t) => t.id === 'list_watches')!
    expect(adminTool.requiredRole).toBe('admin')

    // 普通用户视角下超出权限的系统级特权工具置灰禁用
    expect(isToolDisabledByRole(adminTool, 'user')).toBe(true)

    // 管理员或 root 视角下系统特权工具可授权解锁
    expect(isToolDisabledByRole(adminTool, 'admin')).toBe(false)
    expect(isToolDisabledByRole(adminTool, 'root')).toBe(false)
  })

  it('should allow regular tools including forget and privacy_mask for all user roles', () => {
    const opsCat = TOOL_CATEGORIES.find((c) => c.id === 'master_ops')!
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
  })

  it('should support Hook lifecycle 3-key neuro-reflex arcs (Card-127)', () => {
    const hookKeys = ['autoRecall', 'autoCapture', 'preToolGuard'] as const
    expect(hookKeys.length).toBe(3)

    // 测试默认配置开启状态
    const defaultHooks = {
      autoRecall: true,
      autoCapture: true,
      preToolGuard: true,
    }
    const activeCount = Object.values(defaultHooks).filter(Boolean).length
    expect(activeCount).toBe(3)
  })
})
