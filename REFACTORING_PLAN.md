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
| **Task Card 3** | **QueueFS & Redis 集群化** | QueueFS 支持 Redis 单机/集群/哨兵模式、启动有界过期任务清扫 (0/30/60) | `8c9c2282`, `758fc7f0` | `test_config_validation.py` PASS, 203/203 测试全过, 1933 健康上线 | `v1.3.8` | [x] 已验收并交付 ✅ (Tag: `v1.3.8`) |
| **Task Card 4** | **Session 自动提交 V2** | Session 自动提交服务 (`SessionAutoCommitService`)、局部捕获异常断点恢复 | `d2056e97`, `0ab48f96`, `8e98a3c7` | `test_session_auto_commit.py` PASS, 301/301 回归测试全过, 1933 健康上线 | `v1.3.9` | [x] 已验收并交付 ✅ (Tag: `v1.3.9`) |
| **Task Card 5** | **服务端上下文统一召回** | `/search mode="context"` 组装、分层预算裁剪 (`context_assembler`)、Rerank L1 对齐 | `2cc96e39`, `674f5e60`, `cbc39077` | `test_context_assembler_pipeline.py` PASS, 320/320 测试全过, 1933 健康上线 | `v1.3.10` | [x] 已验收并交付 ✅ (Tag: `v1.3.10`) |
| **Task Card 6** | **企业级认证 (OIDC/LDAP)** | OIDC / LDAP 企业级身份插件、Watch 任务刷新安全 ACL、执行解析器加固 | `444cc87b`, `21029f40`, `03bd4694` | `test_ldap_auth.py` PASS, 37/37 测试全过, 1933 健康上线 | `v1.3.11` | [x] 已验收并交付 ✅ (Tag: `v1.3.11`) |
| **Task Card 7** | **Storage & VikingFS 容错** | `mkdir` 错误主动透传、`mv` 突破 1000 节点深拷贝、废弃向量后端清理 | `0205914d`, `ecab57e1`, `1d02a72b` | `test_mv_copy_node_limit.py` PASS, 67/67 测试全过, 1933 健康上线 | `v1.3.12` | [x] 已验收并交付 ✅ (Tag: `v1.3.12`) |
| **Task Card 8** | **Markdown 与内容写入增强** | `content_write` 处理模式、解析后不拆分 (`no_split`)、CJK Token 预算对齐 | `6f43a404`, `8d1d52fe`, `3087f943` | `test_markdown_split_token_budget.py` PASS, 44/44 测试全过, 1933 健康上线 | `v1.3.13` | [x] 已验收并交付 ✅ (Commit: `cfd40888`, Tag: `v1.3.13`) |

---

## ⚡ 第三部分：当前活跃与待调度 Studio 原子工单 (Scheduled Active Task Cards)

### 📌 P0: [x] [TASK-VERSION-TIMELINE-01] .md 文档资源“查看文件版本”时间轴与“点击回滚版本”功能移植 ✅
- **模块**：OpenVikingStudio 前端 (`src/routes/resources`) + 后端 VikingFS (`openviking/storage/viking_fs/_snapshot.py`)
- **工单 ID**：`TASK-VERSION-TIMELINE-01` ｜ **优先级**：P0（最高）
- **目标**：在 1936 / 1933 资源管理页中，当选中 `.abstract.md` / `.overview.md` 或常规 `.md` 文档时，右上角提供【查看历史版本】按钮，展开版本时间轴并支持一键还原回滚。
- **交付内容与验收结果**：
  - [x] **宽屏主从两栏布局**：`w-[94vw] max-w-6xl h-[86vh]` 双栏时间轴对话框（左侧快照历史，右侧 Diff 与源码）；
  - [x] **全多语言国际化**：中英双语 21 个词条全量支持，彻底解决裸露 Key 问题；
  - [x] **智能回退与筛选**：支持【仅此文件变更】与【显示全盘快照】自由切换；
  - [x] **NO GREEN EVER 差异高亮**：新增行呈现冰青色 (`cyan-400`)，删除行呈现玫瑰红 (`rose-400`)；
  - [x] **后端 Diff 引擎兼容与别名映射**：`HEAD` -> `main` 自动映射，`difflib` 纯 Python 兜底，24 项快照测试 100% 通过；
  - [x] **一键安全回滚**：支持二次确认并调用 `/api/v1/snapshot/restore` 秒级恢复历史版本并自动刷新；
- **交付版本**：`v1.3.14` ｜ **交付 Commit**：`0c93a092` ｜ **交付 Tag**：`v1.3.14`

---

### 📌 P1: [x] [TASK-TASKCENTER-QUEUE-LINK-01] 任务中心切片级真实进度追踪与硬编码 45% 死锁根治 (Task Center Real-Time QueueFS Chunk Progress & Live Telemetry Linkage) ✅
- **模块**：OpenVikingStudio 前端 (`src/routes/tasks`) + 后端 `openviking/service/task_tracker.py`
- **工单 ID**：`TASK-TASKCENTER-QUEUE-LINK-01` ｜ **优先级**：P1（体验治理 / 真实数据流转）
- **核心痛点与背景**：
  1. 当前前端 [`src/routes/tasks/route.tsx:343`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/src/routes/tasks/route.tsx#L320-L344) 中的 `getTaskProgressPct` 存在保底硬编码 `return 45`。当 `admin_reindex` / `add_resource` 处于异步 `running` 状态且 `task.stage` 为 `null` 时，界面上的进度条被恒定死锁在 45%，给用户造成长达半小时假死/无响应的错觉。
  2. 任务中心单一任务 API (`/api/v1/tasks/{id}`) 与底层真实切片管道 API (`/api/v1/observer/system` 产出的 QueueFS Embedding / Semantic-Nodes 队列指标) 彻底割裂，未能在任务卡片与列表行中展示如 `1,737 / 2,826 切片` 的真实动态吞吐。
- **技术方案与交付成果**：
  - [x] **前端任务中心与 QueueFS 实时遥测联动**：在任务列表与任务详情中，自动聚合 QueueFS 当前的切片进度（`Processed / Total`），计算真实动态百分比，彻底切除 `return 45` 硬编码；
  - [x] **可视化切片进度标签**：状态徽章与列表行原生支持多语言切片进度显示：`X/Y 切片 (Z%)`；
  - [x] **后端任务自解释与动态阶段及 Meta 回写 (`task_tracker.py`)**：`update_stage` 支持伴随回写 `meta` 动态字典；
  - [x] **时间渐近平滑估算算法**：当阶段尚未初始化时，基于时间衰减平滑饱和曲线（$1 - e^{-t/25}$）自适应递增（15%~88%），永远告别假死；
  - [x] **测试全绿与构建零报错**：78/78 项 TaskTracker Python 测试全绿通过，前端 `vite build` 0 报错；
- **交付版本**：`v1.3.15` ｜ **交付 Commit**：`6cf396e9` ｜ **交付 Tag**：`v1.3.15`

---

### 📌 P0: [x] [TASK-SKILL-SCANNER-01] 全自动配置驱动技能扫描与自愈同步引擎 (SSOT Skill Scanner) ✅
- **模块**：后端 SkillScanner + 前端 Skills Route ｜ **优先级**：P0
- **交付内容**：
  - [x] 在 `~/.openviking/ov.conf` 的 `skills.sources` 中固化全域 10 大源路径；
  - [x] `openviking/server/skill_scanner.py` 实现配置驱动的递归扫描与 YAML 解析；
  - [x] 服务启动时自动扫描，并在后台按 300s 周期自愈同步；
  - [x] 准确索引去重后的全量 **682** 项技能。

---

### 📌 P0: [x] [TASK-FULL-TELEMETRY-PERSIST-01] 全系统遥测与大盘 16 瓦片统一时序持久化与基线恢复引擎 (Full-Stack Unified Telemetry & Dashboard Persistence Engine) ✅
- **模块**：后端 Observability (`telemetry_store.py`, `models_observer.py`, `retrieval_tracker.py`, SQLite 统一时序库) + 前端 全大盘瓦片 (`monitoring`, `skills`, `tasks`)
- **工单 ID**：`TASK-FULL-TELEMETRY-PERSIST-01` ｜ **优先级**：P0（最高优先级，彻底根除重启归零与空白）
- **核心痛点与目标**：
  彻底根治“服务一重启，大盘数据全归零 / 瓦片变 `--`”的严重体验痛点。将全系统所有观测指标与遥测数据（**4 大 AI 模型 Token / 调用数**、**上下文检索命中率 / 延迟 / 相似度**、**技能中心 6 大瓦片**、**监控大盘 16 项内核深层观测指标**）100% 统一纳入**本地 SQLite 时序持久化存储**，实现服务启动自愈加载历史基线，支持 24h / 7d / 30d / 全量历史无缝回溯，为服务优化与决策提供坚实数据支撑。
- **技术方案与交付内容**：
  - [x] **统一时序持久化存储层 (`telemetry_store.py`)**：在 `_system/telemetry/` 中建立统一 SQLite 库，设计 4 张核心时序表（`model_metrics_audit`, `retrieval_metrics_audit`, `skill_metrics_audit`, `system_metrics_snapshot`），采用 WAL 模式与异步批量写入队列（入队时延 < 1ms）；
  - [x] **服务启动零丢失基线恢复机制 (Zero-Loss Baseline Recovery)**：
    - `TokenUsageTracker` 启动时自动从 SQLite 读取历史累计 Token 与调用次数 (`hydrate_from_store`)；
    - `RetrievalStatsCollector` 启动时自动恢复检索基线（总检索数、命中率、平均分、历史延迟）；
    - 服务重启后，大盘所有 16 项瓦片与 4 大模型表格 **100% 立即展示真实历史累计数据**，永远不再出现 `--` 或 `0`；
  - [x] **多周期趋势与决策支撑 API**：
    - `/api/v1/observer/system`, `/models`, `/retrieval` 与 `/api/v1/system/harness_metrics` 原生支持 `?window=24h|7d|30d|all`；
    - 新增 `/api/v1/system/telemetry/trends?metric=sla|retrieval|tokens|embedding&window=...` 提供真实图表时序点；
  - [x] **前端大盘多周期自由切换**：在监控页支持自由切换时间范围（`24H` / `7D` / `30D` / `ALL`）与实时时序折线图（真实后端数据驱动，彻底切除 mock 假数据）。
- **物理验收结果**：
  - [x] 单元测试 `tests/telemetry/test_telemetry_store.py` 5/5 全部通过，全量 146 项测试全绿；
  - [x] 前端 `npm run build` 0 报错通过；
  - [x] 交付版本：`v1.3.7`。

---

### 📌 P1: [x] [TASK-RETRIEVAL-TREE-01] 检索测试台 `/retrieval` 页 L0/L1/L2 白盒检索轨迹树与得分渲染 ✅
- **模块**：OpenVikingStudio 前端 (`src/routes/retrieval`) ｜ **优先级**：P1
- **目标**：在 `/retrieval` 页面为每次检索结果渲染可折叠的 **L0/L1/L2 白盒检索轨迹树**，展示 Viking 向量匹配路径与相似度分值（如 `Score: 0.985`）。
- **交付内容与验收结果**：
  - [x] **物理匹配层级徽章**：列表项右侧展现 `L0` (Abstract) / `L1` (Overview/SOP) / `L2` (Detail 切片) 徽章；
  - [x] **相似度高信度标签**：`Score: 0.985` 标签自适应高信度（$\ge 0.70$ 门禁）着色；
  - [x] **白盒检索轨迹树展开**：支持折叠展开 Root 检索引擎、层级匹配链路、相似度得分、匹配理由（`match_reason`）及关联扩展节点（`relations`）；
  - [x] **一键复制 URI**：支持一键复制完整 URI 并提供 Toast 提示；
  - [x] **NO GREEN EVER 与字号规范**：100% 遵循 `cyan-500` 冰青主题，全面切除 `< 11px` 微小字体，硬下限 $\ge 11\text{px}$；
  - [x] **全量 i18n 国际化**：中英双语 10+ 词条完全平行维护；
  - [x] **构建验证**：`npm run build` 0 报错；
- **交付版本**：`v1.3.16` ｜ **交付 Commit**：`afe3a6ac` ｜ **交付 Tag**：`v1.3.16`

---

### 📌 P1-3: [x] [TASK-MONITORING-CHARTS-01] 监控页 `/monitoring` Token 节省率与 SLA 时延对比折线图 ✅
- **模块**：OpenVikingStudio 前端 (`src/routes/monitoring`) ｜ **优先级**：P1
- **目标**：在 `/monitoring` 页新增双折线对比图，动态渲染有无 L0/L1 避坑拦截机制下的 Token 节省率（如 `82.4%`）及 P95 响应时延变化趋势。
- **交付内容**：
  - [x] `sla-trend-chart.tsx` 动态对接真实 `/api/v1/system/telemetry/trends?metric=sla&window=...` 后端时序数据；
  - [x] 支持 `24H`/`7D`/`30D`/`ALL` 多周期联动；
  - [x] 100% 遵循 `cyan-500` 冰青主题与 NO GREEN EVER 视觉规范。

---

### 📌 P2: [x] [TASK-SKILL-DRAWER-01] 技能抽屉超长源码高亮与 TOC 目录结构化索引 ✅
- **模块**：技能中心 Detail Drawer (`src/routes/skills`) ｜ **优先级**：P2
- **目标**：详情抽屉引入全量源码语法高亮、TOC 结构化目录索引与行号平滑跳转，支持一键复制代码。
- **交付内容与验收结果**：
  - [x] **Markdown TOC 自动结构化提取**：`extractSkillToc` 自动解析 `#`~`####` 标题、行号及锚点；
  - [x] **交互式 TOC 快捷跳转面板**：支持展开/收起章节目录，点击章节平滑定位至对应代码行；
  - [x] **语法层级与行号高亮**：YAML Frontmatter (`---`, `name:`)、Markdown 标题、代码块及行号多语义高亮；
  - [x] **一键复制源码**：提供复制按钮与 Toast 提示；
  - [x] **NO GREEN EVER 与字号规范**：彻底清除 `< 11px` 微字，全盘采用 `cyan-500` / `sky-500` / `amber-500`；
  - [x] **多语言 i18n**：中英双语 6+ 词条平行维护；
  - [x] **构建验证**：`npm run build` 0 报错；
- **交付版本**：`v1.3.17` ｜ **交付 Commit**：`6b3a4257` ｜ **交付 Tag**：`v1.3.17`

---

### 📌 P2: [x] [TASK-SERVER-DOCTOR-01] 全局系统健康探针与一键自愈面板 ✅
- **模块**：OpenViking Server + Studio Sidebar (`src/components/server-doctor-dialog.tsx`, `src/components/app-shell.tsx`) ｜ **优先级**：P2
- **目标**：侧边栏增加健康诊断状态指示灯，实时监控 1933 RPC 服务与内核连接，提供白盒诊断面板与一键自愈触发能力。
- **交付内容与验收结果**：
  - [x] **侧边栏实时状态指示徽章**：在 Sidebar 设置区集成 `1933 核心健康 (Doctor)` 脉冲指示灯；
  - [x] **4 维系统核心诊断矩阵**：1933 RPC 核心信道（BaseURL、RTT 延时毫秒、Auth Mode）、AGFS 虚拟文件系统挂载状态、VectorDB 向量引擎状态与安全门禁凭据角色；
  - [x] **一键全自动系统物理自愈 (Run Doctor Pipeline)**：执行信道探测、AGFS 事务锁刷新、客户端通讯上下文复位与 React Query 缓存同步 3 步自愈流水线；
  - [x] **自愈实时终端流日志**：带时序时间戳与自愈步骤进度展示；
  - [x] **移动端适配与版本对齐**：移动端顶栏同步对齐动态版本号；
  - [x] **NO GREEN EVER 与字号规范**：100% 采用 `cyan-500` / `sky-500` / `amber-500` / `rose-500` 语义着色，字体 $\ge 11\text{px}$；
  - [x] **中英双语 i18n**：10+ 项词条平行收录；
  - [x] **构建验证**：`npm run build` 0 报错；
- **交付版本**：`v1.3.18` ｜ **交付 Commit**：`05462234` ｜ **交付 Tag**：`v1.3.18`

---

## 📅 第四部分：远期规划与 Epic 卡片 (Milestone Phase 2 & 3)

### 🚀 Milestone Phase 2：技能自演进闭环与质量门禁引擎
- **`[TASK-LOOP-01~07]` Epic-SKILL-LOOP 自进化闭环引擎**：修正事件数据模型、异常 Trace 自动捕获、`CONTEXT / REFLECTION / LESSON` 3 段式自动萃取、Lesson 审核 View、`SKILL.md` 受控版本更新与 Git 自动回滚。
- **`[TASK-SKILLOPT-01~03]` Epic-SKILLOPT 质量门禁引擎**：Attempt 执行引擎与 Judge Gate 评分验证器、健康评分与自动修复建议生成、技能权重动态微调与排名。

### 🚀 Milestone Phase 3：在线创生与端到端隐私安全治理
- **`[TASK-LIVEGEN-01~03]` Epic-LIVE-GEN Skill Live Generator**：SKILL.md 在线 Monaco 编辑器与 YAML Header 语法校验、沙盒环境模拟触发测试、一键自动向量化发布至 Viking 1933 存储。
- **`[TASK-PRIVACY-01~03]` Epic-PRIVACY-GOV 敏感信息二次授权**：服务端敏感字段检索二次过滤与鉴权、前端脱敏展示与安全开关、脱敏审计日志与导出隔离。

---

### [x] v1.3.13 版本已验收通过 🎉
- **Git Commit**: `cfd40888`, Tag: `v1.3.13`
- **交付内容**：
  1. **`content_write` 处理模式与状态汇报 (`processing_mode`)**：支持 `vectors_only` 快速向量索引构建，跳过耗时语义提取；
  2. **文档导入解析后不拆分 (`no_split`) 模式**：长篇 Markdown / PDF 导入保持单个完整文件节点存储，不按层级切碎；
  3. **CJK 中文字符 Token 预算硬核保护**：强制切分算法固化 `MAX_TOKENS_PER_CHAR = 0.7` 上限，彻底杜绝中文超长溢出报错；
  4. **44/44 测试全过**：针对性用例与回归测试全绿通过，1933 生产环境健康上线。

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
