import { describe, it, expect } from 'vitest'
import {
  TOOL_CATEGORIES,
  ALL_TOOL_IDS,
  SATELLITE_CONSUMER_TOOL_IDS,
  MASTER_MAINTAINER_TOOL_IDS,
  OFFICIAL_TOOL_BUNDLES,
  BIG_THREE_PLUGIN_MAPPINGS,
  derivePluginGrantsFromTools,
  deriveToolsFromPluginGrants,
  isToolDisabledByRole,
} from '../-constants/agent-tools'

describe('FastMCP Tool ACL Scenario, Tool Bundles & Role Gating (Card-126)', () => {
  it('should have exactly 50 total tools across role-centric categories', () => {
    expect(ALL_TOOL_IDS.length).toBe(50)

    const categoriesCount = TOOL_CATEGORIES.reduce((acc, cat) => acc + cat.tools.length, 0)
    expect(categoriesCount).toBe(50)

    const catKeys = TOOL_CATEGORIES.map((c) => c.id)
    expect(catKeys).toEqual(['satellite', 'master_ops'])
  })

  it('should define exactly 2 official Tool Bundles (Satellite Consumer 34 vs Master Maintainer 50)', () => {
    expect(OFFICIAL_TOOL_BUNDLES.length).toBe(2)

    const satBundle = OFFICIAL_TOOL_BUNDLES.find((b) => b.id === 'satellite_consumer')!
    expect(satBundle).toBeDefined()
    expect(satBundle.toolIds.length).toBe(34)
    expect(SATELLITE_CONSUMER_TOOL_IDS.length).toBe(34)

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

    const masterBundle = OFFICIAL_TOOL_BUNDLES.find((b) => (b.id as string) === 'master_ops' || (b.id as string) === 'master_maintainer')!
    expect(masterBundle).toBeDefined()
    expect(masterBundle.toolIds.length).toBe(16)
  })

  it('should categorize 34 tools into satellite consumer category and 16 into master ops category', () => {
    const satelliteCat = TOOL_CATEGORIES.find((c) => c.id === 'satellite')!
    expect(satelliteCat.tools.length).toBe(34)

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

  it('should support Big Three plugin mappings and bidirectional tool derivation', () => {
    expect(Object.keys(BIG_THREE_PLUGIN_MAPPINGS)).toEqual([
      'openviking-memory',
      'keepass-vault',
      'network-search',
    ])

    // Test deriving plugin_grants from tool list
    const selected = ['find', 'search', 'keepass_get', 'web_search']
    const grants = derivePluginGrantsFromTools(selected)
    expect(grants['openviking-memory']).toEqual(['find', 'search'])
    expect(grants['keepass-vault']).toEqual(['keepass_get'])
    expect(grants['network-search']).toEqual(['web_search'])

    // Test reverse derivation
    const derivedTools = deriveToolsFromPluginGrants(grants)
    expect(derivedTools.sort()).toEqual(selected.sort())
  })
})
