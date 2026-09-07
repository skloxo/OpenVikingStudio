import {
  ALL_PANORAMA_STEPS,
  TASK_FLOWS,
} from '#/routes/tasks/-components/pipeline-steps-panorama'
import type { PanoramaStepDef } from '#/routes/tasks/-components/pipeline-steps-panorama'

export type TaskFlowItem =
  | { kind: 'single'; step: PanoramaStepDef }
  | { kind: 'parallel'; steps: PanoramaStepDef[] }

export function getTaskFlowItems(taskType: string): TaskFlowItem[] {
  if (taskType === 'add_resource') {
    const s1 = ALL_PANORAMA_STEPS.find((s) => s.id === 'step_ingestion')
    const s2 = ALL_PANORAMA_STEPS.find((s) => s.id === 'step_parse')
    const s3 = ALL_PANORAMA_STEPS.find((s) => s.id === 'step_semantic')
    const s4 = ALL_PANORAMA_STEPS.find((s) => s.id === 'step_embedding')
    const s5 = ALL_PANORAMA_STEPS.find((s) => s.id === 'step_memory_linking')
    const res: TaskFlowItem[] = []
    if (s1) res.push({ kind: 'single', step: s1 })
    if (s2) res.push({ kind: 'single', step: s2 })
    if (s3 && s4) res.push({ kind: 'parallel', steps: [s3, s4] })
    if (s5) res.push({ kind: 'single', step: s5 })
    return res
  }

  if (taskType === 'connector_import') {
    const s1 = ALL_PANORAMA_STEPS.find((s) => s.id === 'step_auth')
    const s2 = ALL_PANORAMA_STEPS.find((s) => s.id === 'step_fetch')
    const s3 = ALL_PANORAMA_STEPS.find((s) => s.id === 'step_parse')
    const s4 = ALL_PANORAMA_STEPS.find((s) => s.id === 'step_semantic')
    const s5 = ALL_PANORAMA_STEPS.find((s) => s.id === 'step_embedding')
    const res: TaskFlowItem[] = []
    if (s1) res.push({ kind: 'single', step: s1 })
    if (s2) res.push({ kind: 'single', step: s2 })
    if (s3) res.push({ kind: 'single', step: s3 })
    if (s4 && s5) res.push({ kind: 'parallel', steps: [s4, s5] })
    return res
  }

  // 质量门禁 (Quality Gate): 四算子时序流
  if (taskType === 'quality_gate' || taskType === 'benchmark_eval') {
    return [
      {
        kind: 'single',
        step: {
          id: 'step_query_sample',
          nameZh: '用例选样',
          nameEn: 'Query Sample',
          unitZh: '用例',
          unitEn: 'cases',
          engineKey: 'Semantic',
          engineNameZh: '语义分析',
          engineNameEn: 'Semantic',
          taskTypes: ['quality_gate'],
          descriptionZh: '从金标库或审计日志抽取待测用例',
          descriptionEn: 'Sample queries from golden suite or audit logs',
        },
      },
      {
        kind: 'single',
        step: {
          id: 'step_vector_retrieve',
          nameZh: '多路检索',
          nameEn: 'Vector Retrieve',
          unitZh: '候选',
          unitEn: 'hits',
          engineKey: 'Embedding',
          engineNameZh: '向量计算',
          engineNameEn: 'Vector Embedding',
          taskTypes: ['quality_gate'],
          descriptionZh: '并发稠密向量与语义检索召回 Top-K',
          descriptionEn: 'Retrieve Top-K candidates via vector index',
        },
      },
      {
        kind: 'single',
        step: {
          id: 'step_ragas_judge',
          nameZh: 'RAGAS裁决',
          nameEn: 'Ragas Judge',
          unitZh: '维度',
          unitEn: 'dims',
          engineKey: 'Semantic',
          engineNameZh: '语义分析',
          engineNameEn: 'Semantic',
          taskTypes: ['quality_gate'],
          descriptionZh: '评估排布精度、覆盖率与忠实度',
          descriptionEn: 'Judge precision, recall, and faithfulness',
        },
      },
      {
        kind: 'single',
        step: {
          id: 'step_metric_assert',
          nameZh: '门禁断言',
          nameEn: 'Metric Assert',
          unitZh: '断言',
          unitEn: 'asserts',
          engineKey: 'Semantic',
          engineNameZh: '语义分析',
          engineNameEn: 'Semantic',
          taskTypes: ['quality_gate'],
          descriptionZh: '调和指标比对与抗熵增熔断判定',
          descriptionEn: 'Assert baseline and guard against entropy',
        },
      },
    ]
  }

  // 知识自愈优化 (Knowledge Remediation): 四工序闭环自愈流
  if (taskType === 'knowledge_remediation' || taskType === 'entropy_healing') {
    return [
      {
        kind: 'single',
        step: {
          id: 'step_fault_locate',
          nameZh: '病灶定位',
          nameEn: 'Fault Locate',
          unitZh: '处',
          unitEn: 'faults',
          engineKey: 'Semantic',
          engineNameZh: '语义提取',
          engineNameEn: 'Semantic',
          taskTypes: ['knowledge_remediation'],
          descriptionZh: '解析门禁未通过用例并反查病灶资源切片',
          descriptionEn: 'Locate failed cases and map fault resource chunks',
        },
      },
      {
        kind: 'single',
        step: {
          id: 'step_conflict_arbitrate',
          nameZh: '冲突仲裁',
          nameEn: 'Conflict Arbitrate',
          unitZh: '项',
          unitEn: 'items',
          engineKey: 'Semantic',
          engineNameZh: '语义提取',
          engineNameEn: 'Semantic',
          taskTypes: ['knowledge_remediation'],
          descriptionZh: '新旧事实版本仲裁并对过期切片墓碑标记',
          descriptionEn: 'Arbitrate conflicting facts and tombstone stale chunks',
        },
      },
      {
        kind: 'single',
        step: {
          id: 'step_targeted_distill',
          nameZh: '靶向重蒸馏',
          nameEn: 'Targeted Distill',
          unitZh: '篇',
          unitEn: 'docs',
          engineKey: 'Semantic',
          engineNameZh: '语义提取',
          engineNameEn: 'Semantic',
          taskTypes: ['knowledge_remediation'],
          descriptionZh: '针对目标文件重新生成密集的L0/L1多尺度摘要',
          descriptionEn: 'Re-distill dense L0/L1 multi-scale summaries',
        },
      },
      {
        kind: 'single',
        step: {
          id: 'step_delta_reindex',
          nameZh: '增量重索引',
          nameEn: 'Delta Reindex',
          unitZh: '切片',
          unitEn: 'chunks',
          engineKey: 'Embedding',
          engineNameZh: '向量计算',
          engineNameEn: 'Vector Embedding',
          taskTypes: ['knowledge_remediation'],
          descriptionZh: '局部更新向量嵌入与HNSW索引临近边',
          descriptionEn: 'Patch vector embeddings and update HNSW graph edges',
        },
      },
    ]
  }

  const flow = TASK_FLOWS.find((f) => f.typeKey === taskType)
  if (!flow) return []
  const items: TaskFlowItem[] = []
  for (const id of flow.stepIds) {
    const step = ALL_PANORAMA_STEPS.find((s) => s.id === id)
    if (step) {
      items.push({ kind: 'single', step })
    }
  }
  return items
}
