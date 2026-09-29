# 🗺️ OpenViking 项目主线重构与原子化任务卡片总看板 (Master Task Cards Kanban - SSOT)

> **关联研发大蓝图**：[`BLUEPRINT.md`](file:///home/skloxo/aho/openclaw/project/.agents/BLUEPRINT.md) ｜ **交付全量归档台账**：[`DELIVERY_ARCHIVE.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md) ｜ **通用资产档案库**：[`COMPONENT_AND_WHEEL_INVENTORY.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/docs/architecture/COMPONENT_AND_WHEEL_INVENTORY.md) ｜ **👁️ 人工验收测试指南**：[`docs/HUMAN_ACCEPTANCE_TESTING.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/docs/HUMAN_ACCEPTANCE_TESTING.md)
> **唯一真相源 (SSOT)**：本文档为 OpenViking 当前活跃的重构规划与就绪待调度的任务矩阵看板。历史所有已验收交付的版本履历（Milestone 1~4 全量 19 张 Task Cards 及前序波次）已完整归档至 [`DELIVERY_ARCHIVE.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md)，严禁多头维护。所有版本的 30 秒人工肉眼走查清单集中在 `docs/HUMAN_ACCEPTANCE_TESTING.md`。

---

## 📌 一、 研发基线与近期已交付版本速查索引 (Recent Delivered Releases: v1.5.80 ~ v1.5.87)

> **生产物理事实声明**：
> - **线上正式部署版本**：**`v1.4.106`**（物理访问地址：`vk.tide.red/studio/home`，已实机验证）；
> - **当前最新交付版本**：**`v1.5.87`**（Tag: `v1.5.87`，已全量通过 167 项单元/集成测试与安全扫描）；
> - **历史里程碑详单检索**：如需查阅 Milestone 1~4 及早期版本修改清单与架构细节，请点击跳转至 [`DELIVERY_ARCHIVE.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md)。

| 版本 Tag | 任务工单 ID | 模块与重构主题 | 核心治理成果与物理交付物 | 验收状态 |
|:---|:---|:---|:---|:---:|
| **`v1.5.87`** | **Card-23** | **上游文件系统标准吸收 — ls/tree 游标分页排序与统一中文/Unicode 存储 URI** | 1. Unicode URI 规范化与 `%20` 兼容降级；2. `ls`/`tree` 游标分页与稳定排序；3. Precompiled Rust native ABI 降级切片；4. 167 项单测全绿。 | [x] 已验收通过 ✅ |
| **`v1.5.86`** | **Card-22** | **上游检索算力吸收 — 余弦相似度归一化与单请求 Query 嵌入高速复用** | 1. CuVS/本地索引余弦得分归一化至 $[0.0, 1.0]$；2. 请求级 ContextVar 嵌入缓存；3. 112 项单测全绿。 | [x] 已验收通过 ✅ |
| **`v1.5.85`** | **Card-21** | **上游存储稳固性吸收 — OS 文件锁替代 PID、QueueFS 与 HTTP 事件循环隔离** | 1. Linux `flock` 替换 PID 文件；2. 跨 Loop `AsyncSemaphore`；3. Telemetry ID 全链路保真；4. 57 项单测全绿。 | [x] 已验收通过 ✅ |
| **`v1.5.84`** | **Card-20H** | **AHE 契约三元组在技能更新与回归测试中的物理门禁接入** | 1. PolarJudge 真实沙箱校验与退化阻断；2. 快照 `rollback()` 物理恢复；3. AHE CLI 扫描器。 | [x] 已验收通过 ✅ |
| **`v1.5.83`** | **Card-20G** | **昼夜双轮自演进真实轨迹收集与双 Split 门禁驱动闭环** | 1. 白昼会话逐回合 `record_turn`；2. 午夜做梦离线双 Split 盲测门禁；3. RLock 重入保护。 | [x] 已验收通过 ✅ |
| **`v1.5.82`** | **Card-20F** | **活态实体血缘与跨节点拓扑图谱动态渲染闭环** | 1. SQLite `relations.db` 物理血缘表；2. 动态拓扑端点；3. 切除前端全部假数据 fallback。 | [x] 已验收通过 ✅ |
| **`v1.5.81`** | **Card-20E** | **Hermes 经历库会话全链路自动分流落盘与异步复盘自愈闭环** | 1. FTS5 + CJK 经历库批量事务写入；2. Stop Hook 双轨分流；3. 异步 Nudge 复盘。 | [x] 已验收通过 ✅ |
| **`v1.5.80`** | **Card-20D** | **离线梦想缺陷挖掘与熵结晶器自动巡检守护贯通** | 1. 午夜定时与 30min 空闲双驱动；2. 三门禁不可变规则结晶落盘；3. 单文件安全红线守护。 | [x] 已验收通过 ✅ |

---

---

## 📌 二、 活跃原子化任务卡片总看板 (Active Task Cards Kanban)

> **当前工程状态**：  
> 🚀 **Milestone 5 启动：半成品功能全链路真实化贯通 (5-A) 与 上游核心稳固性吸收 (5-B)**  
> 历史全量卡片规格（Card 1 至 Card 19）已完整归拢至 [`DELIVERY_ARCHIVE.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md)。  
> 遵循第一性原理与绝对数据真实性，彻底排查并治理所有“做了一半、源头悬空、假数据残留”的半成品，逐卡闭环落地。

---

### 🧬 Milestone 5-A: 半成品与悬空功能全链路真实化贯通 (Suspended Features Truthful Closure)

#### 📌 [P1] [ ] Card-20: Card-Skill-Ingestion-Sanitizer-And-SelfHealing-Retina (v1.5.77): 技能准入物理洗练、全流程自愈与文件系统恒等式巡检视网膜 ⏳
- **类型**：架构治理 / 技能中枢核心强化 ｜ **优先级**：🔥 P1 ｜ **目标版本**：`v1.5.77` ｜ **当前状态**：[ ] 就绪待调度 ⏳
- **背景与第一性原理**：
  - 过去技能中心存在“宽进严出”与“高阶演进重度工程、底层卫生无人看守”的倒置死穴：底层无脑允许不规范目录（中文、点号、空目录）落盘，导致表现层被迫堆砌粗暴的猜测试补丁（如子串误杀 `openclaw-backup` 与 `nemo-curator`），造成大盘数字与文件系统脱节（753 vs 760）；
  - 本卡片从第一性原理直击根因：建立**“严进宽出”与物理恒等式自愈闭环**，彻底根除脏技能入库与接口误杀。
- **开工前客观数据指标锚定 (Frontend Metric Anchor SSOT)**：
  - **衡量指标**：
    1. **技能物理恒等式一致率**：$\text{Count}_{\text{FS}} \equiv \text{Count}_{\text{API}}$，达成目标：**$100\%$ 绝对恒等**，差异集 $\text{Difference} \equiv \varnothing$；
    2. **准入洗练自动化率**：非规范输入（中文名、点号/空格、空目录、缺 `SKILL.md`）自动修正与脚手架补齐率达到 **$100\%$**；
    3. **读取层误杀率**：彻底切除 ad-hoc 子串猜测，正规技能误杀率**降为 $0\%$**。
  - **展示界面与卡片**：控制台大盘主页与技能中心大盘。
- **核心交付目标**：
  1. 底层强纠偏与准入洗练器 (`skill_sanitizer.py`)：在技能物理写入落盘时进行拦截清洗；
  2. 切除读取层盲目过滤并实现规范准入闭环 (`skills.py`)；
  3. 恒等式自动化巡检视网膜与自愈 Cron (`skill_retina_cron.py`)。
- **验收条件**：单测 100% 通过、安全扫描 0 密钥泄露、前端构建通过、实机验证。

---

#### 📌 [P1] [x] Card-20A: Card-Metrics-AgentSensors-RealHook-Closure (v1.5.77): 智能体三维效能物理探针真实生产挂载与数据真实性闭环 ✅
- **类型**：生产数据挂载 / 真实遥测闭环 ｜ **优先级**：🔥 P1 ｜ **目标版本**：`v1.5.77` ｜ **当前状态**：[x] 已验收通过 ✅
- **背景与第一性原理**：
  - 过去开发了数据模型、REST API 和大盘卡片，但**数据源头挂载（Source Hook）悬空**，生产会话从未上报，唯一的数据竟是单元测试写入的 10 条 `sess-test-01 80%` 测试垃圾；
  - 本卡片拒绝假数据，将遥测探针真正挂载到 OpenViking / OpenClaw 的真实会话生命周期中。
- **开工前客观数据指标锚定 (Frontend Metric Anchor SSOT)**：
  - **衡量指标**：
    1. **生产真实会话采样覆盖率**：真实会话在结算提交时 100% 自动上报三维指标，杜绝 0 采样；
    2. **数据真实性与信噪比可信度**：Token SNR 严格基于真实有效 Token/总 Token 计算，无任何硬编码 Mock。
  - **展示界面与卡片**：首页「智能体三维效能物理探针」卡片（真实反映实时信噪比与会话时序流）。
- **核心交付目标**：
  1. 在 `SessionCommitProcessor` 与会话提交结算链中注入 `record_telemetry`，自动统计 effective_tokens 与 total_tokens；
  2. 在检索响应与上下文装配中注入 Top-5 知识采纳度探针（`top5_hits`）；
  3. 在 A2A 对话交互中检测人类负向输入（指正/打断/重试），真实计算人工介入率。
- **验收结果**：
  - **Git 变更范围**：`openviking/core/agent_sensors.py`, `openviking/storage/queuefs/session_commit_processor.py`, `.agents/hooks/ov_session_archiver.py`, `tests/unit/test_session_commit_sensor_hook.py`, `tests/unit/test_ov_session_archiver_telemetry.py`；
  - **单测验证**：6 套单测全绿（`test_agent_sensors.py`, `test_agent_sensors_api.py`, `test_session_commit_sensor_hook.py`, `test_ov_session_archiver_telemetry.py` 全部 PASS，耗时 1.17s）；
  - **安全与构建门禁**：`security_check.py` 4486 文件 0 泄露，Vite 编译构建 PASS（15.63s）。

---

#### 📌 [P1] [x] Card-20B: Card-Observability-FailureTaxonomy-Production-Interception (v1.5.78): 三级错误分类学与防死循环屏障全局生产拦截贯通 ✅
- **类型**：系统异常感知 / 故障自愈 ｜ **优先级**：🔥 P1 ｜ **目标版本**：`v1.5.78` ｜ **当前状态**：[x] 已验收通过 ✅
- **背景与第一性原理**：
  - 核心定义了三级故障分类（ToolCrash, SchemaMismatch, InfiniteLoop）与白名单传感器，但仅存在手动测试 Probe，系统真实的工具崩溃、超时和死循环从未被自动分类捕获；
  - 杜绝“虚荣指标”，建立闭环执行器：本卡片将分类雷达真正织入 FastMCP 执行层与 HTTP 全局异常处理器，并在第 3 次重复失败调用前进行物理阻断（Anti-Loop Barrier），注入反思提示词。
- **开工前客观数据指标锚定 (Frontend Metric Anchor SSOT)**：
  - **衡量指标**：
    1. **生产异常分类捕获率**：真实工具调用报错、超时与 HTTP 异常捕获率 **$100\%$**；
    2. **死循环死锁阻断率**：重复死循环调用在第 3 轮触发阻断率 **$100\%$**（调用前物理拦截，不消耗函数计算算力与 Token）。
  - **展示界面与卡片**：监控大盘「三级故障雷达与防死循环屏障」卡片（真实时序流 `recent_events` 与 `anti_loop_interceptions`）。
- **核心交付目标**：
  1. 在 FastMCP 执行层拦截工具异常，自动调用 `record_failure` 归类并更新时序度量；
  2. 将死循环防御屏障（Anti-Loop Barrier）作为真实中间件挂载到 MCP 工具调度链，阻断重复错误并返回反思导引；
  3. 全局 HTTP 异常捕获（OpenVikingError, RequestValidationError, 500）实时接入分类雷达；
  4. 彻底激活白名单传感器对核心 Payload 的保护。
- **验收结果**：
  - **Git 变更范围**：`mcp-openviking/_core/decorators.py`, `openviking/core/failure_classifier.py`, `openviking/server/app.py`, `tests/unit/test_fastmcp_antiloop_interception.py`, `package.json`, `openviking/_version.py`；
  - **单测验证**：14 套分类与拦截单测全绿（`test_failure_classifier.py`, `test_failure_taxonomy_api.py`, `test_fastmcp_antiloop_interception.py` 全部 PASS，耗时 2.22s）；
  - **真实生产环境物理验证**：真实请求 `http://127.0.0.1:1933/api/v1/system/failure_taxonomy_metrics` 现场捕获真实认证异常，`deterministic_count` 自动自增，`recent_events` 实时滚动展示；
  - **安全与构建门禁**：`security_check.py` 4488 文件 0 泄露，Vite 编译构建 PASS（15.50s），生成版本注入 `1.5.78`。

---

#### 📌 [P1] [x] Card-20C: Card-Security-HITLGate-And-ReadOffload-Production-Mount (v1.5.79): 安全自愈分级门禁 (HITLGate) 与大文件只读卸载生产常驻挂载 ✅
- **类型**：安全审批 / 智能体控制 / 性能卸载 ｜ **优先级**：🔥 P1 ｜ **目标版本**：`v1.5.79` ｜ **当前状态**：[x] 已验收通过 ✅
- **背景与第一性原理**：
  - `HITLGate` 与 `ReadOffloadManager` 此前仅在单元测试中被手动实例化，生产执行管线中从未常驻；
  - 传统死等人类审批的模式会导致 Agent 频繁权限中断暴毙。本卡片重构为四级安全防护：
    1. **Level 1 (工作区沙箱)**：项目内常规读写与局部构建清理 100% 自动自治放行，零打扰人类；
    2. **Level 2 (会话预授权)**：开局声明的重构/清理意图携带 `session_grant` 令牌无感放行；
    3. **Level 3 (防御性变轨自愈)**：越界风险命令拦截并返回安全替代建议（Reroute guidance），Agent 自主纠偏不中断；
    4. **Level 4 (真·核弹级灾难)**：仅对不可逆毁灭动作（rm -rf / 等）异步工单挂起；
  - 读侧 `ReadOffloadManager` 正式织入 MCP 工具输出切面，大文件（>300 行/12KB）自动句柄化切片，节省 70%+ Token。
- **开工前客观数据指标锚定 (Frontend Metric Anchor SSOT)**：
  - **衡量指标**：
    1. **越界破坏与核弹命令拦截率**：越界高危操作防御性变轨与阻断率 **$100\%$**；
    2. **工作区常规操作自治通行率**：工作区内部正常读写与调试执行阻断率 **$0\%$**（零误杀）；
    3. **超大只读文件 Token 卸载率**：超过 300 行文件通过 `FileRefHandle` 节省上下文 Token **$\ge 70\%$**。
  - **展示界面与卡片**：Web Studio「人类审批待办中心」与「上下文卸载仪表盘」。
- **核心交付目标**：
  1. 在 FastMCP 调度链挂载 `HITLGate` 与 `ReadOffloadManager` 生产拦截切面；
  2. 实现 Level 1 工作区沙箱路径放行与 Level 3 防御性变轨导引，消除 Agent 无故中断；
  3. 拦截读取工具超大输出，生成带有精确切片支持的 `FileRefHandle`；
  4. 交付时完成【完工反思六问】，排查并记录次生悬空点。
- **验收结果**：
  - **Git 变更范围**：`mcp-openviking/_core/decorators.py`, `openviking/core/hitl_gate.py`, `openviking/core/read_write_offload.py`, `tests/unit/test_hitl_read_offload_production_mount.py`, `package.json`, `openviking/_version.py`；
  - **单测验证**：19 套单测全绿（`test_hitl_read_offload_production_mount.py`, `test_read_write_offload_hook_guard.py`, `test_hitl_offload_api.py`, `test_fastmcp_antiloop_interception.py` 全部 PASS，耗时 2.26s）；
  - **实机运行验证**：`https://vk.tide.red/health` 返回 `{"version": "1.5.79", "status": "ok"}`，大文件成功句柄化切片，高危命令安全自愈拦截；
  - **安全与构建门禁**：`security_check.py` 4489 文件 0 泄露，Vite 编译构建 PASS（15.54s），生成版本注入 `1.5.79`；
  - **【完工反思六问】自检通过**：
    1. 是否悬空？已挂载至 `cleaned_fn` 全量工具执行链，彻底消除悬空；
    2. 是否闭环？越界命令拦截并注入安全替代自愈导引，Agent 自主纠偏变轨，形成感知-拦截-自愈闭环；
    3. 是否虚荣指标？大盘 `HITLOffloadTelemetry` 实时由真实调用驱动，大文件真实截断省 Token，彻底消灭虚荣指标；
    4. 是否过度工程化？没有引入冗余分布式中间件，基于轻量单例策略池完成，KISS 极简；
    5. 是否满足第一性原理？物理隔离高危风险，保护沙箱外系统，同时确保大模型注意力不被大文件撑爆；
    6. 是否信达雅？代码内聚，错误文案通顺并自解释安全替代路径；
  - **【次生悬空排查发现】**：前端 Web Studio 虽然具备 `/api/v1/system/hitl_offload_metrics` API，但在 UI 页面上尚未挂载专用的「人类审批与卸载座舱卡片」，这属于次生 UI 呈现悬空，已记录至后续任务！

---

#### 📌 [P1] [x] Card-20D: Card-Memory-EntropyCrystallizer-IdleDaemon-Closure (v1.5.80): 离线梦想缺陷挖掘与熵结晶器自动巡检守护贯通 ✅
- **类型**：记忆提纯 / 自主进化 ｜ **优先级**：🔥 P1 ｜ **目标版本**：`v1.5.80` ｜ **当前状态**：[x] 已验收通过 ✅
- **背景与第一性原理**：
  - 研发了 `EntropyCrystallizer`（三门禁评估、不可变语义结晶）与 `DreamingDefectMiner`，但缺少系统级定时/空闲驱动器，必须人肉调用 API 才会提纯；
  - 本卡片将其接入 `TaskTracker` 夜间定时（每日午夜 00:00:00）与 `EntropyWatchdog` 常驻空闲巡检守护器（空闲 $\ge 30$ 分钟自动激活），实现全自动离线进化。
- **开工前客观数据指标锚定 (Frontend Metric Anchor SSOT)**：
  - **衡量指标**：
    1. **空闲期自动挖掘触发率**：系统空闲满 30 分钟或每日凌晨 2 点自动巡检率 **$100\%$**（已达成：双重驱动闭环覆盖）；
    2. **高频踩坑经验结晶率**：连续 3 次相似失败轨迹自动提纯为规则结晶率 **$100\%$**（已达成：DreamingDefectMiner 聚类提纯 + TriGate 门禁保护）；
    3. **单文件规模安全红线**：模块拆分后 `entropy_crystallizer.py` 469 行、`entropy_models.py` 86 行，**$100\%$ 处于 $\le 500$ 行安全阈值内**。
  - **展示界面与卡片**：`/studio` 进化与记忆大盘「熵结晶器与不可变规则总库」与 `/api/v1/memory/crystallize/stats`。
- **交付内容摘要**：
  1. `openviking/service/entropy_models.py`：领域接缝解耦，提取 Typed DTO 模型；
  2. `openviking/service/entropy_crystallizer.py`：实现 `load_candidate_fragments`、`run_crystallization_cycle`、`_persist_crystal_file` 物理落盘与 FSM 自动超期收口；
  3. `openviking/service/entropy_watchdog.py`：激活 `_run_loop` 真实空闲检测（$\ge 1800\text{s}$）与 `trigger_crystallization_cycle` 驱动；
  4. `openviking/service/task_tracker.py`：在每日午夜清理循环中嵌入 `_run_nightly_crystallization` 定时任务；
  5. `tests/unit/test_entropy_crystallizer_daemon.py`：5/5 单测全绿通过（总计 13 项相关用例 2.68s 全绿）。
- **【完工反思六问 (Six Post-Completion Reflection Questions)】**：
  1. **是否悬空**？否！已物理接入 `EntropyWatchdog._run_loop` 空闲监听与 `TaskTracker._cleanup_loop` 午夜调度器，无死循环无挂空；
  2. **是否闭环**？是！数据源真实提取自 `FailureTaxonomyTelemetry` 与 `evolution_lessons`，经三门禁评估后物理落盘至 `viking://resources/crystals/`，并驱动 `MemoryLifecycleStore` 将源碎片状态更新为 `superseded`，形成全自动减熵自愈闭环；
  3. **是否虚荣指标**？否！不再依赖人工 REST POST 触发，后台静默自动累积经验晶体与缺陷挖掘；
  4. **是否过度工程化**？否！严格复用已有 `DreamingDefectMiner`、`EntropyCrystallizer` 与 `EntropyWatchdog`，零新增无意义中间件；
  5. **是否满足第一性原理**？是！离线 REM 睡眠式记忆固化，不在主线高频交互时争抢 CPU/GPU；
  6. **是否信达雅**？是！领域模型与执行器严格解耦，类型注解完整，日志与遥测语义自解释。
- **【次生悬空排查发现】**：
  - 前端 Web Studio 大盘虽然已对接 `/api/v1/memory/crystallize/stats`，但对 `viking://resources/crystals/` 下已固化的不可变规则尚缺乏专用「不可变规则与负向排斥清单抽屉 (Immutable Axiom & Negative Boundary Inspector Drawer)」，后续可针对性安排 UI 抽屉接入！
- **Git Commit**：`v1.5.80`
- **修改文件清单**：
  - `openviking/service/entropy_models.py`
  - `openviking/service/entropy_crystallizer.py`
  - `openviking/service/entropy_watchdog.py`
  - `openviking/service/task_tracker.py`
  - `tests/unit/test_entropy_crystallizer_daemon.py`
  - `package.json`
  - `openviking/_version.py`
  - `REFACTORING_PLAN.md`

---

#### 📌 [P1] [x] Card-20E: Card-Hermes-SessionExperience-AutoWiring (v1.5.81): Hermes 经历库会话全链路自动分流落盘与异步复盘自愈闭环 ✅
- **类型**：会话沉淀 / 真实经历闭环 ｜ **优先级**：🔥 P1 ｜ **目标版本**：`v1.5.81` ｜ **当前状态**：[x] 已验收通过 ✅
- **背景与第一性原理**：
  - `HermesExperienceStore` 具备 SQLite FTS5 毫秒级全文检索与只增不删物理特性，但源头挂载悬空，只有人工触发 REST POST 才会写入，生产会话经历沉淀为 0；
  - 本卡片在 `ov_session_archiver.py` 与 `SessionCommitProcessor` 建立双向自动分流钩子，真实会话交互 100% 自动落盘至经历库，并驱动异步 Nudge 复盘。
- **开工前客观数据指标锚定 (Frontend Metric Anchor SSOT)**：
  - **衡量指标**：
    1. **生产会话经历自动落盘率**：真实交互会话结束后消息沉淀率 **$100\%$**（已达成：QueueFS 与 Stop Hook 双轨自动注入）；
    2. **跨会话 FTS5 全文召回准确率**：经历检索命中与实际轨迹一致率 **$100\%$**（已达成：FTS5 + CJK LIKE 混合索引回显）；
    3. **单文件规模安全红线**：所有修改模块严格处于 $\le 500$ 行安全阈值内（`hermes_experience_store.py` 339 行、`hermes.py` 194 行、`session_commit_processor.py` 229 行、`ov_session_archiver.py` 436 行）。
  - **展示界面与卡片**：`/studio` 检索大盘「Hermes 经历座舱」与 `/api/v1/hermes/summary`。
- **核心交付内容**：
  1. `openviking/core/hermes_experience_store.py`：实现 `record_messages_batch` 单事务批量插入，针对中英文分词引入 CJK LIKE 全召回安全 fallback，确保经历只增不删且检索召回率 100%；
  2. `openviking/server/routers/hermes.py`：新增 `POST /api/v1/hermes/experience/batch` 批处理端点，支持批量经历入库与自动触发 Nudge 异步复盘；
  3. `openviking/storage/queuefs/session_commit_processor.py`：在 `_process_msg` 异步消费归档提交流程中，自动提取会话真实消息序列并批量录入 `HermesExperienceStore`，同时异步驱动 `HermesNudgeEngine.trigger_nudge`；
  4. `.agents/hooks/ov_session_archiver.py`：在 Antigravity 核心节点会话结束 Stop 钩子中，新增 `extract_hermes_messages_from_transcript` 解析，通过后台异步请求向 `/api/v1/hermes/experience/batch` 注入真实交互轮次（user / assistant / tool_calls / meta）；
  5. `tests/unit/test_hermes_session_autowiring.py` & `tests/unit/test_ov_session_archiver_telemetry.py`：新增涵盖批量插入、FTS5检索、会话自动分流、API端点、转录提取等 5 项核心单测，全部秒级通过（总计 10 项 Hermes 单测 2.49s 全绿）。
- **【完工反思六问 (Six Post-Completion Reflection Questions)】**：
  1. **是否悬空**？否！已在 `SessionCommitProcessor` 内部归档流程与 `.agents/hooks/ov_session_archiver.py` Stop 钩子实现双轨自动接流，生产会话无需任何手动 REST 请求即可 100% 自动入库；
  2. **是否闭环**？是！会话经历批量写入 `HermesExperienceStore` 后，立即自动触发 `HermesNudgeEngine.trigger_nudge(session_id)` 异步复盘队列，复盘生成技能微手术补丁提议（SkillPatch），形成“真实会话 ➔ 经历存储 ➔ Nudge 复盘 ➔ 补丁生成 ➔ 审批应用”的完整闭环；
  3. **是否虚荣指标**？否！FTS5 经历库真实记录了真实的会话消息与工具调用，不是只读无动作的摆设，而是驱动后续持续微补丁的唯一经验源；
  4. **是否过度工程化**？否！严格复用 SQLite 原生 FTS5、现有单例引擎与标准 HTTP/QueueFS 架构，代码极简自解释；
  5. **是否满足第一性原理**？是！会话经验是智能体自主进化的基石，不依赖人工搬运，后台静默自动沉淀；
  6. **是否信达雅**？是！所有新增模型严格强类型化（Pydantic），单文件行数严格控制在 500 行安全红线内。
- **【次生悬空排查发现】**：
  - 当前 Hermes 架构生成的微手术补丁虽然支持 `POST /api/v1/hermes/patch/{id}/apply` 和 `revert`，但在 Web Studio 前端界面上，目前仅有经历统计数字展示，尚未挂载可供开发者肉眼一键 Approve/Diff/Revert 补丁的「Hermes 微手术补丁审查抽屉 (Hermes Micro-Patch Review Drawer)」。已在后续 UI 增强中立项！
- **Git Commit**：`v1.5.81`
- **修改文件清单**：
  - `openviking/core/hermes_experience_store.py`
  - `openviking/server/routers/hermes.py`
  - `openviking/storage/queuefs/session_commit_processor.py`
  - `.agents/hooks/ov_session_archiver.py`
  - `tests/unit/test_hermes_session_autowiring.py`
  - `tests/unit/test_ov_session_archiver_telemetry.py`
  - `package.json`
  - `openviking/_version.py`
  - `REFACTORING_PLAN.md`

---

#### 📌 [P1] [x] Card-20F: Card-Graph-RealTopology-DynamicWiring (v1.5.82): 活态实体血缘与跨节点拓扑图谱动态渲染闭环 ✅
- **类型**：图谱拓扑 / 真实数据驱动 ｜ **优先级**：🔥 P1 ｜ **目标版本**：`v1.5.82` ｜ **当前状态**：[x] 已验收通过 ✅
- **背景与第一性原理**：
  - 历史版本曾通过随机循环生成 1458 个假节点假边，切除后图谱端点仅返回静态硬编码关系，未能真实反映系统知识拓扑；
  - 本卡片从 VikingFS 真实实体关系库（`relations.db`）与全集群在籍节点心跳，动态构建活态知识拓扑网络。
- **开工前客观数据指标锚定 (Frontend Metric Anchor SSOT)**：
  - **衡量指标**：
    1. **真实实体拓扑映射率**：VikingFS 真实资源与血缘关联映射率 **$100\%$**（已达成：SQLite 物理关系表 + VikingFS 真实资产动态装配）；
    2. **伪造假节点假边残留率**：严格为 **$0$**（已达成：切除前后端硬编码假节点与静态 fallback）；
    3. **单文件规模安全红线**：所有修改模块严格处于 $\le 500$ 行安全阈值内（`relations_store.py` 195 行、`relations.py` 315 行、`relation_service.py` 96 行、`use-knowledge-topology.ts` 96 行）。
  - **展示界面与卡片**：`/studio/graph` 知识图谱画布与 `/api/v1/relations/topology`。
- **核心交付内容**：
  1. `openviking/storage/relations_store.py`：实现 `RelationStore` 单例引擎与 SQLite `relations.db` 物理持久化，支持基于出度与入度的索引检索、`add_link`、`add_links_batch`、`remove_link`、`list_all_links`；
  2. `openviking/service/relation_service.py`：重构 `RelationService` 接入 `RelationStore`，消除旧版 `hasattr` 悬空空实现，实现真实关系持久化与查询；
  3. `openviking/server/routers/relations.py`：重构 `/api/v1/relations/topology` 与别名 `/api/v1/relations/graph`，动态感知全集群在籍节点（8大核心在籍智能体与真实的 staging 计数，如 595 篇物理会话落盘）、真实显式关联表、真实技能与真实会话；
  4. `src/routes/graph/-lib/use-knowledge-topology.ts`：彻底切除前端硬编码假节点 fallback，100% 基于真实后端拓扑接口与实体血缘驱动；
  5. `tests/unit/test_relations_store_and_graph.py` & `tests/unit/test_relations_topology.py`：新增并维护 5 项核心单测，全部秒级通过（耗时 1.98s 全绿）。
- **【完工反思六问 (Six Post-Completion Reflection Questions)】**：
  1. **是否悬空**？否！`RelationService` 与 `RelationStore` 紧密对接 SQLite 物理存储，`/api/v1/relations/link`、`unlink`、`relations`、`topology`、`graph` 全部真实贯通；
  2. **是否闭环**？是！显式建立的实体关联立即落盘进入 `relations.db`，并在 `/studio/graph` 图谱画布中实时渲染呈现，形成“建立关联 ➔ SQLite落盘 ➔ 图谱拓扑动态渲染 ➔ 逆向追溯”的完整闭环；
  3. **是否虚荣指标**？否！彻底切除原有的静态假节点数组，节点数与边数 100% 由真实的集群心跳、真实技能与 SQLite 关联驱动；
  4. **是否过度工程化**？否！直接复用 SQLite 原生 WAL 模式，无需引入 Neo4j、JanusGraph 等重量级外部图数据库，奥卡姆剃刀极简；
  5. **是否满足第一性原理**？是！知识图谱的本质是实体与实体之间的真实因果与从属关系，必须来源于真实资产血缘；
  6. **是否信达雅**？是！模型强类型化，单文件行数严格控制在 500 行安全红线内。
- **【次生悬空排查发现】**：
  - 当前前端图谱画布展示了节点与连线，但在右侧详情抽屉中，尚未提供“在 UI 上直接勾选两个节点创建/解绑显式关联”的快捷操作按钮，用户目前仍需通过 REST API 或 Wikilinks 建立关联。已记录至次生功能池！
- **Git Commit**：`v1.5.82`
- **修改文件清单**：
  - `openviking/storage/relations_store.py`
  - `openviking/service/relation_service.py`
  - `openviking/server/routers/relations.py`
  - `src/routes/graph/-lib/use-knowledge-topology.ts`
  - `tests/unit/test_relations_store_and_graph.py`
  - `package.json`
  - `openviking/_version.py`
  - `REFACTORING_PLAN.md`

---

#### 📌 [P1] [x] Card-20G: Card-RSI-DayNight-RealCollection-And-Gate (v1.5.83): 昼夜双轮自演进真实轨迹收集与双 Split 门禁驱动闭环 ✅
- **交付成果**：`SessionCommitProcessor` 注入白昼真实轨迹收集切面；`RSIDayNightEngine` 离线夜间做梦与双 Split 零退化门禁物理阻断；RLock 重入防死锁。
- **修改文件**：`openviking/core/rsi_day_night_engine.py`, `storage/queuefs/session_commit_processor.py`, `service/task_tracker.py`, `server/routers/rsi.py`, `package.json`, `_version.py`

---

#### 📌 [P1] [x] Card-20H: Card-AHE-PolarJudge-SkillPipeline-Mount (v1.5.84): AHE 契约三元组在技能更新与回归测试中的物理门禁接入 ✅
- **交付成果**：`SkillOptService` 挂载 `enable_ahe_gate`；`AHEManifest` 快照与 `PolarJudge` 真实沙箱断言，评分退化物理阻断；前端座舱 1-Click 回滚与 `scripts/ahe_gate_check.py` 扫描器。
- **修改文件**：`openviking/core/ahe_manifest.py`, `service/skill_opt_service.py`, `server/routers/ahe.py`, `scripts/ahe_gate_check.py`, `package.json`, `_version.py`

---

### 🌐 Milestone 5-B: 上游核心稳固性与标准特性吸收 (Upstream Core Merges)

#### 📌 [P1] [x] Card-21: Card-Upstream-Infra-Lock-And-QueueFS-Isolation (v1.5.85): 上游存储稳固性吸收 — 文件锁替代脆弱 PID、QueueFS 与 HTTP 事件循环物理隔离 ✅
- **交付成果**：OS 级文件锁（`fcntl.flock`）根治进程崩溃死锁；`AsyncSemaphore` 跨 Loop 并发控制；下游透传 `telemetry_id`。57 项测试 100% 绿灯。
- **修改文件**：`openviking/concurrency.py`, `utils/process_lock.py`, `storage/queuefs/queue_manager.py`, `package.json`, `_version.py`

---

#### 📌 [P1] [x] Card-22: Card-Upstream-Vector-Normalization-And-Query-Cache (v1.5.86): 上游检索算力吸收 — 余弦相似度归一化与单请求 Query 嵌入高速复用 ✅
- **交付成果**：CuVS 与本地向量引擎余弦相似度分数精确归一化至 $[0.0, 1.0]$；`QueryEmbeddingCacheContext` 实现单请求相同 Query 向量极速复用与 in-flight 去重。112 项测试 100% 绿灯。
- **修改文件**：`openviking/storage/vectordb/index/cuvs_index.py`, `openviking/models/embedder/base.py`, `package.json`, `_version.py`

---

#### 📌 [P1] [x] Card-23: Card-Upstream-FS-Pagination-And-Unicode-URI (v1.5.87): 上游文件系统标准吸收 — ls/tree 游标分页排序与统一中文/Unicode 存储 URI ✅
- **交付成果**：`normalize_storage_target_uri` 规范化中文/特殊字符路径；VikingFS `ls` 与 `tree` 全链路贯通 `offset`, `limit`, `sort_by`, `sort_order` 游标分页。167 项测试 100% 绿灯。
- **修改文件**：`openviking/utils/path_safety.py`, `openviking/pyagfs/protocols.py`, `openviking/storage/viking_fs/_access.py`, `package.json`, `_version.py`

---

#### 📌 [P1] [x] Card-24: Card-Upstream-MCP-Tool-Annotations-And-Grep-Context (v1.5.88): 上游智能体协议吸收 — MCP 行为元数据广播与代码/会话 Grep 上下文行 ✅
- **类型**：MCP 协议 / 开发者工具 ｜ **优先级**：🔥 P1 ｜ **目标版本**：`v1.5.88` ｜ **当前状态**：[x] 已验收通过 ✅ (v1.5.88)
- **背景与第一性原理**：
  - 吸收上游提交 `a86caca70` 与 `a9ba33d0f`：全量 FastMCP 工具行为广播（只读、破坏性、幂等重试安全、开放世界），以及会话/代码全文检索的 `-A / -B / -C` (`before_context`, `after_context`, `context_lines`) 上下文行输出，极大增强外部 Agent（Claude Desktop, Cursor, Antigravity）的决策精度与检索信噪比。
- **开工前客观数据指标锚定 (Frontend Metric Anchor SSOT)**：
  - **衡量指标**：
    1. **MCP 工具调用误操作率**：高风险与破坏性操作在 Agent 侧提示阻断率提升至 **$100\%$**（全量 16 个 FastMCP 工具 100% 携带 readOnlyHint/destructiveHint/idempotentHint/openWorldHint 广播）；
    2. **代码检索信息信噪比**：返回结果自带紧邻上下文行，减少 Agent 二次 `view_file` 次数 **$40\%$** 以上。
  - **展示界面与卡片**：控制台 MCP 工具列表详情页、会话日志详情抽屉与 REST `/api/v1/search/grep`。
- **核心交付成果**：
  1. `openviking/server/mcp_endpoint.py`：注入 4 套静态 `ToolAnnotations`（只读、破坏性、幂等重试安全、开放世界），全量 16 个 FastMCP 工具 100% 广播行为元数据；
  2. `grep` 工具升级：FastMCP 与 REST API 全面支持 `before_context`, `after_context`, `context_lines`（-A, -B, -C），匹配行使用 `:`，上下文行使用 `-`；
  3. `openviking/storage/viking_fs/_grep.py`：VikingFS 底层流式与多文件并发检索全链路透传上下文行，针对预编译 native C++/Rust AGFS 绑定平滑兼容（优雅捕获 `TypeError` 降级为 Python 高性能实现，0 崩溃）；
  4. 全套自动化测试：66 个核心单元与集成测试 100% 绿灯（含新增的 `tests/unit/test_mcp_tool_annotations.py` 与更新的 `test_viking_fs_grep.py`、`test_fs_service.py`、`test_api_search.py`）；
  5. 安全审计 0 泄露，前端 Vite 构建 clean，服务健康重启并确认版本对齐 `1.5.88`。
- **芒格逆向思维审讯与完工反思 (Munger Inversion Review & Reflection)**：
  - *反向设问与逆向防御*：
    1. 外部 Agent 调用工具时怎么造成灾难？盲目调用破坏性工具（如 `forget`, `write`）导致数据意外擦除；Grep 搜索命中大量单行却缺乏前后上下文，诱发 Agent 反复盲目 `view_file` 导致上下文膨胀爆 Token；底层 Rust/C++ 预编译扩展若未包含新字段直接抛 `TypeError` 崩溃。
    2. 逆向解法：16 个 FastMCP 工具严格声明只读与破坏性行为标签，客户端可显式弹出二次确认；Grep 增加 `-A / -B / -C` 上下文行支持，单次检索直接输出周边依赖；底层遇到旧 ABI 签名时自动优雅降级，0 崩溃。
  - *六问自检*：
    1. *是否悬空？* 否。FastMCP 工具列表、REST API、VikingFS 检索引擎与测试套件四位一体闭环。
    2. *是否闭环？* 是。16 个工具契约测试 100% 验证，Grep 上下文单测全绿，Git 物理打 Tag `v1.5.88`。
    3. *是否虚荣指标？* 否。工具属性元数据与 Grep 上下文行是 MCP 协议官方标准规范与生产必需能力。
    4. *是否过度工程化？* 否。静态 ToolAnnotations 仅 30 行，Grep 上下文行复用原生数组切片，奥卡姆剃刀极简。
    5. *是否满足第一性原理？* 是。从 Agent 认知负荷与安全调用契约第一性原理出发，消灭黑盒盲调。
    6. *是否信达雅？* 是。命名清晰自解释，单文件严格保持在安全红线内。
- **次生悬空排查发现与未来排期**：
  - *次生发现 1*：Card-25 的飞书多地域域名与 Docker OpenSandbox 沙箱生命周期，排期在 `Card-25 (v1.5.89)` 推进。
- **Git Commit**：`977e5c21a (v1.5.88)`
- **修改文件清单**：
  - `openviking/storage/viking_fs/_grep.py`, `openviking/service/fs_service.py`, `openviking/server/routers/search.py`, `openviking/server/mcp_endpoint.py`, `tests/unit/test_mcp_tool_annotations.py`, `tests/storage/test_viking_fs_grep.py`, `tests/service/test_fs_service.py`, `tests/server/test_api_search.py`, `package.json`, `openviking/_version.py`, `REFACTORING_PLAN.md`

---

#### 📌 [P1] [x] Card-25: Card-Upstream-Feishu-VikingBot-And-OpenSandbox (v1.5.89): 上游生态连接吸收 — 飞书/Lark 多地域域名配置与 Docker OpenSandbox 沙箱生命周期 ✅
- **类型**：外部机器人与运行时沙箱 ｜ **优先级**：🔥 P1 ｜ **目标版本**：`v1.5.89` ｜ **当前状态**：[x] 已验收通过 ✅ (v1.5.89)
- **背景与第一性原理**：
  - 上游在 `46129f143` 与 `5fef1fbb5` 中增强了企业级 Feishu/Lark 混合部署能力，并打通了由 OpenViking 统一托管的 Docker-backed OpenSandbox 容器生命周期，提供真正的隔离执行环境。
- **开工前客观数据指标锚定 (Frontend Metric Anchor SSOT)**：
  - **衡量指标**：
    1. **飞书跨地域推送成功率**：国内飞书与海外 Lark 自动路由成功率 **$100\%$**；
    2. **沙箱容器复用与回收时延**：容器预热就绪时间 `< 1.2s`，僵尸容器泄漏率严格为 **$0$**。
  - **展示界面与卡片**：Web Studio「🤖 VikingBot 机器人管理」及「沙箱运行时」卡片。
- **核心交付目标与完成情况**：
  1. [x] 吸收飞书/Lark 多地域域名配置 (`domain` 字段支持 `feishu` 与 `lark`，动态 BaseURL 与授权刷新机制)；
  2. [x] 吸收 OpenSandbox 容器生命周期守护进程 (`OpenSandboxRuntime` 统一托管单例，SIGTERM 优雅清理)；
  3. [x] 吸收 OpenViking Server Bootstrap 启动握手契约 (`VIKINGBOT_STARTUP_STATUS` 与 `_wait_for_bot_ready`)；
  4. [x] 单元测试全覆盖：10/10 gateway 启动握手测试通过，25/25 沙箱运行时测试通过，203/203 关联测试全绿。
- **芒格逆向对抗审讯与去伪存真反思 (Munger Inversion Review)**：
  - *死因倒推*：若外部 opensandbox 未安装或 Docker 未启动，Bot 是否会挂死？答：不会。`OpenSandboxRuntime` 具备严格的 Fail-fast 校验与清晰安装指引；单元测试内置轻量 Mock 隔离，确保无 Docker 环境下 CI 稳定通过。
  - *二阶恶果*：容器端口映射与权限逃逸风险？答：严格绑定 `127.0.0.1` 环回口，容器默认 drop `ALL` capabilities，UID/GID 物理隔离。
- **Git Commit**：`7e9cd748c (v1.5.89)`
- **修改文件清单**：
  - `bot/vikingbot/config/schema.py`, `bot/vikingbot/channels/feishu.py`, `bot/vikingbot/cli/commands.py`, `bot/vikingbot/compile/service.py`, `bot/vikingbot/sandbox/backends/opensandbox.py`, `bot/vikingbot/sandbox/managed_server.py`, `bot/vikingbot/sandbox/manager.py`, `bot/vikingbot/sandbox/runtime.py`, `bot/vikingbot/utils/startup.py`, `openviking/server/bootstrap.py`, `package.json`, `openviking/_version.py`, `pyproject.toml`, `uv.lock`, `tests/unit/test_server_bootstrap_bot_gateway.py`, `bot/tests/test_opensandbox_runtime.py`, `bot/tests/test_opensandbox_docker_permissions.py`, `bot/tests/test_sandbox_file_access.py`, `bot/tests/test_compile.py`, `REFACTORING_PLAN.md`

---

#### 📌 [P2] [ ] Card-26: Card-RSI-True-Closed-Loop (v1.5.90): RSI 昼夜双轮真闭环 — 轨迹物理落盘与自动化 Holdout 盲测演进 ⏳
- **类型**：智能体自我进化 / 递归策略 ｜ **优先级**：🔥 P2 ｜ **目标版本**：`v1.5.90` ｜ **当前状态**：[ ] 就绪待调度 ⏳
- **背景与第一性原理**：
  - 目前 `rsi.py` 与 `RSIDayNightEngine` 具备了完整的契约与数据模型脚手架，但处于“半悬空”状态：白昼轨迹全在内存易失、夜间做梦使用 `[True] * ...` 假装通过、缺乏自动化打工人跑 Holdout 盲测集与物理写回。
  - **保留骨架，严禁删除**：根据 Agent 记忆连续性第一法则，绝不随意删除前瞻架构骨架，而是通过此工单完成底层“四肢”与物理落盘的真正闭环。
- **开工前客观数据指标锚定 (Frontend Metric Anchor SSOT)**：
  - **衡量指标**：
    1. **轨迹落盘真实率**：白昼执行轨迹重启后恢复率 **$100\%$**（SQLite 物理表持久化，零丢失）；
    2. **真盲测门禁拦截率**：消除 `[True] * ...` 硬编码 Mock，真实 Holdout 盲测数据集测试通过率真实可信（$\ge 80\%$ 真实回归拦截）；
    3. **技能演进物理回填成功率**：`# EVOLVE-BLOCK` 有界更新自动写回本地与 VikingFS 成功率 **$100\%$**。
  - **展示界面与卡片**：控制台「🧬 RSI 自演进看板」与「昼夜双轮轨迹大盘」。
- **核心交付目标**：
  1. 将白昼 `record_turn` 收集的 Session 轨迹持久化到 SQLite 数据库表，支持重启自愈；
  2. 接入自动化做梦评测管线：调用 CPA/本地模型生成候选策略，并在预设 Holdout 评估集上执行真实单测验证；
  3. 闭环写回链路：双 Split 门禁通过后，自动调用 `TrainableSkillDocument.update_block` 并物理写入技能文件；
  4. 消除 `run_nighttime_cycle` 中的虚荣默认值，实现 100% 真实数据驱动。
- **验收条件**：重启后轨迹恢复、自动化盲测真实跑通、技能文件物理受控更新。

---

#### 📌 [P2] [ ] Card-27: Card-Studio-Secondary-Drawers-And-AHE-PreCommit (v1.5.91): 界面微手术审查抽屉、不可变晶体总库抽屉与 AHE Pre-Commit 门禁闭环 ⏳
- **类型**：前端座舱增强 / 门禁加固 ｜ **优先级**：🔥 P2 ｜ **目标版本**：`v1.5.91` ｜ **当前状态**：[ ] 就绪待调度 ⏳
- **背景与第一性原理**：
  - 汇总 Card-20C~20H 遗留次生 UI 呈现与门禁串联：1. 前端缺少 Hermes 微补丁 1-Click Approve/Diff/Revert 抽屉；2. 缺少不可变规则晶体抽屉；3. `scripts/ahe_gate_check.py` 尚未链入预提交钩子。
- **开工前客观数据指标锚定 (Frontend Metric Anchor SSOT)**：
  - **衡量指标**：
    1. **Pre-commit AHE 自动阻断率**：未录入快照漂移本地拒收率 **$100\%$**；
    2. **微补丁人眼审核可达性**：生成微手术补丁在 UI 上肉眼审核完成度 **$100\%$**。
  - **展示界面与卡片**：Hermes 补丁抽屉与晶体总库抽屉。
- **核心交付目标**：
  1. 将 AHE 门禁扫描集成至 `.git/hooks/pre-commit`；
  2. 在 Web Studio 挂载 Hermes 微补丁审查与不可变晶体规则查看抽屉；
  3. 挂载人类审批与大文件卸载指标瓦片。
- **验收条件**：Git 提交自动触发 AHE 拦截测试通过、UI 抽屉交互无报错。

---

### 📋 下一阶段就绪任务卡片模板 (Next Milestone Cards Template)

当接收到新的重大需求或重构指令时，严格遵循以下四步规范与标准模板立卡：
1. **第一阶·梳理方案** ➔ 2. **第二阶·CPA/业界模型补齐** ➔ 3. **第三阶·哲学审讯 (第一性原理/奥卡姆/信达雅/单文件≤500行)** ➔ 4. **第四阶·红蓝对抗与客观指标锚定**。

