// Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: AGPL-3.0

export interface DehydrationResult {
  original_chars: number
  compressed_chars: number
  original_tokens: number
  compressed_tokens: number
  tokens_saved: number
  compression_ratio: number
  structural_fidelity: number
  frozen_blocks_count: number
  latency_ms: number
  engine_used: string
  dehydrated_content: string
}

export interface DehydrationStats {
  total_documents: number
  total_tokens_saved: number
  avg_compression_ratio: number
  avg_latency_ms: number
  active_engine: string
  is_model_loaded: boolean
}

export interface ApplyResult {
  success: boolean
  mode: string
  target_uri: string
  target_path: string
  snapshot_path: string
  original_chars: number
  dehydrated_chars: number
  saved_chars: number
  provenance_event_id: string
}

export const PRESET_SAMPLES: Record<string, { title: string; content: string; uri: string }> = {
  spec: {
    title: '架构规格书',
    uri: 'viking://resources/master_memory/decisions/context_engine_spec.md',
    content: `---
title: OpenViking Context Engine Architecture Specification
version: 1.5.46
category: knowledge-base
---

# 模块设计规范与第一性原理
众所周知，代码库必须拥有清晰高内聚的领域接缝。
显而易见的是，我们必须严格遵守单文件 100 到 300 行的黄金甜点区红线。
毋庸置疑的是，严禁任何人在代码库中引入未经脱水审计的外部臃肿包。
值得注意的是，我们必须保护否定词和控制词，严禁反转核心语义。

\`\`\`python
def evaluate_gate(rate: float) -> bool:
    # 绝对禁止任何绿色，统一采用冰青信号
    assert rate >= 0.50
    return True
\`\`\`

总的来说，归根结底，正如前文所述，系统必须兼顾极致性能与零幻觉。`,
  },
  whitepaper: {
    title: '压缩白皮书',
    uri: 'viking://resources/master_memory/decisions/compression_whitepaper.md',
    content: `---
title: Multi-Engine Context Compression Whitepaper
version: 1.5.46
---

# 课题五：多引擎分级智能压缩体系架构
在现代大规模智能体系统中，上下文膨胀消耗推理 Token 并诱发中间信息衰减。
从某种角度来看，众所周知的是，传统的单一截断策略无法兼顾精度与结构完整性。
具体来说，本系统设计了三层正交压缩矩阵：
1. 阿里 SkillZip：针对可执行流程进行确定性 6 元组规约；
2. Notes-History：针对多轮对话历史进行动态结晶；
3. 微软 LLMLingua-2：针对自然语言 Wiki 文档进行毫秒级抽稀，削减 50% 水话冗余。

\`\`\`bash
# 启动脱水后台任务
openviking wiki dehydrate --rate 0.50 --threshold 0.35
\`\`\`

正如前文所述，整个过程绝对禁止常驻显存，保障 2080Ti 纯净。`,
  },
}
