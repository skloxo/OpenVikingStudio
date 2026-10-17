// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

export interface ValetPreset {
  id: string
  name: string
  description: string
  uri: string
  content: string
  source: string
  caller: string
  isBatch?: boolean
  batchItems?: Array<{ uri: string; content: string }>
}

export const VALET_INGESTION_PRESETS: ValetPreset[] = [
  {
    id: 'preset-fast-handover',
    name: '前门极速入库与物理泊车',
    description: '单次知识毫秒级交接 (<10ms)，返回 HTTP 202 Accepted 与 ValetTicket 凭据',
    uri: 'viking://resources/architecture/wal_pipeline.md',
    content: `# OpenViking WAL & Ingestion Architecture
OpenViking 采用预写日志 (WAL) 与单写多读并发架构。
前门服务在 <10ms 内完成物理落地与票据签发，后台异步准入门禁负责去噪去重。
该设计彻底解除前门阻塞，保护主服务吞吐量。`,
    source: 'ide_cockpit',
    caller: 'CommanderAgent',
  },
  {
    id: 'preset-dedup-barrier',
    name: '冗余碎片静默合并与反熵门禁',
    description: '投递高重合度或低信息熵碎片，触发 AntiEntropyGate 的去重与静默合并',
    uri: 'viking://resources/architecture/wal_pipeline_dup.md',
    content: `# OpenViking WAL & Ingestion Architecture (Duplicate)
OpenViking 采用预写日志 (WAL) 与单写多读并发架构。
前门服务在 <10ms 内完成物理落地与票据签发，后台异步准入门禁负责去噪去重。
该设计彻底解除前门阻塞，保护主服务吞吐量。`,
    source: 'ide_cockpit',
    caller: 'DuplicateTester',
  },
  {
    id: 'preset-batch-ingestion',
    name: '批量知识并发交接与队列吞吐',
    description: '批量分发多条结构化领域知识，验证批处理票据分发与队列消费能力',
    uri: 'viking://resources/batch/overview.md',
    content: `# Batch Ingestion Overview
验证批量前门投递与异步排队执行性能。`,
    source: 'batch_worker',
    caller: 'BatchDistributor',
    isBatch: true,
    batchItems: [
      {
        uri: 'viking://resources/batch/item_1.md',
        content: '# Item 1: Metal 4 Shader Concurrency\nMetal 4 enables multi-queue GPU command stream submission.',
      },
      {
        uri: 'viking://resources/batch/item_2.md',
        content: '# Item 2: MLX Continuous Batching\nMLX-LM supports dynamic prompt caching with zero VRAM fragmentation.',
      },
      {
        uri: 'viking://resources/batch/item_3.md',
        content: '# Item 3: Vector Index HNSW M=16\nQuantized vectors achieve 99.2% recall with 4x memory compression.',
      },
    ],
  },
]
