import { CORE_PANORAMA_STEPS } from './panorama-steps-core'

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

export const ALL_PANORAMA_STEPS: PanoramaStepDef[] = CORE_PANORAMA_STEPS

export interface TaskTypeFlowDef {
  typeKey: string
  nameZh: string
  nameEn: string
  stepIds: string[]
}

/**
 * 10 大真实车间工序流定义 (9 个经典基建车间 + 1 个轻量增量入库)
 */
export const TASK_FLOWS: TaskTypeFlowDef[] = [
  {
    typeKey: 'valet_parking',
    nameZh: '轻量增量入库',
    nameEn: 'Lightweight Ingestion',
    stepIds: ['step_valet_handover', 'step_valet_probe', 'step_valet_decision', 'step_valet_parking'],
  },
  {
    typeKey: 'add_resource',
    nameZh: '资源处理',
    nameEn: 'Resource Ingestion',
    stepIds: ['step_ingestion', 'step_parse', 'step_semantic', 'step_embedding', 'step_memory_linking'],
  },
  {
    typeKey: 'session_commit',
    nameZh: '会话提交',
    nameEn: 'Session Commit',
    stepIds: ['step_serialization', 'step_distillation', 'step_persistence'],
  },
  {
    typeKey: 'add_skill',
    nameZh: '技能导入',
    nameEn: 'Skill Discovery',
    stepIds: ['step_discovery', 'step_validation', 'step_embedding'],
  },
  {
    typeKey: 'connector_import',
    nameZh: '连接器导入',
    nameEn: 'Connector Import',
    stepIds: ['step_auth', 'step_fetch', 'step_parse', 'step_semantic', 'step_embedding'],
  },
  {
    typeKey: 'admin_reindex',
    nameZh: '全局索引重建',
    nameEn: 'Global Reindex',
    stepIds: ['step_scan', 'step_rebuild_semantic', 'step_rebuild_vectors'],
  },
  {
    typeKey: 'snapshot_restore_reindex',
    nameZh: '快照恢复索引',
    nameEn: 'Snapshot Restore',
    stepIds: ['step_inode_restore', 'step_incremental_vector'],
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
  {
    typeKey: 'user_delete',
    nameZh: '用户空间注销',
    nameEn: 'User Space Purge',
    stepIds: ['step_soft_mark', 'step_vector_purge', 'step_disk_wipe'],
  },
]
