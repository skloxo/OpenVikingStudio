// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

export interface PresetScenario {
  id: string
  name: string
  desc: string
  axiom: string
  version_range: string
  deprecated_patterns: string[]
  forbidden_keywords: string[]
  fragments: Array<{
    uri: string
    content: string
    created_at: number
    embedding?: number[]
  }>
}

export const PRESET_SCENARIOS: PresetScenario[] = [
  {
    id: 'port_lessons_passed',
    name: '5条端口规范碎片 (三门全过)',
    desc: '服务端口收口经验，相似度 0.88，冷却 36h',
    axiom: '对外唯一服务端口物理收口为 1933。',
    version_range: '>= v1.5.00',
    deprecated_patterns: ['独立 1936 端口常驻服务', 'M3 算子硬件强绑定'],
    forbidden_keywords: ['1936', 'mlx-agent'],
    fragments: [
      { uri: 'viking://resources/memory/port_note_1.md', content: 'OpenViking core API port physical binding 1933 note 1', created_at: Date.now() / 1000 - 36 * 3600, embedding: [1.0, 0.8, 0.8, 0.8, 0.0, 0.0, 0.0, 0.0] },
      { uri: 'viking://resources/memory/port_note_2.md', content: 'OpenViking core API port physical binding 1933 note 2', created_at: Date.now() / 1000 - 40 * 3600, embedding: [1.0, 0.82, 0.78, 0.8, 0.0, 0.0, 0.0, 0.0] },
      { uri: 'viking://resources/memory/port_note_3.md', content: 'OpenViking core API port physical binding 1933 note 3', created_at: Date.now() / 1000 - 42 * 3600, embedding: [1.0, 0.79, 0.81, 0.8, 0.0, 0.0, 0.0, 0.0] },
      { uri: 'viking://resources/memory/port_note_4.md', content: 'OpenViking core API port physical binding 1933 note 4', created_at: Date.now() / 1000 - 48 * 3600, embedding: [1.0, 0.81, 0.8, 0.79, 0.0, 0.0, 0.0, 0.0] },
      { uri: 'viking://resources/memory/port_note_5.md', content: 'OpenViking core API port physical binding 1933 note 5', created_at: Date.now() / 1000 - 50 * 3600, embedding: [1.0, 0.8, 0.8, 0.81, 0.0, 0.0, 0.0, 0.0] },
    ],
  },
  {
    id: 'hot_fragments_rejected',
    name: '3条未冷却热碎片 (门禁拦截)',
    desc: '条数不足5条且沉淀仅 2h，触发 Gate 1 与 Gate 3 拦截',
    axiom: '临时会话草稿经验',
    version_range: '>= v1.5.00',
    deprecated_patterns: [],
    forbidden_keywords: [],
    fragments: [
      { uri: 'viking://resources/memory/hot_1.md', content: 'In-flight testing session 1', created_at: Date.now() / 1000 - 2 * 3600, embedding: [1.0, 0.9, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] },
      { uri: 'viking://resources/memory/hot_2.md', content: 'In-flight testing session 2', created_at: Date.now() / 1000 - 2.5 * 3600, embedding: [1.0, 0.88, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] },
      { uri: 'viking://resources/memory/hot_3.md', content: 'In-flight testing session 3', created_at: Date.now() / 1000 - 3 * 3600, embedding: [1.0, 0.91, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] },
    ],
  },
  {
    id: 'diffuse_fragments_rejected',
    name: '5条离散异构碎片 (门禁拦截)',
    desc: '语义离散度过大 (相似度 0.22)，触发 Gate 2 拦截',
    axiom: '离散无规律片段',
    version_range: '>= v1.5.00',
    deprecated_patterns: [],
    forbidden_keywords: [],
    fragments: [
      { uri: 'viking://resources/memory/diff_1.md', content: 'Vector database dimension 4096', created_at: Date.now() / 1000 - 30 * 3600, embedding: [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] },
      { uri: 'viking://resources/memory/diff_2.md', content: 'CSS flexbox centering rules', created_at: Date.now() / 1000 - 32 * 3600, embedding: [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] },
      { uri: 'viking://resources/memory/diff_3.md', content: 'Linux zsh environment setup', created_at: Date.now() / 1000 - 35 * 3600, embedding: [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0] },
      { uri: 'viking://resources/memory/diff_4.md', content: 'FastAPI dependency injection', created_at: Date.now() / 1000 - 36 * 3600, embedding: [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0] },
      { uri: 'viking://resources/memory/diff_5.md', content: 'SQLite WAL mode checkpoint', created_at: Date.now() / 1000 - 40 * 3600, embedding: [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0] },
    ],
  },
]
