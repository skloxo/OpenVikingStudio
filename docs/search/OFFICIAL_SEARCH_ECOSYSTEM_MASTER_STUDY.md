# 🌐 全球顶尖 AI 搜索生态系统深度研究与官方规范全景白皮书 (Master Study)
> **生成时间**: 2026-10-11 23:10:35 CST  
> **核心支持**: OpenViking CPA mux-flash 深度推理工兵群  
> **覆盖厂商**: Keenable (80万次/月), Exa ($90/月), Tavily (9,000分/月), SearXNG, Crawl4AI  

---

## Keenable 80万次月配额与 NEEDLE 垂直架构深度分析

### 工兵任务报告：Keenable API 物理契约、NEEDLE 垂直实践与 80万配额最大化方案

---

### 第一部分：API 物理参数契约与 400 Bad Request 避坑规范

#### 1. 核心物理契约 (JSON Schema 约束)
为确保请求 100% 合规，必须严格遵守以下物理参数类型、必填项及默认值约束：

| 参数名 | 类型 | 必填 | 默认值 | 约束与物理限制说明 |
| :--- | :--- | :--- | :--- | :--- |
| `query` | `string` | **是** | 无 | 检索关键词或自然语言问题。长度建议限制在 500 字符以内，避免超长文本导致 token 溢出或语义稀释。 |
| `max_results` | `integer` | 否 | `10` | 返回结果数量。**绝对禁止使用 `num` 替代，否则直接触发 400。** 范围建议 `[1, 50]`。 |
| `mode` | `string` | 否 | `"fast"` | 枚举值：`"fast"`（极速）或 `"pro"`（高精度）。大小写敏感，全小写。 |
| `snippet_max_length` | `integer` | 否 | 系统动态 | 摘要片段字符上限。设为 `0` 可能导致无摘要，建议设为 `500` 或 `1000`

---

## Exa 神经意图检索与 Agent API (POST /agent/runs) 深度分析

**核心结论**：Exa `/agent/runs` 为同步长任务端点，需通过轮询获取结果；`/research` 已废弃。GitHub 检索最优参数为 `category:"github"` 且必须开启 `useAutoprompt`；`findSimilar` 竞品挖掘需结合 `excludeSourceDomain` 过滤噪声。$90/月额度流转方案依赖多账户密钥池化与额度监控自动化。

### 1. Agent API 深度解析（POST /agent/runs）
*   **架构变更**：旧 `/research` 端点返回 410 Gone，官方替换为 `/agent/runs`。
*   **参数机制**：
    *   `query`: 结构化自然语言指令，支持复杂多步调研逻辑（如“找出 X 竞品的最新融资并生成报告”）。
    *   `effort`: 算力消耗控制。`high` 触发深度多跳检索，耗时与 Credits 消耗呈非线性增长。
*   **长报告异步生成模式**：
    *   **非真正的异步**：`POST /agent/runs` 当前实现为**同步阻塞**或**长轮询**模式。
    *   **流程**：发送 POST 请求 -> 服务端启动 Agent 多步推理（内部调用 search/contents） -> 等待长连接或轮询状态 -> 返回最终报告 JSON。
    *   **最佳实践**：设置客户端超时阈值 > 60s，避免 HTTP 断连。若需真异步，需自建队列任务，将 `query` 封装为后台 Job，定时轮询 Agent 状态接口（若官方后续开放 status endpoint）。

### 2. GitHub 源码定位最佳参数
*   **端点**：`POST /search`
*   **配置策略**：
    *   `category`: `"github"` （强制过滤非代码内容）
    *   `type`: `"neural"` （优先语义匹配，优于 `"fast"` 的关键词匹配）
    *   `useAutoprompt`: `true` （自动优化查询词，提升召回率）
    *   `query`: 嵌入具体技术栈关键词（如 “react state management hook”）
*   **正文获取**：对返回的 `results[].url` 调用 `/contents`，设置 `contents.text: true` 获取清洗后的代码块，`highlights: true` 定位关键函数。

### 3. FindSimilar 竞品挖掘配置
*   **端点**：`POST /findSimilar`
*   **最佳参数**：
    *   `url`: 标杆竞品官网或核心文档 URL
    *   `numResults`: 15-20 （平衡覆盖率与相关性噪声）
    *   `excludeSourceDomain`: `true` （必须开启，避免返回同一竞品内部页面）
    *   **后续链路**：提取返回的相似 URL 列表 -> 批量调用 `/search` 或 `/contents` 获取这些站点的核心功能描述 -> 构建竞品功能矩阵。

### 4. $90/月 免费额度无缝流转方案
*   **资源池**：9 个 Exa 账户 x $10/月 = $90 总额度。
*   **架构设计**：
    1.  **密钥池化**：将 9 个 `x-api-key` 存入加密数据库（如 Redis 或 HashiCorp Vault），构建负载均衡中间件。
    2.  **额度监控**：每次请求后，记录各账户当日已用 Credits。Exa 通常按实时消耗扣减，需设置预警阈值（如 80%）。
    3.  **无缝流转逻辑**：
        *   请求到达时，中间件查询各账户剩余配额。
        *   优先路由至**剩余配额最高**的账户，避免单账户触顶导致 402/429 错误。
        *   若单账户本月额度耗尽（$10 用完），自动从活跃池中剔除，下月 1 日重置后重新注入。
        *   监控 `429 Too Many Requests` 错误，触发退避策略并切换备用密钥。
    4.  **合规风险**：9 个账户均为“免费账户赠送”，需确保注册邮箱/IP 独立性，避免被 Exa 风控判定为欺诈封禁。建议分散设备指纹与注册时间间隔。

### 执行检查单
*   [ ] 中间件支持 9 密钥动态路由与配额熔断
*   [ ] `/agent/runs` 客户端超时设为 90s
*   [ ] GitHub 检索固定启用 `category:"github"` + `useAutoprompt`
*   [ ] `findSimilar` 固定启用 `excludeSourceDomain: true`
*   [ ] 月度额度重置日（1日）自动恢复密钥池状态

---

## Tavily 官方端点全矩阵与 Bearer 鉴权闭环分析

# Tavily 四大端点深度解析、Cloudflare 穿透价值与 9 账户 9,000 积分调度方案

---

## 一、 Tavily 四大端点全矩阵与计费逻辑

| 端点 | 核心功能 | 关键参数 | 积分消耗标准 (Credits) | 核心战术价值 |
| :--- | :--- | :--- | :--- | :--- |
| **`/search`** | 多源联网搜索 | `query`, `search_depth` (basic/advanced), `include_answer`, `max_results`, `include_domains/exclude_domains` | **Basic:** 1.0 积分/次<br>**Advanced:** 2.0 积分/次 | 快速获取多源事实、摘要及背景信息。支持域控过滤，聚焦特定站点。 |
| **`/extract`** | 批量正文免爬虫清洗 | `urls` (List), `extract_depth` (basic/advanced) | **Basic:**

---