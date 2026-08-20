import * as React from 'react'
import { useTranslation } from 'react-i18next'
import {
  ChevronDownIcon,
  ChevronRightIcon,
  CpuIcon,
  FilterIcon,
  Layers3Icon,
  WorkflowIcon,
  SparklesIcon,
  ArrowRightIcon,
  BoxesIcon,
} from 'lucide-react'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card, CardHeader, CardTitle, CardDescription } from '#/components/ui/card'
import { cn } from '#/lib/utils'

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
    nameZh: '语义提取',
    nameEn: 'Semantic Extraction',
    descZh: '调用大语言模型（LLM/VLM）提取 L0 概要与 L1 核心概念节点',
    descEn: 'Invoke LLM/VLM to extract L0 summary and L1 concept nodes',
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
  // 1-4: 资源处理相关
  {
    id: 'step_ingestion',
    nameZh: '资源入库',
    nameEn: 'Resource Ingestion',
    engineKey: 'AddResource',
    engineNameZh: '资源入库',
    engineNameEn: 'Resource Ingestion Engine',
    unitZh: '文件',
    unitEn: 'files',
    taskTypes: ['add_resource', 'connector_import'],
    descriptionZh: '校验 SHA256，在 AGFS 中创建物理 Inode 节点并落盘',
    descriptionEn: 'Verify SHA256, create physical Inode in AGFS and persist to disk',
  },
  {
    id: 'step_parse',
    nameZh: '文档解析',
    nameEn: 'Document Parsing',
    engineKey: 'ExternalParse',
    engineNameZh: '文档解析',
    engineNameEn: 'Document Parsing Engine',
    unitZh: '页 / 篇',
    unitEn: 'pages / docs',
    taskTypes: ['add_resource', 'connector_import'],
    descriptionZh: '多格式解析引擎（MarkItDown/PDF/Docx/HTML）段落结构化',
    descriptionEn: 'Multi-format parser structuring Markdown, PDF, Docx, HTML',
  },
  {
    id: 'step_semantic',
    nameZh: '语义提取',
    nameEn: 'Semantic Extraction',
    engineKey: 'Semantic',
    engineNameZh: '语义提取',
    engineNameEn: 'Semantic Extraction Engine',
    unitZh: '节点',
    unitEn: 'nodes',
    taskTypes: ['add_resource', 'connector_import'],
    descriptionZh: '调用 LLM/VLM 大模型脑力提取 L0/L1 概念与分层摘要',
    descriptionEn: 'Invoke LLM/VLM to extract L0/L1 concepts and hierarchical summaries',
  },
  {
    id: 'step_embedding',
    nameZh: '向量建库',
    nameEn: 'Vector Embedding',
    engineKey: 'Embedding',
    engineNameZh: '向量计算',
    engineNameEn: 'Vector Embedding Engine',
    unitZh: '切片',
    unitEn: 'chunks',
    taskTypes: ['add_resource', 'add_skill', 'connector_import'],
    descriptionZh: '文本切片分块，GPU 并发计算稠密向量并存入 VikingDB',
    descriptionEn: 'Text chunking, compute dense vectors on GPU and insert into VikingDB',
  },

  // 5-6: 技能导入相关
  {
    id: 'step_discovery',
    nameZh: '目录扫描',
    nameEn: 'Directory Discovery',
    engineKey: 'AddResource',
    engineNameZh: '资源入库',
    engineNameEn: 'Resource Ingestion Engine',
    unitZh: '目录',
    unitEn: 'dirs',
    taskTypes: ['add_skill'],
    descriptionZh: '遍历扫描 skills/ 插件目录结构与元数据文件',
    descriptionEn: 'Traverse and scan skills/ plugin directory structure and metadata',
  },
  {
    id: 'step_validation',
    nameZh: '规范校验',
    nameEn: 'Spec Validation',
    engineKey: 'AddResource',
    engineNameZh: '资源入库',
    engineNameEn: 'Resource Ingestion Engine',
    unitZh: '技能',
    unitEn: 'skills',
    taskTypes: ['add_skill'],
    descriptionZh: '校验 SKILL.md 的 YAML 头部合规性与执行指令完整性',
    descriptionEn: 'Validate YAML frontmatter compliance and action completeness in SKILL.md',
  },

  // 7-9: 会话归档相关
  {
    id: 'step_archival',
    nameZh: '对话归档',
    nameEn: 'Dialogue Archival',
    engineKey: 'SessionCommit',
    engineNameZh: '会话归档',
    engineNameEn: 'Session Archival Engine',
    unitZh: '轮',
    unitEn: 'turns',
    taskTypes: ['session_commit'],
    descriptionZh: '提取 Agent 对话多轮历史，序列化上下文与消息流水',
    descriptionEn: 'Extract multi-turn dialogue history, serialize context and messages',
  },
  {
    id: 'step_lessons',
    nameZh: '经验萃取',
    nameEn: 'Lesson Extraction',
    engineKey: 'SessionCommit',
    engineNameZh: '会话归档',
    engineNameEn: 'Session Archival Engine',
    unitZh: '条经验',
    unitEn: 'lessons',
    taskTypes: ['session_commit'],
    descriptionZh: '提炼对话中的工程教训、决策偏好并沉淀为记忆 Lessons',
    descriptionEn: 'Distill engineering lessons and decision preferences into memory lessons',
  },
  {
    id: 'step_snapshot',
    nameZh: '快照提交',
    nameEn: 'Snapshot Commit',
    engineKey: 'SessionCommit',
    engineNameZh: '会话归档',
    engineNameEn: 'Session Archival Engine',
    unitZh: '快照',
    unitEn: 'commits',
    taskTypes: ['session_commit'],
    descriptionZh: '生成全局版本快照 Commit，确保跨会话持久化与可回滚',
    descriptionEn: 'Generate global snapshot commit ensuring persistence and rollback',
  },

  // 10-12: 全局索引重建
  {
    id: 'step_scan',
    nameZh: '资源扫描',
    nameEn: 'Resource Scanning',
    engineKey: 'AddResource',
    engineNameZh: '资源入库',
    engineNameEn: 'Resource Ingestion Engine',
    unitZh: '项',
    unitEn: 'items',
    taskTypes: ['admin_reindex'],
    descriptionZh: '递归遍历 AGFS 树上所有登记的物理与虚拟知识节点',
    descriptionEn: 'Recursively traverse all registered physical/virtual nodes in AGFS tree',
  },
  {
    id: 'step_pruning',
    nameZh: '悬空修剪',
    nameEn: 'Orphan Pruning',
    engineKey: 'UserDeletion',
    engineNameZh: '空间注销',
    engineNameEn: 'Namespace Deletion Engine',
    unitZh: '切片',
    unitEn: 'chunks',
    taskTypes: ['admin_reindex'],
    descriptionZh: '清理已删除或断开关联的悬空切片与历史悬空记录',
    descriptionEn: 'Clean up orphaned chunks and dangling historical records',
  },
  {
    id: 'step_reconstruction',
    nameZh: '切片重构',
    nameEn: 'Chunk Reconstruction',
    engineKey: 'Embedding',
    engineNameZh: '向量计算',
    engineNameEn: 'Vector Embedding Engine',
    unitZh: '切片',
    unitEn: 'chunks',
    taskTypes: ['admin_reindex'],
    descriptionZh: '按照最新 Embedding 模型超参数重新切块并计算全量向量',
    descriptionEn: 'Re-chunk and compute full vector embeddings using latest parameters',
  },

  // 13-15: 快照恢复重构
  {
    id: 'step_rollback',
    nameZh: '快照回滚',
    nameEn: 'Snapshot Rollback',
    engineKey: 'SessionCommit',
    engineNameZh: '会话归档',
    engineNameEn: 'Session Archival Engine',
    unitZh: '快照',
    unitEn: 'commits',
    taskTypes: ['snapshot_restore_reindex'],
    descriptionZh: '定位历史快照 Tag，安全回滚 AGFS 目录树状态',
    descriptionEn: 'Locate historical snapshot tag and safely rollback AGFS directory state',
  },
  {
    id: 'step_inodes',
    nameZh: '节点还原',
    nameEn: 'Inode Restoration',
    engineKey: 'AddResource',
    engineNameZh: '资源入库',
    engineNameEn: 'Resource Ingestion Engine',
    unitZh: '节点',
    unitEn: 'inodes',
    taskTypes: ['snapshot_restore_reindex'],
    descriptionZh: '重建快照中的 Inode 索引节点与属性元数据',
    descriptionEn: 'Rebuild Inode index nodes and attribute metadata from snapshot',
  },
  {
    id: 'step_incremental_vector',
    nameZh: '增量向量',
    nameEn: 'Incremental Embedding',
    engineKey: 'Embedding',
    engineNameZh: '向量计算',
    engineNameEn: 'Vector Embedding Engine',
    unitZh: '切片',
    unitEn: 'chunks',
    taskTypes: ['snapshot_restore_reindex'],
    descriptionZh: '仅对差异变更的切片进行增量向量计算与补齐',
    descriptionEn: 'Compute incremental vector embeddings only for modified chunks',
  },

  // 16-17: 连接器导入
  {
    id: 'step_auth',
    nameZh: '连接鉴权',
    nameEn: 'Connector Auth',
    engineKey: 'AddResource',
    engineNameZh: '资源入库',
    engineNameEn: 'Resource Ingestion Engine',
    unitZh: '连接',
    unitEn: 'connections',
    taskTypes: ['connector_import'],
    descriptionZh: '校验飞书/Notion/GitHub/WebDAV 等外部源 Token 与凭证',
    descriptionEn: 'Validate external source tokens for Feishu, Notion, GitHub, WebDAV',
  },
  {
    id: 'step_fetch',
    nameZh: '资源拉取',
    nameEn: 'Remote Fetch',
    engineKey: 'AddResource',
    engineNameZh: '资源入库',
    engineNameEn: 'Resource Ingestion Engine',
    unitZh: '篇',
    unitEn: 'docs',
    taskTypes: ['connector_import'],
    descriptionZh: '从外部 API 批量拉取文档流与附件并缓冲至暂存区',
    descriptionEn: 'Batch fetch document streams and attachments from external APIs',
  },

  // 18-20: 旧数据迁移
  {
    id: 'step_read',
    nameZh: '数据读取',
    nameEn: 'Legacy Read',
    engineKey: 'AddResource',
    engineNameZh: '资源入库',
    engineNameEn: 'Resource Ingestion Engine',
    unitZh: '条',
    unitEn: 'records',
    taskTypes: ['legacy_migration'],
    descriptionZh: '兼容性加载旧版 V1/V2 数据库与历史元数据存储',
    descriptionEn: 'Backward-compatible loading of legacy V1/V2 database records',
  },
  {
    id: 'step_transform',
    nameZh: '格式转换',
    nameEn: 'Schema Transform',
    engineKey: 'AddResource',
    engineNameZh: '资源入库',
    engineNameEn: 'Resource Ingestion Engine',
    unitZh: '项',
    unitEn: 'items',
    taskTypes: ['legacy_migration'],
    descriptionZh: '将旧版 Schema 转换为 OpenViking 标准化 AGFS Schema',
    descriptionEn: 'Transform legacy schema into OpenViking standard AGFS schema',
  },
  {
    id: 'step_agfs_write',
    nameZh: '存储落盘',
    nameEn: 'Storage Persist',
    engineKey: 'AddResource',
    engineNameZh: '资源入库',
    engineNameEn: 'Resource Ingestion Engine',
    unitZh: '节点',
    unitEn: 'inodes',
    taskTypes: ['legacy_migration'],
    descriptionZh: '把迁移后的结构化数据原子写入 AGFS 文件系统并落盘',
    descriptionEn: 'Atomically write migrated structured data into AGFS tree',
  },

  // 21-23: 旧数据清理
  {
    id: 'step_traverse',
    nameZh: '图谱遍历',
    nameEn: 'Graph Traversal',
    engineKey: 'Semantic-Nodes',
    engineNameZh: '语义拓扑',
    engineNameEn: 'Semantic Topology Engine',
    unitZh: '实体',
    unitEn: 'entities',
    taskTypes: ['legacy_cleanup'],
    descriptionZh: '深度遍历知识图谱关联，标记所有活跃与失效引用链',
    descriptionEn: 'Deep traverse knowledge graph to mark active and stale references',
  },
  {
    id: 'step_gc',
    nameZh: '碎片回收',
    nameEn: 'Garbage Collection',
    engineKey: 'UserDeletion',
    engineNameZh: '空间注销',
    engineNameEn: 'Namespace Deletion Engine',
    unitZh: '项',
    unitEn: 'items',
    taskTypes: ['legacy_cleanup'],
    descriptionZh: '执行垃圾回收 (GC) 算法，清除断链悬空实体与无效切片',
    descriptionEn: 'Garbage collection to purge dangling entities and stale chunks',
  },
  {
    id: 'step_free',
    nameZh: '空间释放',
    nameEn: 'Space Release',
    engineKey: 'UserDeletion',
    engineNameZh: '空间注销',
    engineNameEn: 'Namespace Deletion Engine',
    unitZh: 'MB / 字节',
    unitEn: 'MB / bytes',
    taskTypes: ['legacy_cleanup'],
    descriptionZh: '物理释放磁盘占用，整理存储空间并更新配额',
    descriptionEn: 'Physically release disk storage and update namespace quotas',
  },
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
    stepIds: ['step_ingestion', 'step_parse', 'step_semantic', 'step_embedding'],
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
    stepIds: ['step_scan', 'step_pruning', 'step_reconstruction'],
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
]

export function PipelineStepsPanoramaCard() {
  const { i18n } = useTranslation('tasksPage')
  const isZh = i18n.language.startsWith('zh')
  const [isOpen, setIsOpen] = React.useState(false)
  const [activeTab, setActiveTab] = React.useState<'flows' | 'matrix' | 'engines'>('flows')
  const [selectedTaskType, setSelectedTaskType] = React.useState<string>('all')

  const filteredFlows = React.useMemo(() => {
    if (selectedTaskType === 'all') return TASK_FLOWS
    return TASK_FLOWS.filter((f) => f.typeKey === selectedTaskType)
  }, [selectedTaskType])

  return (
    <Card className="rounded-xl border bg-card/75 p-0 shadow-xs transition-all">
      {/* Header Banner */}
      <div
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex cursor-pointer select-none items-center justify-between px-4 py-3 hover:bg-muted/20 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary ring-1 ring-primary/20">
            <WorkflowIcon className="size-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-sans text-sm font-semibold text-foreground">
                {isZh ? '流水线全工序全景大盘' : 'Pipeline Steps Panorama'}
              </span>
              <Badge variant="outline" className="text-[11px] font-mono px-1.5 py-0 h-4.5 bg-muted/30">
                {isZh ? '8 业务任务' : '8 Tasks'}
              </Badge>
              <Badge variant="outline" className="text-[11px] font-mono px-1.5 py-0 h-4.5 bg-primary/10 text-primary border-primary/20">
                {isZh ? '23 原子工序' : '23 Steps'}
              </Badge>
              <Badge variant="outline" className="text-[11px] font-mono px-1.5 py-0 h-4.5 bg-muted/30">
                {isZh ? '7 执行引擎' : '7 Engines'}
              </Badge>
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              {isZh
                ? '任务（业务目标）➔ 编排拆解出 23 道流水线工序 ➔ 调度驱动底层 7 大执行引擎物理计算'
                : 'Business Tasks ➔ Decomposed into 23 Pipeline Steps ➔ Dispatched to 7 Execution Engines'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] font-medium text-muted-foreground">
            {isOpen ? (isZh ? '收起全景' : 'Collapse') : (isZh ? '展开全景' : 'Expand')}
          </span>
          <ChevronDownIcon
            className={cn('size-4 text-muted-foreground transition-transform duration-200', isOpen && 'rotate-180')}
          />
        </div>
      </div>

      {/* Expanded Content */}
      {isOpen && (
        <div className="border-t px-4 py-3.5 space-y-3.5">
          {/* Sub-Header Tabs & Quick Filter */}
          <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-2.5">
            <div className="flex items-center gap-1.5 bg-muted/40 p-0.5 rounded-lg border border-border/60">
              <button
                type="button"
                onClick={() => setActiveTab('flows')}
                className={cn(
                  'px-2.5 py-1 text-xs font-medium rounded-md transition-all cursor-pointer select-none',
                  activeTab === 'flows'
                    ? 'bg-background text-foreground shadow-2xs font-semibold'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {isZh ? '① 任务流转全景 (8 任务)' : '① Task Flows (8 Tasks)'}
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('matrix')}
                className={cn(
                  'px-2.5 py-1 text-xs font-medium rounded-md transition-all cursor-pointer select-none',
                  activeTab === 'matrix'
                    ? 'bg-background text-foreground shadow-2xs font-semibold'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {isZh ? '② 23 道工序总字典' : '② 23 Steps Dictionary'}
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('engines')}
                className={cn(
                  'px-2.5 py-1 text-xs font-medium rounded-md transition-all cursor-pointer select-none',
                  activeTab === 'engines'
                    ? 'bg-background text-foreground shadow-2xs font-semibold'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {isZh ? '③ 7 大引擎承接图' : '③ 7 Engine Mappings'}
              </button>
            </div>

            {activeTab === 'flows' && (
              <div className="flex items-center gap-1.5 overflow-x-auto text-[11px]">
                <button
                  type="button"
                  onClick={() => setSelectedTaskType('all')}
                  className={cn(
                    'px-2 py-0.5 rounded border transition-colors cursor-pointer',
                    selectedTaskType === 'all'
                      ? 'bg-primary/10 text-primary border-primary/30 font-medium'
                      : 'bg-muted/20 text-muted-foreground hover:bg-muted/40',
                  )}
                >
                  {isZh ? '全部任务 (8)' : 'All (8)'}
                </button>
                {TASK_FLOWS.map((f) => (
                  <button
                    key={f.typeKey}
                    type="button"
                    onClick={() => setSelectedTaskType(f.typeKey)}
                    className={cn(
                      'px-2 py-0.5 rounded border transition-colors cursor-pointer whitespace-nowrap',
                      selectedTaskType === f.typeKey
                        ? 'bg-primary/10 text-primary border-primary/30 font-medium'
                        : 'bg-muted/20 text-muted-foreground hover:bg-muted/40',
                    )}
                  >
                    {isZh ? f.nameZh : f.nameEn}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* View 1: 8 任务流转全景 (Task Flows) */}
          {activeTab === 'flows' && (
            <div className="grid grid-cols-1 gap-2.5 md:grid-cols-2">
              {filteredFlows.map((flow, flowIdx) => {
                const steps = flow.stepIds
                  .map((id) => ALL_PANORAMA_STEPS.find((s) => s.id === id))
                  .filter((s): s is PanoramaStepDef => s !== undefined)

                return (
                  <div
                    key={flow.typeKey}
                    className="flex flex-col rounded-lg border bg-background/80 p-3 shadow-2xs space-y-2"
                  >
                    {/* Task Title Row */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-muted-foreground text-xs font-semibold">
                          #{flowIdx + 1}
                        </span>
                        <span className="font-sans font-bold text-xs text-foreground">
                          {isZh ? flow.nameZh : flow.nameEn}
                        </span>
                        <span className="font-mono text-[11px] text-muted-foreground bg-muted/40 px-1 rounded border border-border/50">
                          {flow.typeKey}
                        </span>
                      </div>
                      <Badge variant="outline" className="text-[11px] font-mono px-1.5 py-0">
                        {steps.length} {isZh ? '道工序' : 'steps'}
                      </Badge>
                    </div>

                    {/* Step Chain */}
                    <div className="grid gap-1.5">
                      {steps.map((st, sIdx) => (
                        <div
                          key={st.id}
                          className="flex items-center justify-between rounded-md border bg-muted/15 px-2.5 py-1.5 text-xs"
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <span className="font-mono text-muted-foreground text-[11px] font-medium shrink-0">
                              {sIdx + 1}.
                            </span>
                            <span className="font-medium text-foreground text-xs truncate">
                              {isZh ? st.nameZh : st.nameEn}
                            </span>
                            <span className="font-mono text-[11px] text-muted-foreground bg-muted/50 px-1.5 py-0.2 rounded border border-border/40 shrink-0">
                              {isZh ? st.unitZh : st.unitEn}
                            </span>
                          </div>

                          <div className="flex items-center gap-1.5 shrink-0 ml-2">
                            <ArrowRightIcon className="size-2.5 text-muted-foreground/40" />
                            <Badge
                              variant="outline"
                              className="text-[11px] font-sans font-normal px-1.5 py-0 bg-background text-foreground/85 border-border/70"
                            >
                              <CpuIcon className="size-2.5 mr-1 text-primary/70" />
                              {isZh ? st.engineNameZh : st.engineNameEn}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* View 2: 23 道工序总字典矩阵 (Step Matrix) */}
          {activeTab === 'matrix' && (
            <div className="overflow-x-auto rounded-lg border bg-background/80">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b bg-muted/40 text-muted-foreground text-[11px]">
                    <th className="px-3 py-2 font-medium w-12 text-center">#</th>
                    <th className="px-3 py-2 font-medium w-36">{isZh ? '工序名称' : 'Step Name'}</th>
                    <th className="px-3 py-2 font-medium w-36">{isZh ? '承接执行引擎' : 'Assigned Engine'}</th>
                    <th className="px-3 py-2 font-medium w-24">{isZh ? '量化单位' : 'Unit'}</th>
                    <th className="px-3 py-2 font-medium w-48">{isZh ? '所属业务任务' : 'Task Types'}</th>
                    <th className="px-3 py-2 font-medium">{isZh ? '物理职责说明' : 'Physical Responsibility'}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60 font-mono text-[11px]">
                  {ALL_PANORAMA_STEPS.map((st, i) => (
                    <tr key={st.id} className="hover:bg-muted/20 transition-colors">
                      <td className="px-3 py-2 text-center text-muted-foreground font-semibold">{i + 1}</td>
                      <td className="px-3 py-2 font-sans font-semibold text-foreground text-xs">
                        {isZh ? st.nameZh : st.nameEn}
                      </td>
                      <td className="px-3 py-2">
                        <span className="inline-flex items-center gap-1 font-sans text-foreground bg-muted/50 px-1.5 py-0.5 rounded border border-border/50">
                          <CpuIcon className="size-2.5 text-primary" />
                          {isZh ? st.engineNameZh : st.engineNameEn}
                        </span>
                      </td>
                      <td className="px-3 py-2 font-mono text-muted-foreground font-medium">
                        {isZh ? st.unitZh : st.unitEn}
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap gap-1">
                          {st.taskTypes.map((tKey) => {
                            const matchFlow = TASK_FLOWS.find((f) => f.typeKey === tKey)
                            return (
                              <span
                                key={tKey}
                                className="font-sans text-[11px] bg-secondary/80 text-foreground px-1.5 py-0.2 rounded border border-border/40"
                              >
                                {isZh ? matchFlow?.nameZh ?? tKey : matchFlow?.nameEn ?? tKey}
                              </span>
                            )
                          })}
                        </div>
                      </td>
                      <td className="px-3 py-2 font-sans text-muted-foreground text-[11px]">
                        {isZh ? st.descriptionZh : st.descriptionEn}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* View 3: 7 大执行引擎承接图 (Engine Mappings) */}
          {activeTab === 'engines' && (
            <div className="grid grid-cols-1 gap-2.5 md:grid-cols-2 lg:grid-cols-3">
              {ENGINE_DEFINITIONS.map((eng) => {
                const assignedSteps = ALL_PANORAMA_STEPS.filter((s) => s.engineKey === eng.key)

                return (
                  <div
                    key={eng.key}
                    className="flex flex-col rounded-lg border bg-background/80 p-3 shadow-2xs space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="flex size-6 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
                          <CpuIcon className="size-3.5" />
                        </div>
                        <div>
                          <span className="font-sans font-bold text-xs text-foreground block">
                            {isZh ? eng.nameZh : eng.nameEn}
                          </span>
                          <span className="font-mono text-[11px] text-muted-foreground">
                            {eng.key}
                          </span>
                        </div>
                      </div>
                      <Badge variant="outline" className="text-[11px] font-mono px-1.5 py-0">
                        {assignedSteps.length} {isZh ? '道工序' : 'steps'}
                      </Badge>
                    </div>

                    <p className="text-[11px] text-muted-foreground font-sans">
                      {isZh ? eng.descZh : eng.descEn}
                    </p>

                    <div className="space-y-1 pt-1 border-t border-border/60 mt-auto">
                      <span className="text-[11px] font-medium text-muted-foreground font-sans block">
                        {isZh ? '承接工序清单：' : 'Assigned Steps:'}
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {assignedSteps.map((st) => (
                          <span
                            key={st.id}
                            className="font-sans text-[11px] bg-muted/50 text-foreground px-1.5 py-0.5 rounded border border-border/50"
                          >
                            {isZh ? st.nameZh : st.nameEn}
                            <span className="font-mono text-muted-foreground ml-1">({isZh ? st.unitZh : st.unitEn})</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </Card>
  )
}
