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

## 🗺️ 第二部分：上游 OpenViking 全景演进与合并原子化看板 (131 Commits 持续演进矩阵)

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
| **Task Card 9** | **VikingFS 存储与 Pathlock 锁健壮性** | 目录递归删除标志、add-resource 向量 4xx 异常捕获、命名空间根保护、Pathlock 租约保活与争用退避、资源移动无锁化 | `9791c875`, `9097fef4`, `8acaf7f8`, `10fd775a`, `8ef840da`, `efbe012d`, `b84395d6`, `1ec848e0`, `421c73be`, `2b926247`, `d88967aa` | `pytest tests/storage/` PASS, `test_viking_fs.py` PASS, 1936 健康上线 | `v1.3.49` | [x] 已验收并交付 ✅ (Commit: `e0cd472f`, Tag: `v1.3.49`) |
| **Task Card 10** | **Viking URI 规范化与 viking://~ 用户家目录** | `viking://~` 用户根路径别名、废除无 UID 模糊简写、Server 入口 URI 规范化校验、Entity URI 大小写对齐、全盘 739 物理技能动态同步入库 | `a83b8171`, `ff38bb5d`, `1ed5e211`, `81eba498`, `84467b1b` | `pytest tests/unit/test_uri_*.py` 69/69 PASS, MCP 119/119 PASS, 739 技能真实入库, 1936 上线 | `v1.3.50` | [x] 已验收并交付 ✅ (Commit: `38e28b11`, Tag: `v1.3.50`) |
| **Task Card 11** | **Memory 提取 V3 与 Session 异步非阻塞归档** | 统一 V3 提取与评测、跨会话更新稳定性、JSONL 纯物理换行切分、会话归档非阻塞、Event Tag 过滤 | `c96fbcb8`, `c1cc592a`, `ed1bd4b8`, `996128ab`, `eeff5a49`, `b9ec4f5b`, `7f6085a2`, `056f875e`, `a779c62a`, `bca5a673` | `pytest tests/test_session_*.py` PASS, `test_memory_*.py` PASS | `v1.3.55` | [x] 已验收并交付 ✅ (Tag: `v1.3.55`) |
| **Task Card 12** | **QueueFS 流式调度与并发 Reindex** | 语义任务流式调度、延迟内容实体化、Reindex 向量并发入队、过期任务自动清扫、上传 Task Token 用量透视 | `b877abab`, `75a1447d`, `6617a92c`, `22f00033`, `5de59a11`, `84c0895c`, `67603473`, `da138de7`, `482434ef` | `pytest tests/server/test_admin_rebuild_api.py` 58/58 PASS, `test_admin_api.py` 38/38 PASS, `test_queue_manager.py` PASS, 前端 build 0 报错 | `v1.3.54` | [x] 已验收并交付 ✅ (Tag: `v1.3.54`) |
| **Task Card 13** | **多模态与外部连接器升级** | PDF MinerU 官方 `file_parse` API 重构、飞书云盘与文件夹导入兼容、TOS Connector 参数与 404 容错、大图降采样 | `6e772912`, `c1345a1f`, `592c0fe0`, `5aed7f72`, `00bc9625`, `3bdf9995`, `24cc8c6e` | 连接器单元测试 PASS, 外部资源导入测试通过 | `v1.3.55` | [x] 已验收并交付 ✅ (Tag: `v1.3.55`) |
| **Task Card 14** | **MCP 协议工作区与 Agent 插件矩阵** | MCP `write/edit/tree` 工具 (支持 viking:// 作为工作目录)、recall 收敛统一 context search、Agent Plugins 1.0、TraeCode / DSH 记忆插件 | `4920297c`, `eb5aaf78`, `f6ba06bb`, `868a9600`, `c7044075`, `2cc7ec47`, `8abd61fc`, `b7aa01d2`, `d7ab37c7` | MCP 工具链测试 PASS, `openviking_system_status` 正常 | `v1.3.55` | [x] 已验收并交付 ✅ (Tag: `v1.3.55`) |

---

## ⚡ 第三部分：当前活跃与待调度 Studio 原子工单 (Scheduled Active Task Cards)

### 📌 P0: [x] [TASK-UPSTREAM-SYNC-ALL-01] 上游全量特性同步与测试套件 100% 全绿回归 (Task Cards 11, 13, 14 & Full Regression Green) ✅
- **模块**：全栈核心引擎 (`openviking`, `openviking_cli`, `sdk`, `integrations/langchain`, `tests`)
- **工单 ID**：`TASK-UPSTREAM-SYNC-ALL-01` ｜ **优先级**：P0（核心基线 / 100% 单测全绿）
- **目标**：彻底消解所有上游特性合并冲突，同步缺失的 LangChain / Agent-Plugins / Examples / npm 模块，修复底层所有单测失败，达成 2,173+ 项单元测试 100% 全部通过与前端 Vite Build 零报错。
- **交付内容与验收结果**：
  - [x] **LangChain 官方集成与锁定文件同步**：检出 `integrations/langchain` 与 `uv.lock`，全面通过 `test_langchain_*.py` 边界测试与运行时 Actor-Peer 验证；
  - [x] **多模态与 VLM / 编码器增强**：`text_encoding.py` 解决中日文编码消解；`openai_vlm.py` 恢复流式响应与 Token 用量统计；`gemini_embedders.py` 支持可选延迟导入与 3072/768 维度映射；
  - [x] **FSService Git 转发与快照锁回退**：`fs_service.py` 统一转发 `raw=True` 与 `paths or None`；`tests/conftest.py` 实现 `RAGFSBindingClient` 动态 Pathlock 内存 Fallback（`_acquire_tree`, `_acquire_exact`, `_acquire_batch`, `_as_borrowed`, `_to_handoff`, `_adopt`, `_release`），支持 `LockAcquisitionError` 瞬态争用抛出；
  - [x] **Memory V3 多块替换与提取循环**：`patch.py` 修复 `SearchReplaceBlock` 导入与无原始内容时多 Block 合并；`extract_loop.py` 严谨对齐 Page ID 与行前缀过滤规则；
  - [x] **全自动化测试 100% 通过**：
    - `pytest -o addopts="" tests/unit tests/parse tests/agfs`：**2,173 passed, 62 skipped, 0 failed (100% 全绿通过)**；
  - [x] **前端编译构建通过**：`npm run build` 0 报错（18.72s 编译完成）；
- **交付版本**：`v1.3.55` ｜ **交付 Tag**：`v1.3.55`

### 📌 P0: [x] [TASK-QUEUEFS-STREAMING-REINDEX-01] QueueFS 流式调度与并发 Reindex 合并 (Task Card 12) ✅
- **模块**：OpenViking Server (`openviking/storage/queuefs`, `openviking/service/reindex_executor.py`, `openviking/server/routers/content.py`, `openviking/storage/content_write.py`)
- **工单 ID**：`TASK-QUEUEFS-STREAMING-REINDEX-01` ｜ **优先级**：P0（核心吞吐与调度稳定性）
- **目标**：合并上游 QueueFS 语义任务流式调度、Reindex 向量并发入队、Search Tag 标签保护、延迟内容实体化及多租户鉴权。
- **交付内容与验收结果**：
  - [x] **Reindex 权限鉴权与 Tag 标签物理保护**：`_authorize_reindex_uri` 统一采用 `resolve_current_user_uri` 解析当前用户 URI；`_upsert_context` 在批量 Upsert 时精准保留 `search_tags`，彻底防止元数据丢失；
  - [x] **QueueFS 异步容错与流式任务调度**：`named_queue.py` 全面捕获 `AGFSClientError` 防止未就绪快照抛错；集成 Semantic DAG 与最新概览生成提示词模板；
  - [x] **VikingFS 内容写入与目录向量化**：`embedding_utils.py` 与 `content_write.py` 参数物理对齐，`vectorize_directory_meta` 支持 `include_overview` / `include_abstract`；
  - [x] **全自动化测试 100% 通过**：
    - `tests/server/test_admin_rebuild_api.py`：58/58 全通 (100%)
    - `tests/server/test_admin_api.py`：38/38 全通 (100%)
    - `tests/server/test_api_content.py` & `test_api_content_write.py`：39/39 全通 (100%)
    - `tests/storage/test_semantic_processor_*.py`：94/94 全通 (100%)
    - `tests/server/test_request_wait_tracking.py`：4/4 全通 (100%)
  - [x] **前端编译构建通过**：`npm run build` 0 报错；
- **交付版本**：`v1.3.54` ｜ **交付 Tag**：`v1.3.54`

---

### 📌 P0: [x] [TASK-CONSOLIDATE-PLAYGROUND-01] 资源库与实验场极简降维收口 & 全屏文件画布 (Consolidate Resources into Playground & Focus Canvas Mode) ✅
- **模块**：OpenVikingStudio 前端 (`src/routes/playground`, `src/routes/resources`, `src/components/app-shell.tsx`)
- **工单 ID**：`TASK-CONSOLIDATE-PLAYGROUND-01` ｜ **优先级**：P0（架构极简 / 奥卡姆剃刀）
- **目标**：贯彻“如无必要，勿增实体”哲学，消除资源库与实验场的功能重叠与心智摩擦，将资源库能力与入口 100% 收口归并在实验场，并提供全屏/聚焦文件画布模式。
- **交付内容与验收结果**：
  - [x] **导航栏精简**：从 `app-shell.tsx` 侧边栏移除重复的【资源库】菜单项，统一以【实验场】作为核心工作台；
  - [x] **平滑路由重定向**：访问 `/resources`（含 `?uri=...`、`?search=...`）时通过 `beforeLoad` 自动无缝转发至 `/playground`，完美兼容历史外链与书签；
  - [x] **全屏/聚焦文件画布 (Focus Canvas Mode)**：在 Context Explorer 顶部工具栏增加 `PanelRightClose / PanelRightOpen` 聚焦切换按钮，一键隐藏中右栏调试终端，让中间文件预览/编辑器撑满 100% 全屏，满足宽屏沉浸式阅读需求；
  - [x] **偏好持久化**：全屏视图偏好自动记录在 `localStorage`；
  - [x] **全功能 100% 物理对齐**：L0/L1/L2 分级摘要预览、Git 版本时间线与代码 Diff 对比、全文搜索 Palette、批量上传与目录树增删改查一站式闭环；
  - [x] **编译构建通过**：前端 `npm run build` 0 报错通过；
- **交付版本**：`v1.3.53` ｜ **交付 Commit**：`2dfcfa7c` ｜ **交付 Tag**：`v1.3.53`

---

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

### 📌 P0: [x] [TASK-COMPUTE-DUALBRAIN-01] Mac Studio (M3 Ultra 256G) 本地原生算力节点挂载与 Dual-Brain 智能网关 (auto-router) 优化部署 ✅
- **模块**：多端分布式算力肢体 / 智能模型网关 / MLX 原生推理引擎
- **工单 ID**：`TASK-COMPUTE-DUALBRAIN-01` ｜ **优先级**：P0（算力基础设施与智能分流中枢）
- **核心目标与背景**：
  为 OpenViking 体外大脑记忆中枢、OpenClaw 与 Hermes 提供零外部依赖、100% 本地私有化的高性能大模型推理基座。在 Mac Studio（M3 Ultra 256GB 统一内存，800GB/s 内存总线）上基于 Apple 原生 **MLX** 框架部署双模型常驻与智能网关，解决传统大模型推理冷启动延迟高、思考链与 Tool Calling 格式破坏 JSON 解析等核心瓶颈。
- **技术方案与交付成果**：
  - [x] **双模型原生 BF16 无损全精度物理常驻**：
    - 🧠 **奥尼 35B (Ornith-1.5-35B-A3B-MLX)**：MoE 混合专家架构（总 35B / 激活 3.5B），实测吞吐 **50+ Tokens/s**，承载 90% 的纯文本推理、代码重构、数学推演与 Tool Calling；
    - 👁️ **千问 27B-VL (Qwen3.8-27B-MTPLX-bf16)**：Dense 27B 密集视觉模型，承载 10% 的屏幕截图、UI 解析与图表 OCR；
    - 静态显存占用 122.9GB (48%)，动态显存留存 126.8GB (52%)，并发 128k 上下文零 OOM 风险；
  - [x] **智能网关 (`gateway.py` 端口 13389) 四重无损优化**：
    - **自动多模态分流**：检测到图片毫秒级分流千问 27B-VL，纯文本自动分流奥尼 35B，支持自动 HA 容灾热切；
    - **开机 Metal 预编译预热 (In-Memory Warmup)**：启动时自动预热 1-Token 计算图，首字延迟（TTFT）压至 **1.4s** 级别；
    - **思维链与结构化工具解耦**：非流式模式下自动分离 `<think>` 推理内容至 `reasoning_content`，Tool Calling 自动编译为标准 OpenAI 结构，彻底根除 OpenViking `Expected dict` 报错；
    - **显存锁死与长连接**：`sysctl iogpu.wired_limit_mb=249856` (244GB) + `mx.set_wired_limit(210GB)` + `mx.set_cache_limit(32GB)` + Uvicorn 120s Keep-Alive；
  - [x] **中央网关 (CPA 8317) 统一调度与零直连铁律**：
    - CPA `config.yaml` 映射 `Mac Studio` (`http://8.129.0.26:13389/v1`)；
    - OpenViking (`ov.conf`)、OpenClaw (`openclaw.json`) 与 Hermes (`config.yaml`) 统一向 `http://127.0.0.1:8317/v1` 请求 `auto-router`，零客户端直连配置；
  - [x] **全维质量与速度基准回归验收 100% 通过**：
    - 数学概率严格推导 4.75s（答案 $P=1/2$ 100% 正确）；
    - 原生 Tool Calling 1.57s（标准 JSON 结构 100% 正确提取）；
    - OpenViking 生产级会话提取端到端 HTTP 200 成功入库。
- **交付版本**：`v1.3.16` ｜ **数字层归档**：`viking://resources/master_memory/mac_studio_deployment_architecture.md`

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

- **[x] `[TASK-TASKLIST-EXEC-PROGRESS-01]` 任务列表工序执行动态与纯净任务状态解耦重构 (Execution Progress Telemetry & Clean Task Status) ✅**：
  - **交付版本**：`v1.3.22` ｜ **交付 Tag**：`v1.3.22`；
  - **核心成果**：
    1. **工序执行动态与引擎进度统一呈现 (`getTaskExecutionDynamic`)**：彻底切除表格中千篇一律的整串静态工序名称胶囊，原「流水线工序」列全面升级为「工序执行进度」列；
    2. **进行中任务实时步进与动态微进度条**：展示活跃工序（如 `工序 3/4: 向量计算`）、底层承接引擎微徽章（`Embedding`）、百分比进度条与切片级物理吞吐（如 `1,192 / 14,689 切片 (8%)`）；
    3. **已完成与异常任务极简交付摘要**：完成态展示结构化交付结果（如 `✓ 3 轮对话已归档 · 2 经验沉淀`、`✓ 14,661 个文件已落盘索引`），异常态明确指出中断阶段（`✕ 在工序 [向量计算] 执行中断`）；
    4. **状态列职责纯净化 (Pure Task Status)**：彻底移出悬挂在状态徽章下方的复杂工作量标签，状态列仅保留纯净的 `已完成` / `进行中 95%` / `排队中` / `失败` 徽章与重试按钮，极简优雅；
    5. **工序专业术语信达雅升华**：全盘 23 道工序统一为纯正 4 字极客领域术语（`悬空修剪`、`存储落盘`、`碎片回收`、`格式转换`）；
    6. **100% NO GREEN EVER 视觉克制与双语 i18n 维护**。

- **[x] `[TASK-TASKCENTER-PIPELINE-5050-01]` 任务与执行引擎 50/50 独立卡片高密架构与微胶囊工序流转体系 (8 Tasks · 23 Steps · 7 Engines) ✅**：
  - **交付版本**：`v1.3.21` ｜ **交付 Tag**：`v1.3.21` ｜ **交付 Commit**：`127b6470`；
  - **核心成果**：
    1. **8 任务 · 23 工序 · 7 引擎完整数据映射 SSOT**：在 `pipeline-steps-panorama.tsx` 与 `queue-status-card.tsx` 中建立统一字典与引擎承接矩阵；
    2. **任务与引擎 50/50 单行高密并排**：左侧展示 8 大业务任务流转链，右侧展示 7 大底层执行引擎物理负载，拒绝 Tab 遮盖，底部汇总行像素级物理平齐；
    3. **并发工序外框合并与极简 Chevron `›` 流转符**：单行内通过单个中性外框包裹并发工序（如 `[ 语义提取 & 向量建库 ]`），使用超窄 ChevronRight 图标连接，避免超宽换行与横向滚动条；
    4. **全量悬浮 3 段式结构化画像 Tooltip**：
       - 鼠标悬浮于任意工序：展示工序中文名、量化单位徽章、物理职责说明及承接执行引擎；
       - 鼠标悬浮于任意执行引擎：展示 CPU 芯片图标、引擎名称、底层 Raw Key、工序总数徽章、引擎物理职责描述与全量承接工序微胶囊清单；
    5. **奥卡姆剃刀彻底切除冗余全景大盘**：因所有信息已 100% 优雅融入顶置 50/50 双卡，彻底切除底部冗余的全景大盘卡片，界面清爽极致；
    6. **去引擎化文案与 i18n 双语规范**：统一移除名称后缀“引擎”，右侧表头精准显示为 `引擎名称`，字号严格 $\ge 11\text{px}$，100% NO GREEN EVER。

- **[x] `[TASK-PIPELINE-QUANTIFY-01]` 全工序切片/节点/页数物理工作量全景量化透视 ✅**：
  - **交付版本**：`v1.3.20` ｜ **交付 Tag**：`v1.3.20`；
  - **核心成果**：
    1. **12 大全工序物理量化模型 (`task-pipeline.ts`)**：支持资源处理 (文件数/切片数)、技能导入 (技能数/Frontmatter 校验)、会话提交 (轮次/经验萃取数)、空间注销 (向量/文件擦除数)、连接器导入 (文档数/MB 体积)、全局重建 (扫描条目/重构切片)、快照回滚 (还原 Inode 节点)、旧数据迁移/清理 (条目数/GC 释放体积)、Watch 增量监听 (变更事件数)；
    2. **切片/节点/页数自适应徽章**：在任务列表「状态」列中呈现如 `⚡ 1,192 / 14,689 切片 (8%)`、`🧠 48 / 320 节点 (15%)`、`📑 16 / 54 页`、`📦 128 / 850 文件` 等真实物理吞吐量；
    3. **工序流转与抽屉步进器对齐**：工序流转列与抽屉垂直步骤完整支持计量单位与数量展示；
    4. **中英双语与 NO GREEN EVER 规范**：全量词条中英平行录入，字号 $\ge 11\text{px}$，1933 生产环境热更上线。

- **`[TASK-LOOP-01~07]` Epic-SKILL-LOOP 自进化闭环引擎**：修正事件数据模型、异常 Trace 自动捕获、`CONTEXT / REFLECTION / LESSON` 3 段式自动萃取、Lesson 审核 View、`SKILL.md` 受控版本更新与 Git 自动回滚。
- **`[TASK-SKILLOPT-01~03]` Epic-SKILLOPT 质量门禁引擎**：Attempt 执行引擎与 Judge Gate 评分验证器、健康评分与自动修复建议生成、技能权重动态微调与排名。

### 🚀 Milestone Phase 3：在线创生与端到端隐私安全治理
- **`[TASK-LIVEGEN-01~03]` Epic-LIVE-GEN Skill Live Generator**：SKILL.md 在线 Monaco 编辑器与 YAML Header 语法校验、沙盒环境模拟触发测试、一键自动向量化发布至 Viking 1933 存储。
- **`[TASK-PRIVACY-01~03]` Epic-PRIVACY-GOV 敏感信息二次授权**：服务端敏感字段检索二次过滤与鉴权、前端脱敏展示与安全开关、脱敏审计日志与导出隔离。

### [x] v1.4.3 补丁版本已验收发布 🎉
- **Git Tag**: `v1.4.3` ｜ **版本类型**：Patch Release (Z 交互与任务治理版本)
- **交付内容**：
  1. **任务中心失败与已取消任务一键清理 API (`POST /api/v1/tasks/clear-failed`)**：支持批量永久清除所有历史失败和取消状态的死结任务单据，瞬间恢复看板整洁与 100% 成功率；
  2. **单任务物理删除接口与交互 (`DELETE /api/v1/tasks/{task_id}`)**：TaskTracker 底层与 HTTP 服务端新增单任务安全删除能力，前端表格行支持单个终态任务快速清理；
  3. **Web Studio 任务看板交互增强**：顶部工具栏新增 `🗑️ 清除失败与取消任务` 快捷按钮，失败徽章旁集成快速删除与重试双按钮。

---

### [x] v1.4.2 补丁版本已验收发布 🎉
- **Git Tag**: `v1.4.2` ｜ **版本类型**：Patch Release (Z 策略增强版本)
- **交付内容**：
  1. **任务中心生命周期全域 30 天保留策略**：将已完成任务 (`TTL_COMPLETED`) 与失败任务 (`TTL_FAILED`) 的保留时间统一由 24h / 7d 升级为 **30 个自然日 (2,592,000 秒)**，单机任务缓存容量上限 (`MAX_TASKS`) 扩容至 **50,000 条**；
  2. **每日自然日凌晨定时清理调度**：废除原先每 5 分钟频繁清理协程，重构为每日当地时间凌晨 00:00:00 准点触发的低频静默清理调度器（`_seconds_until_next_midnight`）；
  3. **任务历史追溯全周期保障**：保障历史工单长周期可观测与回溯，彻底解决已完成任务过早被自动回收的问题。

---

### [x] v1.4.1 补丁版本已验收发布 🎉
- **Git Tag**: `v1.4.1` ｜ **版本类型**：Patch Release (Z 修复版本)
- **交付内容**：
  1. **Pathlock 锁机制与 Native 绑定兼容性修复 (Cherry-pick 4130de0f)**：解决 `ragfs_python.abi3.so` 原生库缺失 `pathlock_acquire_tree` 导致 Session Commit 与 Admin Reindex 任务启动崩溃报错（`AttributeError: 'RAGFSBindingClient' object has no attribute 'pathlock_acquire_tree'`）的问题；
  2. **默认 Pathlock 优雅降级与 Bypass 机制**：未重新编译 native binding 期间自动跳过底层锁调用，避免任务死锁与超时；
  3. **任务中心僵尸/孤儿任务彻底清空与自愈**：完成全量 42h+ 残留运行态孤儿任务批量取消，恢复任务队列与调度器健康。

---

### [x] v1.4.0 重大里程碑版本已验收发布 🎉
- **Git Tag**: `v1.4.0` ｜ **版本类型**：Major Monorepo & Exocortex Release (中版本 Y 升级)
- **交付内容**：
  1. **前后端全栈工程单仓库 (Monorepo) 物理收口归一**：彻底消除双仓库协同摩擦，实现 Python 后端、Rust AGFS/VikingDB、React 19 Vite Web Studio、多语言 SDK 与 Agent 插件矩阵统一管理；
  2. **14 大上游核心特性 100% 全量合并与全套 2,173 项测试全绿**：涵盖多模态 MinerU/VLM、QueueFS 流式调度与并发 Reindex、Session 自动提交 V2、Memory V3 记忆提取、SDK Options 签名同步与细粒度 Pathlock 锁机制；
  3. **全景可视化 Web Studio 深度集成与双轨架构**：提供智能实验场全屏聚焦画布、50/50 独立卡片任务中心切片级真实吞吐度量 ($X/Y$ 物理流转)、多轮会话回溯、748+ 实体技能资产管理与 16 项系统/GPU 遥测大屏；
  4. **Mac Studio M3 Ultra 256G 原生算力节点与 Dual-Brain 网关部署**：BF16 双模型常驻（奥尼 35B 50+ Tok/s + 千问 27B-VL）、Metal 预热、思维链与 Tool Calling 解耦；
  5. **极客性冷淡视觉规范 (NO GREEN EVER SSOT)**：全盘封杀绿色，字号硬下限 $\ge 11\text{px}$，像素级物理平齐。

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

> **目标**：在上游后端合并全部完成后，对以下 **11 大“有强大后端能力无可视化界面”的核心模块** 逐一进行 Studio 可视化页面建设与交互闭环。

| 工单 ID | 对应后端路由 / 模块 | 核心可视化交付目标 | 优先级 |
| :--- | :--- | :--- | :---: |
| **`TASK-UI-EVAL-BENCHMARK-01`** | `openviking/eval/` (`ragas/`, `rag_eval.py`) | **RAG 评测实验室与 Benchmark 质量基准大屏 (RAG Evaluation Lab)**：可视化管理评测数据集 (JSONL)、一键发起并发打分评测；展示 Ragas 4 大核心维度（精确度、召回率、忠实度、答案相关性）雷达图与指标柱状图；提供多策略 A/B Benchmark 对比与单 Case 检索片段/回答扣分下钻透视。 | 🔴 P1（核心质量度量门面） |
| **`TASK-UI-POLICY-TRAINER-01`** | `openviking/session/train/` | **策略强化训练与经验提炼演进工作台 (Policy Trainer & Gradient Evolution)**：可视化管理训练用例集 (Cases) 与评判准则 (Rubrics)；白盒展开 Rollout 动作轨迹、奖励 (Reward) 与梯度估算；呈现提炼出的经验 Markdown Diff 对比并支持一键采纳合并入库。 | 🔴 P1（智能体自演进中枢） |
| **`TASK-UI-STORAGE-IO-INSPECTOR-01`** | `openviking/eval/recorder/` (`analyze_records`, `play_recorder`) | **存储层 IO 性能录制与多后端回放分析大屏 (IO Recorder & Storage Playback)**：一键开启 FS / VikingDB IO 实时录制；可视化展示操作耗时瀑布流与 P95/P99 延迟分布；支持在本地 NVMe 与远程 S3/TOS 间一键回放对比吞吐与倍率。 | 🟡 P2（深度性能调优） |
| **`TASK-UI-CONFIG-SETTINGS-01`** | `routers/settings.py` / `skills.py` | **项目全局可视化配置中心 & 技能扫描源管理**：提供全局常用配置可视化操作面板。支持用户自定义填写/增删技能文件夹物理路径，一键挂载到 Wiki 并触发实时扫描入库；支持模型网关、环境变量与存储参数可视化调整。 | 🔴 P1（核心交互门面） |
| **`TASK-UI-AGENT-EVOL-01`** | `routers/agent_evolution.py` | **Agent Evolution 演进全景可视化大屏（路径、轨迹与成果全透视）**：新增独立演进全景看板，提供【成长路径时间轴】、【执行动作与纠偏轨迹拓扑】、【经验胜率与正负向成效分布图】三大视界，让用户直观透明看到智能体的进化过程。 | 🔴 P1（重点前调） |
| **`TASK-UI-WATCHES-01`** | `routers/watches.py` | **资源自动订阅与 Watch 监控看板**：提供 GitHub Repo / Web 资源订阅任务管理、自动同步触发器、运行流水线日志查看。 | 🔴 P1 |
| **`TASK-UI-PRIVACY-01`** | `routers/privacy_configs.py` | **隐私安全与敏感信息脱敏治理中心**：脱敏规则配置、敏感字段打码开关、二次授权弹窗与合规审计日志导出。 | 🟡 P2 |
| **`TASK-UI-OVPACK-01`** | `routers/pack.py` | **知识大脑一键打包与迁移导入中心**：提供 OVPack 便携知识包一键导出、本地 ZIP 拖拽导入与解包校验面板。 | 🟡 P2 |
| **`TASK-UI-SNAPSHOT-01`** | `routers/snapshot.py` | **VikingFS 物理快照与历史版本回滚中枢**：全盘快照时间线、快照内容树比对、一键安全还原与灾备演练。 | 🟡 P2 |
| **`TASK-UI-RELATIONS-01`** | `routers/relations.py` | **知识图谱关系与血缘动态编辑面板**：资源与记忆 Link / Unlink 交互连线、关系类型打标与多跳图谱遍历。 | 🟢 P3 |
| **`TASK-UI-WEBDAV-01`** | `routers/webdav.py` | **WebDAV 挂载与网络存储连接管理面板**：一键生成/吊销 WebDAV 挂载凭据、连接指引（Windows/Mac 挂载盘）与实时流量。 | 🟢 P3 |
| **`TASK-UI-OBSERVER-01`** | `routers/observer.py` | **实时事件观测流与慢查询白盒调试器**：Server-Sent Events (SSE) 实时事件流水、向量检索慢查询火焰图与白盒 Trace。 | 🟢 P3 |

---

### 🎴 [专项工单详情] TASK-UI-AGENT-EVOL-01：Agent Evolution 演进全景可视化看板 (Evolution Path, Trajectories & Outcomes Dashboard)
- **模块**：OpenVikingStudio 前端 (`src/routes/evolution` / `src/routes/harness-logs`) + 后端 `AgentEvolutionService` (`/api/v1/agent-evolution/*`)
- **工单 ID**：`TASK-UI-AGENT-EVOL-01` ｜ **优先级**：P1（核心心智感知与成果透视）
- **核心目标**：彻底解决 Agent Evolution 后端有轨迹、有经验但前端用户“看不见、摸不着、感知弱”的黑盒问题。打造简单、直白、极具科技质感的三大核心可视化视界：
  1. 🛤️ **【视界一：演进里程碑与成长时间轴 (Evolution Path)】**：
     - 按时间瀑布流直观展示智能体随交互发生的认知跃迁点；
     - 自动打标：`[规则固化]`、`[避坑经验]`、`[正向策略]`、`[工具参数修正]`，并提供原会话溯源直达。
  2. ⚡ **【视界二：执行动作与碰壁纠偏轨迹拓扑 (Execution Trajectories Flow)】**：
     - 结构化展开智能体执行任务时的完整流水线：`思考 -> 工具调用 -> 报错拦截 -> 自我纠偏 -> 交付`；
     - 突出高亮展示哪里碰壁（如 429、格式异常）以及如何自愈，让机器决策过程 100% 透明白盒化。
  3. 📊 **【视界三：成果成效与经验分布仪表盘 (Outcomes & Distribution Analytics)】**：
     - **经验胜率与正负向成效分布图**：对接 `/api/v1/agent-evolution/experiences/outcome-distribution`，直观呈现 Positive / Negative 经验比例与演进健康度；
     - **Few-Shot 经验复用与命中热力统计**：展示沉淀的案例与经验在后续任务中被召回的频次与成效；
     - **提效 ROI 量化看板**：统计因经验沉淀带来的交互轮次减少量与 Token 节省估算。
- **视觉规范约定**：
  - 严格遵循 Layer 1：亮暗双模支持、极客性冷淡设计、NO GREEN EVER（冰青 `cyan-500` 正向、玫瑰红 `rose-500` 负向/报错、沉静哑光灰 `muted`）、字号硬下限 $\ge 11\text{px}$、卡片内边距 `p-3.5`、`mt-auto` 物理平齐。
- **状态**：⬜ 待开发（已完成设计规格化与工单锁定）。

---

### 🎴 [专项工单详情] TASK-UI-CONFIG-SETTINGS-01：项目全局可视化配置中心 & 技能扫描源动态管理 (Project Settings & Skill Sources Dashboard)
- **模块**：OpenVikingStudio 前端 (`src/routes/settings` / `src/routes/config`) + 后端 `ConfigService` (`/api/v1/config/*`) 与 `SkillScanner`
- **工单 ID**：`TASK-UI-CONFIG-SETTINGS-01` ｜ **优先级**：P1（核心配置白盒化与用户自定义门面）
- **核心目标**：将所有常用系统配置（尤其技能扫描源、模型节点、存储参数、环境变量）彻底告别黑盒与命令行，打造所见即所得的可视化配置中心。包含以下核心模块：
  1. 📂 **【技能扫描源动态管理 (Skill Sources Manager)】**：
     - 用户可在界面自由添加/删除技能物理目录绝对路径（如 `/path/to/my-custom-skills`、`~/.hermes/` 等）；
     - 提供 **“一键挂载到 Wiki (Mount to VikingFS)”** 与 **“立即重新扫描 (Trigger Rescan)”** 按钮；
     - 实时展示各路径下的技能扫描状态、入库成功数、异常 YAML 提示；
     - 自动持久化保存已配置的路径列表，系统重启自动重新监听并增量入库。
  2. 🧠 **【模型与算力节点路由配置 (AI Models & Compute Nodes)】**：
     - 可视化配置 Mac Studio 256G (M3 Ultra `13100` MLX)、Windows 2080Ti 与第三方 API Provider 密钥与 Endpoints；
     - 实时一键 Ping 测连通性与 VRAM 状态探测。
  3. ⚙️ **【系统运行参数与存储策略 (Runtime & Storage Settings)】**：
     - VikingFS 存储工作区、CJK 切分阈值、向量引擎并发数的 UI 开关与滑动调节器。
- **视觉规范约定**：
  - 极客性冷淡排版、最小字号 $\ge 11\text{px}$、NO GREEN EVER、50/50 紧凑网格。

---

### 🎴 [专项工单详情] TASK-UI-EVAL-BENCHMARK-01：RAG 评测实验室与 Benchmark 质量基准大屏 (RAG Evaluation & Benchmark Lab)
- **模块**：OpenVikingStudio 前端 (`src/routes/evaluation` / `src/routes/benchmark`) + 后端 `openviking/eval/` (`ragas/`, `rag_eval.py`, `/api/v1/eval/*`)
- **工单 ID**：`TASK-UI-EVAL-BENCHMARK-01` ｜ **优先级**：🔴 P1（核心质量度量门面）
- **核心目标**：将后端的 Ragas 评测能力、检索精确度/召回率/忠实度打分以及多策略 A/B 对比能力做成可视化评测交互工作台。包含以下核心模块：
  1. 📁 **【评测集与 Ground Truth 样本库管理 (Dataset & Sample Hub)】**：
     - 支持用户在 UI 界面一键上传/切换评测数据集 (JSONL)，在线预览 Query、Context 片段与标准答案 (Ground Truth)；
     - 提供样本搜索、标签分类与单条样本快速编辑。
  2. 🚀 **【一键评测调度与实时进度 (Evaluation Runner)】**：
     - 支持可视化配置评测参数（并发 Worker 数、超时时间、打分模型选择：GPT-4o / Claude / 本地 MLX）；
     - 实时展示评测进度条与打分流式流水线。
  3. 📊 **【RAGAS 4 维雷达图与质量度量大屏 (Multi-Dimensional Metrics Radar)】**：
     - 可视化展示 **上下文精确度 (Context Precision)**、**上下文召回率 (Context Recall)**、**答案忠实度 (Faithfulness)** 与 **答案相关性 (Answer Relevance)** 4 维雷达图；
     - 汇总平均分、P95 检索时延与端到端响应耗时。
  4. 🔬 **【多策略 A/B Benchmark 对比 (Strategy Comparison)】**：
     - 支持对比不同配置组合（如 Chunk Size: 1500 vs 512、Reranker: On vs Off、检索深度: L0 vs L1 vs L2）下的雷达覆盖面与柱状图差异。
  5. 🔍 **【单 Case 深度透视下钻 (Case Deep Inspector)】**：
     - 点击任一评测样本，并排比对检索命中片段、LLM 生成回答与 Ground Truth，高亮扣分原因与归因说明。
- **视觉规范约定**：
  - 极客性冷淡设计、NO GREEN EVER（冰青 `cyan-500` 正向高分、玫瑰红 `rose-500` 低分告警、沉静灰 `muted`）、字号 $\ge 11\text{px}$、50/50 并排卡片。

---

### 🎴 [专项工单详情] TASK-UI-POLICY-TRAINER-01：策略强化训练与经验提炼演进工作台 (Policy Trainer & Gradient Evolution)
- **模块**：OpenVikingStudio 前端 (`src/routes/policy-trainer`) + 后端 `openviking/session/train/` (`/api/v1/session/train/*`)
- **工单 ID**：`TASK-UI-POLICY-TRAINER-01` ｜ **优先级**：🔴 P1（智能体自演进中枢）
- **核心目标**：将智能体经验提炼、策略优化流水线（PolicyOptimizationPipeline）从命令行黑盒变为所见即所得的可视化训练工作台。包含：
  1. 🎯 **【训练用例与评分准则管理 (Cases & Rubrics Hub)】**：
     - 可视化浏览与新增训练 Case，配置 Rubric 评分准则权重（Criteria & Weight）。
  2. 🔁 **【Rollout 轨迹与梯度估算白盒展开 (Rollout & Gradient Flow)】**：
     - 结构化展开智能体多轮动作轨迹、工具调用入参与真实环境奖励（Reward）；
     - 白盒化展示 `ExperienceGradientEstimator` 估算出的语义梯度与策略反思。
  3. 📝 **【经验补丁 Diff 审核与一键合并 (Experience Patch Diff & Merging)】**：
     - Markdown 纯净并排 Diff（Before / After），清晰标注 Rationale 理由与置信度；
     - 提供 **“一键采纳并合并至 Wiki 经验库 (Accept & Commit to VikingFS)”** 与一键拒绝。
- **视觉规范约定**：
  - 严格遵循性冷淡克制、NO GREEN EVER、最小字号 11px、双主题平齐容器。

---

### 🎴 [专项工单详情] TASK-UI-STORAGE-IO-INSPECTOR-01：存储层 IO 性能录制与多后端回放分析大屏 (IO Recorder & Storage Playback)
- **模块**：OpenVikingStudio 前端 (`src/routes/storage-inspector`) + 后端 `openviking/eval/recorder/` (`analyze_records`, `play_recorder`)
- **工单 ID**：`TASK-UI-STORAGE-IO-INSPECTOR-01` ｜ **优先级**：🟡 P2（深度性能调优）
- **核心目标**：实现对 VikingFS 底层文件 IO 与 VikingDB 向量 IO 的毫秒级观测、录制与跨后端重放对比：
  1. ⏺️ **【IO Recorder 录制控制台】**：一键启停 IO 录制器，实时监控当前录制日志文件体积与操作计数；
  2. 📈 **【操作耗时分布与热点瀑布流】**：按 `fs.read`, `fs.write`, `fs.tree`, `vikingdb.search`, `vikingdb.upsert` 分类统计 P50/P95/P99 耗时与慢操作排名；
  3. 🔄 **【跨存储后端回放性能对比 (Playback Benchmark)】**：一键回放录制文件，直观比对本地存储 vs 对象存储（S3/TOS）的吞吐量与耗时加速比。
- **视觉规范约定**：
  - 紧凑等宽数值 `tabular-nums`、NO GREEN EVER、50/50 独立卡片并排。

---
### [x] v1.3.52 版本已验收通过 🎉
- **Git Commit**: `0c0db7af`, Tag: `v1.3.52`
- **对应任务卡片**：`[TASK-UPSTREAM-MEMORY-V3-01]` Memory V3 会话提取、归档解耦与全链路零硬编码对齐
- **交付内容**：
  1. **Memory V3 记忆提取引擎与会话提交稳定性提升**：合并 `ed1bd4b8` / `c96fbcb8` / `0ea10190` / `6a252eba` / `b9ec4f5b` / `056f875e`，实现全异步非阻塞 Phase 2 记忆归档；
  2. **绝对数据真实性 (100% Zero Hardcoding)**：彻底切除前端 `all_skills.json` 静态文件与 `648` 兜底硬编码，100% 真实后端数据驱动；
  3. **技能中心防抖防闪烁加固**：优化 React Query 缓存与焦点行为 (`staleTime: 60_000`, `refetchOnWindowFocus: false`)，杜绝窗口切换带来的微闪；
  4. **全套自动化测试 131/131 全绿通过**：`test_api_sessions.py` (51/51), `test_session_commit.py` (18/18), `test_namespace_uri_classification.py` (24/24), `test_config_loader.py` (38/38) 全部物理绿灯。



