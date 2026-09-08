import { CORE_PANORAMA_STEPS } from './panorama-steps-core'
import { ENTROPY_PANORAMA_STEPS } from './panorama-steps-entropy'

export interface PanoramaStepDef {
  id: string
  nameZh: string
  nameEn: string
  engineKey:
    | 'AddResource'
    | 'ExternalParse'
    | 'Semantic'
    | 'Semantic-Nodes'
    | 'Embedding'
    | 'SessionCommit'
    | 'UserDeletion'
  engineNameZh: string
  engineNameEn: string
  unitZh: string
  unitEn: string
  taskTypes: string[]
  operators?: string[]
  descriptionZh: string
  descriptionEn: string
}

export interface EngineDef {
  key:
    | 'AddResource'
    | 'ExternalParse'
    | 'Semantic'
    | 'Semantic-Nodes'
    | 'Embedding'
    | 'SessionCommit'
    | 'UserDeletion'
  nameZh: string
  nameEn: string
  descZh: string
  descEn: string
}

export const ENGINE_DEFINITIONS: EngineDef[] = [
  {
    key: 'AddResource',
    nameZh: '资源入库',
    nameEn: 'Resource Ingestion',
    descZh: '负责文件系统落盘、SHA256 校验、Inode 创建与外部源下载拉取',
    descEn: 'AGFS disk writes, SHA256 hashing, Inode creation, connector fetch',
  },
  {
    key: 'ExternalParse',
    nameZh: '文档解析',
    nameEn: 'Document Parsing',
    descZh: '多格式解析器（PDF, Markdown, HTML, 代码）段落结构化与分页',
    descEn: 'Multi-format parser for PDF, Markdown, HTML, code structuring',
  },
  {
    key: 'Semantic',
    nameZh: '语义分析',
    nameEn: 'Semantic Extraction & Gate',
    descZh: '调用大模型提取概念概要、萃取经验记忆并执行抗熵增质检四大算子',
    descEn: 'Invoke LLM/VLM for concepts, lesson extraction, and quality gate operators',
  },
  {
    key: 'Embedding',
    nameZh: '向量计算',
    nameEn: 'Vector Embedding',
    descZh: '文本切片分块，GPU 并发计算稠密向量并写入 VikingDB 向量库',
    descEn: 'Chunk text, GPU vector computation, insert into VikingDB',
  },
  {
    key: 'SessionCommit',
    nameZh: '会话归档',
    nameEn: 'Session Archival',
    descZh: '处理多轮对话流水、萃取长程经验 Lesson 并打上 AGFS 快照',
    descEn: 'Process multi-turn dialogue, extract lessons, commit AGFS snapshot',
  },
  {
    key: 'UserDeletion',
    nameZh: '空间注销',
    nameEn: 'Space Purge',
    descZh: '租户空间解绑、向量集合批量 Drop 擦除与无主孤儿垃圾回收',
    descEn: 'Namespace unbinding, vector drop, disk erase and orphan GC',
  },
  {
    key: 'Semantic-Nodes',
    nameZh: '语义拓扑',
    nameEn: 'Semantic Topology',
    descZh: '知识图谱关联遍历与跨资源实体网状关联构建',
    descEn: 'Knowledge graph traversal and cross-resource relation building',
  },
]

export const ALL_PANORAMA_STEPS: PanoramaStepDef[] = [
  ...CORE_PANORAMA_STEPS,
  ...ENTROPY_PANORAMA_STEPS,
]

export interface TaskTypeFlowDef {
  typeKey: string
  nameZh: string
  nameEn: string
  stepIds: string[]
}

export const TASK_FLOWS: TaskTypeFlowDef[] = [
  {
    typeKey: 'add_resource',
    nameZh: '资源处理',
    nameEn: 'Resource Ingestion',
    stepIds: ['step_ingestion', 'step_parse', 'step_semantic', 'step_embedding', 'step_memory_linking'],
  },
  {
    typeKey: 'add_skill',
    nameZh: '技能导入',
    nameEn: 'Skill Discovery',
    stepIds: ['step_discovery', 'step_validation', 'step_embedding'],
  },
  {
    typeKey: 'session_commit',
    nameZh: '会话提交',
    nameEn: 'Session Commit',
    stepIds: ['step_archival', 'step_lessons', 'step_snapshot'],
  },
  {
    typeKey: 'admin_reindex',
    nameZh: '全局索引重建',
    nameEn: 'Global Reindex',
    stepIds: ['step_scan', 'step_reconstruction', 'step_pruning'],
  },
  {
    typeKey: 'snapshot_restore_reindex',
    nameZh: '快照恢复索引',
    nameEn: 'Snapshot Restore',
    stepIds: ['step_rollback', 'step_inodes', 'step_incremental_vector'],
  },
  {
    typeKey: 'connector_import',
    nameZh: '连接器导入',
    nameEn: 'Connector Import',
    stepIds: ['step_auth', 'step_fetch', 'step_parse', 'step_semantic', 'step_embedding'],
  },
  {
    typeKey: 'legacy_migration',
    nameZh: '旧数据迁移',
    nameEn: 'Legacy Migration',
    stepIds: ['step_read', 'step_transform', 'step_agfs_write'],
  },
  {
    typeKey: 'legacy_cleanup',
    nameZh: '旧数据清理',
    nameEn: 'Legacy Cleanup',
    stepIds: ['step_traverse', 'step_gc', 'step_free'],
  },
  { typeKey: 'quality_gate', nameZh: '质量门禁', nameEn: 'Quality Gate', stepIds: ['step_quality_gate'] },
  { typeKey: 'benchmark_eval', nameZh: '基准质检', nameEn: 'Benchmark Evaluation', stepIds: ['step_quality_gate'] },
  { typeKey: 'knowledge_remediation', nameZh: '知识自愈优化', nameEn: 'Knowledge Remediation', stepIds: ['step_fault_locate', 'step_conflict_arbitrate', 'step_targeted_distill', 'step_delta_reindex'] },
  { typeKey: 'memory_dream', nameZh: '记忆流反思做梦', nameEn: 'Memory Stream & Reflection', stepIds: ['step_scan_observations', 'step_cluster_themes', 'step_distill_insights', 'step_consolidate_master'] },
  { typeKey: 'memory_compaction', nameZh: '分层内存压缩淘汰', nameEn: 'Hierarchical Compaction', stepIds: ['step_evaluate_tiers', 'step_cosine_deduplication', 'step_prune_and_archive', 'step_rebalance_index'] },
  { typeKey: 'fact_mutation', nameZh: '增量事实四态流转', nameEn: 'Fact 4-Way Mutation', stepIds: ['step_extract_atomic_facts', 'step_semantic_conflict_check', 'step_execute_4way_mutation', 'step_commit_knowledge_graph'] },
  { typeKey: 'entity_summarization', nameZh: '时态图谱实体浓缩', nameEn: 'Entity Summarization', stepIds: ['step_extract_entities_relations', 'step_temporal_timeline_ordering', 'step_merge_temporal_contradictions', 'step_update_entity_index'] },
  { typeKey: 'four_tier_governance', nameZh: '四层治理同主题合并', nameEn: 'Four-Tier Governance', stepIds: ['step_tier_diagnosis', 'step_topic_grouping', 'step_llm_topic_synthesis', 'step_writeback_and_cleanup'] },
]
