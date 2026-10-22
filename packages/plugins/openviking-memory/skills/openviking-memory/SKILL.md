---
name: openviking-memory
description: OpenViking 体外大脑核心记忆操作规范 — 指导 Agent 在开局检索历史经验、执行中精准查阅架构与凭据、任务结束时将关键决策与经验教训持久化回写至 Master Memory。
---

# 🧠 OpenViking 核心记忆操作规范 (openviking-memory)

> **物理第一性原理**：单个会话的上下文容量是有限且易失的，而体外大脑是跨越会话、跨越智能体、跨越物理节点的唯一持久化真相源 (SSOT)。

---

## 一、记忆生命周期循环 (The Recall-Execute-Persist Loop)

```
[任务启动] ──────► [任务推进] ──────► [任务收尾]
    │                    │                  │
    ▼                    ▼                  ▼
openviking_find    openviking_read    openviking_write /
(意图先验召回)      (切片按需深读)     openviking_record_evolution_lesson
```

---

## 二、标准工具调用准则

### 1. 开局先验检索 (`openviking_find`)
- **原则**：面对复杂架构、未知的项目规范或历史设计决策时，优先调用 `openviking_find(query="...")`；
- **目标空间**：系统优先从公共共享层 `viking://resources/master_memory/` 召回高确定性事实；
- **防重复盲搜**：若 Hook 已在调用前注入了相关记忆摘要，直接阅读上下文，禁止相同 query 盲搜。

### 2. 精准按需深入 (`openviking_read` / `openviking_smart_read`)
- **原则**：摘要不足以支撑精准编码时，使用 URI 直接读取完整文件；
- **分层读取**：对于特大文档，可指定分层级别（L0 摘要、L1 骨架、L2 全文），保护工作记忆。

### 3. 永久沉淀回写 (`openviking_write` / `openviking_record_evolution_lesson`)
- **架构决策与规范**：写入 `viking://resources/master_memory/...`；
- **踩坑与故障反思**：调用 `openviking_record_evolution_lesson`，系统自动写入本地技能与 Master Memory 双写存盘，形成智力复利。
