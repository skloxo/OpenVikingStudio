# 🗺️ OpenViking 项目主线重构与原子化任务卡片总看板 (Master Task Cards Kanban - SSOT)

> **关联研发大蓝图**：[`BLUEPRINT.md`](file:///home/skloxo/aho/openclaw/project/.agents/BLUEPRINT.md) ｜ **交付全量归档台账**：[`DELIVERY_ARCHIVE.md`](file:///home/skloxo/aho/openclaw/project/DELIVERY_ARCHIVE.md) ｜ **通用资产档案库**：[`COMPONENT_AND_WHEEL_INVENTORY.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/docs/architecture/COMPONENT_AND_WHEEL_INVENTORY.md)
> **唯一真相源 (SSOT)**：本文档为 OpenViking 当前活跃的重构规划与就绪待调度的任务矩阵看板。历史所有已验收交付的版本履历已完整归档至 `DELIVERY_ARCHIVE.md`，严禁多头维护。

---

## 📌 一、 研发基线与近期已交付版本速查表 (Recent Delivered Releases: v1.4.96 ~ v1.4.110)

> **生产物理事实声明**：
> - **线上正式部署版本**：**`v1.4.106`**（物理访问地址：`vk.tide.red/studio/home`，已实机验证）；
> - **本地代码库封板版本**：**`v1.5.0`**（🎉 正式 Major/Minor 里程碑封板发布，package.json 与 Git Tag 对齐）；
> - **正式发布公告 (Release Notes)**：查阅 [`docs/releases/RELEASE_v1.5.0.md`](docs/releases/RELEASE_v1.5.0.md) 获取从 v1.4.0 到 v1.5.0 全景演进亮点；
> - **全量历史归档**：v1.4.4 ~ v1.4.95 及 Milestone 1 全量 70+ 个已交付卡片与 Git Commits 请查阅 [`DELIVERY_ARCHIVE.md`](file:///home/skloxo/aho/openclaw/project/DELIVERY_ARCHIVE.md)。

| 版本 Tag | 任务工单 ID | 模块与重构主题 | 核心治理成果与物理交付物 | 验收状态 |
|:---|:---|:---|:---|:---:|
| **`v1.4.110`** | **Card-2080Ti-XiaomiMo-Parity-And-Restart** | **2080Ti 本地 Windows 宿主机 XiaomiMiMo 插件同频对齐、ELECTRON_RUN_AS_NODE 环境变量隔离与 4096 引擎重启闭环** | 1. **物理根因定位**: 3070 升级 messages.transform 插件后，2080Ti Windows 宿主机未同步，运行旧版 7KB 插件缺乏 messages.transform 钩子；<br>2. **环境隔离自愈**: 彻底查清在 WSL2/PowerShell 下直接重启 `Xiaomi MiMo.exe` 继承 `ELECTRON_RUN_AS_NODE=1` 导致应用以 headless Node 模式立即退出的隐蔽缺陷，通过 `Remove-Item env:ELECTRON_RUN_AS_NODE` 恢复桌面 GUI 交互与 4096 引擎拉起；<br>3. **实机模拟双题全绿**: Agnes 2.5 Flash (得分88.5, 千问14B/32B, 100%免费) 与 Mac Studio (FRP 13100, FRP 隧道) 检索注入 100% 命中；<br>4. **4096 引擎正常监听**: `plugin.log` 记录 `server init called`，MiMo 正常运行于 Session 1。<br>**Commit Hash**：（本次提交）\ | **修改文件**：`package.json`, `openviking/_version.py`, `REFACTORING_PLAN.md` |
| **`v1.4.109`** | **Card-Fleet-MiMo-Universal-Plugin** | **全集群 XiaomiMiMo 消息流直接注入插件 (messages.transform) 升级、本地落盘日志与 3070 引擎重启闭环** | 1. 查明 `experimental.chat.system.transform` 不生效原因：MiMo 桌面端后端模型服务忽略了 system 数组注入；<br>2. 升级落地 `experimental.chat.messages.transform` 直接将核心记忆前置拼接入 `lastUserMsg.parts`，彻底保证后端大模型 100% 收到 OpenViking 核心记忆；<br>3. 实现独立排障日志 `plugin.log` 自动追加至本地磁盘；<br>4. 3070 远端实机 4/4 题目 100% 正确回答（涵盖 Groq 27B、Mac Studio Qwen 3.8 Flash、Agnes 2.5 Flash、Mac Studio FRP 13100 端口与 IP）；<br>**Commit Hash**：`30a404373` \ | **修改文件**：`mcp-openviking/mimo_openviking_plugin.mjs`, `REFACTORING_PLAN.md` |
| **`v1.4.107`** | **Card-XiaomiMo-DualNode-Unified-Standard** | **全集群 XiaomiMiMo 客户端零子进程纯原生 ESM 插件大一统、跨节点 (2080Ti/3070) 目录与配置标准归一 (SSOT)** | 1. **全集群工业级统一标准 (SSOT)**: 坚决摒弃“这台机器一种配置、那台机器另一种配置”的碎片化负债；全集群 XiaomiMiMo 统一落盘于 `C:\Users\Skl\.openviking\mimo-openviking-plugin.mjs` 与 `C:\Users\Skl\.config\mimocode\mimocode.jsonc`；<br>2. **零子进程原生 Fetch 重构**: 升级 `mimo_openviking_plugin.mjs`，去除对外部 Python/Venv/WSL 子进程的依赖，使用 Node.js 18+ 内置原生 `fetch` 与毫秒级 AbortController，耗时降至 < 10ms，零进程派生开销；<br>3. **容错式正则配置解析**: 采用零依赖正向正则从 `mimocode.jsonc` 动态抽取 `OPENVIKING_API`/`OPENVIKING_API_KEY`/`OPENVIKING_ACTOR_PEER`，天然免疫 Windows 反斜杠、注释与 JSONC 语法格式容错；<br>4. **双端实机全链路测试通过**: 2080Ti 本地实测通过 (`2080TI PREFETCH SUCCESS: YES`)，3070 远程同步通过，双机统一在 `mimocode.jsonc` 中注册 `"plugin"`；<br>5. **一键入网工具集升级**: 在 `mcp-openviking/install_satellite.ps1` 中原生集成 Xiaomi MiMo 配置代码块输出；单文件 219 行处于黄金甜点区；<br>**Commit Hash**：`bb6c4fd5d` \ | **修改文件**：`package.json`, `openviking/_version.py`, `mcp-openviking/mimo_openviking_plugin.mjs`, `mcp-openviking/install_satellite.ps1`, `REFACTORING_PLAN.md` |
| **`v1.4.106`** | **Card-3070-XiaomiMo-Pydantic-Bun-Fix** | **3070 节点 XiaomiMiMo 客户端 FastMCP/Pydantic 崩溃根治、僵尸进程肃清与 ESM 官方插件化注入闭环** | 1. **问题 A (MCP 崩溃根治)**: 查清 Pydantic 2.9+ 环境下 FastMCP `_create_wrapped_model` 使用 `result=annotation` 报 `PydanticUserError` 崩溃根因，在 `_core/decorators.py` 与 `satellite_mcp_server.py` 注入防御性猴子补丁 (`result=(annotation, ...)`), 严格恪守单文件 $\le 500$ 行铁律 (当前 497 行)，单测 11/11 全绿，远端实机 16/16 工具注册 100% 成功；<br>2. **问题 B (统一路径与僵尸进程肃清)**: 物理终止 3070 远端残留的 6 个月前历史僵尸进程 (PID 65688 / 7276)，统一并锁死 SSOT 路径 `C:\Users\Skl\.openviking\satellite_mcp_server.py`；<br>3. **问题 C (Hook 注入物理根因与官方插件化重构)**: 逆向反编译 MiMo Desktop 核心包 `app.asar`，查明其对 `{hook,hooks}/*.{js,ts}` 强制执行 `await Bun.build(...)`，而桌面端基于 Node.js/Electron 运行导致抛出 `Bun.build is not a function` 这一根本物理缺陷；查明官方插件化机制 `PluginLoader.loadExternal` 与系统提示词钩子 `experimental.chat.system.transform` (`output.system.push(mem)`)；<br>4. **官方 ESM 插件投产与配置闭环**: 研发并发布 `mcp-openviking/mimo_openviking_plugin.mjs`，远端部署为 `C:\Users\Skl\.openviking\mimo-openviking-plugin.mjs`，在 `mimocode.jsonc` 注册 `"plugin"`，使用 Electron Node 原生环境测试 100% 成功加载并注册 3 大钩子 (`session.userQuery.pre`, `experimental.chat.system.transform`, `session.post`)；<br>5. 禁用所有导致 `Bun.build` 报错的旧 `openviking-lifecycle.ts` 副本，Vite 前端构建 100% PASS (18.79s)。<br>**Commit Hash**：`3999df49b` \ | **修改文件**：`package.json`, `openviking/_version.py`, `mcp-openviking/_core/decorators.py`, `mcp-openviking/satellite_mcp_server.py`, `mcp-openviking/mimo_openviking_plugin.mjs`, `REFACTORING_PLAN.md` |
| **`v1.4.105`** | **Card-Peer-Grid-Purge-Mac-Compute** | **厘清算力与智能体边界：彻底肃清 Mac Studio 离线算力幻觉实体 (mlx-agent)，精准收口 7 大真实在籍 Agent** | 1. 厘清物理基础设施真相：Mac Studio (M3 Ultra) 严格定位为底层大模型离线推理算力节点 (MLX-LM)，并非执行工程工作流的独立智能体；<br>2. 彻底剔除 `console.py` 中历史残留与幻觉混淆的 `mlx-agent@mac`；<br>3. 首页 Agent Peer 看板精准收口为 2080Ti (4) + 3070 (3) 共 7 名真实在籍干活智能体；<br>4. 前端构建与端到端实机验证 100% 纯净无幻觉；<br>**Commit Hash**：`37cd25ab1` \ | **修改文件**：`package.json`, `openviking/_version.py`, `openviking/server/routers/console.py`, `REFACTORING_PLAN.md` |
| **`v1.4.104`** | **Card-Home-Peer-Grid-Authenticity** | **首页 Agent Peer 记忆中枢看护看板真实化重构与 client@node 身份矩阵贯通** | 1. 彻底切除 `console.py` 扫描历史 7 月份假数据文件夹与盲目硬编码逻辑；<br>2. 建立全集群真实在籍节点矩阵（2080Ti 本地 4 Agent、3070 远程 3 Agent、Mac Studio 离线算力）与实时消息数累加机制；<br>3. 动态感知卫星 Agent（通过请求头 `X-OpenViking-Actor-Peer` 调用的新 Agent 自动列入看板）；<br>4. 前端 `peer-memory-grid.tsx` 优雅渲染 `[2080TI]`, `[3070]`, `[MAC]` 节点徽章与清晰角色说明；<br>5. 物理删除卡滞的 UI 走查测试任务 (`biz_res_running_embed` 与 `biz_valet_running_probe`)；<br>**Commit Hash**：`a8710b0da` \ | **修改文件**：`package.json`, `openviking/_version.py`, `openviking/server/routers/console.py`, `src/routes/home/-components/peer-memory-grid.tsx` |
| **`v1.4.103`** | **Card-Satellite-Universal-Onboarding** | **卫星智能体「提示词 + Key」一键自举入网体系、跨端极简分发与全集群身份契约固化 (Onboarding SSOT)** | 1. 升级 `install_satellite.sh` 与 `install_satellite.ps1`，原生支持 `--peer`/`-p`、`--key`/`-k` 与 `--api`/`-a` 参数，生成自包含启动包装脚本；<br>2. 安装过程原生集成 `/health` 握手自检，回显 `✅ 握手成功！智能体唯一身份证已接入中枢: client@node`；<br>3. 发布全能入网指南 [`mcp-openviking/ONBOARDING.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/mcp-openviking/ONBOARDING.md)，沉淀一键复制即用的「入职自举提示词」与 8 行标准 JSON 配置代码块；<br>4. 优化 `tools/fleet.py` FRP 穿透命令执行超时上限 (10s ➔ 20s)，提升弱网与高并发下远程运维鲁棒性；<br>**Commit Hash**：`4e995fe00` \ | **修改文件**：`package.json`, `mcp-openviking/install_satellite.sh`, `mcp-openviking/install_satellite.ps1`, `mcp-openviking/tools/fleet.py`, `mcp-openviking/ONBOARDING.md` |
| **`v1.4.102`** | **Card-XiaomiMo-DualNode-Attribution** | **2080Ti 本地 Windows 与 3070 远端 XiaomiMo (小米客户端) 统一身份穿透与双端舰队自动纳管** | 1. 查清 2080Ti 本地 Windows (`/mnt/c/Users/Skl/.config/mimocode/`) 与 3070 远端均部署了 XiaomiMo 客户端的物理事实；<br>2. 自动升级两端配置，写入真实且合规的身份签名 `xiaomimo@2080ti` 与 `xiaomimo@3070`；<br>3. `_core/config.py` 与 `satellite_mcp_server.py` 同步支持 `xiaomimo` / `mimocode` 自动嗅探归一；<br>4. 前端 `task-record.ts` 优雅映射并高密展示为 `[2080TI] XiaomiMo` 与 `[3070] XiaomiMo`；<br>5. 舰队工具 `tools/fleet.py` 巡检与同步方法全面纳管两端 XiaomiMo 客户端配置状态，自动化验证 100% 通过。 | 双节点 XiaomiMo 客户端身份精准归因，舰队工具 100% 自动纳管，单测试全绿 |
| **`v1.4.101`** | **Card-3070-Dual-Agent-Isolation** | **3070 节点反重力 IDE 与 WorkBuddy 身份物理隔离治理与双向环境自动嗅探机制** | 1. 查清 3070 节点共存 Antigravity IDE 与 WorkBuddy 调用同一个 MCP 的物理事实；<br>2. 升级 `satellite_mcp_server.py` 与 `_core/config.py`，引入进程执行特征 + 环境变量指纹双重自动嗅探 (`full_ctx`)，即使共用同一脚本也能精准识别；<br>3. 3070 远端 `C:\Users\Skl\.gemini\config\mcp_config.json` 自动配置 `antigravity@3070`；<br>4. `tools/fleet.py` 一键全自动化推流覆盖 3070 双路径 (`.openviking/` 与 `.workbuddy/openviking-mcp/`)；<br>5. 远端实机探针 100% 验证双 Agent 身份绝对隔离 (`peers_isolated: True`)，Vitest 36/36、Pytest 11/11 全绿。 | 3070 双 Agent 身份隔离 100% 验证通过，单文件均 $\le 500$ 行 |
| **`v1.4.100`** | **Card-Fleet-Ops-Identity-Rollout** | **全集群智能体统一身份穿透 (client@node) 落地、双模 MCP/Hook 自动装配与舰队自动同频闭环 (Fleet Ops)** | 1. 制定并落地全网统一 Agent 身份规范 `{client}@{node}` / `{client}.{role}@{node}`，严格符合官方正则；<br>2. 核心 MCP (`_core/config.py`) 与卫星 MCP (`satellite_mcp_server.py`) 自动解析节点平台与客户端环境，请求头自动注入 `X-OpenViking-Actor-Peer` 与 `X-Caller`；<br>3. 后端写路由 (`content.py`) 优先透传真实 actor peer，彻底切除 `default` 租户名误判；<br>4. 工作区与全局 Hook (`ov_pre_invocation.py`, `ov_session_archiver.p| **Card-Runtime-TwoTierAgentLoop-OnionGuard** | **pi 生产级双层事件循环、四层洋葱防御与中途插话/主动刹车契约** | 1. 吸收生产级 pi/agent-loop.ts 743 行源码精读与洋葱模型：终结单层 while 循环无法中途插话、死循环无法优雅中止与异常崩溃顽疾；<br>2. 双层事件循环架构：外层管控会话与模型切换，内层循环推进 hasMoreToolCalls || pendingMessages.length > 0；<br>3. 四层洋葱保护：核心循环、模型防御、用户控制（异步插话队列 + 优雅 Abort）、调度增强；<br>4. 工具主动刹车契约：返回 terminate: true 立即终止工具迭代提前交付。 | 双层循环与四层洋葱，中途插话零丢消息，工具主动刹车，异常优雅降级 | `P0` | `v1.5.01` | [x] 已验收通过 ✅ |
| **`v1.5.02`** | **Card-Memory-ColdQuarantine-ZombiePurge** | **存量僵尸记忆冷归档与 1936 毒性软隔离专项 (Zombie Memory Quarantine & 1936 Detox)** | 1. 物理排查与冷备隔离：研发 `scripts/quarantine_zombie_memories.py`（241 行黄金甜点区，支持 `--dry-run` 与 `--restore`），将 1,159 个 2026 年 7 月份废弃 session 草稿（3,833 文件，4.2 MB）安全备份至 `~/.openviking/data/archive/zombie_sessions/20260915_091547/` 并落盘 `quarantine_manifest.json`；<br>2. 官方标准 API 闭环清理：通过 `DELETE /api/v1/fs` 并发安全清理 1,159 个资源，同步清除 VectorDB 中对应的 L0/L1/L2 嵌入与语义标记（成功率 1159/1159，0 失败）；<br>3. 物理验真双全通过：`openviking_find("1936")` 检索结果归零（前缀草稿完全清除，仅留官方 1936 下线交付规范），`openviking_find("antigravity_master")` 完全回归真实工具/应用实体记忆，Hook 预取污染彻底肃清；<br>4. 门禁验证：单测 54/54 全绿，安全扫描 4,206 文件零泄密，Vite 构建 PASS。<br>**Commit Hash**：`36848c2e4` | **修改文件**：`package.json`, `openviking/_version.py`, `scripts/quarantine_zombie_memories.py`, `REFACTORING_PLAN.md` | [x] 已验收通过 ✅ |
| **Card-Harness-DeepSeek-AgentScope-SpecDriven** | **DeepSeek-Harness 极简规范外壳、AgentScope Java 2.0 生产级运行时与企业级四不变式** | 1. 吸收 DeepSeek 官方开源 deepseek-harness、2026 上半年自进化综述与阿里 AgentScope Java 2.0 GA：确立 Harness 四大不可变式（可终止、可隔离、可恢复、可观测）；<br>2. Workspace 抽象文件系统 (Abstract File System)：静态资产（AGENTS.md/Skills）与运行时数据（Session/MEMORY.md）解耦；<br>3. 物理免压缩白名单：长任务规划详情、异步子 Agent 追踪状态、权限授权记录物理免受上下文压缩破坏；<br>4. 工具失败分类捕获与防死循环重试，多租户 Runtime Context 显式传递。 | 彻底终结长会话规划与状态丢失，沙盒隔离与成本硬限制 100% 生效，多租户解耦 | `P0` | `v1.5.03` | ⏳ 待排期 |
| **Card-Harness-ReadWriteOffload-HookGuard** | **腾讯 DECO 级读写两侧 Offload 护栏与 Hook 切面长文本防偷懒/防越权体系** | 1. 吸收腾讯《DECO 数仓 Agent 引擎护栏实践》：彻底根治模型在长脚本（1200+行）生成时的“省略偷懒 (/* 省略若干行 */)”与“未经确认越权推生产”绝症；<br>2. Hook 切面与推理循环解耦：围绕模型与工具调用建立独立前后回调拦截；<br>3. 读写两侧 Offload：LLM 绝不直接接触全文！读拦截写入只读沙箱并下发 file_ref 句柄，写拦截强制走 copy_file + str_replace 小步增量补丁；<br>4. 危险操作 HITL 门禁：状态机检查当前阶段，未确认前物理阻断发布工具。 | 彻底封杀长文本省略偷懒，大文件上下文开销降 90%，越权操作 100% 物理拦截 | `P0` | `v1.5.04` | ⏳ 待排期 |
| **Card-Verify-MultiMetricGate** | **交付物多维物理验真门禁（内容哈希 + 增量覆盖率 + 单测真跑，防 Exit 0 假完成）** | 1. 吸收字节《Aspire》虚假闭环教训与 Goodhart 定炼防范，重构 Task Completion 判定；<br>2. 代码开发类任务强制双重物理验真：Diff 变更行数 > 0 且关键集成测试真实通过；<br>3. 阻断 Agent 通过 mock、swallow 异常或加空注释伪造 Exit 0 宣布交付；<br>4. 作为 Wave 1 运行时与 Wave 4 自演进的不可逾越物理防线。 | 任务中心物理验真断言生效，虚假 Exit 0 100% 拦截，任务流转真实可信 | `P0` | `v1.5.05` | ⏳ 待排期 |
| **Card-Harness-SpecDrivenFSM** | **第三代数仓级多智能体 Harness 架构（Spec 结构化文件驱动 + 协调者专家分离 + 12 状态有限状态机）** | 1. 吸收阿里千问数仓 Harness 实践与 Qwen《Skill-SP》：确立 Agent = Model + Harness，下限由工程托底；<br>2. Orchestrator 与 Specialist 物理分工：协调者只调度、把关、评审，严禁下场写业务代码；专家在独立沙箱专精窄接口；<br>3. Spec 结构化文件驱动通信：跨阶段全面废除长会话历史总线，统一传递结构化文件路径，阶段终点强制生成固定格式 CP 检查点摘要；<br>4. 生成者与评估者严格分离（Generator != Evaluator）；<br>5. 12 状态有限状态机与故障三分法，支持秒级断点续接。 | 上下文污染清零，阶段成果物可追溯可审计，故障断点续接率 100%，消除独角戏越轨 | `P1` | `v1.5.06` | ⏳ 待排期 |
| **Card-Retrieval-BM25Hybrid** | **SQLite FTS5 词法与稠密向量双路混合检索与 RRF 融合 (BM25 Hybrid Retrieval)** | 1. 吸收《BM25 Wins at Scale》(arXiv:2607.26497) 与生产混检共识，破除纯 Dense 向量在精确符号上的检索盲区；<br>2. 本地零外部依赖：基于 SQLite 原生 FTS5 虚拟表建立文本/经验倒排索引；<br>3. 双路召回并行流：Dense Vector (qwen3-vl-emb) + Sparse BM25 (FTS5) 毫秒级并行捞取候选集；<br>4. 无参 RRF 融合：采用标准倒数排名融合 (k=60) 归一化排序，输入单次 Cross-Encoder Reranker 精排；<br>5. 补齐代码符号、错误堆栈、端口与文件名精准命中专项单测。 | 精确代码符号与错误排查召回率大幅提升，保持单次 RER 契约不变，延迟开销几乎为 0 | `P0` | `v1.5.07` | ⏳ 待排期 |
| **Card-Retrieval-LocalFirst-zgSemanticSearch** | **阿里 zg 级端侧本地命令行语义搜索、四重奏融合与代码符号防盲搜护栏（深度整合 TieredLazyFetch 分级契约）** | 1. 吸收阿里 Qwen+Zvec《zg (zvec-grep)》、Karpathy 知识空间与 CPA 导师分级懒加载黄金律：彻底解决 Agent 在终端疯狂跑 rg 盲猜代码导致上百文件撑爆上下文；<br>2. 深度整合 TieredLazyFetch：引入 depth 契约，depth=0（元数据行号）、depth=1（紧凑指纹前后1行，默认推荐）、depth=2（完整块）；<br>3. 端侧四重奏检索引擎：32MB 超轻静态模型向量感知 + BM25 词频 + RRF 无参融合 + ripgrep 精确匹配；<br>4. AST 符号级切片（函数/类），Local-First 纯端侧 0 显存依赖，万行仓库 30s 极速建库；<br>5. 工具调用减少 50%，Token 减半。 | 彻底终结代码符号盲搜，纯本地 32MB 模型 0 显存，分级懒加载契约落地，Token 减 50% | `P0` | `v1.5.08` | ⏳ 待排期 |
| **Card-RAG-Abstention-ZeroHallucination-Pipeline** | **千万级语料 RAG 约束验证与弃答门禁流水线、RARG 语义引导相关性搜索与 MinHash 去重** | 1. 吸收千万级工业 RAG 深度记事、腾讯/中科院信工所开源 RARG、七牛开发者与 6 曦轩：彻底攻克海量文档下模型默认“盲猜”导致的严重幻觉；<br>2. 前置 MinHash LSH 近重复去重与 NFKC 分词标准化，阻断冗余拷贝霸榜；<br>3. RARG 语义引导搜索：embed_recall 排序候选路径，单线程 rg -j1 顺序扫描，结合起点 10 段线索与局部重排；<br>4. 独立 Verifier 判官与主动弃答门禁 (Abstention Gate)：证据不足或置信度低于阈值强制拒答，幻觉率压制到接近 0。 | 10M+ 文档毫秒级检索，局部重排工具调用降低 70%，主动弃答将幻觉率压制至接近 0 | `P1` | `v1.5.09` | ⏳ 待排期 |
| **Card-Knowledge-HG-RAG-HierarchicalCompass** | **HG-RAG 分层指南针拓扑检索、Karpathy LLM Wiki 与 WeKnora 读写分离知识工程** | 1. 吸收 PaperAGI《HG-RAG》、Karpathy LLM Wiki、翻斗花园二蛋 Graph Engineering 与 WeKnora 企业实践：解决多跳实体推导断层与合并单元格大类丢失；<br>2. HG-RAG 分层指南针拓扑：构建可漫游父子关联索引，结构化主数据表叶子 chunk 自洽回填全路径大类；<br>3. 编辑台与服务台物理分离（Read/Write Decoupling）：重型解析与图计算隔离在编辑台，生产服务台保持只读极速响应；<br>4. 零分叉 Overlay 覆盖层升级：同名替换 > 新增组件 > 变量覆盖 > 幂等锚点补丁。 | 跨层级多跳检索准确率提升 25%，结构化表路径零丢失，读写分离彻底消除生产磁盘撑爆 | `P1` | `v1.5.10` | ⏳ 待排期 |
| **Card-Extraction-ZeroThinking-BisectionHeal** | **记忆提取零思考硬开关、Token 截断二分切片自愈与条数/字数双门禁体系** | 1. 吸收《无银三百两》提取检修实战：根治提取长对话时 171 次调用 97 次空返回、耗时 2.5 小时的死锁绝症；<br>2. 记忆提取强制关闭 Thinking 思考（enable_thinking=False），切除思考对正文 max_tokens 预算的挤占，提速 10~20 倍，Token 消耗降 70%+；<br>3. 严格区分偶发与截断：截断物理阻断原样重试，自动触发区间二分切片并发抽取；<br>4. 消息总字数 >4000 或条数 >25 双门禁预切片；<br>5. 入库防爆安全切分。 | 提取场景零思考提速 20 倍，截断二分自愈清零空返回，字数条数双门禁防死锁 | `P0` | `v1.5.11` | ⏳ 待排期 |
| **Card-Memory-LifecycleFSM** | **记忆版本状态机 (active/disputed/superseded) 与冲突挂链降权机制** | 1. 吸收《LLM Wiki 长文》与腾讯自进化飞轮真核：“我们已经会编译经验，但还不会给记忆写状态机”；<br>2. 记忆 Schema 引入一等公民状态：status: active | disputed | superseded 与 superseded_by 演进指针；<br>3. 写入侧冲突检测：新经验推翻旧经验时自动挂链标记 superseded，禁止静默并存误导；<br>4. 检索侧物理降权 (Demotion)：superseded / disputed 状态条目默认大幅降权或过滤，优先返回最新有效经验；<br>5. Studio 大盘与记忆抽屉直观展示被取代条目划线状态与演进血缘链。 | 彻底根除“旧错误经验比新经验得分更高导致 Agent 被误导”的致命缺陷，单测全绿 | `P1` | `v1.5.12` | ⏳ 待排期 |
| **Card-Memory-EntropyCrystallizer-TriGate** | **存量历史碎片三门并联结晶归纳器与不可变事实 SSOT 熔炼 (Entropy Crystallizer & SSOT Distillation)** | 1. 吸收 2026-09-08 架构共识（Card-Entropy-02）：解决存量碎片越积越多引发的向量库熵增与检索混淆；<br>2. 三门并联硬门禁：聚类条数 >= 5 条、语义余弦相似度均值 > 0.75、沉淀时间 >= 24h 冷却期；<br>3. 熔铸输出标准三层晶体结构：L0 核心公理（无歧义强事实）、L1 版本与证据链（明确生效版本范围与 commit hash）、L2 负向排斥哨兵（显式封杀已废弃模式）；<br>4. 原碎片挂载 superseded 演进指针并移出活跃库进入冷归档，达成活跃向量节点物理净减少。 | 散落碎片熔铸为不可变事实库，活跃向量节点物理净减，三门并联杜绝假结晶 | `P1` | `v1.5.13` | ⏳ 待排期 |
| **Card-Context-ActiveNotesAndHistory** | **Codex 级主动上下文治理（Notes 高密活跃状态 + History 独立检索分仓，切除有损 Compaction）** | 1. 吸收 DeepEvolution 对 Codex 最新架构解密 (PR #39827)：废除有损全局 Compaction 摘要（多次压缩导致路径、错误码、中间未完成状态严重失真）；<br>2. 状态与历史双轨分仓：Notes 存高密度结构化核心事实常驻上下文，History 存原始对话流移出上下文独立分仓；<br>3. 主动调阅工具：模型按需调用 list_history_windows / search_history 检索历史；<br>4. 阻断长会话上下文失忆与信息衰减。 | 切除有损压缩，关键路径/报错信息零失真，长程多轮会话状态持久保真 | `P1` | `v1.5.14` | ⏳ 待排期 |
| **Card-Skill-ZipOnWrite-ContractualCompression** | **阿里 SkillZip 写入即压缩引擎、六元组强类型契约与 0-Rollout 确定性重构防膨胀** | 1. 吸收阿里/浙大/杜克《SkillZip》：终结自进化技能膨胀 5.2 倍的“复读机死因”（重复代码与琐碎特例堆叠）；<br>2. 六元组强类型契约化解析（接口、工作流、协议、规则、契约、证据）；<br>3. Explain Once, Reference Everywhere：公共动作抽取为共享过程函数，公共规则提升至最小公共作用域；<br>4. 0-Rollout 确定性优化（动态规划规则放置 + 加权装箱）；<br>5. Zip-on-Write 门禁：写入即压缩，长度全程锁定种子 1.6~1.9 倍，压缩率超 30% 且基准表现持平反超。 | 技能契约化解析，0-Rollout 确定性重构，写入即压缩防膨胀复利，压缩率 30%+ | `P1` | `v1.5.15` | ⏳ 待排期 |
| **Card-Memory-ValetIngestion-AntiEntropyGate** | **前门自动泊车异步分流与反熵增去噪去重准入门禁 (Valet Ingestion Engine & Anti-Entropy Gate)** | 1. 彻底根治写入阻塞：前门践行自动泊车异步分流模型，秒级交钥匙返回 202 Accepted，调用方零写延迟；<br>2. 后台 Worker 异步执行 MinHash LSH 近重复检测与语义去噪，阻断同义碎片反复堆叠；<br>3. 存储底座封顶消灭侧门：统一拦截 WebDAV、REST 与 MCP 写入路径，建立统一准入流；<br>4. 配合非对称时效动力学：长期未命中条目自动降权，防范近亲繁殖与规则通胀。 | 写入 10ms 极速交钥匙，后台异步深减熵，消灭存储侧门，全链路反熵增闭环 | `P1` | `v1.5.16` | ⏳ 待排期 |
| **Card-Hygiene-AsymmetricDecayAndBench** | **知识卫生异步巡检 (Knowledge Hygiene)、非对称衰减与真实查询回归金标集** | 1. 吸收非对称淘汰律：“错误记忆的伤害远大于正确记忆的收益”；<br>2. 挂载轻量后台巡检 Worker：识别死重条目（零召回）、冲突簇与孤立引用，坚守奥卡姆剃刀：只输出报告与建议，绝不自动化盲目删数据；<br>3. 时效动力学与非对称衰减：对长期未命中或被标记存疑的条目降低基础检索权重；<br>4. 真实查询金标回归集 (Gold Benchmark)：从真实 find 提取 50~100 条覆盖符号、报错、规则的测试集，固定上下文 Token 预算，作为检索算法/模型升级的不可逾越门禁。 | 知识库死重与冲突可视可控，模型/检索演进具备固定物理标尺，告别盲飞调参 | `P1` | `v1.5.17` | ⏳ 待排期 |
| **Card-Evolve-HermesEvolveLoop-Patch** | **Hermes 级经历与能力解耦存储、Periodic Nudges 异步副进程复盘与 Patch 级技能微补丁自进化机制** | 1. 吸收 DeepEvolution《Hermes Agent Evolve Loop》与全景导论：实现经历（SessionDB）与能力（Skill/Memory）严格物理分层；<br>2. 跨会话 FTS5 真实消息检索（拒绝虚假 LLM 摘要）；<br>3. Periodic Nudges 异步副进程复盘：主任务完成后异步派发轻量工兵模型复盘轨迹并提取经验，零阻塞用户交互；<br>4. Patch 优先技能微手术：skill_manage 强制局部增量替换（≤30行），保留 90% 经过验证的边界逻辑，防范 Edit 模式全量重写的严重幻觉覆盖。 | 经历与能力物理分层，真实轨迹 FTS5 检索，异步副进程复盘，Patch 局部微手术防遗忘 | `P1` | `v1.5.18` | ⏳ 待排期 |
| **Card-Skill-EvaluationRetina** | **Skill 质量视网膜与自动化评测门禁体系 (Skill-as-Code & Testing CI / skill-up 规范落地)** | 1. 吸收阿里开源 skill-up 与 AI 软件测试方法论，彻底终结“改动一行提示词行为漂移、跑一遍 Demo 没报错就裸奔上线”；<br>2. 规范化测试工程结构：建立 evals/cases/（声明式 YAML 用例）、evals/fixtures/（数据脚手架）、evals/eval.yaml（引擎与断言配置）；<br>3. 落地三级判定器引擎（Exact/Regex 匹配断言、Command 脚本退出码、agent_judge LLM 语义判官）；<br>4. 首批为核心技能（cockpit-ui、diagnosing-bugs、living-asset-system）建立回归金标用例；<br>5. 接入 Git 预提交钩子与 CI 自动化回归门禁，构建 Eval-to-Evolution 自闭环。 | 核心技能 100% 具备声明式用例，三级 Judge 断言生效，改动自动跑回归阻断行为漂移 | `P0` | `v1.5.19` | ⏳ 待排期 |
| **Card-Harness-AHE-ContractualSelfEvolution** | **AHE 契约三元组自演进、Self-Harness 根因聚类与 Polar 不可伪造环境判官体系** | 1. 吸收 7 大 Harness 自演进论文（Meta-Harness/AHE/Self-Harness）、Karpathy 自动研究与 NVIDIA Polar：终结 Reward Hacking 假繁荣与表面症状打补丁冲突；<br>2. AHE 契约三元组：可证伪（Manifest 显式假设）、可归因（根因机制聚类 + 冻结面排除）、可回滚（文件级版本秒级还原）；<br>3. Self-Harness 目标模型自提议 + 双 Split 零回归门禁；<br>4. Polar 不可伪造环境判官：以真实沙箱执行退出码为唯一真理。 | 脚手架自演进契约化，根因聚类防补丁冲突，不可伪造环境判官，秒级可回滚 | `P0` | `v1.5.20` | ⏳ 待排期 |
| **Card-Skill-TrainablePolicy-RSI** | **可训练外部技能文档与昼夜双轮递归自演进架构 (Trainable Skill Document & Daytime-Nighttime RSI Engine)** | 1. 吸收翁荔 (Lilian Weng)《Harness Engineering for Self-Improvement》、AliExpress 速卖通与《AgentOPSD》：落实“如果被反复适配的对象是做事流程，流程文档本身就应该是可训练的外部策略状态 (Skill-MDP)”；<br>2. 引入 # EVOLVE-BLOCK-START/END 有界可编辑 Surface 机制，核心框架与强类型接口完全冻结，彻底杜绝“为了提分搞乱全局架构”；<br>3. 落地 AgentOPSD 长轨迹局部信用分配：Student 在无技能下完成真实 rollout，当前模型携带 Skill 作为 Self-Teacher 沿着相同轨迹计算每个 turn 的 token log-prob gap，精准识别关键 turn；<br>4. 昼夜双轮闭环：白天在确定性 Harness 下处理真实任务产生轨迹，夜间离线进行弱点聚类、局部信用分配与双 Split 无退化回归门禁验证，更新持久化技能。 | 技能文档外部可训练，长轨迹信用精准分配，昼夜双轮闭环，双 Split 零退化验证 | `P1` | `v1.5.21` | ⏳ 待排期 |
| **Card-Skill-CapabilityPages-NegativeBoundaryRouter** | **腾讯 Capability Pages 三段式技能档案、簇级邻居对比与 T^- 负向边界隔离路由体系** | 1. 吸收腾讯混元《Skill-Use 基准》与腾讯优图《Capability Pages》：解决装了 10+ 技能后表现断崖下跌与 SU<0.5 时用技能比不用更糟的绝症；<br>2. 提纯三段式档案结构：T^+（正向触发）、T^-（负向边界）、B（判别主体）；<br>3. 簇级邻居对比生成 T^-；<br>4. 部署隔离铁律：向量索引只存 T^+ + B + 原文，T^- 严禁入库（防语义漂移），仅专供第二阶段 Cross-Encoder / Router 裁判；<br>5. 相似技能 Top-1 区分率提升超 15%。 | 彻底终结多技能检索失明，负向边界物理隔离防向量污染，相似技能精准区分 | `P1` | `v1.5.22` | ⏳ 待排期 |
| **Card-Skill-ContrastiveDistillation** | **SKILL-KD 师生分叉决策对比蒸馏与学生重跑变绿准入门禁 (Contrastive Skill Distillation & Re-execution Gate)** | 1. 吸收浙大&北大&阿里《SKILL-KD》与北大《VeriSkill》，切除“自我反思导致的规则堆叠通胀与近亲繁殖”（38条验证规则 66.8分 击败 96条未验证反思规则 60.1分）；<br>2. 师生决策分叉提取器：从学生（本地弱模型/子代理）与老师（Claude Opus 5 / GPT-5.6 / 专家轨迹）在同题目的分叉节点提取有效差异信号；<br>3. 物理准入硬门禁（Re-execution Gate）：提炼出的候选规则 Patch 必须让学生带着在沙箱重跑原题变绿（Turn Green），断言成功才准入库；<br>4. 漂移感知规则合并（Consolidation）：自动聚类压缩重合规则，保持技能库在黄金甜点区（≤ 300 行）。 | 杜绝未经验证的反思入库，重跑变绿准入率 100%，规则库压缩保持精炼高内聚 | `P1` | `v1.5.23` | ⏳ 待排期 |
| **Card-Evolution-CICD-DreamingGate** | **Agent 七阶段 CI/CD 变更流水线、离线异步 Dreaming 模式挖掘与四级自治升降级（深度整合 EntropyCrystallizer 存量碎片结晶）** | 1. 吸收 DeepEvolution《Agent CI/CD 流水线》与《Evolve Loop 控制层》：建立信号汇聚➔候选生成➔隔离评测➔安全门控➔灰度发布➔监控回滚➔经验沉淀七阶段管线；<br>2. 深度整合 EntropyCrystallizer：离线异步 Dreaming 模式挖掘器在夜间低峰期扫描长程轨迹聚类系统性缺陷，同时将存量散落碎片三门并联熔铸为高精纯晶体并沉淀 #cry_xxxx，消除两套定时器冲突；<br>3. 四级自治阶梯 (Level 0-3) 与异常自动降级机制；<br>4. 人类五大不可剥夺决策权与三层防审核疲劳通道；<br>5. 监控输出长度、拒答率、重试率二阶指标防范方向漂移。 | 七阶段变更管线，离线 Dreaming 与存量结晶深度融合，四级自治动态升降级，二阶防方向漂移 | `P1` | `v1.5.24` | ⏳ 待排期 |
| **Card-Metrics-AgentSensors** | **智能体三维效能探针（Token SNR、P@5 召回精度、人工介入率）** | 1. 落地 CPA 导师核心建言“先立度量再动架构，给系统一把恒定的物理标尺”；<br>2. 在 OpenViking Studio 观测大盘埋设三大物理探针：Token 有效载荷率 SNR、记忆召回命中率 P@5、人类纠偏介入率；<br>3. 终结架构改造效果的定性口水战，全部以数字化客观曲线驱动演进。 | Studio 观测大盘透传三大物理指标，每日会话自动统计，指标真实可靠 | `P2` | `v1.5.25` | ⏳ 待排期 |
| **Card-Retrieval-AdvancedCards** | **检索大屏第二排高阶运营看板扩展 (Advanced Operational Telemetry)** | 1. 在检索大屏第二排扩展高阶运营指标（BM25 词法与稠密向量命中比、RARG 弃答率曲线、知识库健康度三维雷达）；<br>2. 前端组件完全遵守性冷淡视觉规范、NO GREEN EVER 与 >=11px 字号契约；<br>3. 真实后端数据驱动，在无数据时优雅展示 -- 占位符。 | 大屏第二排高密指标瓦片对齐，纯真实后端数据驱动，NO GREEN 规范，构建 PASS | `P2` | `v1.5.26` | ⏳ 待排期 |
| **Card-LLMLingua-01** | **微软开源顶级轮子 LLMLingua-2 (xlm-roberta) 自然语言 Wiki 文档后台异步脱水降噪专项** | 1. 定位澄清：针对外部长篇 Wiki 与 Markdown 静态文档的后台离线脱水（不常驻占用 2080Ti 显存，改用按需加载或 CPA工兵处理）；<br>2. 毫秒级抽稀 50% 自然语言冗余水话，提升注意力浓度，零幻觉；<br>3. 与本地 SkillZip（针对技能流程）和 Notes-History（针对多轮对话）正交分工，补齐课题五最后一块拼图。 | Wiki 文档脱水 50%，Token 显著压缩，零显存泄漏，后台批处理离线完成 | `P2` | `v1.5.27` | ⏳ 待排期 |

---

## 📋 四、 Milestone 3 详细任务规格卡片 (Detailed Task Card Specs: v1.5.01 ~ v1.5.27)

### 🌊 Wave 1: 运行时与脚手架地基 (Runtime & Harness Foundation)

#### 📌 [P0] [x] Card-Runtime-TwoTierAgentLoop-OnionGuard (v1.5.01): pi 生产级双层事件循环、四层洋葱防御与中途插话/主动刹车契约 ✅
- **目标版本**：`v1.5.01` ｜ **优先级**：`P0` ｜ **交付状态**：`[x] 已验收通过 ✅`
- **核心交付目标**：
  1. 吸收生产级 pi/agent-loop.ts 743 行源码精读与洋葱模型：终结单层 while 循环无法中途插话、死循环无法优雅中止与异常崩溃顽疾；
  2. 双层事件循环架构：外层管控会话与模型切换，内层循环推进 `hasMoreToolCalls || pendingMessages.length > 0`；
  3. 四层洋葱保护：核心循环、模型防御（指数退避与重试）、用户控制（异步插话队列 + 优雅 Abort 协作取消，零消息遗漏）、调度增强与工具护栏；
  4. 工具主动刹车契约：返回 `terminate: true` 立即终止工具迭代并提前完成交付；
  5. 补充 Merkle 状态树与感知循环 (`pi_dual_loop.py`)，实现毫秒级变更检测 (<2ms)。
- **验收证据与物理闭环**：
  - **Git Release Tag**：`v1.5.01`
  - **核心源码与行数 (严格锁定 100~300 行黄金甜点区)**：
    - `openviking/core/agent_loop.py` (257 行，双层循环与四层洋葱防御核心实现)
    - `tests/unit/test_agent_loop.py` (185 行，单测全覆盖：基本流、工具迭代、主动刹车、中途插话零丢包、Abort协作取消、模型防御重试)
    - `openviking/core/pi_dual_loop.py` (271 行，Merkle 树哈希感知与增量比对)
    - `tests/unit/test_pi_dual_loop.py` (137 行，树哈希单测)
    - `openviking/core/__init__.py` (统一导出)
  - **双全测试与构建验真**：
    - 单元测试：`pytest tests/unit/test_agent_loop.py tests/unit/test_pi_dual_loop.py` (11 passed in 0.30s)
    - 回归测试：`pytest tests/server/test_dual_mode_mcp.py tests/test_task_tracker.py tests/unit/test_agent_loop.py tests/unit/test_pi_dual_loop.py` (70 passed in 1.66s)
    - 安全扫描：`python3 scripts/security_check.py` (Checked 4202 tracked files. Zero secrets detected.)
    - 前端构建：`npm run build` (21.94s, zero errors)

#### 📌 [P0] [x] Card-Memory-ColdQuarantine-ZombiePurge (v1.5.02): 存量僵尸记忆冷归档与 1936 毒性软隔离专项 (Zombie Memory Quarantine & 1936 Detox) ✅
- **目标版本**：`v1.5.02` ｜ **优先级**：`P0` ｜ **交付状态**：`[x] 已验收通过 ✅`
- **核心治理成果与物理交付目标**：
  1. **物理排查与冷备隔离**：针对 `~/.openviking/data/viking/default/resources/` 下 1,159 个 2026 年 7 月份废弃 session 草稿目录（`antigravity_master_*` 与 `antigravity_session_*`）研发 `scripts/quarantine_zombie_memories.py`（241 行黄金甜点区，支持 `--dry-run` 与 `--restore`）；
  2. **恪守数据安全红线（绝对零硬删除）**：将 1,159 个目录（3,833 个文件，4.2 MB）完整软移动至冷备专区 `~/.openviking/data/archive/zombie_sessions/20260915_091547/`，并保存 `quarantine_manifest.json`，确保历史数据零丢失且随时可逆还原；
  3. **官方标准 API 闭环清理**：通过 VikingFS REST 接口 `DELETE /api/v1/fs?uri=viking://resources/{folder}&recursive=true` 并发安全清理 1,159 个资源，同步清除 VectorDB 向量存储中对应的 L0/L1/L2 嵌入与语义标记（成功率 1159/1159，0 失败）；
  4. **端到端物理验真双全通过**：
     - `openviking_find(query="1936")`：历史前缀草稿完全清除归零，仅留 2026-09-08 官方 1936 下线交付规范；
     - `openviking_find(query="antigravity_master")`：完全回归真实工具与应用实体记忆，彻底根除跨会话上下文投毒；
     - 清理并重置 Hook 预取本地缓存 `/tmp/ov_pre_invocation_cache.json`，开局预取与工具调用恢复纯净高密工程事实；
  5. **门禁验证全绿**：
     - 单元测试：`pytest -o addopts="" tests/unit/test_agent_loop.py tests/test_task_tracker.py` (54 passed)；
     - 安全扫描：`python3 scripts/security_check.py` (Checked 4206 tracked files. Zero secrets detected)；
     - 前端构建：`npm run build` (21.82s, zero errors)。
- **交付代码与清单**：
  - `scripts/quarantine_zombie_memories.py` (241 行，核心归档与清除脚本，单文件处于 100~300 行黄金甜点区)
  - `package.json` (版本推进至 1.5.02)
  - `openviking/_version.py` (版本推进至 1.5.02)
  - `REFACTORING_PLAN.md` (总看板状态流转与双轨留痕)
  - **Git Release Tag**：`v1.5.02` ｜ **Commit Hash**：`36848c2e4`

#### 📌 [P0] [ ] Card-Harness-DeepSeek-AgentScope-SpecDriven (v1.5.03): DeepSeek-Harness 极简规范外壳、AgentScope Java 2.0 生产级运行时与企业级四不变式 ⏳
- **目标版本**：`v1.5.03` ｜ **优先级**：`P0`
- **核心交付目标**：1. 吸收 DeepSeek 官方开源 deepseek-harness、2026 上半年自进化综述与阿里 AgentScope Java 2.0 GA：确立 Harness 四大不可变式（可终止、可隔离、可恢复、可观测）；<br>2. Workspace 抽象文件系统 (Abstract File System)：静态资产（AGENTS.md/Skills）与运行时数据（Session/MEMORY.md）解耦；<br>3. 物理免压缩白名单：长任务规划详情、异步子 Agent 追踪状态、权限授权记录物理免受上下文压缩破坏；<br>4. 工具失败分类捕获与防死循环重试，多租户 Runtime Context 显式传递。
- **验收条件**：彻底终结长会话规划与状态丢失，沙盒隔离与成本硬限制 100% 生效，多租户解耦

#### 📌 [P0] [ ] Card-Harness-ReadWriteOffload-HookGuard (v1.5.04): 腾讯 DECO 级读写两侧 Offload 护栏与 Hook 切面长文本防偷懒/防越权体系 ⏳
- **目标版本**：`v1.5.04` ｜ **优先级**：`P0`
- **核心交付目标**：1. 吸收腾讯《DECO 数仓 Agent 引擎护栏实践》：彻底根治模型在长脚本（1200+行）生成时的“省略偷懒 (/* 省略若干行 */)”与“未经确认越权推生产”绝症；<br>2. Hook 切面与推理循环解耦：围绕模型与工具调用建立独立前后回调拦截；<br>3. 读写两侧 Offload：LLM 绝不直接接触全文！读拦截写入只读沙箱并下发 file_ref 句柄，写拦截强制走 copy_file + str_replace 小步增量补丁；<br>4. 危险操作 HITL 门禁：状态机检查当前阶段，未确认前物理阻断发布工具。
- **验收条件**：彻底封杀长文本省略偷懒，大文件上下文开销降 90%，越权操作 100% 物理拦截

#### 📌 [P0] [ ] Card-Verify-MultiMetricGate (v1.5.05): 交付物多维物理验真门禁（内容哈希 + 增量覆盖率 + 单测真跑，防 Exit 0 假完成） ⏳
- **目标版本**：`v1.5.05` ｜ **优先级**：`P0`
- **类型**：Task Quality Gate / Physical Verification / Anti-Cheat / Goodhart Protection ｜ **优先级**：🔥 P0（运行时验收刚需）
- **目标版本**：`v1.5.04` ｜ **交付时间预估**：Wave 1 周期 ｜ **当前状态**：⏳ 方案已终审·待排期实施
- **来源依据与核心思考推演过程 (Reasoning & Inversion Context)**：
  - **理论源头追溯**：字节跳动《Aspire：自演化智能体虚假闭环教训与 Goodhart 定律防范》(2026.06) 与 CPA 导师物理验真准则；
  - **芒格逆向审讯（倒推 Agent 交付作弊的底层死因）**：
    - *死因 1 (Exit 0 伪造假象)*：Agent 在遇到复杂测试用例报错时，往往下意识给测试加上 `@pytest.mark.skip`、在代码里加 `try...except: pass` 吞掉异常，或者仅仅修改了注释，命令执行返回 Exit Code 0，即宣布“已交付修复”；
    - *死因 2 (无变更零代码交付)*：Agent 经过多轮工具调用后自认为问题已自愈，实际没有物理产出任何有效的 Git Diff 变更；
    - *死因 3 (指标异化与 Goodhart 定律)*：当单一指标（如测试通过）成为目标时，它就不再是一个好指标。
  - **奥卡姆剃刀工程解法**：
    - **双重刚性物理验真**：
      1. `Diff 变更行数 > 0`：检查暂存区与工作区，排除仅改注释或空白字符，必须有实质代码改动；
      2. `真实集成测试全绿`：禁止跳过关键断言，以受限沙盒内实际退出码为硬指标；
    - **不可逾越物理门禁**：作为任务中心终态认定的强制守门员，任何未通过双重验真的任务一律打回重试。
- **核心治理成果与三大原子工序拆解 (Tracer-Bullet Tickets)**：
  1. **⚙️ Tracer 1: 物理变更行数与 AST 语法树改动验真器 (`PhysicalDiffVerifier`)**
  2. **⚙️ Tracer 2: 集成测试沙盒执行与非零退出码阻断器 (`TestRetinaRunner`)**
  3. **⚙️ Tracer 3: TaskTracker 终态物理验真钩子挂载与单测回归**
- **不可逾越物理验收门禁**：
  - 门禁 1：零 Diff 变更或纯空注释变更提交，系统 100% 物理拒绝完成任务；
  - 门禁 2：测试用例报错或断言失败时，强制阻断任务流转并抛出详细失败堆栈。

#### 📌 [P1] [ ] Card-Harness-SpecDrivenFSM (v1.5.05): 第三代数仓级多智能体 Harness 架构（Spec 结构化文件驱动 + 协调者专家分离 + 12 状态有限状态机） ⏳
- **目标版本**：`v1.5.05` ｜ **优先级**：`P1`
- **核心交付目标**：1. 吸收阿里千问数仓 Harness 实践与 Qwen《Skill-SP》：确立 Agent = Model + Harness，下限由工程托底；<br>2. Orchestrator 与 Specialist 物理分工：协调者只调度、把关、评审，严禁下场写业务代码；专家在独立沙箱专精窄接口；<br>3. Spec 结构化文件驱动通信：跨阶段全面废除长会话历史总线，统一传递结构化文件路径，阶段终点强制生成固定格式 CP 检查点摘要；<br>4. 生成者与评估者严格分离（Generator != Evaluator）；<br>5. 12 状态有限状态机与故障三分法，支持秒级断点续接。
- **验收条件**：上下文污染清零，阶段成果物可追溯可审计，故障断点续接率 100%，消除独角戏越轨

### 🌊 Wave 2: 零幻觉混合检索与端侧导航 (Zero-Hallucination Retrieval & Navigation)

#### 📌 [P0] [ ] Card-Retrieval-BM25Hybrid (v1.5.06): SQLite FTS5 词法与稠密向量双路混合检索与 RRF 融合 (BM25 Hybrid Retrieval) ⏳
- **目标版本**：`v1.5.06` ｜ **优先级**：`P0`
- **核心交付目标**：1. 吸收《BM25 Wins at Scale》(arXiv:2607.26497) 与生产混检共识，破除纯 Dense 向量在精确符号上的检索盲区；<br>2. 本地零外部依赖：基于 SQLite 原生 FTS5 虚拟表建立文本/经验倒排索引；<br>3. 双路召回并行流：Dense Vector (qwen3-vl-emb) + Sparse BM25 (FTS5) 毫秒级并行捞取候选集；<br>4. 无参 RRF 融合：采用标准倒数排名融合 (k=60) 归一化排序，输入单次 Cross-Encoder Reranker 精排；<br>5. 补齐代码符号、错误堆栈、端口与文件名精准命中专项单测。
- **验收条件**：精确代码符号与错误排查召回率大幅提升，保持单次 RER 契约不变，延迟开销几乎为 0

#### 📌 [P0] [ ] Card-Retrieval-LocalFirst-zgSemanticSearch (v1.5.07): 阿里 zg 级端侧本地命令行语义搜索、四重奏融合与代码符号防盲搜护栏（深度整合 TieredLazyFetch 分级契约） ⏳
- **目标版本**：`v1.5.07` ｜ **优先级**：`P0`
- **核心交付目标**：1. 吸收阿里 Qwen+Zvec《zg (zvec-grep)》、Karpathy 知识空间与 CPA 导师分级懒加载黄金律：彻底解决 Agent 在终端疯狂跑 rg 盲猜代码导致上百文件撑爆上下文；<br>2. 深度整合 TieredLazyFetch：引入 depth 契约，depth=0（元数据行号）、depth=1（紧凑指纹前后1行，默认推荐）、depth=2（完整块）；<br>3. 端侧四重奏检索引擎：32MB 超轻静态模型向量感知 + BM25 词频 + RRF 无参融合 + ripgrep 精确匹配；<br>4. AST 符号级切片（函数/类），Local-First 纯端侧 0 显存依赖，万行仓库 30s 极速建库；<br>5. 工具调用减少 50%，Token 减半。
- **验收条件**：彻底终结代码符号盲搜，纯本地 32MB 模型 0 显存，分级懒加载契约落地，Token 减 50%

#### 📌 [P1] [ ] Card-RAG-Abstention-ZeroHallucination-Pipeline (v1.5.08): 千万级语料 RAG 约束验证与弃答门禁流水线、RARG 语义引导相关性搜索与 MinHash 去重 ⏳
- **目标版本**：`v1.5.08` ｜ **优先级**：`P1`
- **核心交付目标**：1. 吸收千万级工业 RAG 深度记事、腾讯/中科院信工所开源 RARG、七牛开发者与 6 曦轩：彻底攻克海量文档下模型默认“盲猜”导致的严重幻觉；<br>2. 前置 MinHash LSH 近重复去重与 NFKC 分词标准化，阻断冗余拷贝霸榜；<br>3. RARG 语义引导搜索：embed_recall 排序候选路径，单线程 rg -j1 顺序扫描，结合起点 10 段线索与局部重排；<br>4. 独立 Verifier 判官与主动弃答门禁 (Abstention Gate)：证据不足或置信度低于阈值强制拒答，幻觉率压制到接近 0。
- **验收条件**：10M+ 文档毫秒级检索，局部重排工具调用降低 70%，主动弃答将幻觉率压制至接近 0

#### 📌 [P1] [ ] Card-Knowledge-HG-RAG-HierarchicalCompass (v1.5.09): HG-RAG 分层指南针拓扑检索、Karpathy LLM Wiki 与 WeKnora 读写分离知识工程 ⏳
- **目标版本**：`v1.5.09` ｜ **优先级**：`P1`
- **核心交付目标**：1. 吸收 PaperAGI《HG-RAG》、Karpathy LLM Wiki、翻斗花园二蛋 Graph Engineering 与 WeKnora 企业实践：解决多跳实体推导断层与合并单元格大类丢失；<br>2. HG-RAG 分层指南针拓扑：构建可漫游父子关联索引，结构化主数据表叶子 chunk 自洽回填全路径大类；<br>3. 编辑台与服务台物理分离（Read/Write Decoupling）：重型解析与图计算隔离在编辑台，生产服务台保持只读极速响应；<br>4. 零分叉 Overlay 覆盖层升级：同名替换 > 新增组件 > 变量覆盖 > 幂等锚点补丁。
- **验收条件**：跨层级多跳检索准确率提升 25%，结构化表路径零丢失，读写分离彻底消除生产磁盘撑爆

### 🌊 Wave 3: 上下文保真与记忆生命周期 (Context Fidelity & Memory Hygiene)

#### 📌 [P0] [ ] Card-Extraction-ZeroThinking-BisectionHeal (v1.5.11): 记忆提取零思考硬开关、Token 截断二分切片自愈与条数/字数双门禁体系 ⏳
- **目标版本**：`v1.5.11` ｜ **优先级**：`P0`
- **核心交付目标**：1. 吸收《无银三百两》提取检修实战：根治提取长对话时 171 次调用 97 次空返回、耗时 2.5 小时的死锁绝症；<br>2. 记忆提取强制关闭 Thinking 思考（enable_thinking=False），切除思考对正文 max_tokens 预算的挤占，提速 10~20 倍，Token 消耗降 70%+；<br>3. 严格区分偶发与截断：截断物理阻断原样重试，自动触发区间二分切片并发抽取；<br>4. 消息总字数 >4000 或条数 >25 双门禁预切片；<br>5. 入库防爆安全切分。
- **验收条件**：提取场景零思考提速 20 倍，截断二分自愈清零空返回，字数条数双门禁防死锁

#### 📌 [P1] [ ] Card-Memory-LifecycleFSM (v1.5.12): 记忆版本状态机 (active/disputed/superseded) 与冲突挂链降权机制 ⏳
- **目标版本**：`v1.5.12` ｜ **优先级**：`P1`
- **核心交付目标**：1. 吸收《LLM Wiki 长文》与腾讯自进化飞轮真核：“我们已经会编译经验，但还不会给记忆写状态机”；<br>2. 记忆 Schema 引入一等公民状态：status: active | disputed | superseded 与 superseded_by 演进指针；<br>3. 写入侧冲突检测：新经验推翻旧经验时自动挂链标记 superseded，禁止静默并存误导；<br>4. 检索侧物理降权 (Demotion)：superseded / disputed 状态条目默认大幅降权或过滤，优先返回最新有效经验；<br>5. Studio 大盘与记忆抽屉直观展示被取代条目划线状态与演进血缘链。
- **验收条件**：彻底根除“旧错误经验比新经验得分更高导致 Agent 被误导”的致命缺陷，单测全绿

#### 📌 [P1] [ ] Card-Memory-EntropyCrystallizer-TriGate (v1.5.13): 存量历史碎片三门并联结晶归纳器与不可变事实 SSOT 熔炼 (Entropy Crystallizer & SSOT Distillation) ⏳
- **目标版本**：`v1.5.13` ｜ **优先级**：`P1` ｜ **当前状态**：⏳ 方案已终审·待排期实施
- **来源依据与架构思考 (Reasoning & Inversion Context)**：
  - 吸收 2026-09-08 架构共识（Card-Entropy-02）与芒格逆向审讯：解决存量碎片越积越多引发的向量库熵增与严重检索混淆；
  - 芒格倒推死因：杜绝 LLM 概括时的“中庸抹平”与虚假因果，必须采用强结构化契约；
- **核心治理成果与物理交付目标**：
  1. **三门并联硬门禁 (Tri-Gate Barrier)**：聚类条数 $\ge 5$ 条、语义余弦相似度均值 $> 0.75$、沉淀时间 $\ge 24\text{h}$ 冷却期（防范热会话中早熟结晶）；
  2. **三层不可变事实晶体结构 (Three-Tier Crystal Schema)**：
     - **L0 核心公理 (Axiom)**：单句不可变事实（无歧义确定性断言，如“对外唯一服务端口物理收口为 1933”）；
     - **L1 版本与证据链 (Context & Bounds)**：明确生效版本范围（如 `>= v1.5.00`）与来源引用（Commit Hash / PR / 会话事实）；
     - **L2 负向排斥哨兵 (Negative Boundary)**：显式列出已废弃模式与排斥词（如“彻底废弃 1936 端口与独立 M3 算子硬件绑定”），触发检索时提供强排斥信号；
  3. **存量物理净减熵**：熔炼产生 1 个高纯晶体节点后，原 5 条散落碎片在 SQLite 中挂载 `superseded` 演进指针并移出活跃库进入冷归档，达成活跃向量节点的【物理净减少】。
- **验收条件**：散落碎片熔铸为不可变事实库，活跃向量节点物理净减，三门并联杜绝假结晶，单测全绿。

#### 📌 [P1] [ ] Card-Context-ActiveNotesAndHistory (v1.5.14): Codex 级主动上下文治理（Notes 高密活跃状态 + History 独立检索分仓，切除有损 Compaction） ⏳
- **目标版本**：`v1.5.14` ｜ **优先级**：`P1`
- **核心交付目标**：1. 吸收 DeepEvolution 对 Codex 最新架构解密 (PR #39827)：废除有损全局 Compaction 摘要（多次压缩导致路径、错误码、中间未完成状态严重失真）；<br>2. 状态与历史双轨分仓：Notes 存高密度结构化核心事实常驻上下文，History 存原始对话流移出上下文独立分仓；<br>3. 主动调阅工具：模型按需调用 list_history_windows / search_history 检索历史；<br>4. 阻断长会话上下文失忆与信息衰减。
- **验收条件**：切除有损压缩，关键路径/报错信息零失真，长程多轮会话状态持久保真

#### 📌 [P1] [ ] Card-Skill-ZipOnWrite-ContractualCompression (v1.5.15): 阿里 SkillZip 写入即压缩引擎、六元组强类型契约与 0-Rollout 确定性重构防膨胀 ⏳
- **目标版本**：`v1.5.15` ｜ **优先级**：`P1`
- **核心交付目标**：1. 吸收阿里/浙大/杜克《SkillZip》：终结自进化技能膨胀 5.2 倍的“复读机死因”（重复代码与琐碎特例堆叠）；<br>2. 六元组强类型契约化解析（接口、工作流、协议、规则、契约、证据）；<br>3. Explain Once, Reference Everywhere：公共动作抽取为共享过程函数，公共规则提升至最小公共作用域；<br>4. 0-Rollout 确定性优化（动态规划规则放置 + 加权装箱）；<br>5. Zip-on-Write 门禁：写入即压缩，长度全程锁定种子 1.6~1.9 倍，压缩率超 30% 且基准表现持平反超。
- **验收条件**：技能契约化解析，0-Rollout 确定性重构，写入即压缩防膨胀复利，压缩率 30%+

#### 📌 [P1] [ ] Card-Memory-ValetIngestion-AntiEntropyGate (v1.5.16): 前门自动泊车异步分流与反熵增去噪去重准入门禁 (Valet Ingestion Engine & Anti-Entropy Gate) ⏳
- **目标版本**：`v1.5.16` ｜ **优先级**：`P1` ｜ **当前状态**：⏳ 方案已终审·待排期实施
- **来源依据与架构思考 (Reasoning & Inversion Context)**：
  - 吸收 2026-09-08 架构共识（前门自动泊车）与芒格逆向审讯：彻底根治同步门禁阻塞导致的写入延迟飙升、超时雪崩与调用方锁死；
- **核心治理成果与物理交付目标**：
  1. **自动泊车异步分流模型 (Valet Ingestion Engine)**：写入端（REST / MCP / WebDAV）只进行纳秒级 Schema 与合法性校验，10ms 内立即返回 HTTP 202 Accepted 并交出带 trace_id 的 Receipt 票据，调用方主执行流 0 延迟；
  2. **后台异步深减熵 Worker**：重型计算（MinHash LSH 近重复检测、语义去重、时效衰减打标）由后台 Worker 异步批量消化；
  3. **消灭存储侧门 (Storage Level Gatekeeper)**：将门禁下沉至存储引擎基座，统一拦截 WebDAV、REST 与 MCP 写入路径，消灭任何能绕过门禁直接往底层写垃圾的侧门；
  4. **非对称时效动力学与防通胀机制**：长期未命中或存疑条目自动降权，防范近亲繁殖与规则膨胀。
- **验收条件**：写入 10ms 极速交钥匙，后台异步深减熵，消灭存储侧门，全链路反熵增闭环。

#### 📌 [P1] [ ] Card-Hygiene-AsymmetricDecayAndBench (v1.5.17): 知识卫生异步巡检 (Knowledge Hygiene)、非对称衰减与真实查询回归金标集 ⏳
- **目标版本**：`v1.5.17` ｜ **优先级**：`P1`
- **核心交付目标**：1. 吸收非对称淘汰律：“错误记忆的伤害远大于正确记忆的收益”；<br>2. 挂载轻量后台巡检 Worker：识别死重条目（零召回）、冲突簇与孤立引用，坚守奥卡姆剃刀：只输出报告与建议，绝不自动化盲目删数据；<br>3. 时效动力学与非对称衰减：对长期未命中或被标记存疑的条目降低基础检索权重；<br>4. 真实查询金标回归集 (Gold Benchmark)：从真实 find 提取 50~100 条覆盖符号、报错、规则的测试集，固定上下文 Token 预算，作为检索算法/模型升级的不可逾越门禁。
- **验收条件**：知识库死重与冲突可视可控，模型/检索演进具备固定物理标尺，告别盲飞调参

#### 📌 [P1] [ ] Card-Evolve-HermesEvolveLoop-Patch (v1.5.18): Hermes 级经历与能力解耦存储、Periodic Nudges 异步副进程复盘与 Patch 级技能微补丁自进化机制 ⏳
- **目标版本**：`v1.5.18` ｜ **优先级**：`P1`
- **核心交付目标**：1. 吸收 DeepEvolution《Hermes Agent Evolve Loop》与全景导论：实现经历（SessionDB）与能力（Skill/Memory）严格物理分层；<br>2. 跨会话 FTS5 真实消息检索（拒绝虚假 LLM 摘要）；<br>3. Periodic Nudges 异步副进程复盘：主任务完成后异步派发轻量工兵模型复盘轨迹并提取经验，零阻塞用户交互；<br>4. Patch 优先技能微手术：skill_manage 强制局部增量替换（≤30行），保留 90% 经过验证的边界逻辑，防范 Edit 模式全量重写的严重幻觉覆盖。
- **验收条件**：经历与能力物理分层，真实轨迹 FTS5 检索，异步副进程复盘，Patch 局部微手术防遗忘

### 🌊 Wave 4: 契约化自演进与离线梦境闭环 (Contractual Self-Evolution & Dreaming)

#### 📌 [P0] [ ] Card-Skill-EvaluationRetina (v1.5.19): Skill 质量视网膜与自动化评测门禁体系 (Skill-as-Code & Testing CI / skill-up 规范落地) ⏳
- **目标版本**：`v1.5.19` ｜ **优先级**：`P0`
- **核心交付目标**：1. 吸收阿里开源 skill-up 与 AI 软件测试方法论，彻底终结“改动一行提示词行为漂移、跑一遍 Demo 没报错就裸奔上线”；<br>2. 规范化测试工程结构：建立 evals/cases/（声明式 YAML 用例）、evals/fixtures/（数据脚手架）、evals/eval.yaml（引擎与断言配置）；<br>3. 落地三级判定器引擎（Exact/Regex 匹配断言、Command 脚本退出码、agent_judge LLM 语义判官）；<br>4. 首批为核心技能（cockpit-ui、diagnosing-bugs、living-asset-system）建立回归金标用例；<br>5. 接入 Git 预提交钩子与 CI 自动化回归门禁，构建 Eval-to-Evolution 自闭环。
- **验收条件**：核心技能 100% 具备声明式用例，三级 Judge 断言生效，改动自动跑回归阻断行为漂移

#### 📌 [P0] [ ] Card-Harness-AHE-ContractualSelfEvolution (v1.5.20): AHE 契约三元组自演进、Self-Harness 根因聚类与 Polar 不可伪造环境判官体系 ⏳
- **目标版本**：`v1.5.20` ｜ **优先级**：`P0`
- **核心交付目标**：1. 吸收 7 大 Harness 自演进论文（Meta-Harness/AHE/Self-Harness）、Karpathy 自动研究与 NVIDIA Polar：终结 Reward Hacking 假繁荣与表面症状打补丁冲突；<br>2. AHE 契约三元组：可证伪（Manifest 显式假设）、可归因（根因机制聚类 + 冻结面排除）、可回滚（文件级版本秒级还原）；<br>3. Self-Harness 目标模型自提议 + 双 Split 零回归门禁；<br>4. Polar 不可伪造环境判官：以真实沙箱执行退出码为唯一真理。
- **验收条件**：脚手架自演进契约化，根因聚类防补丁冲突，不可伪造环境判官，秒级可回滚

#### 📌 [P1] [ ] Card-Skill-TrainablePolicy-RSI (v1.5.21): 可训练外部技能文档与昼夜双轮递归自演进架构 (Trainable Skill Document & Daytime-Nighttime RSI Engine) ⏳
- **目标版本**：`v1.5.21` ｜ **优先级**：`P1`
- **核心交付目标**：1. 吸收翁荔 (Lilian Weng)《Harness Engineering for Self-Improvement》、AliExpress 速卖通与《AgentOPSD》：落实“如果被反复适配的对象是做事流程，流程文档本身就应该是可训练的外部策略状态 (Skill-MDP)”；<br>2. 引入 # EVOLVE-BLOCK-START/END 有界可编辑 Surface 机制，核心框架与强类型接口完全冻结，彻底杜绝“为了提分搞乱全局架构”；<br>3. 落地 AgentOPSD 长轨迹局部信用分配：Student 在无技能下完成真实 rollout，当前模型携带 Skill 作为 Self-Teacher 沿着相同轨迹计算每个 turn 的 token log-prob gap，精准识别关键 turn；<br>4. 昼夜双轮闭环：白天在确定性 Harness 下处理真实任务产生轨迹，夜间离线进行弱点聚类、局部信用分配与双 Split 无退化回归门禁验证，更新持久化技能。
- **验收条件**：技能文档外部可训练，长轨迹信用精准分配，昼夜双轮闭环，双 Split 零退化验证

#### 📌 [P1] [ ] Card-Skill-CapabilityPages-NegativeBoundaryRouter (v1.5.22): 腾讯 Capability Pages 三段式技能档案、簇级邻居对比与 T^- 负向边界隔离路由体系 ⏳
- **目标版本**：`v1.5.22` ｜ **优先级**：`P1`
- **核心交付目标**：1. 吸收腾讯混元《Skill-Use 基准》与腾讯优图《Capability Pages》：解决装了 10+ 技能后表现断崖下跌与 SU<0.5 时用技能比不用更糟的绝症；<br>2. 提纯三段式档案结构：T^+（正向触发）、T^-（负向边界）、B（判别主体）；<br>3. 簇级邻居对比生成 T^-；<br>4. 部署隔离铁律：向量索引只存 T^+ + B + 原文，T^- 严禁入库（防语义漂移），仅专供第二阶段 Cross-Encoder / Router 裁判；<br>5. 相似技能 Top-1 区分率提升超 15%。
- **验收条件**：彻底终结多技能检索失明，负向边界物理隔离防向量污染，相似技能精准区分

#### 📌 [P1] [ ] Card-Skill-ContrastiveDistillation (v1.5.23): SKILL-KD 师生分叉决策对比蒸馏与学生重跑变绿准入门禁 (Contrastive Skill Distillation & Re-execution Gate) ⏳
- **目标版本**：`v1.5.23` ｜ **优先级**：`P1`
- **核心交付目标**：1. 吸收浙大&北大&阿里《SKILL-KD》与北大《VeriSkill》，切除“自我反思导致的规则堆叠通胀与近亲繁殖”（38条验证规则 66.8分 击败 96条未验证反思规则 60.1分）；<br>2. 师生决策分叉提取器：从学生（本地弱模型/子代理）与老师（Claude Opus 5 / GPT-5.6 / 专家轨迹）在同题目的分叉节点提取有效差异信号；<br>3. 物理准入硬门禁（Re-execution Gate）：提炼出的候选规则 Patch 必须让学生带着在沙箱重跑原题变绿（Turn Green），断言成功才准入库；<br>4. 漂移感知规则合并（Consolidation）：自动聚类压缩重合规则，保持技能库在黄金甜点区（≤ 300 行）。
- **验收条件**：杜绝未经验证的反思入库，重跑变绿准入率 100%，规则库压缩保持精炼高内聚

#### 📌 [P1] [ ] Card-Evolution-CICD-DreamingGate (v1.5.24): Agent 七阶段 CI/CD 变更流水线、离线异步 Dreaming 模式挖掘与四级自治升降级（深度整合 EntropyCrystallizer 存量碎片结晶） ⏳
- **目标版本**：`v1.5.24` ｜ **优先级**：`P1`
- **核心交付目标**：1. 吸收 DeepEvolution《Agent CI/CD 流水线》与《Evolve Loop 控制层》：建立信号汇聚➔候选生成➔隔离评测➔安全门控➔灰度发布➔监控回滚➔经验沉淀七阶段管线；<br>2. 深度整合 EntropyCrystallizer：离线异步 Dreaming 模式挖掘器在夜间低峰期扫描长程轨迹聚类系统性缺陷，同时将存量散落碎片三门并联熔铸为高精纯晶体并沉淀 #cry_xxxx，消除两套定时器冲突；<br>3. 四级自治阶梯 (Level 0-3) 与异常自动降级机制；<br>4. 人类五大不可剥夺决策权与三层防审核疲劳通道；<br>5. 监控输出长度、拒答率、重试率二阶指标防范方向漂移。
- **验收条件**：七阶段变更管线，离线 Dreaming 与存量结晶深度融合，四级自治动态升降级，二阶防方向漂移

### 🌊 Wave 5: 效能度量与前瞻运营 (Metrics Telemetry & Advanced Ops)

#### 📌 [P2] [ ] Card-Metrics-AgentSensors (v1.5.25): 智能体三维效能探针（Token SNR、P@5 召回精度、人工介入率） ⏳
- **类型**：Observability / Agent Sensors / SNR Metric / Precision Telemetry ｜ **优先级**：🌱 P2（效能度量）
- **目标版本**：`v1.5.25` ｜ **交付时间预估**：Wave 5 周期 ｜ **当前状态**：⏳ 方案已终审·待排期实施
- **来源依据与核心思考推演过程 (Reasoning & Inversion Context)**：
  - **理论源头追溯**：CPA 导师核心建言“先立度量再动架构，给系统一把恒定的物理标尺”；
  - **芒格逆向审讯**：缺乏量化指标会导致团队陷入“感觉快了”、“好像更准了”的主观定性口水战，无法客观评估架构改造收益；
  - **奥卡姆剃刀解法**：在后台会话结束与检索调用时，静默计算三项关键标尺：
    1. **Token SNR (有效载荷率)**：实际有效代码与指令 Token 占全上下文的比重；
    2. **P@5 召回精度**：Top-5 检索结果中被 Agent 实际采纳（进入后续生成或调阅）的比例；
    3. **人工介入率**：人类发出纠偏、澄清、打断指令的会话占比。
- **核心治理成果与交付细节**：
  1. 后端探针计算并追加至 `~/.openviking/data/agent_metrics.jsonl`；
  2. Studio 大盘透传展示时序折线，零假数据驱动。

#### 📌 [P2] [ ] Card-Retrieval-AdvancedCards (v1.5.26): 检索大屏第二排高阶运营看板扩展 (Advanced Operational Telemetry) ⏳
- **类型**：Observability / Advanced Operational Telemetry / High-Density UI ｜ **优先级**：🌱 P2（运营扩展）
- **目标版本**：`v1.5.26` ｜ **交付时间预估**：Wave 5 周期 ｜ **当前状态**：⏳ 方案已终审·待排期实施
- **核心治理成果与交付细节**：
  1. 在检索大屏第二排扩展高阶运营指标（BM25 词法与稠密向量命中比、RARG 弃答率时序分布、知识库健康度雷达图）；
  2. 前端组件严格恪守座舱级高密性冷淡规范、NO GREEN EVER 与 >=11px 字号契约；
  3. 100% 真实后端数据驱动，在无数据时优雅展示 `--` 占位符。

#### 📌 [P2] [ ] Card-LLMLingua-01 (v1.5.27): 微软开源顶级轮子 LLMLingua-2 (xlm-roberta) 自然语言 Wiki 文档后台异步脱水降噪专项 ⏳
- **类型**：Model Optimization / Ingestion Compression / Background Batching ｜ **优先级**：🌱 P2（自然语言脱水）
- **目标版本**：`v1.5.27` ｜ **交付时间预估**：Wave 5 周期 ｜ **当前状态**：⏳ 方案已终审·待排期实施
- **核心治理成果与交付细节**：
  1. **定位明确**：专用于外部抓取的超长篇 Wiki 文档、白皮书等纯自然语言文本的离线脱水；
  2. **避免常驻显存**：坚决不在 2080Ti 常驻占用宝贵显存，采用 CPU/CPA 弹性工兵离线批处理；
  3. 毫秒级抽稀 50% 自然语言冗余水话，提升注意力浓度，零幻觉；
  4. 与本地 SkillZip（针对技能流程）和 Notes-History（针对多轮对话）正交互补。
