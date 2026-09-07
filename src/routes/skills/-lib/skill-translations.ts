import type { SkillScope } from './skill-types'

// 技能常见英文名 ➔ 信达雅地道中文自解释映射
export const CHINESE_SKILL_NAME_MAP: Record<string, string> = {
  'master-dev': '顶级通用代码开发与项目迭代总控',
  'auto-pr': 'Git PR 自动化闭环处理 SOP',
  'diagnosing-bugs': 'Bug 诊断与性能排查闭环',
  'tdd': '测试驱动开发 (红绿重构)',
  'codebase-design': '深度模块设计与 Seam 建模',
  'domain-modeling': '领域建模与统一语言',
  'code-review': '代码审查规范 Spec 双轴核验',
  'to-spec': '需求规格化与 Spec 沉淀',
  'to-tickets': 'Tracer Bullet 细粒度工单拆解',
  'research': '一手官方文档技术调研',
  'prototype': '快速原型验证与探索',
  'improve-codebase-architecture': '架构扫描与深度重构建议',
  'triage': '工单分流与状态机推进',
  'wayfinder': '宏大工程路线图规划',
  'grill-me': '深度需求拷问与设计对齐',
  'grill-with-docs': '文档驱动型架构拷问与 ADR 沉淀',
  'implement': '基于 Spec 的功能标准实现',
  'resolving-merge-conflicts': 'Git 分支合并冲突消除',
  'setup-matt-pocock-skills': 'Matt Pocock 工程技能套件配置',
  'ask-matt': '工程技能智能路由与导航',
  'openviking-master': 'OpenViking 体外大脑中枢开发总控',
  'openviking-memory-benchmark': 'OpenViking 记忆中枢基准测试与遥测',
  'mac-studio-remote-ops': 'Mac Studio 远程运维与 MLX 算力编排',
  'tide-trading-dev': 'TideTrading 量化交易系统开发',
  'antigravity-guide': 'Antigravity IDE 官方开发指南',
  'agy-customizations': 'Antigravity 自定义技能与规则开发',
  'auto-job-hunter': '自动化职位检索与简历匹配',
  'a-share-risk-alert': 'A股风险监控与实时预警',
  'company-creator': '企业信息画像与知识图谱生成',
  'electron-proxy-windows': 'Windows Electron 代理网络分流',
  'memory-index-fallback-chain': '记忆索引多级降级链',
  'openclaw-docs': 'OpenClaw 架构规范与开发文档',
  'stock-rt-subscribe': '股票实时行情与量化订阅',
  'skill-creator': '技能资产自动创建与规约提取',
  'skill-governance': '技能资产治理规范与定期审查',
  'hermes-config-audit': 'Hermes 运行时配置自检与优化',
  'repo-tracker': 'Git 仓库代码变动与演进跟踪',
}

export const ENGINEERING_SKILLS = [
  'master-dev',
  'auto-pr',
  'diagnosing-bugs',
  'tdd',
  'codebase-design',
  'domain-modeling',
  'code-review',
  'to-spec',
  'to-tickets',
  'research',
  'prototype',
  'improve-codebase-architecture',
  'triage',
  'wayfinder',
  'grill-me',
  'grill-with-docs',
  'implement',
  'resolving-merge-conflicts',
  'setup-matt-pocock-skills',
  'ask-matt',
  'openviking-master',
  'openviking-memory-benchmark',
  'mac-studio-remote-ops',
  'tide-trading-dev',
  'antigravity-guide',
  'agy-customizations',
  'skill-creator',
  'skill-governance',
  'hermes-config-audit',
  'repo-tracker',
]

export function isEngineeringSkill(name: string, source?: string): boolean {
  return (
    ENGINEERING_SKILLS.includes(name) ||
    source === 'Antigravity' ||
    name.includes('openviking') ||
    name.includes('antigravity') ||
    name.includes('dev') ||
    name.includes('audit')
  )
}

export function isDataSkill(name: string): boolean {
  return (
    name.startsWith('sn-') ||
    name.includes('chart') ||
    name.includes('excel') ||
    name.includes('statistics') ||
    name.includes('analysis') ||
    name.includes('filtering') ||
    name.includes('coloring') ||
    name.includes('reading') ||
    name.includes('export')
  )
}

export function getChineseSkillName(name: string): string {
  return CHINESE_SKILL_NAME_MAP[name] || name
}

export function getChineseSkillDescription(rawDesc: string): string {
  if (
    !rawDesc ||
    rawDesc.includes('用于自动化处理') ||
    rawDesc.includes('业务逻辑的标准工程规约')
  ) {
    return '暂无额外说明'
  }
  return rawDesc
}

export function getSkillSource(
  name: string,
  scope?: SkillScope,
  source?: string,
): { label: string; badgeClass: string } {
  if (source === 'system' || isEngineeringSkill(name, source)) {
    return {
      badgeClass:
        'border-cyan-500/30 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 font-medium',
      label: '工程研发',
    }
  }
  if (scope === 'agent' || name.startsWith('a-share') || name.startsWith('stock') || name.startsWith('auto-job')) {
    return {
      badgeClass: 'border-border bg-muted/40 text-foreground',
      label: '智能体',
    }
  }
  if (isDataSkill(name)) {
    return {
      badgeClass: 'border-border bg-muted/30 text-foreground',
      label: '数据办公',
    }
  }
  return {
    badgeClass: 'border-border bg-muted/30 text-foreground',
    label: '个人偏好',
  }
}

export function getFallbackSkillContent(name: string, description: string): string {
  const cnName = CHINESE_SKILL_NAME_MAP[name] || name
  return `---
name: ${name}
description: "${description || '暂无自然语言意图描述'}"
---

# ${cnName} (${name})

## 🎯 技能意图感应与适用场景
${description || '自动侦测用户自然语言意图并静默唤醒执行。'}

## 📋 极客 SOP 规范流程
1. **意图诊断**: 自动抓取与分析上下文环境中的工程依赖及配置文件；
2. **规范执行**: 依照 OpenViking 标准准则与约束，进行高内聚低耦合的落地处理；
3. **闭环交付**: 自动发起单元测试与构建验证，确保零逻辑瑕疵。
`
}
