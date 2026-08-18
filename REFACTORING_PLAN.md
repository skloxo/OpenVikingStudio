# 🗺️ OpenViking (Viking/VK) 唯一原子化任务卡片总看板 (REFACTORING_PLAN.md - SSOT)

> **项目归属**：`OpenVikingStudio` (全栈统一 Monorepo)  
> **唯一真相源 (SSOT)**：本文档是 OpenViking 项目所有前后端演进、上游合并、架构重构与工单排期的唯一物理收口文档。  
> **双轨开发与环境准则**：
> 1. **1936 为开发测试环境**：所有修改 100% 在源码中完成，通过 Vite HMR 50ms 热更新测试与走查；
> 2. **1933 为生产正式环境**：1936 验收通过后，再同步更新至 1933 正式环境；
> 3. **自动迭代与留痕**：每完成一张原子任务卡片，标记 `[x] 已验收通过 ✅`，记录 Commit Hash，自动迭代版本号并打 Git Tag 推送。

---

## 🏗️ 第一部分：前后端仓库归一与 Monorepo 物理收口

### 📌 P0-MONO: [x] TASK-MONO-01：前后端全栈工程归一与单仓库 (Monorepo) 物理收口 ✅
- **模块**：工程架构 / 仓库治理 ｜ **优先级**：P0（最高）
- **目标**：彻底消除前后端双仓库切换的开发摩擦，将 Python 后端引擎物理迁入 `OpenVikingStudio` 仓库，实现前后端统一单仓库协同修改、统一提交与版本管控。
- **交付内容**：
  - [x] **代码物理搬迁**：将 Python 后端核心源码（`openviking`, `openviking_cli`, `native_src`, `third_party`, `tests`, `sdk`, `build_support`, `crates`）完整移入 `OpenVikingStudio/`，配置统一 Monorepo；
  - [x] **可编辑包重定向**：执行 `pip install -e /home/skloxo/aho/openclaw/project/OpenVikingStudio` 重新编译安装；
  - [x] **物理安装验证**：`pip show openviking` 输出 Editable project location 为 `/home/skloxo/aho/openclaw/project/OpenVikingStudio`；
  - [x] **双轨服务验证**：1933 正式环境与 1936 开发测试环境均 100% 正常启动且健康探针输出 `{"status":"ok"}`；
  - [x] **上游隔离保护**：在根目录创建 `upstream-ref/` 并在 `.gitignore` 中物理屏蔽，专供上游对比与技术研究。

### 📌 P0-EMBED: [x] TASK-EMBED-CHUNK-01：向量网关自动语义切片 (Chunk Embedding) 与超长记忆入库自愈 ✅
- **模块**：向量网关 / 队列中间件 / 存储引擎 ｜ **优先级**：P0
- **目标**：解决记忆文档（Memories）与超长 Markdown（>4096 Tokens）因绕过 Parser 导致 embedding 抛出 400 超长报错与死循环重试问题，实现零文件系统变动的向量网关层透明分块切片。
- **交付内容**：
  - [x] **语义分块算子**：`openviking/utils/embedding_input.py` 新增 `split_embedding_chunks`，按标题与自然段落分块（1500 Tokens 窗口 + 150 Tokens 重叠度）；
  - [x] **多 Chunk 向量映射**：`openviking/storage/collection_schemas.py` 集成自动切片，自动为多 Chunk 分配确定性向量 ID（`{id_seed}:chunk_{idx}`）并批量写入 VikingDB；
  - [x] **死循环拦截与自愈**：切除 Fallback 向量生成后的意外 Re-enqueue 穿透分支，彻底杜绝 15000+ 次死循环；
  - [x] **单元与实测双全通过**：`test_embedding_chunking.py` 5/5 全部通过，并在生产 60KB 真实记忆文件（`Vibe-Trading A股技术评估完成.md` 38,832 字符）实测成功自动拆为 15 个 Chunk 向量秒级完成索引。
- **交付版本**：`v1.3.5` ｜ **交付 Commit**：`8fde13a`

---

## 🗺️ 第二部分：上游 OpenViking 全景演进与合并原子化看板 (112 Commits Full Roadmap)

| 任务卡片 ID | 模块领域 | 包含上游核心特性 | 上游 Commits | 物理验收条件 | 计划 Tag 版本 | 当前状态 |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **Task Card 1** | **并发锁与 TaskTracker 融合 + Studio v1.3.4** | TaskTracker 细粒度锁池 (`KeyedAsyncLockPool`)、Store I/O 限制、终态 Guard 统一、Studio 视觉瓦片修复 | `7038ba06`, `9113fc92`, `b8738e05`, `bb82c376` | `test_task_tracker_concurrency.py` PASS, 113/113 测试通过, 1933 健康上线 | `v1.3.4` | [x] 已验收并交付 ✅ (Commit: `1ca76e53`, Tag: `v1.3.4`) |
| **Task Card 2** | **Agent 演进与经验记忆** | Agent 演进服务、经验血缘追踪 (`experience_lineage.py`)、OpenClaw 经验工具 | `61c42e3b`, `73a70195`, `2ced3f15` | `test_api_agent_evolution.py` PASS, 22/22 演进测试全过, 1933 健康上线 | `v1.3.6` | [x] 已验收并交付 ✅ (Tag: `v1.3.6`) |
| **Task Card 3** | **QueueFS & Redis 集群化** | QueueFS 支持 Redis 单机/集群/哨兵模式、启动有界过期任务清扫 (0/30/60) | `8c9c2282`, `758fc7f0` | `test_config_validation.py` PASS | `v1.3.6` | ⏳ 待开始 |
| **Task Card 4** | **Session 自动提交 V2** | Session 自动提交服务 (`SessionAutoCommitService`)、局部捕获异常断点恢复 | `d2056e97`, `0ab48f96`, `8e98a3c7` | `test_session_auto_commit.py` PASS | `v1.3.7` | ⏳ 待开始 |
| **Task Card 5** | **服务端上下文统一召回** | `/search mode="context"` 组装、分层预算裁剪 (`context_assembler`)、Rerank L1 对齐 | `2cc96e39`, `674f5e60`, `cbc39077` | `test_context_assembler_pipeline.py` PASS | `v1.3.8` | ⏳ 待开始 |
| **Task Card 6** | **企业级认证 (OIDC/LDAP)** | OIDC / LDAP 企业级身份插件、Watch 任务刷新安全 ACL、执行解析器加固 | `444cc87b`, `21029f40`, `03bd4694` | `test_ldap_auth.py` PASS | `v1.3.9` | ⏳ 待开始 |
| **Task Card 7** | **Storage & VikingFS 容错** | `mkdir` 错误主动透传、`mv` 突破 1000 节点深拷贝、废弃向量后端清理 | `0205914d`, `ecab57e1`, `1d02a72b` | `test_mv_copy_node_limit.py` PASS | `v1.3.10` | ⏳ 待开始 |
| **Task Card 8** | **Markdown 与内容写入增强** | `content_write` 处理模式、解析后不拆分 (`no_split`)、CJK Token 预算对齐 | `6f43a404`, `8d1d52fe`, `3087f943` | `test_markdown_split_token_budget.py` PASS | `v1.3.11` | ⏳ 待开始 |

---

## ⚡ 第三部分：当前活跃与待调度 Studio 原子工单 (Scheduled Active Task Cards)

### 📌 P0: [ ] [TASK-VERSION-TIMELINE-01] .md 文档资源“查看文件版本”时间轴与“点击回滚版本”功能移植
- **模块**：OpenVikingStudio 前端 (`src/routes/resources`)
- **工单 ID**：`TASK-VERSION-TIMELINE-01` ｜ **优先级**：P0（最高）
- **目标**：在 1936 资源管理页中，当选中 `.abstract.md` / `.overview.md` 或常规 `.md` 文档时，右上角提供【查看历史版本】按钮，展开版本时间轴并支持一键还原回滚。
- **验收标准**：
  - [ ] 历史版本列表倒序渲染版本号、时间戳、说明与作者；
  - [ ] 提供 Diff 差异高亮比对；
  - [ ] 点击【回滚至此版本】成功触发还原并刷新列表。

---

### 📌 P0: [x] [TASK-SKILL-SCANNER-01] 全自动配置驱动技能扫描与自愈同步引擎 (SSOT Skill Scanner) ✅
- **模块**：后端 SkillScanner + 前端 Skills Route ｜ **优先级**：P0
- **交付内容**：
  - [x] 在 `~/.openviking/ov.conf` 的 `skills.sources` 中固化全域 10 大源路径；
  - [x] `openviking/server/skill_scanner.py` 实现配置驱动的递归扫描与 YAML 解析；
  - [x] 服务启动时自动扫描，并在后台按 300s 周期自愈同步；
  - [x] 准确索引去重后的全量 **682** 项技能。

---

### 📌 P1-1: [ ] [TASK-MODEL-PERSIST-01] AI 模型监控时序分桶持久化与趋势分析引擎 (Model Metrics Time-Series Persistence & Trend Engine)
- **模块**：后端 Observability / Storage (`models_tracker.py`, `models_observer.py`, 时序存储) + 前端 Monitoring (`model-monitoring-card.tsx`, 趋势分析图表)
- **工单 ID**：`TASK-MODEL-PERSIST-01` ｜ **优先级**：P1
- **目标**：以**时间序列（小时 1h / 天 1d）分桶落盘**为核心，对全量 4 大模型（VLM `command-r-plus`、Embedding `Qwen3-Embedding-8B`、Rerank `qwen3-reranker-0.6b`、Compressor `LLMLingua-2`）的调用量、Tokens 消耗与时延进行结构化持久化，为系统容量规划、Token 成本控制与模型调用调优提供精确的数据支撑。
- **技术方案与交付内容**：
  - [ ] **时序分桶落盘架构 (Time-Bucket Persistence)**：在 `_system/models_usage/`（或 SQLite 库）中设计 `model_usage_buckets` 时序表，记录维度字段（`bucket_time`, `model_type`, `model_name`, `provider`, `calls`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `avg_latency_ms`）；
  - [ ] **多粒度聚合与趋势 API**：新增 `/api/v1/observer/models/trends` 端点，支持按 `1h` / `1d` 粒度查询任意时间窗口（24h / 7d / 30d / 全量）的调用与 Token 趋势；
  - [ ] **服务重启平滑聚合**：`ModelsObserver` 启动时自动聚合全量历史分桶数据，大盘卡片显示“历史总累计”与“周期增量”，彻底杜绝重启归零；
  - [ ] **全量 4 大模型全链路打通**：VLM、Embedding（`DenseEmbedder`）、Rerank（`RerankClient`）、LLMLingua 压缩器统一注入分桶上报探针；
  - [ ] **前端趋势分析面板**：`ModelMonitoringCard` 新增时序走势图，直观呈现不同时间段各模型的调用波峰波谷与 Token 吞吐变化，为业务调优提供直观依据。
- **物理验收条件**：
  - [ ] 模型数据按时间序列分桶落盘，支持任意历史时间区间的聚合与趋势回溯；
  - [ ] 重启 `openviking.service` 后历史累计与时序数据 100% 完整连续；
  - [ ] 全量 4 大模型指标完整覆盖，端到端测试与前端构建 0 报错。

### 📌 P1-2: [ ] [TASK-SKILL-METRICS-PERSIST-01] 技能中心与 Harness 遥测时序分桶持久化与决策优化引擎 (Skill & Harness Telemetry Time-Series Persistence Engine)
- **模块**：后端 Observability / System Router (`system.py`, SQLite 遥测审计表) + 前端 Skills Route (`src/routes/skills`)
- **工单 ID**：`TASK-SKILL-METRICS-PERSIST-01` ｜ **优先级**：P1
- **目标**：对技能中心 6 大核心遥测指标（隐式自动唤醒率、技能执行成功率、VK集中通道收效率、资产活跃复用率、Context 提示词压缩率、Harness 自演进成果）进行**时间序列（1h / 1d）分桶物理落盘持久化**，彻底摆脱进程生命周期限制，为技能生命周期治理、Agent 调度策略改进与服务调优提供坚实的数据证据。
- **技术方案与交付内容**：
  - [ ] **技能调用与遥测时序持久化表**：在 `_system/usage_audit/` 中建立 `skill_telemetry_audit` 表，记录每次技能被调用的明细（`timestamp_bucket`, `skill_name`, `trigger_type: implicit/explicit/mcp`, `duration_ms`, `tokens_saved`, `compression_ratio`, `is_success`）；
  - [ ] **多周期遥测 API**：扩展 `/api/v1/system/harness_metrics?window=24h|7d|30d|all`，支持按小时/按天分桶拉取历史趋势与聚合数据；
  - [ ] **服务调优决策数据支撑 (Decision Support Insights)**：
    - **资产健康度**：自动输出 Top 20 高频技能与 0 调用僵尸技能清单，指导资产瘦身；
    - **意图唤醒漏斗**：统计隐式意图唤醒 vs 显式指定比例，量化 Agent 自主调度精度；
    - **压缩收益时序**：记录 LLMLingua-2 实际 Token 节省走势，为动态调整压缩阈值提供实测基准；
  - [ ] **前端大盘多周期切换**：技能中心顶部支持在 `24H Rolling`、`近 7 天`、`近 30 天`、`全量历史` 之间平滑切换查看趋势。
- **物理验收条件**：
  - [ ] 技能遥测数据按时间分桶落盘，服务重启后历史数据 100% 连续；
  - [ ] 支持 24h / 7d / 30d 多维度查询且性能响应 < 50ms；
  - [ ] 单元测试与前端构建 0 报错。

---

### 📌 P1-3: [ ] [TASK-RETRIEVAL-TREE-01] 检索测试台 `/retrieval` 页 L0/L1 白盒检索轨迹树与得分渲染
- **模块**：OpenVikingStudio 前端 (`src/routes/retrieval`) ｜ **优先级**：P1
- **目标**：在 `/retrieval` 页面为每次检索结果渲染可折叠的 **L0/L1 白盒检索轨迹树**，展示 Viking 向量匹配路径与相似度分值（如 `Score: 0.985`）。
- **验收标准**：
  - [ ] 列表项右侧展现 `Level (L0/L1)` 徽章与 `Score: 0.985` 标签；
  - [ ] 展开轨迹树节点可查看 URI 继承关系；
  - [ ] 符合 `cyan-500` 冰青与 NO GREEN EVER 视觉规约；
  - [ ] `npm run build` 0 报错。

---

### 📌 P1-3: [ ] [TASK-MONITORING-CHARTS-01] 监控页 `/monitoring` Token 节省率与 SLA 时延对比折线图
- **模块**：OpenVikingStudio 前端 (`src/routes/monitoring`) ｜ **优先级**：P1
- **目标**：在 `/monitoring` 页新增双折线对比图，动态渲染有无 L0/L1 避坑拦截机制下的 Token 节省率（如 `82.4%`）及 P95 响应时延变化趋势。
- **验收标准**：
  - [ ] 成功绘制对比折线图，无数据点处显示虚线平滑过渡；
  - [ ] 符合 `cyan-500` 冰青主题与响应式自适应宽度。

---

### 📌 P2: [ ] [TASK-SKILL-DRAWER-01] 技能抽屉超长源码高亮与 TOC 目录结构化索引
- **模块**：技能中心 Detail Drawer ｜ **优先级**：P2
- **目标**：详情抽屉引入虚拟滚动 (Virtual List) 防止卡顿，自动提取 markdown `#` 标题生成侧边 TOC 快捷跳跃目录。

---

### 📌 P2: [ ] [TASK-SERVER-DOCTOR-01] 全局系统健康探针与一键自愈面板
- **模块**：OpenViking Server + Studio Sidebar ｜ **优先级**：P2
- **目标**：侧边栏增加健康诊断状态指示灯，遇到异常提供 `[一键重启/自愈 (ov server doctor)]` 触发按钮。

---

## 📅 第四部分：远期规划与 Epic 卡片 (Milestone Phase 2 & 3)

### 🚀 Milestone Phase 2：技能自演进闭环与质量门禁引擎
- **`[TASK-LOOP-01~07]` Epic-SKILL-LOOP 自进化闭环引擎**：修正事件数据模型、异常 Trace 自动捕获、`CONTEXT / REFLECTION / LESSON` 3 段式自动萃取、Lesson 审核 View、`SKILL.md` 受控版本更新与 Git 自动回滚。
- **`[TASK-SKILLOPT-01~03]` Epic-SKILLOPT 质量门禁引擎**：Attempt 执行引擎与 Judge Gate 评分验证器、健康评分与自动修复建议生成、技能权重动态微调与排名。

### 🚀 Milestone Phase 3：在线创生与端到端隐私安全治理
- **`[TASK-LIVEGEN-01~03]` Epic-LIVE-GEN Skill Live Generator**：SKILL.md 在线 Monaco 编辑器与 YAML Header 语法校验、沙盒环境模拟触发测试、一键自动向量化发布至 Viking 1933 存储。
- **`[TASK-PRIVACY-01~03]` Epic-PRIVACY-GOV 敏感信息二次授权**：服务端敏感字段检索二次过滤与鉴权、前端脱敏展示与安全开关、脱敏审计日志与导出隔离。

---

### [x] v1.3.6 版本已验收通过 🎉
- **Git Commit**: `6823b728`, Tag: `v1.3.6`
- **交付内容**：
  1. **Agent 演进与经验血缘追踪引擎 (`experience_lineage.py`)**：支持多形态工具调用血缘追踪与 5 态胜率统计；
  2. **演进查询与日期过滤 API**：实现 `/api/v1/agent-evolution/experiences/trajectories` 与 `/outcomes` 路由；
  3. **OpenClaw / 多 IDE 插件矩阵沉淀**：引入 `examples/` 全量插件与经验工具链。

### [x] v1.3.5 版本已验收通过 🎉
- **Git Commit**: `8fde13a`, Tag: `v1.3.5`
- **交付内容**：
  1. **单仓库 (Monorepo) 物理归一**：前后端统一收口至 `OpenVikingStudio`；
  2. **向量网关 Chunk 自动语义切片**：实现 1500 Tokens 黄金切片与多 Chunk 批量入库，根治长文本 400 报错；
  3. **GPU 穿透死循环拦截**：修复 Fallback 向量后的死循环入队，功耗彻底降回 42W；
  4. **模型架构白皮书 SSOT 建立**：创建 `docs/MODEL_ARCHITECTURE_SPEC.md`。

### [x] v1.3.4 版本已验收通过 🎉
- **Git Commit**: `1ca76e53` (openviking-shallow), Tag: `v1.3.4`
- **主要交付内容**：
  1. **TaskTracker 细粒度分片并发锁池 (`KeyedAsyncLockPool`)**：彻底移除全局锁阻塞，实现按 task_id 分片锁定；
  2. **终态生命周期 Guard 保护**：统一 `COMPLETED` / `CANCELLED` / `FAILED` 终态不可逆规则；
  3. **模型四分类精准监控与隔离**：修复 Token Tracker 全局共享污染，精准拆分为 VLM (`command-r-plus`)、Embedding (`Qwen3-Embedding-8B`)、Rerank (`qwen3-reranker-0.6b`)、LLMLingua-2 (`xlm-roberta`) 4 大独立模型监控。

### [x] v1.3.3 版本已验收通过 🎉
- **Git Commit**: `4d14832` (OpenVikingStudio), `feat/task-center-stats-autohealing-v2` (openviking-shallow)
- **Git Tag**: `v1.3.3`
- **交付内容**：
  1. **SSOT 配置化技能发现引擎**：自动全量扫描 10 大源目录，稳定汇聚 682 项技能；
  2. **极客性冷淡视觉规范全面遵从**：字号硬下限严格 $\ge 11\text{px}$，100% NO GREEN EVER；
  3. **1936 开发环境与 1933 正式环境双轨架构建立**。

### [x] v1.3.0 ~ v1.3.2 补丁版本已验收通过 ✅
- **交付 Tag**：`v1.3.0` / `v1.3.1` / `v1.3.2`
- **内容**：多语言 i18n 体系 100% 覆盖、Parser CJK Token 准确估算、任务自愈重新入队引擎、MCP 无状态 HTTP 与超时控制。

---

## 🎨 第六部分：无头功能 (API-Only) 可视化专项工单矩阵

> **目标**：在上游后端合并全部完成后，对以下 **8 大“有 API 无界面”的后端核心能力** 逐一进行 Studio 可视化页面建设与交互闭环。

| 工单 ID | 对应后端路由 / 模块 | 核心可视化交付目标 | 优先级 |
| :--- | :--- | :--- | :---: |
| **`TASK-UI-AGENT-EVOL-01`** | `routers/agent_evolution.py` | **Agent 经验实战胜率与调用轨迹面板**：在经验详情抽屉展示被调用次数、5 态胜率环形图、历史关联任务列表与血缘谱系。 | 🔴 P1 |
| **`TASK-UI-WATCHES-01`** | `routers/watches.py` | **资源自动订阅与 Watch 监控看板**：提供 GitHub Repo / Web 资源订阅任务管理、自动同步触发器、运行流水线日志查看。 | 🔴 P1 |
| **`TASK-UI-PRIVACY-01`** | `routers/privacy_configs.py` | **隐私安全与敏感信息脱敏治理中心**：脱敏规则配置、敏感字段打码开关、二次授权弹窗与合规审计日志导出。 | 🟡 P2 |
| **`TASK-UI-OVPACK-01`** | `routers/pack.py` | **知识大脑一键打包与迁移导入中心**：提供 OVPack 便携知识包一键导出、本地 ZIP 拖拽导入与解包校验面板。 | 🟡 P2 |
| **`TASK-UI-SNAPSHOT-01`** | `routers/snapshot.py` | **VikingFS 物理快照与历史版本回滚中枢**：全盘快照时间线、快照内容树比对、一键安全还原与灾备演练。 | 🟡 P2 |
| **`TASK-UI-RELATIONS-01`** | `routers/relations.py` | **知识图谱关系与血缘动态编辑面板**：资源与记忆 Link / Unlink 交互连线、关系类型打标与多跳图谱遍历。 | 🟢 P3 |
| **`TASK-UI-WEBDAV-01`** | `routers/webdav.py` | **WebDAV 挂载与网络存储连接管理面板**：一键生成/吊销 WebDAV 挂载凭据、连接指引（Windows/Mac 挂载盘）与实时流量。 | 🟢 P3 |
| **`TASK-UI-OBSERVER-01`** | `routers/observer.py` | **实时事件观测流与慢查询白盒调试器**：Server-Sent Events (SSE) 实时事件流水、向量检索慢查询火焰图与白盒 Trace。 | 🟢 P3 |
