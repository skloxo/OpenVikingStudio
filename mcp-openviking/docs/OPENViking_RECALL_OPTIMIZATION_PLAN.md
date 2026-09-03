# OpenViking (vk) 记忆召回与 MCP 架构迭代优化方案

> **文件位置**: `/home/skloxo/aho/openclaw/mcp-openviking/docs/OPENViking_RECALL_OPTIMIZATION_PLAN.md`  
> **创建日期**: 2026-07-28  
> **状态**: 草案 / 待迭代验证  

---

## 一、 背景与现有表现评估

在最近的实测基准测试中，OpenViking 展现出了优秀的向量语义召回能力：
- **召回延迟**: ~1.8 秒
- **Top-1 语义相关度**: 达到 **0.997**（针对“OpenWiki 前端重构 像素级一致”）
- **分级摘要**: 支持 `Level 0 (.abstract.md)` / `Level 1 (.overview.md)` / `Level 2 (Full Detail)` 渐进式折叠展示

但在高频多代理协同与极速交互场景下，仍存在以下待优化瓶颈与演进空间。

---

## 二、 核心优化维度与技术方案

### 1. MCP 指令适配层与降级容错机制 (Command Mapping & Fallback)

* **存在问题**:  
  当 MCP 工具（如 `openviking_code_search` / `openviking_store`）向底层 CLI 发送 `ov code search` 或 `ov commit` 时，由于底层的 `ov` CLI 子命令变更，会抛出 `未知命令: code / commit` 的错误。
* **优化方案**:
  - 在 `mcp_openviking_server.py` 中增加**指令映射代理模块 (Command Translation Layer)**。
  - 将 `code_search` 自动转译为带精准路径过滤的 `ov search --uri=viking://code/`。
  - 将 `store` / `commit` 指令捕获并静默路由至 REST API (`http://127.0.0.1:1933/api/v1/search/store`) 或直接写入文件图谱。

---

### 2. 混合检索算法 (Hybrid RAG: Dense Vector + Lexical BM25)

* **存在问题**:  
  纯向量检索在理解自然语言意图时效果极佳（0.997 高分），但在检索**精准代码符号、具体函数名（如 `useStudioStore`）或微小报错日志**时，Embedding 可能发生语义稀释。
* **优化方案**:
  - 引入 **Dense + Sparse 混合双通道召回**：
    1. **向量通道**：用于捕捉长文本、架构意图与上下文语义。
    2. **BM25 / Ripgrep 通道**：用于精确匹配类名、变量名、错误码。
  - **RRF (Reciprocal Rank Fusion) 重排序**：综合两通道得分重新输出 Top-K。

---

### 3. REST API 接口规范统一与 LRU 热点缓存

* **存在问题**:  
  HTTP POST `/api/v1/search/find` 与 CLI `ov search` 的 Payload 参数解析存在少许差异，造成直接 HTTP 请求时的字段兼容问题。
* **优化方案**:
  - **Payload 兼容层**：统一支持 `{"query": "..."}` 与 `{"q": "..."}` 及 URL Query 参数。
  - **内存级热点缓存 (LRU Cache)**：对高频调用的开局记忆查询（如 `master_memory` / `global_rules`）增加 60 秒的内存 LRU Cache，将热点召回耗时从 **1.8秒 提升至 < 50毫秒**。

---

### 4. 上下文 Token 动态控制 (Level-Filtered Retrieval)

* **优化方案**:
  - 允许 MCP 工具在调用 `openviking_find` 时传入 `level` 参数（例如 `level=1` 仅返回 Overview，`level=0` 仅返回 Abstract）。
  - 在大模型 Context 上下文空间紧张时，默认采用 Level 0/1 摘要召回，仅在明确需要细粒度代码实现时才展开 Level 2，显著节省 Prompt Token 消耗。

---

### 5. 跨项目 Master Memory 共享集中化

* **优化方案**:
  - 将所有 IDE 会话记忆统一归档至 `viking://resources/master_memory/` 节点。
  - 解决由于 IDE 会话切换导致的记忆断层问题，确保跨账户、跨会话 100% 连贯同频。

---

## 三、 实施 roadmap

| 阶段 | 优化项 | 优先级 | 预期收益 |
| :--- | :--- | :--- | :--- |
| **Phase 1** | MCP 指令适配层 (`mcp_openviking_server.py` 修复) | **P0 (紧急)** | 消除 `ov code` 命令错误，提升 MCP 稳定性 |
| **Phase 2** | LRU 内存缓存与 API Payload 兼容 | **P1 (高)** | 将热点召回耗时由 1.8s 降至 < 50ms |
| **Phase 3** | Hybrid RAG 混合检索（向量 + 代码精确符号） | **P1 (高)** | 代码符号检索准确率达到 100% |
| **Phase 4** | Level 0/1/2 动态 Context 节能调控 | **P2 (中)** | 减少 60%+ 的记忆注入 Token 消耗 |

EOF
