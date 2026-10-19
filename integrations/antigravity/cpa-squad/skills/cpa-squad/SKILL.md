---
name: cpa-squad
description: OpenViking 跨模型算力工兵与多智能体协同专用技能。涵盖第二意见交叉核验 (cpa_consult) 与大规模并发扇出 (cpa_fanout) 调度 SOP。
---

# ⚡ CPA 算力协同工兵技能 (CPA Squad Ops)

## 一、核心物理契约与第一性原理

1. **第二意见对抗审讯 (Second Opinion Cross-Check)**：
   - 面对高难度算法架构选型或难以排查的疑难 Bug，避免单模型认知偏见；
   - 调用 `openviking_cpa_consult` 引入外部模型（如 DeepSeek-R1 / V3）进行异构第二意见交叉核验。

2. **并发扇出极速调研 (Concurrent Fanout)**：
   - 当需要针对大批量文档、文件或待办项进行并行处理时，调用 `openviking_cpa_fanout`；
   - 依托轻量模型工兵并发扇出，带全局超时熔断守护，秒级脱水交付。

---

## 二、标准工具调用

1. **`openviking_cpa_consult`**：
   - 参数：`prompt`, `model`, `sys_prompt`, `timeout=25`
   - 用途：单点深度推演咨询。

2. **`openviking_cpa_fanout`**：
   - 参数：`items`, `task_prompt`, `concurrency=4`, `timeout=30`
   - 用途：批量分块处理与并发脱水聚合报告。
