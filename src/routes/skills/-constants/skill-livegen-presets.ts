// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

export interface SkillLiveGenPreset {
  id: string
  name: string
  title: string
  description: string
  templateType: 'standard' | 'diagnosis' | 'ui' | 'workflow'
  allowedTools: string[]
  tags: string[]
  sampleQueries: string[]
}

export const SKILL_LIVEGEN_PRESETS: SkillLiveGenPreset[] = [
  {
    id: 'diagnosing-bugs',
    name: 'diagnosing-bugs',
    title: '故障诊断与根因追踪 SOP',
    description: '针对报错、程序崩溃、性能慢、死锁或异常时，自动执行日志提取、红绿测试与根因追踪闭环。',
    templateType: 'diagnosis',
    allowedTools: ['run_command', 'view_file', 'grep_search'],
    tags: ['diagnosis', 'debug', 'sop'],
    sampleQueries: [
      '接口报错 500 且抛出数据库死锁异常，请排查',
      '程序崩了，内存不断泄露如何定位？',
      '帮我看看今天的天气预报',
    ],
  },
  {
    id: 'cockpit-ui',
    name: 'cockpit-ui',
    title: '座舱级高密性冷淡设计体系',
    description: '遵循 NO GREEN EVER 🚫、字号 >=12px、等宽数字与座舱最高信息密度律的前端开发与重构规范。',
    templateType: 'ui',
    allowedTools: ['view_file', 'replace_file_content', 'multi_replace_file_content'],
    tags: ['ui', 'cockpit', 'frontend'],
    sampleQueries: [
      '开发一个高密度的系统 CPU/RAM 监控座舱卡片',
      '重构表格页面视觉，消除绿色并应用冰青强调色',
      '重启远程 3070 节点服务器',
    ],
  },
  {
    id: 'auto-pr',
    name: 'auto-pr',
    title: 'Git PR 全自动闭环处理 SOP',
    description: '自动执行前后端双轨 PR 拆分、冲突消解、单元测试 (pytest) + 构建双全门禁、Tag 锚定与留痕闭环。',
    templateType: 'workflow',
    allowedTools: ['run_command', 'view_file'],
    tags: ['git', 'automation', 'pr'],
    sampleQueries: [
      '发 PR 并自动运行单元测试与构建门禁验证',
      '解决当前分支与 main 分支的 Git 合并冲突',
      '备份当前 SQLite 数据库文件',
    ],
  },
]
