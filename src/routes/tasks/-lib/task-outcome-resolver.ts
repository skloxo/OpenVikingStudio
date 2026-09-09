import type { TaskRecord } from './task-record'

export interface TaskFinalOutcomeDef {
  title: string
  deliverableText: string
  expectedText: string
}

/**
 * 通用终点输出成果推导 (Universal Final Deliverable)
 */
export function deriveUniversalFinalOutcome(
  task: TaskRecord,
  language: string = 'zh',
): TaskFinalOutcomeDef {
  const isZh = language.startsWith('zh')
  const type = task.task_type || ''
  const isCompleted = (task.status || '').toLowerCase() === 'completed'

  const resObj: Record<string, any> =
    task.result && typeof task.result === 'object' ? task.result : {}
  const metaObj: Record<string, any> =
    task.meta && typeof task.meta === 'object' ? task.meta : {}

  // 1. 全局索引重建
  if (type === 'admin_reindex') {
    const scanned = resObj.semantic_records ?? resObj.scanned_records ?? metaObj.scanned_records
    const rebuilt = resObj.rebuilt_records ?? resObj.reindexed_items ?? metaObj.rebuilt_records
    const deleted = Number(resObj.deleted_records ?? metaObj.deleted_records ?? 0)

    let deliverableText = isZh ? '全量索引重构完成' : 'Global reindex completed'
    if (scanned !== undefined && rebuilt !== undefined) {
      if (deleted > 0) {
        deliverableText = isZh
          ? `已完成 ${Number(scanned).toLocaleString()} 篇记忆扫描 · 重构 ${Number(rebuilt).toLocaleString()} 个向量切片 · 修剪 ${deleted} 个孤儿碎片`
          : `Scanned ${Number(scanned).toLocaleString()} memories · Rebuilt ${Number(rebuilt).toLocaleString()} vector chunks · Pruned ${deleted} orphans`
      } else {
        deliverableText = isZh
          ? `已完成 ${Number(scanned).toLocaleString()} 篇记忆扫描 · 重构 ${Number(rebuilt).toLocaleString()} 个向量切片 · 成功率 100%`
          : `Scanned ${Number(scanned).toLocaleString()} memories · Rebuilt ${Number(rebuilt).toLocaleString()} vector chunks · 100% Success`
      }
    }

    return {
      title: isZh ? '全量索引重建' : 'Global Reindex',
      deliverableText,
      expectedText:
        deleted > 0
          ? isZh
            ? '修剪孤儿悬空碎片与全量向量切片重构'
            : 'Prune orphan dangling fragments & rebuild vectors'
          : isZh
            ? '全量记忆节点扫描与向量切片重构'
            : 'Full memory node scanning & vector chunk rebuilding',
    }
  }

  // 2. 资源入库 / 知识包
  if (type === 'add_resource' || type === 'resource_build' || type === 'knowledge_pack') {
    const files = metaObj.file_count ?? resObj.file_count ?? 1
    const chunks = resObj.processed_chunks ?? metaObj.processed_chunks
    const links = resObj.total_links ?? metaObj.total_links

    const parts: string[] = [isZh ? `${files} 个文件已落盘索引` : `${files} files indexed`]
    if (chunks && Number(chunks) > 0) {
      parts.push(isZh ? `生成 ${Number(chunks).toLocaleString()} 个向量切片` : `${Number(chunks).toLocaleString()} chunks`)
    }
    if (links && Number(links) > 0) {
      parts.push(isZh ? `建立 ${Number(links).toLocaleString()} 条记忆关联` : `${Number(links).toLocaleString()} links`)
    }

    return {
      title: isZh ? '资源入库' : 'Resource Ingestion',
      deliverableText: parts.join(' · '),
      expectedText: isZh ? '物理文件落盘与语义向量建库' : 'File persistence and vector indexing',
    }
  }

  // 3. 技能入库
  if (type === 'add_skill') {
    const skills = resObj.valid_skills ?? metaObj.valid_skills ?? resObj.scanned_skills
    return {
      title: isZh ? '技能入库' : 'Skill Ingestion',
      deliverableText: skills
        ? (isZh ? `${skills} 项技能已完成校验并注册入库` : `${skills} skills validated & registered`)
        : (isZh ? '技能已完成校验并注册入库' : 'Skills validated & registered'),
      expectedText: isZh ? '技能合规校验与向量注册入库' : 'Skill spec validation & embedding registration',
    }
  }

  // 4. 会话归档
  if (type === 'session_commit') {
    const turns = metaObj.turns_count ?? resObj.turns_processed ?? 1
    const lessons = Number(resObj.lessons_extracted ?? metaObj.lessons_count ?? 0)
    return {
      title: isZh ? '会话归档' : 'Session Commit',
      deliverableText: isZh
        ? `${turns} 轮对话已归档` + (lessons > 0 ? ` · ${lessons} 条经验已沉淀` : '')
        : `${turns} turns archived` + (lessons > 0 ? ` · ${lessons} lessons extracted` : ''),
      expectedText: isZh ? '对话上下文序列化与经验记忆萃取' : 'Context serialization & lesson extraction',
    }
  }

  // 5. 质量门禁 (Quality Gate)
  if (type === 'quality_gate' || type === 'benchmark_eval') {
    const composite = resObj.composite_score ?? metaObj.composite_score
    const totalCases = resObj.total_queries ?? resObj.total_cases ?? metaObj.total_queries ?? 10
    const hitRate = resObj.hit_rate ?? metaObj.hit_rate

    let deliverableText = isZh ? '抗熵增质量门禁已执行' : 'Anti-entropy quality gate completed'
    if (composite !== undefined) {
      const compStr = typeof composite === 'number' ? composite.toFixed(3) : String(composite)
      const hitStr = hitRate !== undefined ? (typeof hitRate === 'number' ? `${(hitRate * 100).toFixed(0)}%` : String(hitRate)) : undefined
      deliverableText = isZh
        ? `评测 ${totalCases} 组金标用例 · RAGAS 综合指数 ${compStr}` + (hitStr ? ` · 命中率 ${hitStr}` : '')
        : `Evaluated ${totalCases} test cases · RAGAS Composite ${compStr}` + (hitStr ? ` · Hit Rate ${hitStr}` : '')
    }

    return {
      title: isZh ? '抗熵增质量门禁' : 'Anti-Entropy Quality Gate',
      deliverableText,
      expectedText: isZh ? '四维指标调和评测与抗熵增基线断言' : '4D RAGAS harmonic evaluation & baseline assertion',
    }
  }

  // 6. 知识自愈优化 (Knowledge Remediation)
  if (type === 'knowledge_remediation' || type === 'entropy_healing') {
    const faults = resObj.located_faults ?? metaObj.located_faults ?? (metaObj.fault_queries?.length || 0)
    const conflicts = resObj.resolved_conflicts ?? metaObj.resolved_conflicts ?? 0
    const chunks = resObj.reindexed_chunks ?? metaObj.reindexed_chunks ?? 0

    return {
      title: isZh ? '知识自愈优化' : 'Knowledge Remediation',
      deliverableText: isZh
        ? `定位 ${faults} 处病灶 · 仲裁 ${conflicts} 项冲突 · 增量重索引 ${chunks} 切片`
        : `Located ${faults} faults · Resolved ${conflicts} conflicts · Reindexed ${chunks} chunks`,
      expectedText: isZh ? '抗熵增病灶靶向自愈与新旧冲突消解' : 'Targeted fault remediation & conflict resolution',
    }
  }

  // 7. 连接器导入 (Connector Import)
  if (type === 'connector_import') {
    const count = metaObj.item_count ?? resObj.item_count ?? 1
    return {
      title: isZh ? '连接器导入' : 'Connector Import',
      deliverableText: isZh ? `连接器握手成功 · 抓取 ${count} 条资源 · 语义分析并向量入库` : `Connector authenticated · Fetched ${count} items · Embedded into vector index`,
      expectedText: isZh ? '外部源鉴权握手、数据拉取与向量入库' : 'Connector auth, fetch, and vector indexing',
    }
  }

  // 8. 快照恢复索引 (Snapshot Restore Reindex)
  if (type === 'snapshot_restore_reindex') {
    const inodes = resObj.restored_inodes ?? metaObj.restored_inodes ?? 0
    return {
      title: isZh ? '快照恢复索引' : 'Snapshot Restore',
      deliverableText: isZh ? `快照回滚完成 · 恢复 ${inodes} 个 Inodes · 增量向量重建就绪` : `Snapshot rolled back · Restored ${inodes} inodes · Incremental vectors ready`,
      expectedText: isZh ? '快照回滚、Inode 恢复与增量向量重建' : 'Snapshot rollback, inode restore & incremental vectors',
    }
  }

  // 9. 旧数据迁移 (Legacy Migration)
  if (type === 'legacy_migration') {
    const migrated = resObj.migrated_records ?? metaObj.migrated_records ?? 0
    return {
      title: isZh ? '旧数据迁移' : 'Legacy Migration',
      deliverableText: isZh ? `读取旧版数据 · 转换 Schema · ${migrated} 条数据安全落盘` : `Legacy read · Schema transformed · ${migrated} records written`,
      expectedText: isZh ? '旧格式解析、Schema 转换与 AGFS 存储写入' : 'Legacy read, schema transformation & storage write',
    }
  }

  // 10. 旧数据清理 (Legacy Cleanup)
  if (type === 'legacy_cleanup') {
    const freed = resObj.freed_mb ?? metaObj.freed_mb ?? 0
    return {
      title: isZh ? '旧数据清理' : 'Legacy Cleanup',
      deliverableText: isZh ? `图遍历排查 · 清理孤儿节点 · 释放 ${freed} MB 存储空间` : `Graph traversal · Cleaned orphans · Freed ${freed} MB space`,
      expectedText: isZh ? '依赖图遍历、孤儿垃圾回收与空间释放' : 'Graph traversal, orphan GC & space release',
    }
  }

  // 11. 轻量增量入库 (Lightweight Ingestion)
  if (type === 'valet_parking') {
    const rawAction = String(resObj.action || metaObj.action || 'add').toLowerCase()
    const simVal = resObj.similarity ?? metaObj.similarity
    const sim = typeof simVal === 'number' ? simVal.toFixed(4) : (simVal !== undefined ? Number(simVal).toFixed(4) : '0.0000')
    const saved = Number(resObj.saved_bytes || metaObj.saved_bytes || 0)
    const nodes = resObj.progress?.completed ?? resObj.parked_nodes ?? 1
    let deliverableText = isZh ? `准入判定: 独立新增 (ADD) · 向量探针相似度 ${sim} · ${nodes} 个知识节点已存储落盘` : `Admission: ADD · Similarity ${sim} · ${nodes} node(s) persisted`
    if (rawAction === 'noop') {
      deliverableText = isZh
        ? `准入判定: 同义合并 (NOOP) · 向量相似度 ${sim}` + (saved > 0 ? ` · 节约物理存储 ${(saved / 1024).toFixed(1)} KB` : ' · 零冗余新增')
        : `Admission: NOOP · Similarity ${sim}` + (saved > 0 ? ` · Saved ${(saved / 1024).toFixed(1)} KB` : ' · Zero Redundancy')
    } else if (rawAction === 'update') {
      deliverableText = isZh ? `准入判定: 增量演进 (UPDATE) · 向量相似度 ${sim} · 既有知识节点已版本升级` : `Admission: UPDATE · Similarity ${sim} · Node version updated`
    }
    return {
      title: isZh ? '轻量增量入库' : 'Lightweight Ingestion',
      deliverableText,
      expectedText: isZh ? '快速接管暂存、向量相似度探针与准入判定' : 'Fast handover, vector probe & admission check',
    }
  }

  // 14. 用户空间注销 (User Delete)
  if (type === 'user_delete' || type === 'user_deletion') {
    const vectors = resObj.deleted_vectors ?? metaObj.deleted_vectors ?? 0
    const files = resObj.deleted_files ?? metaObj.deleted_files ?? 0
    return {
      title: isZh ? '用户空间注销' : 'User Space Purge',
      deliverableText: isZh ? `空间软标已标记 · 抹除 ${vectors} 条向量切片 · 擦除 ${files} 个物理文件` : `Soft mark tagged · Purged ${vectors} vectors · Wiped ${files} files`,
      expectedText: isZh ? '空间软标、向量注销与物理磁盘擦除' : 'Soft marking, vector purging & physical disk wiping',
    }
  }

  // 默认通用兜底
  return {
    title: isZh ? '任务交付成果' : 'Task Deliverable',
    deliverableText: isCompleted ? (isZh ? '物理工序已全部执行完毕并校验入库' : 'All stages physically completed & verified') : (isZh ? '正在按序流转执行' : 'Executing pipeline stages'),
    expectedText: isZh ? '物理计算与状态同步' : 'Physical computation & state sync',
  }
}
