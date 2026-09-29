# 🗺️ OpenViking 项目主线重构与原子化任务卡片总看板 (Master Task Cards Kanban - SSOT)

> **关联研发大蓝图**：[`BLUEPRINT.md`](file:///home/skloxo/aho/openclaw/project/.agents/BLUEPRINT.md) ｜ **交付全量归档台账**：[`DELIVERY_ARCHIVE.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md) ｜ **通用资产档案库**：[`COMPONENT_AND_WHEEL_INVENTORY.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/docs/architecture/COMPONENT_AND_WHEEL_INVENTORY.md) ｜ **👁️ 人工验收测试指南**：[`docs/HUMAN_ACCEPTANCE_TESTING.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/docs/HUMAN_ACCEPTANCE_TESTING.md)
> **唯一真相源 (SSOT)**：本文档为 OpenViking 当前活跃的重构规划与就绪待调度的任务矩阵看板。历史所有已验收交付的版本履历（Milestone 1~4 全量 19 张 Task Cards 及前序波次）已完整归档至 [`DELIVERY_ARCHIVE.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md)，严禁多头维护。所有版本的 30 秒人工肉眼走查清单集中在 `docs/HUMAN_ACCEPTANCE_TESTING.md`。

---

## 📌 一、 研发基线与近期已交付版本速查索引 (Recent Delivered Releases: v1.5.70 ~ v1.5.76)

> **生产物理事实声明**：
> - **线上正式部署版本**：**`v1.4.106`**（物理访问地址：`vk.tide.red/studio/home`，已实机验证）；
> - **最新生产封板版本**：**`v1.5.76`**（Tag: `v1.5.76`，Commit: `03e1b4728`，已全量推流至远端）；
> - **历史里程碑详单检索**：如需查阅具体版本的修改文件清单、自动化单测回显与架构细节，请点击跳转至 [`DELIVERY_ARCHIVE.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md)。

| 版本 Tag | 任务工单 ID | 模块与重构主题 | 核心治理成果与物理交付物 | 验收状态 |
|:---|:---|:---|:---|:---:|
| **`v1.5.76`** | **Card-Cache-Tier2-LRU-FastHit** | 亚毫秒级 LRU 本地二级缓存引擎、防击穿协议与 10k 并发压测总盘 | 1. LRU 亚毫秒级二级缓存 (`cache_tier2_engine.py`, 195行)，`wait=False` 防击穿协议；<br>2. REST API 端点 (`/api/v1/cache/stats`, `/clear`, `/benchmark`)；<br>3. 监控大盘交互卡片 (`tier2-cache-card.tsx`, 198行)；<br>4. 实测 10,000 次操作平均延迟 0.0007ms，单测 6/6 全绿，生产构建通过。<br>**详见台账**：[`DELIVERY_ARCHIVE.md#card-19`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md) | [x] 已验收通过 ✅ |
| **`v1.5.75`** | **Card-DSPy-MIPO-Prompt-Compiler** | Stanford DSPy (MIPO) 强类型提示词编译、Few-Shot 自优化与试验台 | 1. DSPy 编译引擎 (`dspy_compiler_engine.py`, 223行)，强类型 Schema 规约提取与 Strict JSON 输出；<br>2. 检索大屏 Tab 11 试验台套件 (`dspy-compiler-cockpit.tsx`, 265行)；<br>3. 实机验证编译耗时 0.87ms，契约状态 PASS 零幻觉，单测 5/5 全绿。<br>**详见台账**：[`DELIVERY_ARCHIVE.md#card-18`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md) | [x] 已验收通过 ✅ |
| **`v1.5.74`** | **Card-Context-Router-Pipeline** | 异构多引擎上下文路由网关、自适应语义分段与统一重组管线 | 1. 统一调度 5 驱压缩矩阵 (Native Caching, LLMLingua-2, TokenShift, SkillZip, Active Notes)；<br>2. 5 类提示词片段自适应语义分段与严格保序无损重组；<br>3. 检索大屏 Tab 10 路由网关座舱 (`context-router-cockpit.tsx`, 373行)；单测 7/7 全绿。<br>**详见台账**：[`DELIVERY_ARCHIVE.md#card-17`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md) | [x] 已验收通过 ✅ |
| **`v1.5.73`** | **Card-TokenShift-ASTAware-CodeCompressor** | PointFive TokenShift 代码语法树保护探针与分级无损压缩 | 1. AST 语法感知三级渐进压缩 (L0 大纲 ~70%, L1 骨架 ~50%, L2 紧凑 ~25%)；<br>2. Python / TS / JS / SQL / Shell 多语言 AST 破坏率严格为 0；<br>3. 检索大屏专属 Tab 座舱 (`tokenshift-cockpit.tsx`, 327行)；单测 7/7 全绿。<br>**详见台账**：[`DELIVERY_ARCHIVE.md#card-16`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md) | [x] 已验收通过 ✅ |
| **`v1.5.72`** | **Card-SkillOpt-QualityGate-And-AutoOpt-Engine** | SkillOpt Attempt / Judge 质量门禁引擎与自动优化 Patch 闭环 | 1. 规范/能力/信噪比/触发区分度四维评分标尺 (0~100分) 与 Grade S~D 评级；<br>2. Attempt 执行测试与 Judge Gate 判据输出；<br>3. 技能大盘「🎯 SkillOpt 评测与体检」一级 Tab；单测 7/7 全绿。<br>**详见台账**：[`DELIVERY_ARCHIVE.md#card-15`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md) | [x] 已验收通过 ✅ |
| **`v1.5.71`** | **Card-Skill-LiveGen-Editor-And-Sandbox** | LiveGen 在线技能创生脚手架、规范校验与自然语言沙箱 | 1. Monaco 高亮编辑、YAML 校验与单文件规模阶梯评估；<br>2. 中文滑窗 n-gram 语义触发推演沙箱；<br>3. 技能大盘「✨ LiveGen 在线技能创生」一级 Tab；单测 7/7 全绿。<br>**详见台账**：[`DELIVERY_ARCHIVE.md#card-14`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md) | [x] 已验收通过 ✅ |
| **`v1.5.70`** | **Card-Privacy-Masker-And-PydanticV2** | 统一动态隐私脱敏引擎 (PrivacyMasker) 与 Pydantic V2 告警清退 | 1. 高性能预编译正则脱敏管道 (`privacy_masker.py`, 123行)；<br>2. Pydantic V2 `model_config = ConfigDict(...)` 升级，全库测试 0 告警 0 失败；<br>3. 客户端 LocalClient / Session 动态导出加固；单测 12/12 全绿。<br>**详见台账**：[`DELIVERY_ARCHIVE.md#card-13`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md) | [x] 已验收通过 ✅ |

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

#### 📌 [P1] [ ] Card-20E: Card-Hermes-SessionExperience-AutoWiring (v1.5.81): Hermes 经历库会话全链路自动分流落盘与异步复盘自愈闭环 ⏳
- **类型**：会话沉淀 / 真实经历闭环 ｜ **优先级**：🔥 P1 ｜ **目标版本**：`v1.5.81` ｜ **当前状态**：[ ] 就绪待调度 ⏳
- **背景与第一性原理**：
  - `HermesExperienceStore` 具备 SQLite FTS5 毫秒级全文检索与只增不删物理特性，但源头挂载悬空，只有人工触发 REST POST 才会写入，生产会话经历沉淀为 0；
  - 本卡片在 `ov_session_archiver.py` 与 `SessionCommitProcessor` 建立双向自动分流钩子，真实会话交互 100% 自动落盘至经历库，并驱动异步 Nudge 复盘。
- **开工前客观数据指标锚定 (Frontend Metric Anchor SSOT)**：
  - **衡量指标**：
    1. **生产会话经历自动落盘率**：真实交互会话结束后消息沉淀率 **$100\%$**；
    2. **跨会话 FTS5 全文召回准确率**：经历检索命中与实际轨迹一致率 **$100\%$**。
  - **展示界面与卡片**：检索大盘「Hermes 经历座舱」与会话中心。
- **核心交付目标**：
  1. 在 `SessionCommitProcessor` 中注入 Hermes 消息流写入钩子；
  2. 在会话结束 Hook 中打通真实 tool_calls 与 meta 沉淀；
  3. 激活异步 Nudge 队列定时复盘与微补丁提议。
- **验收条件**：会话结束后自动写入 SQLite FTS5 经历库、检索端点回显真实记录、单测全绿。

---

#### 📌 [P1] [ ] Card-20F: Card-Graph-RealTopology-DynamicWiring (v1.5.82): 活态实体血缘与跨节点拓扑图谱动态渲染闭环 ⏳
- **类型**：图谱拓扑 / 真实数据驱动 ｜ **优先级**：🔥 P1 ｜ **目标版本**：`v1.5.82` ｜ **当前状态**：[ ] 就绪待调度 ⏳
- **背景与第一性原理**：
  - 历史版本曾通过随机循环生成 1458 个假节点假边，切除后图谱端点仅返回静态硬编码关系，未能真实反映系统知识拓扑；
  - 本卡片从 VikingFS 真实实体关系库（`relations.db`）与全集群在籍节点心跳，动态构建活态知识拓扑网络。
- **开工前客观数据指标锚定 (Frontend Metric Anchor SSOT)**：
  - **衡量指标**：
    1. **真实实体拓扑映射率**：VikingFS 真实资源与血缘关联映射率 **$100\%$**；
    2. **伪造假节点假边残留率**：严格为 **$0$**。
  - **展示界面与卡片**：`/studio/graph` 知识图谱画布。
- **核心交付目标**：
  1. 重构 `/api/v1/relations/graph` 路由，从 SQLite 真实关系表动态拉取实体与关联边；
  2. 整合跨节点在籍 Agent 心跳与任务流转链路；
  3. 前端图谱画布适配高密性冷淡视觉规范，切除一切硬编码静态 fallback。
- **验收条件**：图谱 100% 由真实后端数据驱动、单测全绿、前端构建 PASS。

---

#### 📌 [P1] [ ] Card-20G: Card-RSI-DayNight-RealCollection-And-Gate (v1.5.83): 昼夜双轮自演进真实轨迹收集与双 Split 门禁驱动闭环 ⏳
- **类型**：递归自演进 / 门禁验证 ｜ **优先级**：🔥 P1 ｜ **目标版本**：`v1.5.83` ｜ **当前状态**：[ ] 就绪待调度 ⏳
- **背景与第一性原理**：
  - `RSIDayNightEngine` 实现了白昼轨迹收集与夜间信用分配及 Holdout 盲测无退化门禁，但缺乏生产拦截切面与昼夜定时切换；
  - 本卡片在 MCP 工具执行与 `TaskTracker` 中注入收集切面，定时在夜间低峰期执行双 Split 门禁演进。
- **开工前客观数据指标锚定 (Frontend Metric Anchor SSOT)**：
  - **衡量指标**：
    1. **真实执行轨迹白昼收集率**：白昼模式下真实调用轨迹捕获率 **$100\%$**；
    2. **Holdout 验证集零退化拦截率**：策略演进时出现既有能力破坏时物理阻断率 **$100\%$**。
  - **展示界面与卡片**：进化大盘「昼夜双轮自演进看板」。
- **核心交付目标**：
  1. 将 `record_turn` 作为轻量切面挂载至 FastMCP 工具完成钩子；
  2. 在夜间低峰期触发 Holdout 盲测与局部信用分配；
  3. 门禁验证通过后才允许更新技能可编辑区块。
- **验收条件**：白昼真实轨迹自动累加、夜间模拟验证拦截退化、单测全绿。

---

#### 📌 [P1] [ ] Card-20H: Card-AHE-PolarJudge-SkillPipeline-Mount (v1.5.84): AHE 契约三元组在技能更新与回归测试中的物理门禁接入 ⏳
- **类型**：契约门禁 / 技能生命周期 ｜ **优先级**：🔥 P1 ｜ **目标版本**：`v1.5.84` ｜ **当前状态**：[ ] 就绪待调度 ⏳
- **背景与第一性原理**：
  - `AHEEngine` 与 `PolarJudge` 实现了可回滚快照与假设验证，但作为孤立单例未接入技能变更工作流；
  - 本卡片将其挂载到技能更新、Git Pre-commit 与 `skill_opt` 中，发生漂移或断言失败时物理阻断提交流水线。
- **开工前客观数据指标锚定 (Frontend Metric Anchor SSOT)**：
  - **衡量指标**：
    1. **技能变更快照漂移告警率**：未授权文件变更与快照漂移检测率 **$100\%$**；
    2. **Polar 判官假设失败阻断率**：断言不满足时物理阻止写入/发布率 **$100\%$**。
  - **展示界面与卡片**：技能大盘「AHE 契约与 Polar 判官」卡片。
- **核心交付目标**：
  1. 在 `skill_opt` 优化发布前强制调用 `create_manifest` 与 `verify_manifest`；
  2. 结合 PolarJudge 验证技能关键功能是否完好；
  3. 发生不符合预期时自动生成回滚快照与归因聚类。
- **验收条件**：技能优化违背假设时物理拦截、回滚测试通过、单测全绿。

---

### 🌐 Milestone 5-B: 上游核心稳固性与标准特性吸收 (Upstream Core Merges)

#### 📌 [P1] [ ] Card-21: Card-Upstream-Infra-Lock-And-QueueFS-Isolation (v1.5.78): 上游存储稳固性吸收 — 文件锁替代脆弱 PID、QueueFS 与 HTTP 事件循环物理隔离 ⏳
- **类型**：底层存储架构 / 进程生命周期 ｜ **优先级**：🔥 P1 ｜ **目标版本**：`v1.5.78` ｜ **当前状态**：[ ] 就绪待调度 ⏳
- **背景与第一性原理**：

  - 上游核心提交 `f316f2756` 与 `a681e099e` 直击容器/重启后 PID 漂移导致死锁，以及异步 QueueFS 任务阻塞 FastAPI 主事件循环的深水区 Bug；
  - 本卡片吸收该纯工程基建优化，切除旧版 600 余行脆弱的本地 PID 文件检查，引入 `openviking.concurrency` 专用线程事件循环，实现后台任务与 HTTP 请求物理隔离。
- **开工前客观数据指标锚定 (Frontend Metric Anchor SSOT)**：
  - **衡量指标**：
    1. **HTTP 请求 P99 抖动延迟**：在后台大批量队列处理时，前端请求 P99 延迟从 `~180ms` 降至 `< 15ms`（消除事件循环争抢）；
    2. **服务重启死锁率**：异常停机或硬重启后存储锁自愈通过率达到 **$100\%$**（0 残留 PID 误判）。
  - **展示界面与卡片**：控制台「系统健康」卡片及「队列流水线」性能仪表盘。
- **核心交付目标**：
  1. 移植上游 `openviking/concurrency.py`，实现后台队列专用 Worker Loop 与服务主 Loop 彻底解耦；
  2. 移植 `openviking/utils/process_lock.py` 文件锁改造，仅保护本地存储与 cuvs 后端，支持优雅抢占与超时回收；
  3. 补齐写入等待时下游索引遗漏的边缘修复 (`2b7efd566`)。
- **验收条件**：单测 100% 通过、并发重启压力测试 0 锁死、安全扫描 0 泄露。

---

#### 📌 [P1] [ ] Card-22: Card-Upstream-Vector-Normalization-And-Query-Cache (v1.5.79): 上游检索算力吸收 — 余弦相似度归一化与单请求 Query 嵌入高速复用 ⏳
- **类型**：向量引擎 / 语义检索引擎 ｜ **优先级**：🔥 P1 ｜ **目标版本**：`v1.5.79` ｜ **当前状态**：[ ] 就绪待调度 ⏳
- **背景与第一性原理**：
  - 上游在 `707a6da62` 与 `2cdf64c7a` 中解决了两项高频痛点：余弦相似度分数漂移未统一到 $[0, 1]$ 导致前端难以设定统一过滤阈值；复杂上下文装配时重复对相同 Query 发起多次 embedding 计算。
- **开工前客观数据指标锚定 (Frontend Metric Anchor SSOT)**：
  - **衡量指标**：
    1. **单请求检索耗时**：多阶段复合检索（Find + Context Explorer）端到端延迟降低 **$35\% \sim 50\%$**（避免重复向量化）；
    2. **余弦相似度分数确定性**：跨本地索引/cuvs 的相似度分值百分之百严格落入 $[0.0, 1.0]$ 区间。
  - **展示界面与卡片**：检索大盘「实时召回测试」及「Token / 延迟监控卡片」。
- **核心交付目标**：
  1. 吸收本地向量索引与 cuvs 引擎余弦相似度归一化算子；
  2. 吸收请求级 Query Embedding 内存 Cache 机制，单次请求内相同文本只嵌入一次；
  3. 保持与我们现存的 Tier-2 LRU 亚毫秒二级缓存无缝化合。
- **验收条件**：单测 100% 通过、检索基准测试 P@5 保持 100%、无精度回退。

---

#### 📌 [P1] [ ] Card-23: Card-Upstream-FS-Pagination-And-Unicode-URI (v1.5.80): 上游文件系统标准吸收 — ls/tree 游标分页排序与统一中文/Unicode 存储 URI ⏳
- **类型**：VikingFS / 协议与路径规范 ｜ **优先级**：🔥 P1 ｜ **目标版本**：`v1.5.80` ｜ **当前状态**：[ ] 就绪待调度 ⏳
- **背景与第一性原理**：
  - 上游在 `94ff079f5` 与 `d8f675445` 中全面落地了海量节点场景下的游标分页能力与多语言 Unicode 路径规范化，杜绝万级节点下一次性拉取导致 OOM 或截断。
- **开工前客观数据指标锚定 (Frontend Metric Anchor SSOT)**：
  - **衡量指标**：
    1. **万级目录遍历峰值内存**：从原本单次全量内存峰值 `~85MB` 降至分批稳定 `< 8MB`；
    2. **中文/复杂符号路径兼容率**：包含特殊中文、空格与复合符号路径读取准确率提升至 **$100\%$**。
  - **展示界面与卡片**：资源大盘文件浏览器（支持顺畅无限滚动与排序）及 REST API 文档。
- **核心交付目标**：
  1. 吸收 VikingFS `ls` 与 `tree` 的游标分页参数（`cursor`, `page_size`, `sort_by`, `sort_order`）；
  2. 吸收统一 URI 规范化引擎，消除 URL-encoded 与原生中文字符路径的割裂；
  3. 适配前端资源树组件的渐进加载。
- **验收条件**：单测 100% 通过、万级目录遍历测试通过、前端构建无报错。

---

#### 📌 [P1] [ ] Card-24: Card-Upstream-MCP-Tool-Annotations-And-Grep-Context (v1.5.81): 上游智能体协议吸收 — MCP 行为元数据广播与代码/会话 Grep 上下文行 ⏳
- **类型**：MCP 协议 / 开发者工具 ｜ **优先级**：🔥 P1 ｜ **目标版本**：`v1.5.81` ｜ **当前状态**：[ ] 就绪待调度 ⏳
- **背景与第一性原理**：
  - 上游在 `a86caca70` 与 `a9ba33d0f` 中新增了 MCP 工具行为广播（如只读、长耗时、高危险提示），以及会话/代码全文检索的 `-A / -B / -C` 上下文行输出，极大增强外部 Agent（Claude Desktop, Cursor, Antigravity）的决策精度。
- **开工前客观数据指标锚定 (Frontend Metric Anchor SSOT)**：
  - **衡量指标**：
    1. **MCP 工具调用误操作率**：高风险操作在 Agent 侧提示阻断率提升至 **$100\%$**；
    2. **代码检索信息信噪比**：返回结果自带紧邻上下文，减少 Agent 二次 `view_file` 次数 **$40\%$** 以上。
  - **展示界面与卡片**：控制台 MCP 工具列表详情页、会话日志详情抽屉。
- **核心交付目标**：
  1. 在 FastMCP 导出工具中注入行为元数据注解（Tool Annotations）；
  2. 扩展会话与文件 Grep 引擎，支持 `context_lines`, `before_context`, `after_context`；
  3. 同步优化本地与卫星双模态 MCP 接口。
- **验收条件**：MCP Inspector 校验通过、Grep 单测全绿、安全扫描 0 泄露。

---

#### 📌 [P1] [ ] Card-25: Card-Upstream-Feishu-VikingBot-And-OpenSandbox (v1.5.82): 上游生态连接吸收 — 飞书/Lark 多地域域名配置与 Docker OpenSandbox 沙箱生命周期 ⏳
- **类型**：外部机器人与运行时沙箱 ｜ **优先级**：🔥 P2 ｜ **目标版本**：`v1.5.82` ｜ **当前状态**：[ ] 就绪待调度 ⏳
- **背景与第一性原理**：
  - 上游在 `46129f143` 与 `5fef1fbb5` 中增强了企业级 Feishu/Lark 混合部署能力，并打通了由 OpenViking 统一托管的 Docker-backed OpenSandbox 容器生命周期，提供真正的隔离执行环境。
- **开工前客观数据指标锚定 (Frontend Metric Anchor SSOT)**：
  - **衡量指标**：
    1. **飞书跨地域推送成功率**：国内飞书与海外 Lark 自动路由成功率 **$100\%$**；
    2. **沙箱容器复用与回收时延**：容器预热就绪时间 `< 1.2s`，僵尸容器泄漏率严格为 **$0$**。
  - **展示界面与卡片**：Web Studio「🤖 VikingBot 机器人管理」及「沙箱运行时」卡片。
- **核心交付目标**：
  1. 吸收飞书/Lark API 动态 BaseURL 与授权刷新机制；
  2. 吸收 OpenSandbox 容器生命周期守护进程；
  3. 保持前端座舱级性冷淡高密设计。
- **验收条件**：飞书双向连通测试通过、Docker 沙箱启动/销毁测试通过。

---

### 📋 下一阶段就绪任务卡片模板 (Next Milestone Cards Template)

当接收到新的重大需求或重构指令时，严格遵循以下四步规范与标准模板立卡：
1. **第一阶·梳理方案** ➔ 2. **第二阶·CPA/业界模型补齐** ➔ 3. **第三阶·哲学审讯 (第一性原理/奥卡姆/信达雅/单文件≤500行)** ➔ 4. **第四阶·红蓝对抗与客观指标锚定**。

