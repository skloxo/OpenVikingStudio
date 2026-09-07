/**
 * Task Pipeline Schema (SSOT)
 *
 * 核心哲学：实事求是 —— A就是A，B就是B，不要虚构C。
 * 1. 纯动作型工序 (Action-Only)：成功即展示“已完成”，严禁虚构造假数字 (如 1/1 次、1/1 空间、1/1 快照)；
 * 2. 量化计数型工序 (Metric-Counted)：严格绑定后端物理汇报字段，无数据则展示状态，绝不编造假数字；
 * 3. 按需触发型工序 (On-Demand)：仅当物理产出 > 0 或正在运行时按需呈现，产出为 0 坚决剔除伪工序。
 * 4. 算子可扩展 (Extensible)：未来增加新算子或新引擎，只需在此声明配置，通用引擎自动动态适配。
 */

export interface AtomicStepSpec {
  id: string
  nameZh: string
  nameEn: string
  unitZh?: string
  unitEn?: string
  /** 运行时 stage 关键词匹配 */
  stageKeywords: string[]
  /** 从 result / meta 中提取真实计数候选键 (按优先级降序) */
  metricKeys?: string[]
  /** 从 result / meta 中提取预估总量候选键 (按优先级降序) */
  totalKeys?: string[]
  /** 是否为按需旁路工序：已完成时若指标 <= 0 则彻底剔除伪工序 */
  isOnDemand?: boolean
  /** 是否为纯动作工序：成功时无需造假数字，直接展示状态徽章 */
  isActionOnly?: boolean
  /** 承接该工序的底层引擎 Key */
  engineKey?: string
}

export const ATOMIC_STEP_SPECS: Record<string, AtomicStepSpec> = {
  // 1. 连接鉴权 (纯动作)
  step_auth_handshake: {
    id: 'step_auth_handshake',
    nameZh: '连接鉴权',
    nameEn: 'Auth Handshake',
    stageKeywords: ['auth', 'handshake', 'connect'],
    isActionOnly: true,
    engineKey: 'viking_connectors',
  },
  // 2. 外部拉取 (量化计数)
  step_external_fetch: {
    id: 'step_external_fetch',
    nameZh: '资源拉取',
    nameEn: 'External Fetch',
    unitZh: '篇',
    unitEn: 'docs',
    stageKeywords: ['fetch', 'download', 'pull'],
    metricKeys: ['downloaded_files', 'fetched_docs', 'total_files'],
    engineKey: 'viking_connectors',
  },
  // 3. 文档解析 (量化计数)
  step_parsing: {
    id: 'step_parsing',
    nameZh: '文档解析',
    nameEn: 'Document Parse',
    unitZh: '页',
    unitEn: 'pages',
    stageKeywords: ['parse', 'extract_text', 'ocr'],
    metricKeys: ['parsed_pages', 'total_pages', 'parsed_files', 'scanned_pages'],
    totalKeys: ['total_pages', 'file_count'],
    engineKey: 'external_parse',
  },
  // 4. 语义提炼 (量化计数)
  step_semantic: {
    id: 'step_semantic',
    nameZh: '语义提炼',
    nameEn: 'Semantic Distill',
    unitZh: '篇',
    unitEn: 'docs',
    stageKeywords: ['semantic', 'distill', 'summarize'],
    metricKeys: ['semantic_records', 'scanned_records', 'semantic_nodes', 'total_nodes'],
    totalKeys: ['scanned_records', 'total_nodes'],
    engineKey: 'semantic',
  },
  // 5. 切片重构 / 向量建库 (量化计数)
  step_embedding: {
    id: 'step_embedding',
    nameZh: '切片重构',
    nameEn: 'Vector Embedding',
    unitZh: '切片',
    unitEn: 'chunks',
    stageKeywords: ['vector', 'embed', 'chunk', 'rebuild'],
    metricKeys: ['rebuilt_records', 'reindexed_items', 'processed_chunks', 'embedded_files', 'slices_count', 'embedded_skills'],
    totalKeys: ['rebuilt_records', 'total_chunks'],
    engineKey: 'embedding',
  },
  // 6. 记忆关联 (按需触发)
  step_memory_linking: {
    id: 'step_memory_linking',
    nameZh: '记忆关联',
    nameEn: 'Memory Linking',
    unitZh: '关联',
    unitEn: 'links',
    stageKeywords: ['link', 'relation', 'graph'],
    metricKeys: ['total_links', 'created_relations', 'links_count'],
    isOnDemand: true,
    engineKey: 'knowledge_graph',
  },
  // 7. 悬空修剪 (按需触发)
  step_pruning: {
    id: 'step_pruning',
    nameZh: '悬空修剪',
    nameEn: 'Orphan Pruning',
    unitZh: '切片',
    unitEn: 'chunks',
    stageKeywords: ['prune', 'cleanup', 'orphan'],
    metricKeys: ['deleted_records', 'deleted_chunks', 'pruned_orphans'],
    isOnDemand: true,
    engineKey: 'vector_store',
  },
  // 8. 技能扫描 (量化/状态)
  step_skill_scan: {
    id: 'step_skill_scan',
    nameZh: '技能扫描',
    nameEn: 'Skill Discovery',
    unitZh: '项',
    unitEn: 'skills',
    stageKeywords: ['scan', 'discover', 'find'],
    metricKeys: ['scanned_skills', 'total_skills'],
    engineKey: 'agent_skills',
  },
  // 9. 规范审计 (量化计数)
  step_spec_audit: {
    id: 'step_spec_audit',
    nameZh: '规范审计',
    nameEn: 'Spec Audit',
    unitZh: '技能',
    unitEn: 'skills',
    stageKeywords: ['valid', 'audit', 'spec', 'verify'],
    metricKeys: ['valid_skills', 'audited_skills', 'passed_skills'],
    totalKeys: ['scanned_skills', 'total_skills'],
    engineKey: 'agent_skills',
  },
  // 9.5 技能向量建库 (量化计数)
  step_skill_embedding: {
    id: 'step_skill_embedding',
    nameZh: '向量建库',
    nameEn: 'Skill Embedding',
    unitZh: '技能',
    unitEn: 'skills',
    stageKeywords: ['embed', 'vector', 'skill_embed'],
    metricKeys: ['embedded_skills', 'valid_skills', 'slices_count'],
    totalKeys: ['valid_skills', 'scanned_skills', 'total_skills'],
    engineKey: 'embedding',
  },
  // 10. 会话归档 (量化计数)
  step_session_archive: {
    id: 'step_session_archive',
    nameZh: '对话归档',
    nameEn: 'Dialogue Archive',
    unitZh: '轮',
    unitEn: 'turns',
    stageKeywords: ['archive', 'session', 'turns'],
    metricKeys: ['turns_count', 'turns_processed', 'messages_count'],
    engineKey: 'viking_fs',
  },
  // 11. 经验萃取 (按需触发)
  step_lesson_extraction: {
    id: 'step_lesson_extraction',
    nameZh: '经验萃取',
    nameEn: 'Lesson Distill',
    unitZh: '条经验',
    unitEn: 'lessons',
    stageKeywords: ['lesson', 'extract', 'memory_extract'],
    metricKeys: ['lessons_extracted', 'memories_extracted', 'lessons_count'],
    isOnDemand: true,
    engineKey: 'semantic',
  },
  // 12. 快照提交 (纯动作)
  step_snapshot_commit: {
    id: 'step_snapshot_commit',
    nameZh: '快照提交',
    nameEn: 'Snapshot Commit',
    stageKeywords: ['snapshot', 'commit'],
    isActionOnly: true,
    engineKey: 'viking_fs',
  },
  // 13. 快照回滚 (纯动作)
  step_snapshot_rollback: {
    id: 'step_snapshot_rollback',
    nameZh: '快照回滚',
    nameEn: 'Snapshot Rollback',
    stageKeywords: ['rollback', 'restore_commit'],
    isActionOnly: true,
    engineKey: 'viking_fs',
  },
  // 14. 节点还原 (量化计数)
  step_inode_restore: {
    id: 'step_inode_restore',
    nameZh: '节点还原',
    nameEn: 'Inodes Restore',
    unitZh: '节点',
    unitEn: 'inodes',
    stageKeywords: ['inode', 'restore_nodes', 'file_tree'],
    metricKeys: ['restored_inodes', 'total_inodes'],
    engineKey: 'viking_fs',
  },
  // 15. 标记清理 (纯动作)
  step_soft_mark: {
    id: 'step_soft_mark',
    nameZh: '标记清理',
    nameEn: 'Soft Mark',
    stageKeywords: ['mark', 'soft_delete'],
    isActionOnly: true,
    engineKey: 'viking_fs',
  },
  // 16. 向量注销 (按需触发)
  step_vector_purge: {
    id: 'step_vector_purge',
    nameZh: '向量注销',
    nameEn: 'Vector Purge',
    unitZh: '条',
    unitEn: 'vectors',
    stageKeywords: ['purge', 'vector_delete'],
    metricKeys: ['deleted_vectors', 'purged_vectors'],
    isOnDemand: true,
    engineKey: 'vector_store',
  },
  // 17. 磁盘擦除 (按需触发)
  step_disk_wipe: {
    id: 'step_disk_wipe',
    nameZh: '磁盘擦除',
    nameEn: 'Disk Wipe',
    unitZh: '项',
    unitEn: 'items',
    stageKeywords: ['wipe', 'disk_delete', 'unlink'],
    metricKeys: ['deleted_files', 'wiped_items'],
    isOnDemand: true,
    engineKey: 'viking_fs',
  },
  // 18. 旧版数据读取 (量化计数)
  step_legacy_read: {
    id: 'step_legacy_read',
    nameZh: '旧数据读取',
    nameEn: 'Legacy Read',
    unitZh: '条',
    unitEn: 'records',
    stageKeywords: ['read', 'scan_legacy'],
    metricKeys: ['scanned_count', 'migrated_count'],
    engineKey: 'viking_fs',
  },
  // 19. 格式转换 (量化计数)
  step_schema_transform: {
    id: 'step_schema_transform',
    nameZh: '格式转换',
    nameEn: 'Schema Transform',
    unitZh: '条',
    unitEn: 'records',
    stageKeywords: ['transform', 'convert'],
    metricKeys: ['migrated_count', 'converted_count'],
    engineKey: 'viking_fs',
  },
  // 20. 存储落盘 (量化计数)
  step_viking_write: {
    id: 'step_viking_write',
    nameZh: '存储落盘',
    nameEn: 'Viking Write',
    unitZh: '节点',
    unitEn: 'nodes',
    stageKeywords: ['write', 'flush'],
    metricKeys: ['migrated_count', 'written_nodes'],
    engineKey: 'viking_fs',
  },
  // 21. 图谱遍历 (量化计数)
  step_graph_traverse: {
    id: 'step_graph_traverse',
    nameZh: '图谱遍历',
    nameEn: 'Graph Traverse',
    unitZh: '实体',
    unitEn: 'entities',
    stageKeywords: ['traverse', 'walk'],
    metricKeys: ['cleaned_items', 'traversed_entities'],
    engineKey: 'knowledge_graph',
  },
  // 22. 碎片回收 (按需触发)
  step_orphan_gc: {
    id: 'step_orphan_gc',
    nameZh: '碎片回收',
    nameEn: 'Orphan GC',
    unitZh: '项',
    unitEn: 'items',
    stageKeywords: ['gc', 'collect', 'orphan_clean'],
    metricKeys: ['cleaned_items', 'reclaimed_items'],
    isOnDemand: true,
    engineKey: 'viking_fs',
  },
  // 23. 空间释放 (纯动作)
  step_space_release: {
    id: 'step_space_release',
    nameZh: '空间释放',
    nameEn: 'Space Release',
    stageKeywords: ['free', 'release', 'vacuum'],
    isActionOnly: true,
    engineKey: 'viking_fs',
  },
}

/**
 * 任务类型 -> 候选标准工序流映射 (Task Flow Registry)
 * 每种任务只需声明其物理流动的工序 ID 序列。
 * 后续新增算子或任务，只需在此注册，通用引擎负责全自动自适应求值！
 */
export const TASK_FLOW_REGISTRY: Record<string, string[]> = {
  add_resource: [
    'step_parsing',
    'step_semantic',
    'step_embedding',
    'step_memory_linking',
  ],
  resource_build: [
    'step_parsing',
    'step_semantic',
    'step_embedding',
  ],
  knowledge_pack: [
    'step_parsing',
    'step_semantic',
    'step_embedding',
  ],
  add_skill: [
    'step_skill_scan',
    'step_spec_audit',
    'step_skill_embedding',
  ],
  session_commit: [
    'step_session_archive',
    'step_lesson_extraction',
    'step_snapshot_commit',
  ],
  admin_reindex: [
    'step_semantic',
    'step_embedding',
    'step_pruning',
  ],
  snapshot_restore_reindex: [
    'step_snapshot_rollback',
    'step_inode_restore',
    'step_embedding',
  ],
  connector_import: [
    'step_auth_handshake',
    'step_external_fetch',
    'step_parsing',
    'step_semantic',
    'step_embedding',
  ],
  legacy_migration: [
    'step_legacy_read',
    'step_schema_transform',
    'step_viking_write',
  ],
  legacy_cleanup: [
    'step_graph_traverse',
    'step_orphan_gc',
    'step_space_release',
  ],
  user_delete: [
    'step_soft_mark',
    'step_vector_purge',
    'step_disk_wipe',
  ],
  user_deletion: [
    'step_soft_mark',
    'step_vector_purge',
    'step_disk_wipe',
  ],
}
