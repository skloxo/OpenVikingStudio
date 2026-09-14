# 🗺️ OpenViking 项目主线重构与原子化任务卡片总看板 (Master Task Cards Kanban - SSOT)

> **关联研发大蓝图**：[`BLUEPRINT.md`](file:///home/skloxo/aho/openclaw/project/.agents/BLUEPRINT.md) ｜ **交付全量归档台账**：[`DELIVERY_ARCHIVE.md`](file:///home/skloxo/aho/openclaw/project/DELIVERY_ARCHIVE.md) ｜ **通用资产档案库**：[`COMPONENT_AND_WHEEL_INVENTORY.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/docs/architecture/COMPONENT_AND_WHEEL_INVENTORY.md)
> **唯一真相源 (SSOT)**：本文档为 OpenViking 当前活跃的重构规划与就绪待调度的任务矩阵看板。历史所有已验收交付的版本履历已完整归档至 `DELIVERY_ARCHIVE.md`，严禁多头维护。

---

## 📌 一、 研发基线与近期已交付版本速查表 (Recent Delivered Releases: v1.4.96 ~ v1.4.110)

> **生产物理事实声明**：
> - **线上正式部署版本**：**`v1.4.106`**（物理访问地址：`vk.tide.red/studio/home`，已实机验证）；
> - **本地代码库封板版本**：**`v1.4.110`**（Git Tags 与 package.json 同频）；
> - **全量历史归档**：v1.4.4 ~ v1.4.95 及 Milestone 1 全量 70+ 个已交付卡片与 Git Commits 请查阅 [`DELIVERY_ARCHIVE.md`](file:///home/skloxo/aho/openclaw/project/DELIVERY_ARCHIVE.md)。

| 版本 Tag | 任务工单 ID | 模块与重构主题 | 核心治理成果与物理交付物 | 验收状态 |
|:---|:---|:---|:---|:---:|
| **`v1.4.110`** | **Card-2080Ti-XiaomiMo-Parity-And-Restart** | **2080Ti 本地 Windows 宿主机 XiaomiMiMo 插件同频对齐、ELECTRON_RUN_AS_NODE 环境变量隔离与 4096 引擎重启闭环** | 1. **物理根因定位**: 3070 升级 messages.transform 插件后，2080Ti Windows 宿主机未同步，运行旧版 7KB 插件缺乏 messages.transform 钩子；<br>2. **环境隔离自愈**: 彻底查清在 WSL2/PowerShell 下直接重启 `Xiaomi MiMo.exe` 继承 `ELECTRON_RUN_AS_NODE=1` 导致应用以 headless Node 模式立即退出的隐蔽缺陷，通过 `Remove-Item env:ELECTRON_RUN_AS_NODE` 恢复桌面 GUI 交互与 4096 引擎拉起；<br>3. **实机模拟双题全绿**: Agnes 2.5 Flash (得分88.5, 千问14B/32B, 100%免费) 与 Mac Studio (FRP 13100, IP 8.129.0.26) 检索注入 100% 命中；<br>4. **4096 引擎正常监听**: `plugin.log` 记录 `server init called`，MiMo 正常运行于 Session 1。<br>**Commit Hash**：（本次提交）\ | **修改文件**：`package.json`, `openviking/_version.py`, `REFACTORING_PLAN.md` |
| **`v1.4.109`** | **Card-Fleet-MiMo-Universal-Plugin** | **全集群 XiaomiMiMo 消息流直接注入插件 (messages.transform) 升级、本地落盘日志与 3070 引擎重启闭环** | 1. 查明 `experimental.chat.system.transform` 不生效原因：MiMo 桌面端后端模型服务忽略了 system 数组注入；<br>2. 升级落地 `experimental.chat.messages.transform` 直接将核心记忆前置拼接入 `lastUserMsg.parts`，彻底保证后端大模型 100% 收到 OpenViking 核心记忆；<br>3. 实现独立排障日志 `plugin.log` 自动追加至本地磁盘；<br>4. 3070 远端实机 4/4 题目 100% 正确回答（涵盖 Groq 27B、Mac Studio Qwen 3.8 Flash、Agnes 2.5 Flash、Mac Studio FRP 13100 端口与 IP）；<br>**Commit Hash**：`30a404373` \ | **修改文件**：`mcp-openviking/mimo_openviking_plugin.mjs`, `REFACTORING_PLAN.md` |
| **`v1.4.107`** | **Card-XiaomiMo-DualNode-Unified-Standard** | **全集群 XiaomiMiMo 客户端零子进程纯原生 ESM 插件大一统、跨节点 (2080Ti/3070) 目录与配置标准归一 (SSOT)** | 1. **全集群工业级统一标准 (SSOT)**: 坚决摒弃“这台机器一种配置、那台机器另一种配置”的碎片化负债；全集群 XiaomiMiMo 统一落盘于 `C:\Users\Skl\.openviking\mimo-openviking-plugin.mjs` 与 `C:\Users\Skl\.config\mimocode\mimocode.jsonc`；<br>2. **零子进程原生 Fetch 重构**: 升级 `mimo_openviking_plugin.mjs`，去除对外部 Python/Venv/WSL 子进程的依赖，使用 Node.js 18+ 内置原生 `fetch` 与毫秒级 AbortController，耗时降至 < 10ms，零进程派生开销；<br>3. **容错式正则配置解析**: 采用零依赖正向正则从 `mimocode.jsonc` 动态抽取 `OPENVIKING_API`/`OPENVIKING_API_KEY`/`OPENVIKING_ACTOR_PEER`，天然免疫 Windows 反斜杠、注释与 JSONC 语法格式容错；<br>4. **双端实机全链路测试通过**: 2080Ti 本地实测通过 (`2080TI PREFETCH SUCCESS: YES`)，3070 远程同步通过，双机统一在 `mimocode.jsonc` 中注册 `"plugin"`；<br>5. **一键入网工具集升级**: 在 `mcp-openviking/install_satellite.ps1` 中原生集成 Xiaomi MiMo 配置代码块输出；单文件 219 行处于黄金甜点区；<br>**Commit Hash**：`bb6c4fd5d` \ | **修改文件**：`package.json`, `openviking/_version.py`, `mcp-openviking/mimo_openviking_plugin.mjs`, `mcp-openviking/install_satellite.ps1`, `REFACTORING_PLAN.md` |
| **`v1.4.106`** | **Card-3070-XiaomiMo-Pydantic-Bun-Fix** | **3070 节点 XiaomiMiMo 客户端 FastMCP/Pydantic 崩溃根治、僵尸进程肃清与 ESM 官方插件化注入闭环** | 1. **问题 A (MCP 崩溃根治)**: 查清 Pydantic 2.9+ 环境下 FastMCP `_create_wrapped_model` 使用 `result=annotation` 报 `PydanticUserError` 崩溃根因，在 `_core/decorators.py` 与 `satellite_mcp_server.py` 注入防御性猴子补丁 (`result=(annotation, ...)`), 严格恪守单文件 $\le 500$ 行铁律 (当前 497 行)，单测 11/11 全绿，远端实机 16/16 工具注册 100% 成功；<br>2. **问题 B (统一路径与僵尸进程肃清)**: 物理终止 3070 远端残留的 6 个月前历史僵尸进程 (PID 65688 / 7276)，统一并锁死 SSOT 路径 `C:\Users\Skl\.openviking\satellite_mcp_server.py`；<br>3. **问题 C (Hook 注入物理根因与官方插件化重构)**: 逆向反编译 MiMo Desktop 核心包 `app.asar`，查明其对 `{hook,hooks}/*.{js,ts}` 强制执行 `await Bun.build(...)`，而桌面端基于 Node.js/Electron 运行导致抛出 `Bun.build is not a function` 这一根本物理缺陷；查明官方插件化机制 `PluginLoader.loadExternal` 与系统提示词钩子 `experimental.chat.system.transform` (`output.system.push(mem)`)；<br>4. **官方 ESM 插件投产与配置闭环**: 研发并发布 `mcp-openviking/mimo_openviking_plugin.mjs`，远端部署为 `C:\Users\Skl\.openviking\mimo-openviking-plugin.mjs`，在 `mimocode.jsonc` 注册 `"plugin"`，使用 Electron Node 原生环境测试 100% 成功加载并注册 3 大钩子 (`session.userQuery.pre`, `experimental.chat.system.transform`, `session.post`)；<br>5. 禁用所有导致 `Bun.build` 报错的旧 `openviking-lifecycle.ts` 副本，Vite 前端构建 100% PASS (18.79s)。<br>**Commit Hash**：`3999df49b` \ | **修改文件**：`package.json`, `openviking/_version.py`, `mcp-openviking/_core/decorators.py`, `mcp-openviking/satellite_mcp_server.py`, `mcp-openviking/mimo_openviking_plugin.mjs`, `REFACTORING_PLAN.md` |
| **`v1.4.105`** | **Card-Peer-Grid-Purge-Mac-Compute** | **厘清算力与智能体边界：彻底肃清 Mac Studio 离线算力幻觉实体 (mlx-agent)，精准收口 7 大真实在籍 Agent** | 1. 厘清物理基础设施真相：Mac Studio (M3 Ultra) 严格定位为底层大模型离线推理算力节点 (MLX-LM)，并非执行工程工作流的独立智能体；<br>2. 彻底剔除 `console.py` 中历史残留与幻觉混淆的 `mlx-agent@mac`；<br>3. 首页 Agent Peer 看板精准收口为 2080Ti (4) + 3070 (3) 共 7 名真实在籍干活智能体；<br>4. 前端构建与端到端实机验证 100% 纯净无幻觉；<br>**Commit Hash**：`37cd25ab1` \ | **修改文件**：`package.json`, `openviking/_version.py`, `openviking/server/routers/console.py`, `REFACTORING_PLAN.md` |
| **`v1.4.104`** | **Card-Home-Peer-Grid-Authenticity** | **首页 Agent Peer 记忆中枢看护看板真实化重构与 client@node 身份矩阵贯通** | 1. 彻底切除 `console.py` 扫描历史 7 月份假数据文件夹与盲目硬编码逻辑；<br>2. 建立全集群真实在籍节点矩阵（2080Ti 本地 4 Agent、3070 远程 3 Agent、Mac Studio 离线算力）与实时消息数累加机制；<br>3. 动态感知卫星 Agent（通过请求头 `X-OpenViking-Actor-Peer` 调用的新 Agent 自动列入看板）；<br>4. 前端 `peer-memory-grid.tsx` 优雅渲染 `[2080TI]`, `[3070]`, `[MAC]` 节点徽章与清晰角色说明；<br>5. 物理删除卡滞的 UI 走查测试任务 (`biz_res_running_embed` 与 `biz_valet_running_probe`)；<br>**Commit Hash**：`a8710b0da` \ | **修改文件**：`package.json`, `openviking/_version.py`, `openviking/server/routers/console.py`, `src/routes/home/-components/peer-memory-grid.tsx` |
| **`v1.4.103`** | **Card-Satellite-Universal-Onboarding** | **卫星智能体「提示词 + Key」一键自举入网体系、跨端极简分发与全集群身份契约固化 (Onboarding SSOT)** | 1. 升级 `install_satellite.sh` 与 `install_satellite.ps1`，原生支持 `--peer`/`-p`、`--key`/`-k` 与 `--api`/`-a` 参数，生成自包含启动包装脚本；<br>2. 安装过程原生集成 `/health` 握手自检，回显 `✅ 握手成功！智能体唯一身份证已接入中枢: client@node`；<br>3. 发布全能入网指南 [`mcp-openviking/ONBOARDING.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/mcp-openviking/ONBOARDING.md)，沉淀一键复制即用的「入职自举提示词」与 8 行标准 JSON 配置代码块；<br>4. 优化 `tools/fleet.py` FRP 穿透命令执行超时上限 (10s ➔ 20s)，提升弱网与高并发下远程运维鲁棒性；<br>**Commit Hash**：`4e995fe00` \ | **修改文件**：`package.json`, `mcp-openviking/install_satellite.sh`, `mcp-openviking/install_satellite.ps1`, `mcp-openviking/tools/fleet.py`, `mcp-openviking/ONBOARDING.md` |
| **`v1.4.102`** | **Card-XiaomiMo-DualNode-Attribution** | **2080Ti 本地 Windows 与 3070 远端 XiaomiMo (小米客户端) 统一身份穿透与双端舰队自动纳管** | 1. 查清 2080Ti 本地 Windows (`/mnt/c/Users/Skl/.config/mimocode/`) 与 3070 远端均部署了 XiaomiMo 客户端的物理事实；<br>2. 自动升级两端配置，写入真实且合规的身份签名 `xiaomimo@2080ti` 与 `xiaomimo@3070`；<br>3. `_core/config.py` 与 `satellite_mcp_server.py` 同步支持 `xiaomimo` / `mimocode` 自动嗅探归一；<br>4. 前端 `task-record.ts` 优雅映射并高密展示为 `[2080TI] XiaomiMo` 与 `[3070] XiaomiMo`；<br>5. 舰队工具 `tools/fleet.py` 巡检与同步方法全面纳管两端 XiaomiMo 客户端配置状态，自动化验证 100% 通过。 | 双节点 XiaomiMo 客户端身份精准归因，舰队工具 100% 自动纳管，单测试全绿 |
| **`v1.4.101`** | **Card-3070-Dual-Agent-Isolation** | **3070 节点反重力 IDE 与 WorkBuddy 身份物理隔离治理与双向环境自动嗅探机制** | 1. 查清 3070 节点共存 Antigravity IDE 与 WorkBuddy 调用同一个 MCP 的物理事实；<br>2. 升级 `satellite_mcp_server.py` 与 `_core/config.py`，引入进程执行特征 + 环境变量指纹双重自动嗅探 (`full_ctx`)，即使共用同一脚本也能精准识别；<br>3. 3070 远端 `C:\Users\Skl\.gemini\config\mcp_config.json` 自动配置 `antigravity@3070`；<br>4. `tools/fleet.py` 一键全自动化推流覆盖 3070 双路径 (`.openviking/` 与 `.workbuddy/openviking-mcp/`)；<br>5. 远端实机探针 100% 验证双 Agent 身份绝对隔离 (`peers_isolated: True`)，Vitest 36/36、Pytest 11/11 全绿。 | 3070 双 Agent 身份隔离 100% 验证通过，单文件均 $\le 500$ 行 |
| **`v1.4.100`** | **Card-Fleet-Ops-Identity-Rollout** | **全集群智能体统一身份穿透 (client@node) 落地、双模 MCP/Hook 自动装配与舰队自动同频闭环 (Fleet Ops)** | 1. 制定并落地全网统一 Agent 身份规范 `{client}@{node}` / `{client}.{role}@{node}`，严格符合官方正则；<br>2. 核心 MCP (`_core/config.py`) 与卫星 MCP (`satellite_mcp_server.py`) 自动解析节点平台与客户端环境，请求头自动注入 `X-OpenViking-Actor-Peer` 与 `X-Caller`；<br>3. 后端写路由 (`content.py`) 优先透传真实 actor peer，彻底切除 `default` 租户名误判；<br>4. 工作区与全局 Hook (`ov_pre_invocation.py`, `ov_session_archiver.py`)、本地配置 (`mcp_config.json`, `openclaw.json`) 统一升级至 `antigravity@2080ti` 与 `openclaw@2080ti`；<br>5. 注册 OpenViking MCP 原生舰队工具 `tools/fleet.py` (`openviking_fleet_check`, `openviking_fleet_sync`)，一键推流 3070 节点并通过 SSH 探针验证闭环；<br>6. 前端任务中心高密自解释展示 `[NODE] Client`，Vitest 36 套 174 单测全绿，Vite 构建 PASS。 | 舰队自动同步闭环，跨节点提交方真实精准归因，单文件严格 $\le 500$ 行，无缝平滑升级 |
| **`v1.4.99`** | **Card-Tasks-Initiator-Authenticity** | **任务中心提交方真实性治理与智能体身份穿透契约** | 1. 拔除后端 `write` 在未指定 caller 时盲目退化为 `default` 租户名缺陷；<br>2. Hook 后台归档携带显式 `caller="Agent (Antigravity)"` 与 `X-Caller` 请求头；<br>3. 前端提纯通用 `parseInitiator(raw, taskType)`，原子入库历史 `default` 自动按契约矫正为 `🤖 Antigravity`；<br>4. 任务详情抽屉补齐【提交方】字段与图标展示；<br>5. 后台 CPA 工兵完成全代码库密钥与假数据审计，0 阻碍落盘任务看板。 | Vitest 单测 36 套 174 项 100% PASS，Vite 生产构建 PASS (18.10s)，服务重启正常 |
| **`v1.4.98`** | **Card-Tasks-AuthenticMemoryImpact-Purge** | **原子入库记忆增量硬编码假数据 (+4 ~1) 彻底切除与 100% 真实数据对齐** | 1. 深入物理根因：排查出 `task-pipeline-diagram.tsx` 中遇 `antigravity_sessions` 强行无脑 push 4 项伪造条目（milestones, entities, cases, trajectories）的致命硬编码缺陷；<br>2. 彻底切除所有虚构记忆项代码，100% 严格由后端真实入库决策 `decision.action`（新增 1 / 更新 1 / 淘汰 1）真实驱动；<br>3. 坚决捍卫绝对数据真实性底线，彻底消灭所有原子入库雷同“+4 ~1 -0”的虚假假象；<br>4. 36 套前端单测 173 项 100% PASS，Vite 生产构建通过。 | 记忆增量审计快照 100% 真实可信，实事求是，无任何虚构衍生条目 |
| **`v1.4.97`** | **Card-Tasks-SingleRow-Standardization** | **任务中心严格单行高密度重构、标题去冗余与成果物直达抽屉收拢治理** | 1. 严格落实单行高密度原则 (Single Row)，消除上下折叠多层堆叠，各任务类型行高统一收敛为标准 40px；<br>2. 彻底剥离任务标题中的各类 Emoji (如 📥) 与冗余冒号前缀 (如 "资源处理:", "原子入库：")；<br>3. 表格重构为规范 7 列：任务名称、类型、任务编号 (#shortId)、提交方 (Bot/User 图标+名称)、关联资源 (单行等宽截断)、执行状态与进度、创建时间；<br>4. 成果物直达彻底从列表行移出，收拢至任务详情抽屉顶部专用高密卡片，支持一键复制与外部打开；<br>5. 36 套前端单测 173 项 100% PASS，Vite 构建 PASS，实机截图验证通过。 | 列表严格单行整齐划一，标题纯净无冗余，7列规范各司其职，抽屉成果物直达优雅呈现 |
| **`v1.4.96`** | **Card-Satellite-MCP-Fix** | **卫星 MCP 并行超时根除、FastMCP 异步卸载与 tree/relations 路由修复** | 1. 宿主配置超时由 5s 升级标定为 30s (30000ms)，消灭预算错位与 -32001；<br>2. FastMCP 同步工具双轨包装：传给 FastMCP 的是 async 线程池卸载函数 (`asyncio.to_thread`)，解除 stdio 事件循环卡死；<br>3. 重型检索池 (`find`/`search`/`smart_read`) 引入进程内 `asyncio.Semaphore(2)` 保护；<br>4. 后端支持 POST `/api/v1/fs/tree` 并双向兼容 GET，消灭 405；<br>5. 后端注册 `relations_router` 并守卫 `VikingFS.relations` 缺失降级，消灭 404/500；<br>6. 严格守卫单文件 ≤500 行安全红线与 11 项全量单测 PASS。 | 4 工具并发调用 5.94s 成功，消灭 -32001，tree 真实返回 280KB+，relations 返回 200 OK，pytest 11 项全绿 |
| **`v1.4.96`** | **Card-Tasks-HighDensity-And-Terminology** | **任务中心回归高密度纯列表与「原子入库」统一命名** | 1. 顺应座舱最高信息密度原则，彻底切除低密卡片视图切换与底部多余折叠抽屉 (`system-ops-view`)；<br>2. 任务路由 (`route.tsx`) 收敛至 ~100 行纯高密度单列表；<br>3. 彻底肃清历史遗留的“轻量增量入库”、“清增量入库”、“托管入库”，全系统后端路由、前端单元格、交付物解析与多语言统一命名为标准 4 字「原子入库」(`Atomic Ingestion`)；<br>4. 35 套前端测试 167 项与后端 pytest 全绿，Vite 编译通过，实机截图验证通过。 | 任务中心纯高密度列表展示，彻底消除卡片模式和冗余底部面板，所有入库任务 100% 统一为「原子入库」 |

---

## ⚡ 二、 Milestone 3 活跃待调度工单流水线 (Milestone 3 Active Pipeline: v1.5.01 ~ v1.5.20)

> **4-Wave DAG 编排演进策略**：
> - **🌊 Wave 1 (v1.5.01 ~ v1.5.04)**：**运行时与脚手架地基** — 双层事件循环、四层洋葱防御、DeepSeek 四不变式、DECO 读写 Offload 护栏；
> - **🌊 Wave 2 (v1.5.05 ~ v1.5.08)**：**零幻觉混合检索与知识拓扑** — SQLite FTS5 BM25 词法稠密混检、RARG 语义引导与主动弃答门禁、HG-RAG 分层指南针、zg 端侧代码搜索；
> - **🌊 Wave 3 (v1.5.09 ~ v1.5.14)**：**上下文保真与记忆卫生** — FSM 记忆状态机 (active/superseded)、Notes-History 双轨分仓、零思考二分切片、SkillZip 写入即压缩、非对称衰减、Hermes 复盘；
> - **🌊 Wave 4 (v1.5.15 ~ v1.5.20)**：**契约化自演进与离线梦境闭环** — Skill 质量视网膜与三级判官、AHE 契约三元组、Skill-MDP 昼夜双轮 RSI、Capability Pages $T^-$ 负向边界、SKILL-KD 对比蒸馏、七阶段 CI/CD 梦境管线。

| 任务工单 ID | 模块与重构主题 | 现状与核心治理目标 | 目标规范硬线 | 优先级 | 计划版本 | 当前状态 |
|:---|:---|:---|:---|:---:|:---:|:---:|
| **Card-Runtime-TwoTierAgentLoop-OnionGuard** | **pi 生产级双层事件循环、四层洋葱防御与中途插话/主动刹车契约** | 1. 吸收生产级 pi/agent-loop.ts 743 行源码精读与洋葱模型：终结单层 while 循环无法中途插话、死循环无法优雅中止与异常崩溃顽疾；<br>2. 双层事件循环架构：外层管控会话与模型切换，内层循环推进 hasMoreToolCalls || pendingMessages.length > 0；<br>3. 四层洋葱保护：核心循环、模型防御、用户控制（异步插话队列 + 优雅 Abort）、调度增强；<br>4. 工具主动刹车契约：返回 terminate: true 立即终止工具迭代提前交付。 | 双层循环与四层洋葱，中途插话零丢消息，工具主动刹车，异常优雅降级 | `P0` | `v1.5.01` | ⏳ 待排期 |
| **Card-Harness-DeepSeek-AgentScope-SpecDriven** | **DeepSeek-Harness 极简规范外壳、AgentScope Java 2.0 生产级运行时与企业级四不变式** | 1. 吸收 DeepSeek 官方开源 deepseek-harness、2026 上半年自进化综述与阿里 AgentScope Java 2.0 GA：确立 Harness 四大不可变式（可终止、可隔离、可恢复、可观测）；<br>2. Workspace 抽象文件系统 (Abstract File System)：静态资产（AGENTS.md/Skills）与运行时数据（Session/MEMORY.md）解耦；<br>3. 物理免压缩白名单：长任务规划详情、异步子 Agent 追踪状态、权限授权记录物理免受上下文压缩破坏；<br>4. 工具失败分类捕获与防死循环重试，多租户 Runtime Context 显式传递。 | 彻底终结长会话规划与状态丢失，沙盒隔离与成本硬限制 100% 生效，多租户解耦 | `P0` | `v1.5.02` | ⏳ 待排期 |
| **Card-Harness-ReadWriteOffload-HookGuard** | **腾讯 DECO 级读写两侧 Offload 护栏与 Hook 切面长文本防偷懒/防越权体系** | 1. 吸收腾讯《DECO 数仓 Agent 引擎护栏实践》：彻底根治模型在长脚本（1200+行）生成时的“省略偷懒 (/* 省略若干行 */)”与“未经确认越权推生产”绝症；<br>2. Hook 切面与推理循环解耦：围绕模型与工具调用建立独立前后回调拦截；<br>3. 读写两侧 Offload：LLM 绝不直接接触全文！读拦截写入只读沙箱并下发 file_ref 句柄，写拦截强制走 copy_file + str_replace 小步增量补丁；<br>4. 危险操作 HITL 门禁：状态机检查当前阶段，未确认前物理阻断发布工具。 | 彻底封杀长文本省略偷懒，大文件上下文开销降 90%，越权操作 100% 物理拦截 | `P0` | `v1.5.03` | ⏳ 待排期 |
| **Card-Harness-SpecDrivenFSM** | **第三代数仓级多智能体 Harness 架构（Spec 结构化文件驱动 + 协调者专家分离 + 12 状态有限状态机）** | 1. 吸收阿里千问数仓 Harness 实践与 Qwen《Skill-SP》：确立 Agent = Model + Harness，下限由工程托底；<br>2. Orchestrator 与 Specialist 物理分工：协调者只调度、把关、评审，严禁下场写业务代码；专家在独立沙箱专精窄接口；<br>3. Spec 结构化文件驱动通信：跨阶段全面废除长会话历史总线，统一传递结构化文件路径，阶段终点强制生成固定格式 CP (Checkpoint) 检查点摘要；<br>4. 生成者与评估者严格分离（Generator != Evaluator）：独立 Evaluator 拿着硬性 Checklist 逐项核验；<br>5. 12 状态有限状态机与故障三分法（可重试/需回退/必须中止），支持秒级断点续接；<br>6. 接入 Monorepo 显式 Pipeline DAG，消除 Agent 猜测。 | 上下文污染清零，阶段成果物可追溯可审计，故障断点续接率 100%，消除独角戏越轨 | `P1` | `v1.5.04` | ⏳ 待排期 |
| **Card-Retrieval-BM25Hybrid** | **SQLite FTS5 词法与稠密向量双路混合检索与 RRF 融合 (BM25 Hybrid Retrieval)** | 1. 吸收《BM25 Wins at Scale》(arXiv:2607.26497) 与生产混检共识，破除纯 Dense 向量在精确符号上的检索盲区；<br>2. 本地零外部依赖：基于 SQLite 原生 FTS5 虚拟表建立文本/经验倒排索引；<br>3. 双路召回并行流：Dense Vector (qwen3-vl-emb) + Sparse BM25 (FTS5) 毫秒级并行捞取候选集；<br>4. 无参 RRF 融合：采用标准倒数排名融合 (k=60) 归一化排序，输入单次 Cross-Encoder Reranker 精排；<br>5. 补齐代码符号、错误堆栈、端口与文件名精准命中专项单测。 | 精确代码符号与错误排查召回率大幅提升，保持单次 RER 契约不变，延迟开销几乎为 0 | `P0` | `v1.5.05` | ⏳ 待排期 |
| **Card-RAG-Abstention-ZeroHallucination-Pipeline** | **千万级语料 RAG 约束验证与弃答门禁流水线、RARG 语义引导相关性搜索与 MinHash 去重** | 1. 吸收千万级工业 RAG 深度记事、腾讯/中科院信工所开源 RARG、七牛开发者与 6 曦轩：彻底攻克海量文档下模型默认“盲猜”导致的严重幻觉；<br>2. 前置 MinHash LSH 近重复去重与 NFKC 分词标准化，阻断冗余拷贝霸榜；<br>3. RARG 语义引导搜索：embed_recall 排序候选路径，单线程 rg -j1 顺序扫描，结合起点 10 段线索与局部重排；<br>4. 独立 Verifier 判官与主动弃答门禁 (Abstention Gate)：证据不足或置信度低于阈值强制拒答，幻觉率压制到接近 0。 | 10M+ 文档毫秒级检索，局部重排工具调用降低 70%，主动弃答将幻觉率压制至接近 0 | `P0` | `v1.5.06` | ⏳ 待排期 |
| **Card-Knowledge-HG-RAG-HierarchicalCompass** | **HG-RAG 分层指南针拓扑检索、Karpathy LLM Wiki 与 WeKnora 读写分离知识工程** | 1. 吸收 PaperAGI《HG-RAG》、Karpathy LLM Wiki、翻斗花园二蛋 Graph Engineering 与 WeKnora 企业实践：解决多跳实体推导断层与合并单元格大类丢失；<br>2. HG-RAG 分层指南针拓扑：构建可漫游父子关联索引，结构化主数据表叶子 chunk 自洽回填全路径大类；<br>3. 编辑台与服务台物理分离（Read/Write Decoupling）：重型解析与图计算隔离在编辑台，生产服务台保持只读极速响应；<br>4. 零分叉 Overlay 覆盖层升级：同名替换 > 新增组件 > 变量覆盖 > 幂等锚点补丁。 | 跨层级多跳检索准确率提升 25%，结构化表路径零丢失，读写分离彻底消除生产磁盘撑爆 | `P0` | `v1.5.07` | ⏳ 待排期 |
| **Card-Retrieval-LocalFirst-zgSemanticSearch** | **阿里 zg 级端侧本地命令行语义搜索、四重奏融合与代码符号防盲搜护栏** | 1. 吸收阿里 Qwen+Zvec《zg (zvec-grep)》与 Karpathy 可行走知识空间：彻底解决 Agent 在终端疯狂跑 rg 猜代码函数名导致上百文件撑爆上下文的 Token 黑洞；<br>2. 端侧四重奏检索引擎：32MB 超轻静态模型向量感知 + BM25 词频 + RRF 无参排名融合 + ripgrep 精确匹配；<br>3. AST 符号级切片（函数/类），提供坐标精准切片；<br>4. Local-First 纯端侧 0 显存依赖，万行仓库 30s 极速建库；<br>5. 工具调用减少 50%，Token 减半。 | 彻底终结代码符号盲搜，纯本地 32MB 模型 0 显存，工具调用减半，Token 减 50% | `P0` | `v1.5.08` | ⏳ 待排期 |
| **Card-Memory-LifecycleFSM** | **记忆版本状态机 (active/disputed/superseded) 与冲突挂链降权机制** | 1. 吸收《LLM Wiki 长文》与腾讯自进化飞轮真核：“我们已经会编译经验，但还不会给记忆写状态机”；<br>2. 记忆 Schema 引入一等公民状态：status: active | disputed | superseded 与 superseded_by 演进指针；<br>3. 写入侧冲突检测：新经验推翻旧经验时自动挂链标记 superseded，禁止静默并存误导；<br>4. 检索侧物理降权 (Demotion)：superseded / disputed 状态条目默认大幅降权或过滤，优先返回最新有效经验；<br>5. Studio 大盘与记忆抽屉直观展示被取代条目划线状态与演进血缘链。 | 彻底根除“旧错误经验比新经验得分更高导致 Agent 被误导”的致命缺陷，单测全绿 | `P1` | `v1.5.09` | ⏳ 待排期 |
| **Card-Context-ActiveNotesAndHistory** | **Codex 级主动上下文治理（Notes 高密活跃状态 + History 独立检索分仓，切除有损 Compaction）** | 1. 吸收 DeepEvolution 对 Codex 最新架构解密 (PR #39827)：废除有损全局 Compaction 摘要（多次压缩导致路径、错误码、中间未完成状态严重失真）；<br>2. 状态与历史双轨分仓：Notes 存高密度结构化核心事实常驻上下文，History 存原始对话流移出上下文独立分仓；<br>3. 主动调阅工具：模型按需调用 list_history_windows / search_history 检索历史；<br>4. 阻断长会话上下文失忆与信息衰减。 | 切除有损压缩，关键路径/报错信息零失真，长程多轮会话状态持久保真 | `P1` | `v1.5.10` | ⏳ 待排期 |
| **Card-Extraction-ZeroThinking-BisectionHeal** | **记忆提取零思考硬开关、Token 截断二分切片自愈与条数/字数双门禁体系** | 1. 吸收《无银三百两》提取检修实战：根治提取长对话时 171 次调用 97 次空返回、耗时 2.5 小时的死锁绝症；<br>2. 记忆提取强制关闭 Thinking 思考（enable_thinking=False），切除思考对正文 max_tokens 预算的挤占，提速 10~20 倍，Token 消耗降 70%+；<br>3. 严格区分偶发与截断：截断物理阻断原样重试，自动触发区间二分切片并发抽取；<br>4. 消息总字数 >4000 或条数 >25 双门禁预切片；<br>5. 入库防爆安全切分。 | 提取场景零思考提速 20 倍，截断二分自愈清零空返回，字数条数双门禁防死锁 | `P0` | `v1.5.11` | ⏳ 待排期 |
| **Card-Skill-ZipOnWrite-ContractualCompression** | **阿里 SkillZip 写入即压缩引擎、六元组强类型契约与 0-Rollout 确定性重构防膨胀** | 1. 吸收阿里/浙大/杜克《SkillZip》：终结自进化技能膨胀 5.2 倍的“复读机死因”（重复代码与琐碎特例堆叠）；<br>2. 六元组强类型契约化解析（接口、工作流、协议、规则、契约、证据）；<br>3. Explain Once, Reference Everywhere：公共动作抽取为共享过程函数，公共规则提升至最小公共作用域；<br>4. 0-Rollout 确定性优化（动态规划规则放置 + 加权装箱）；<br>5. Zip-on-Write 门禁：写入即压缩，长度全程锁定种子 1.6~1.9 倍，压缩率超 30% 且基准表现持平反超。 | 技能契约化解析，0-Rollout 确定性重构，写入即压缩防膨胀复利，压缩率 30%+ | `P0` | `v1.5.12` | ⏳ 待排期 |
| **Card-Hygiene-AsymmetricDecayAndBench** | **知识卫生异步巡检 (Knowledge Hygiene)、非对称衰减与真实查询回归金标集** | 1. 吸收非对称淘汰律：“错误记忆的伤害远大于正确记忆的收益”；<br>2. 挂载轻量后台巡检 Worker：识别死重条目（零召回）、冲突簇与孤立引用，坚守奥卡姆剃刀：只输出报告与建议，绝不自动化盲目删数据；<br>3. 时效动力学与非对称衰减：对长期未命中或被标记存疑的条目降低基础检索权重；<br>4. 真实查询金标回归集 (Gold Benchmark)：从真实 find 提取 50~100 条覆盖符号、报错、规则的测试集，固定上下文 Token 预算，作为检索算法/模型升级的不可逾越门禁。 | 知识库死重与冲突可视可控，模型/检索演进具备固定物理标尺，告别盲飞调参 | `P1` | `v1.5.13` | ⏳ 待排期 |
| **Card-Evolve-HermesEvolveLoop-Patch** | **Hermes 级经历与能力解耦存储、Periodic Nudges 异步副进程复盘与 Patch 级技能微补丁自进化机制** | 1. 吸收 DeepEvolution《Hermes Agent Evolve Loop》与全景导论：实现经历（SessionDB）与能力（Skill/Memory）严格物理分层；<br>2. 跨会话 FTS5 真实消息检索（拒绝虚假 LLM 摘要）；<br>3. Periodic Nudges 异步副进程复盘：主任务完成后异步派发轻量工兵模型复盘轨迹并提取经验，零阻塞用户交互；<br>4. Patch 优先技能微手术：skill_manage 强制局部增量替换（≤30行），保留 90% 经过验证的边界逻辑，防范 Edit 模式全量重写的严重幻觉覆盖。 | 经历与能力物理分层，真实轨迹 FTS5 检索，异步副进程复盘，Patch 局部微手术防遗忘 | `P0` | `v1.5.14` | ⏳ 待排期 |
| **Card-Skill-EvaluationRetina** | **Skill 质量视网膜与自动化评测门禁体系 (Skill-as-Code & Testing CI / skill-up 规范落地)** | 1. 吸收阿里开源 skill-up 与 AI 软件测试方法论，彻底终结“改动一行提示词行为漂移、跑一遍 Demo 没报错就裸奔上线”；<br>2. 规范化测试工程结构：建立 evals/cases/（声明式 YAML 用例）、evals/fixtures/（数据脚手架）、evals/eval.yaml（引擎与断言配置）；<br>3. 落地三级判定器引擎（Exact/Regex 匹配断言、Command 脚本退出码、agent_judge LLM 语义判官）；<br>4. 首批为核心技能（cockpit-ui、diagnosing-bugs、living-asset-system）建立回归金标用例；<br>5. 接入 Git 预提交钩子与 CI 自动化回归门禁，构建 Eval-to-Evolution 自闭环。 | 核心技能 100% 具备声明式用例，三级 Judge 断言生效，改动自动跑回归阻断行为漂移 | `P0` | `v1.5.15` | ⏳ 待排期 |
| **Card-Harness-AHE-ContractualSelfEvolution** | **AHE 契约三元组自演进、Self-Harness 根因聚类与 Polar 不可伪造环境判官体系** | 1. 吸收 7 大 Harness 自演进论文（Meta-Harness/AHE/Self-Harness）、Karpathy 自动研究与 NVIDIA Polar：终结 Reward Hacking 假繁荣与表面症状打补丁冲突；<br>2. AHE 契约三元组：可证伪（Manifest 显式假设）、可归因（根因机制聚类 + 冻结面排除）、可回滚（文件级版本秒级还原）；<br>3. Self-Harness 目标模型自提议 + 双 Split 零回归门禁；<br>4. Polar 不可伪造环境判官：以真实沙箱执行退出码为唯一真理。 | 脚手架自演进契约化，根因聚类防补丁冲突，不可伪造环境判官，秒级可回滚 | `P0` | `v1.5.16` | ⏳ 待排期 |
| **Card-Skill-TrainablePolicy-RSI** | **可训练外部技能文档与昼夜双轮递归自演进架构 (Trainable Skill Document & Daytime-Nighttime RSI Engine)** | 1. 吸收翁荔 (Lilian Weng)《Harness Engineering for Self-Improvement》、AliExpress 速卖通与《AgentOPSD》：落实“如果被反复适配的对象是做事流程，流程文档本身就应该是可训练的外部策略状态 (Skill-MDP)”；<br>2. 引入 # EVOLVE-BLOCK-START/END 有界可编辑 Surface 机制，核心框架与强类型接口完全冻结，彻底杜绝“为了提分搞乱全局架构”；<br>3. 落地 AgentOPSD 长轨迹局部信用分配：Student 在无技能下完成真实 rollout，当前模型携带 Skill 作为 Self-Teacher 沿着相同轨迹计算每个 turn 的 token log-prob gap，精准识别关键 turn；<br>4. 昼夜双轮闭环：白天在确定性 Harness 下处理真实任务产生轨迹，夜间离线进行弱点聚类、局部信用分配与双 Split（Held-in / Held-out）无退化回归门禁验证，更新持久化技能。 | 技能文档外部可训练，长轨迹信用精准分配，昼夜双轮闭环，双 Split 零退化验证 | `P0` | `v1.5.17` | ⏳ 待排期 |
| **Card-Skill-CapabilityPages-NegativeBoundaryRouter** | **腾讯 Capability Pages 三段式技能档案、簇级邻居对比与 T^- 负向边界隔离路由体系** | 1. 吸收腾讯混元《Skill-Use 基准》与腾讯优图《Capability Pages》：解决装了 10+ 技能后表现断崖下跌与 SU<0.5 时用技能比不用更糟的绝症；<br>2. 提纯三段式档案结构：T^+（正向触发）、T^-（负向边界）、B（判别主体）；<br>3. 簇级邻居对比生成 T^-；<br>4. 部署隔离铁律：向量索引只存 T^+ + B + 原文，T^- 严禁入库（防语义漂移），仅专供第二阶段 Cross-Encoder / Router 裁判；<br>5. 相似技能 Top-1 区分率提升超 15%。 | 彻底终结多技能检索失明，负向边界物理隔离防向量污染，相似技能精准区分 | `P0` | `v1.5.18` | ⏳ 待排期 |
| **Card-Skill-ContrastiveDistillation** | **SKILL-KD 师生分叉决策对比蒸馏与学生重跑变绿准入门禁 (Contrastive Skill Distillation & Re-execution Gate)** | 1. 吸收浙大&北大&阿里《SKILL-KD》与北大《VeriSkill》，切除“自我反思导致的规则堆叠通胀与近亲繁殖”（38条验证规则 66.8分 击败 96条未验证反思规则 60.1分）；<br>2. 师生决策分叉提取器：从学生（本地弱模型/子代理）与老师（Claude Opus 5 / GPT-5.6 / 专家轨迹）在同题目的分叉节点提取有效差异信号；<br>3. 物理准入硬门禁（Re-execution Gate）：提炼出的候选规则 Patch 必须让学生带着在沙箱重跑原题变绿（Turn Green），断言成功才准入库；<br>4. 漂移感知规则合并（Consolidation）：自动聚类压缩重合规则，保持技能库在黄金甜点区（≤ 300 行）。 | 杜绝未经验证的反思入库，重跑变绿准入率 100%，规则库压缩保持精炼高内聚 | `P1` | `v1.5.19` | ⏳ 待排期 |
| **Card-Evolution-CICD-DreamingGate** | **Agent 七阶段 CI/CD 变更流水线、离线异步 Dreaming 模式挖掘与四级自治升降级控制层** | 1. 吸收 DeepEvolution《Agent CI/CD 流水线》与《Evolve Loop 控制层》：建立信号汇聚➔候选生成➔隔离评测➔安全门控➔灰度发布➔监控回滚➔经验沉淀七阶段管线；<br>2. 离线异步 Dreaming 模式挖掘器：每日/每周扫描长程轨迹聚类系统性缺陷与最佳工作流；<br>3. 四级自治阶梯 (Level 0-3) 与异常自动降级机制；<br>4. 人类五大不可剥夺决策权与三层防审核疲劳通道；<br>5. 监控输出长度、拒答率、重试率二阶指标防范方向漂移。 | 七阶段变更管线，离线 Dreaming 轨迹挖掘，四级自治动态升降级，二阶防方向漂移 | `P0` | `v1.5.20` | ⏳ 待排期 |

---

## 📋 三、 Milestone 3 详细任务规格卡片 (Detailed Task Card Specs: v1.5.01 ~ v1.5.20)

### 🌊 Wave 1: 运行时与脚手架地基 (Runtime & Harness Foundation)

#### 📌 [P0] [ ] Card-Runtime-TwoTierAgentLoop-OnionGuard (v1.5.01): pi 生产级双层事件循环、四层洋葱防御与中途插话/主动刹车契约 ⏳

- **类型**：Agent Runtime / Event Loop / Onion Architecture / Interrupt Handling / Tool Termination Contract ｜ **优先级**：🔥 P0（待排期实施）
- **目标版本**：`v1.5.01` ｜ **交付时间预估**：下个迭代周期 ｜ **当前状态**：⏳ 方案已终审·待排期实施
- **来源依据与核心思考推演过程 (Reasoning & Inversion Context)**：
  - **理论源头追溯**：生产级 Agent 循环 `pi/agent-loop.ts` 743 行源码精读与洋葱防御模型 (AI萝卜 2026.08.01)；
  - **芒格逆向审讯（倒推单层 Agent 循环失控与死锁的底层死因）**：
    - *死因 1（单层 while(true) 的僵化与中途失控）*：简陋 Agent 仅用单层循环，工具执行时用户完全无法插话；一旦模型进入死循环，人类按 Ctrl+C 只能暴力强杀进程，导致工作区状态和已消耗 Token 彻底丢失；
    - *死因 2（工具无法主动刹车）*：模型反复调用同一个无效工具，工具明知任务已完成或无法执行，却无法告知事件循环“请立刻终止”，只能眼睁睁看着模型跑满 max_turns；
    - *死因 3（异常无防线引发事件循环崩溃）*：工具抛出未捕获异常或模型输出非法 JSON 时，主循环直接崩溃，无法优雅返回错误信息供模型自我纠偏。
  - **奥卡姆剃刀工程解法**：
    - **双层事件循环 (Two-Tier Loop)**：
      - 外层循环：管控会话生命周期、多轮用户交互与模型动态切换 (`prepareNextTurn`)；
      - 内层循环：管控当前轮次的多工具调用与用户中途插话处理，推进条件严格为：`hasMoreToolCalls || pendingMessages.length > 0`；
    - **四层洋葱防御架构 (Four-Layer Onion Guard)**：
      1. 核心循环层（问模型 ➔ 执行工具 ➔ 喂回结果）；
      2. 模型保护层（流式输出拦截、工具输入严格 Schema 预检、错误消息格式化喂回）；
      3. 用户控制层（异步 `pendingMessages` 队列中途插话、优雅 `AbortController` 信号广播）；
      4. 调度增强层（多只读工具并发执行、`afterToolCall` 拦截改写、动态模型降级）；
    - **工具主动终止契约 (`terminate: true`)**：工具在返回 payload 中可显式声明 `terminate: true`，主循环感知后立即将 `hasMoreToolCalls` 置为 `false`，实现优雅提前收工。
- **核心治理成果与三大原子工序拆解 (Tracer-Bullet Tickets)**：
  1. **⚙️ Tracer 1: 双层事件循环推进器与 `pendingMessages` 中途插话合并器 (`TwoTierAgentLoop`)**
     - *文件*：[`openviking/core/two_tier_agent_loop.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/two_tier_agent_loop.py)；
     - *逻辑*：拆分外层轮次循环与内层工具执行循环；维护非阻塞异步输入队列，在内层循环每个 step 之间原子化消费并合并用户插话。
  2. **⚙️ Tracer 2: 四层洋葱防护切面与工具 `terminate: true` 主动退出控制器 (`OnionGuard`)**
     - *文件*：[`openviking/core/onion_guard.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/onion_guard.py)；
     - *逻辑*：注入四层拦截包装，规范工具返回结构中的 `terminate` 标志位；若为 true 立即阻断后续工具链下发并转入文本交付。
  3. **⚙️ Tracer 3: 双层循环中途插话、主动刹车与优雅中断回归套件**
     - *文件*：[`tests/test_two_tier_agent_loop.py`](file:///home/skloxo/aho/openclaw/project/tests/test_two_tier_agent_loop.py)；
     - *逻辑*：模拟工具长任务执行过程中用户发出插话指令、Abort 信号及工具自主终止，断言无崩溃、无丢失消息且状态优雅收口。
- **不可逾越的物理验收门禁 (Non-Negotiable Acceptance Gates)**：
  - **门禁 1（优雅中断零数据丢失）**：用户发出 Abort 信号时，必须在当前工具执行完毕或 500ms 内优雅挂起并持久化上下文状态，严禁进程崩溃；
  - **门禁 2（用户插话零丢失）**：内层循环执行期间收到的用户新输入，必须在下一次向模型发起请求前 100% 合并注入；
  - **门禁 3（主动刹车即刻响应）**：工具声明 `terminate: true` 后，系统在当前 Step 必须终止工具迭代并进入最终交付输出。

---

#### 📌 [P0] [ ] Card-Harness-DeepSeek-AgentScope-SpecDriven (v1.5.02): DeepSeek-Harness 极简规范外壳、AgentScope Java 2.0 生产级运行时与企业级四不变式 ⏳

- **类型**：Agent Harness / Runtime Invariants / Workspace Decoupling / State Protection / Multi-Tenant Isolation ｜ **优先级**：🔥 P0（待排期实施）
- **目标版本**：`v1.5.02` ｜ **交付时间预估**：下个迭代周期 ｜ **当前状态**：⏳ 方案已终审·待排期实施
- **来源依据与核心思考推演过程 (Reasoning & Inversion Context)**：
  - **理论源头追溯**：
    1. DeepSeek 官方开源《deepseek-harness：围绕模型构建生产级代理外壳与最小循环》(2026.08)；
    2. 阿里云云原生《AgentScope Java 2.0 GA：基于 ReAct 推理内核构建企业级 Harness 外壳》(2026.07)；
    3. 七牛开发者《2026 上半年智能体脚手架 (Harness) 自演进综述与失效模式分析》(2026.07)；
    4. 6 曦轩《大模型格式崩溃与确定性防御策略》(2026.07)；
  - **芒格逆向审讯（倒推 Agent Harness 生产失控的三大致命死因）**：
    - *死因 1 (缺乏轮次、成本与沙盒边界导致失控逃逸)*：将 Harness 误当成纯 Prompt 调优，底层缺少 `max_turns` / `cost_limit` 物理硬卡，模型进入无限自循环吞噬 Token；工具执行未限定 `sandbox_root`，导致越权触碰宿主机敏感文件；
    - *死因 2 (工具报错无分类捕获引发同一错误死循环)*：工具执行失败、参数校验不通过时直接裸报错抛给模型，模型缺少重试策略与结构化摘要，陷入反复调用同一工具同一参数的崩溃循环；
    - *死因 3 (无保护全局压缩洗掉关键业务状态)*：长会话达到上下文窗口阈值时粗暴做全局摘要或截断，将最关键的“前置任务规划 (Plan)”、“异步子 Agent 追踪任务状态”以及“敏感工具授权记录”物理冲刷丢失，导致模型行为严重漂移。
  - **奥卡姆剃刀工程解法**：
    - **生产级 Harness 四大不变式 (The 4 Invariants)**：
      1. **可终止 (Terminable)**：显式注入 `max_turns`、`cost_limit`、超时熔断与中途优雅中断信号；
      2. **可隔离 (Isolated)**：限定 `sandbox_root`，工具读写与命令执行 100% 限制在容器或工作目录沙盒内；
      3. **可恢复 (Recoverable)**：工具失败分类捕获并生成错误摘要；上下文压缩强制启用白名单保护；
      4. **可观测 (Observable)**：单次调用、工具输入输出、Token 消耗全链路追踪可回放；
    - **Workspace 抽象文件系统 (Abstract File System)**：将静态资产（`AGENTS.md` / `SKILL.md` / 子代理定义）与运行时数据（Session / `MEMORY.md` / 临时文件）严格解耦，支持物理磁盘与分布式对象存储平滑切换；
    - **物理免压缩白名单 (Uncompressible State Whitelist)**：长任务规划详情、异步子 Agent 句柄、安全权限授权记录在上下文压缩时物理保留，严禁被摘要模型吞噬。
- **核心治理成果与四大原子工序拆解 (Tracer-Bullet Tickets)**：
  1. **⚙️ Tracer 1: Harness 生产级运行循环与四不变式状态机 (`AgentHarnessLoop`)**
     - *文件*：[`openviking/core/agent_harness_loop.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/agent_harness_loop.py)；
     - *逻辑*：实现标准循环：状态装配 ➔ 上下文边界校验 ➔ 模型推理 ➔ 工具路由 ➔ 状态更新；内置 `max_turns`、`cost_limit` 与 `tool_timeout` 刚性约束，一旦超限立即触发确定性退出与优雅收敛。
  2. **⚙️ Tracer 2: Workspace 抽象文件系统与多租户隔离层 (`WorkspaceFS`)**
     - *文件*：[`openviking/core/workspace_fs.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/workspace_fs.py)；
     - *逻辑*：提供统一文件操作接口，显式区分镜像级静态只读资产与用户会话级动态读写空间；支持单机目录沙盒与多租户 `RuntimeContext(user_id, session_id)` 物理隔离。
  3. **⚙️ Tracer 3: 核心状态免压缩白名单与 Flush 记忆分拣器 (`ContextFlushGovernor`)**
     - *文件*：[`openviking/core/context_flush_governor.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/context_flush_governor.py)；
     - *逻辑*：在触发上下文压缩（如消耗达到窗口 75%）时，自动将 Plan 规划树、未决异步子任务句柄和权限授权记录提升至保护区；普通对话历史做分拣与关键信息提取，大工具输出落盘为文件句柄 `file_ref` 替代全文。
  4. **⚙️ Tracer 4: 运行时不变式与异常诱捕测试套件**
     - *文件*：[`tests/test_harness_runtime_invariants.py`](file:///home/skloxo/aho/openclaw/project/tests/test_harness_runtime_invariants.py)；
     - *逻辑*：覆盖无限循环截断、沙盒越界读写拦截、工具连续报错优雅自愈、规划白名单免压缩等 15 组端到端硬核断言。
- **不可逾越的物理验收门禁 (Non-Negotiable Acceptance Gates)**：
  - **门禁 1（刚性终止门禁）**：人为构造死循环任务，Harness 必须在严格达到 `max_turns` 或 `cost_limit` 阈值时 100% 强行终止，退出码非零但输出安全摘要；
  - **门禁 2（沙盒越界拦截率 100%）**：任何尝试通过 `../` 或绝对路径突破 `sandbox_root` 的工具调用必须被物理阻断；
  - **门禁 3（核心状态零丢失）**：经过多轮压缩（上下文缩小 60% 以上）后，任务规划树与进行中子任务状态键值完整度必须保持 100%。

#### 📌 [P0] [ ] Card-Harness-ReadWriteOffload-HookGuard (v1.5.03): 腾讯 DECO 级读写两侧 Offload 护栏与 Hook 切面长文本防偷懒/防越权体系 ⏳
- **类型**：Guardrails / Hook Architecture / Read-Write Offload / HITL Circuit Breaker ｜ **优先级**：🔥 P0（待排期实施）
- **目标版本**：`v1.5.03` ｜ **交付时间预估**：下个迭代周期 ｜ **当前状态**：⏳ 方案已终审·待排期实施
- **来源依据与核心思考推演过程 (Reasoning & Inversion Context)**：
  - **理论源头追溯**：
    1. 腾讯技术工程《DECO 生产级数仓 Agent 引擎护栏层实践：Hook 切面拦截长文本偷懒与越权》(2026.07)；
    2. 大鱼北游《自进化三部曲：验证器会被什么毁掉》(2026.09)；
  - **芒格逆向审讯（倒推生产级长文本 Agent 的三大绝症）**：
    - *绝症 1（生成偷懒）*：处理 1000+ 行大文件（SQL、核心代码）时，LLM 物理超出 Token 预算或为了图省事，中间跳过大段逻辑写句 `/* 省略若干行 */`，随后若无其事继续，导致产物残缺破坏生产环境；
    - *绝症 2（擅自越权）*：Agent 在需求理解或方案设计阶段，未经用户确认，径直调用发布工具把半成品推向生产；
    - *绝症 3（Prompt 失效）*：在 Prompt 里写上千字“⚠️ 绝对严禁省略、绝对禁止越权”，模型依然选择性忽略——因为长文本是物理预算问题，越权是状态机脱节问题，Prompt 根本管不住。
  - **奥卡姆剃刀解法（解耦基础设施与 ReAct 推理）**：
    - **Hook 切面层解耦**：围绕模型调用与工具调用建立前后回调切面，独立于 ReAct 循环；
    - **读写两侧 Offload**：LLM 永远不直接接触脚本全文！读截断：Hook 拦截后写入沙箱只读快照（`/mnt/chat-offload/`），LLM 上下文只留引用句柄 `file_ref` 与只读路径；写截断：强制使用 `copy_file` + `str_replace` 小步增量打补丁，严禁全量重写；
    - **危险操作 HITL 门禁**：状态机检查当前阶段，未确认前物理阻断发布工具。
- **核心治理成果与三大原子工序拆解 (Tracer-Bullet Tickets)**：
  1. **⚙️ Tracer 1: 读写两侧 Offload 沙箱引擎与引用句柄协议**
     - *文件*：[`openviking/core/offload_sandbox.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/offload_sandbox.py)；
     - *逻辑*：建立只读快照区与可编辑工作副本区；当工具返回大文本（>300 行或 >4KB）时，Hook 自动拦截并存盘，替换为引用句柄下发给 Agent；Agent 仅需持句柄按需查看局部切片。
  2. **⚙️ Tracer 2: Hook 切面长文本截断与 str_replace 局部增量补丁校验器**
     - *文件*：[`openviking/core/hook_guard_patch.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/hook_guard_patch.py)；
     - *逻辑*：写操作强制阻断大文件全量重写；强制 Agent 使用精确的字符串查找替换（Target ➔ Replacement），写入前自动执行静态语法与 AST 完整性校验，出现省略符号（如 `...`、`省略若干`）直接物理阻断。
  3. **⚙️ Tracer 3: 危险操作 HITL 阶段状态拦截与物理断路器**
     - *文件*：[`openviking/core/hitl_circuit_breaker.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/hitl_circuit_breaker.py)；
     - *逻辑*：标记危险工具（发布、删除、改生产配置）；Hook 拦截到调用时，核验任务状态机是否处于已审批状态（Approved）；未审批时直接拦截并弹出人机协同确认，从机制上杜绝自作主张。
- **不可逾越的物理验收门禁 (Non-Negotiable Acceptance Gates)**：
  - **门禁 1（残缺省略 0 容忍）**：输出产物包含省略注释或代码残缺时，写入工具退出码非 0 并拒绝落盘；
  - **门禁 2（大文件 Context 占用压缩 80%+）**：1200 行脚本在上下文中的 Token 占用从 8000+ 骤降至 150 Token 以内；
  - **门禁 3（越权拦截率 100%）**：未获得确认指令前，危险工具调用 100% 被断路器拦截。

#### 📌 [P1] [ ] Card-Harness-SpecDrivenFSM (v1.5.04): 第三代数仓级多智能体 Harness 架构（Spec 结构化文件驱动 + 协调者专家分离 + 12 状态有限状态机） ⏳
- **类型**：Multi-Agent Architecture / Spec-Driven Bus / Orchestration / Finite State Machine ｜ **优先级**：⚡ P1（待排期实施）
- **目标版本**：`v1.5.04` ｜ **交付时间预估**：下个迭代周期 ｜ **当前状态**：⏳ 方案已终审·待排期实施
- **来源依据与核心思考推演过程 (Reasoning & Inversion Context)**：
  - **理论源头追溯**：阿里千问/数仓团队《一、为什么需要Harness》(2026.07) + 阿里 Qwen《Skill-SP》(2026.07) + 浮之静《pnpm 12.4 Pipeline DAG》(2026.09)；
  - **芒格逆向审讯（倒推多智能体系统的死因）**：
    - *死因 1*：全能 Agent 独角戏导致中间状态无法追溯，协调者亲自下场写代码导致分工体系瞬间崩塌；
    - *死因 2*：Agent 之间靠对话历史传递上游产出，多轮之后把上下文窗口塞满草稿废话，导致下游决策被严重污染；
    - *死因 3*：生成者既当运动员又当裁判，自满自恋导致低级缺陷被包装成“已完成”交付。
  - **奥卡姆剃刀工程解法**：采用 `Orchestrator + Specialist` 分离、Spec 结构化文件总线与 12 状态有限状态机。
- **核心治理成果与四大原子工序拆解 (Tracer-Bullet Tickets)**：
  1. **⚙️ Tracer 1: Spec 结构化文件总线与 CP 检查点摘要压缩器**
     - *文件*：[`openviking/core/spec_bus.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/spec_bus.py)；
     - *逻辑*：全盘封杀跨阶段直接传递长对话历史！Agent 间协作统一通过预定义 Schema 的 Spec 结构化文件（`task_spec.json`, `plan_spec.md`, `code_diff.patch`）传递路径；每个阶段结束时，强制将上下文压缩为一段固定格式的 CP (Checkpoint) 检查点摘要（`结论 | 传递给下游的关键信息 | 待关注事项`），保持下游窗口绝对纯净。
  2. **⚙️ Tracer 2: 协调者不写代码与独立 Evaluator 质检门禁守卫**
     - *文件*：[`openviking/core/orchestrator_guard.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/orchestrator_guard.py)；
     - *逻辑*：强制约束协调者（Orchestrator）仅拥有 6 个显式身份（调度员、澄清员、审查员、门禁员、汇报员、重试员），严禁调用文件写工具直接产出业务代码；写代码和评审质量必须是两个独立 Agent（Generator != Evaluator），质检员依据显式 Checklist 逐项核验。
  3. **⚙️ Tracer 3: 12 状态有限状态机与故障三分法断点续接引擎**
     - *文件*：[`openviking/core/task_fsm.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/task_fsm.py)；
     - *逻辑*：定义标准 12 状态生命周期（从需求接收、拆解、澄清、方案设计、编码、测试到终态）；故障严格三分：
       - ① 可重试（工具超时或临时异常，自动重试 1~2 次）；
       - ② 需回退（门禁检查不通过，回退到上一个稳定 Spec 检查点重新调用专家重新生成）；
       - ③ 必须中止（需求理解根本性偏差，主动坦诚叫停并呼叫人工）。
       任何时刻中断，系统直接根据状态文件与 Spec 文件在几秒内实现断点续接，无需重跑已完成工序。
  4. **⚙️ Tracer 4: Monorepo 显式 Pipeline DAG 任务图集成**
     - *文件*：[`scripts/pipeline_runner.py`](file:///home/skloxo/aho/openclaw/project/scripts/pipeline_runner.py)；
     - *逻辑*：吸收 pnpm 12.4 pipeline 理念，为混合语言项目输出显式任务 DAG 图；Agent 执行前直接读取任务图获取执行与测试依赖顺序，严禁从零散脚本中猜测，提升自动化执行确定性。
- **不可逾越的物理验收门禁 (Non-Negotiable Acceptance Gates)**：
  - **门禁 1（会话零污染）**：阶段间仅允许传递 Spec 路径与 CP 摘要，跨阶段对话历史泄露率严格为 0；
  - **门禁 2（质检物理解耦）**：生成 Agent 与评审 Agent 必须具有不同的独立 Session 与 Prompt 边界，严禁自评自核；
  - **门禁 3（断点秒级恢复）**：模拟任务中断，恢复执行耗时 $\le 3$ 秒且 100% 还原至中断前稳定检查点。

### 🌊 Wave 2: 零幻觉混合检索与知识拓扑 (Zero-Hallucination Retrieval & Knowledge Topology)

#### 📌 [P0] [ ] Card-Retrieval-BM25Hybrid (v1.5.05): SQLite FTS5 词法与稠密向量双路混合检索与 RRF 融合 (BM25 Hybrid Retrieval) ⏳
- **类型**：Information Retrieval / Hybrid Search / Sparse-Dense Fusion / SQLite FTS5 ｜ **优先级**：🔥 P0（待排期实施）
- **目标版本**：`v1.5.05` ｜ **来源依据**：A2 《BM25 Wins at Scale》(arXiv:2607.26497) + A6/A8 生产混检红蓝净启发
- **核心治理成果与交付目标**：
  1. **直击物理盲区与第一性原理**：
     - 当前 OpenViking 采用纯稠密向量检索 (`qwen3-vl-emb` @ 11432) + 重排 (`qwen3-vl-rer` @ 11433)；
     - 稠密向量擅长概括性语义，但对于 Agent 最常检索的代码符号、文件名/路径（如 `satellite_mcp_server.py`）、端口号（`1933`、`11432`）、报错指纹（`UnicodeEncodeError`）存在天然的表征丢失与粗排漏召回；
     - 论文已实证：随着语料增长，词法检索（BM25）具备低成本与精确匹配的显著优势，二者互为不可替代的补集。
  2. **零外部重量级依赖的 SQLite FTS5 词法路**：
     - 坚决贯彻奥卡姆剃刀，拒绝引入 Elasticsearch、Meilisearch 等外部臃肿组件；
     - 在现有 SQLite 数据库中启用原生的 `fts5` 全文检索引擎，以零外部依赖、极低内存开销建立轻量级倒排索引；
     - 同步对写入的 lessons、skills、resources 标题与正文建立分词倒排记录。
  3. **双路并行召回与无参 RRF 融合 (Reciprocal Rank Fusion)**：
     - 检索入口 `find` / `search` 同时发起 Dense 向量召回 (Top-K_dense) 与 FTS5 BM25 词法召回 (Top-K_sparse)；
     - 使用无超参数调优风险的经典 RRF 算法合并排序：$RRF\_Score(d) = \frac{1}{60 + rank_{dense}(d)} + \frac{1}{60 + rank_{sparse}(d)}$；
     - 严格遵守 FAST 模式契约：融合去重后的优质候选（如 Top-12）统一下发给单次 Cross-Encoder Reranker 精排打分，RER 计算开销保持不变。
  4. **精确符号检索测试套件**：
     - 编写包含代码变量、路径、端口、报错信息的 20 组端到端单元测试，断言混合检索下精确匹配召回率达到 100%。

#### 📌 [P0] [ ] Card-RAG-Abstention-ZeroHallucination-Pipeline (v1.5.06): 千万级语料 RAG 约束验证与弃答门禁流水线、RARG 语义引导相关性搜索与 MinHash 去重 ⏳

- **类型**：Industrial RAG / Zero Hallucination / Abstention Gate / MinHash LSH / RARG Corpus Interaction ｜ **优先级**：🔥 P0（待排期实施）
- **目标版本**：`v1.5.06` ｜ **交付时间预估**：下个迭代周期 ｜ **当前状态**：⏳ 方案已终审·待排期实施
- **来源依据与核心思考推演过程 (Reasoning & Inversion Context)**：
  - **理论源头追溯**：
    1. 深度记事《Handling 10M+ docs using RAG with zero hallucinations: 检索、约束、验证与弃答流水线》(2026.06)；
    2. 腾讯与中科院信工所《RARG: A New Role for Relevance: Guiding Corpus Interaction in Agentic Search》(arXiv:2607.24223, 2026.08)；
    3. AI 大模型观察站《千万级工业 RAG 幻觉压制全景流水线与工程避坑指南》(2026.08)；
    4. LLM 大模型 Seven《RAG 文档进 Index 前的工程治理：从分词清洗到近重复去重》(2026.08)；
  - **芒格逆向审讯（倒推海量语料 RAG 幻觉与失效的底层死因）**：
    - *死因 1 (规模越大幻觉呈指数级上升与模型默认猜测倾向)*：语料达到千万级时，任何问题都能搜出看似相关的片段；如果关键证据缺失，生成模型天生倾向于“流畅地胡编乱造”，而不会主动保持沉默；
    - *死因 2 (无序模式匹配淹没可见窗口)*：直接用 `rg` 搜索关键词产生海量匹配结果，关键证据排在截断线之外，Agent 耗尽轮次无法收敛；
    - *死因 3 (近重复段落霸榜导致虚假高召回)*：同一份制度、通知或代码的三份拷贝霸占了检索 Top-5，模型误以为证据确凿，实际上多来源印证为零，严重挤占有效上下文。
  - **奥卡姆剃刀工程解法**：
    - **“当证据缺失时，唯一安全的失败方式是弃答 (Abstention First)”**：与其训练模型变得更聪明，不如构建确定性的外层判官系统，在置信度不足时硬性阻断生成并主动弃答；
    - **入库前两重过滤**：NFKC 规范化分词（消除空白与连字对 BM25 破坏） + MinHash LSH 近重复去重（近似线性复杂度，剔除冗余拷贝）；
    - **RARG 语义引导范围搜索 (Search Scope Order)**：
      - 语义嵌入模型 (`embed_recall`) 先给候选文档排序，生成 `/tmp/scope_N.txt`；
      - 终端单线程按序扫描：`cat /tmp/scope_N.txt | xargs -d '\n' rg -j1 "PATTERN"`，优先扫最相关文档；
      - 提取前序 10 段起步锚点（Seed Clues）+ 局部重排（Local Re-rank 500 选 30），将工具调用收敛轮次压缩 70%；
    - **两阶段约束验证与弃答门禁 (Abstention Gate)**：
      - 句子级强制引用断言；
      - 独立 Verifier 模型打支持度分数（Support Score），低于阈值（如 0.35）强制拒答，压制幻觉至接近 0。
- **核心治理成果与四大原子工序拆解 (Tracer-Bullet Tickets)**：
  1. **⚙️ Tracer 1: NFKC 文本标准化与 MinHash LSH 近重复去重清洗器 (`CorpusDeduplicator`)**
     - *文件*：[`openviking/core/corpus_deduplicator.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/corpus_deduplicator.py)；
     - *逻辑*：入库前执行 Unicode NFKC 正则标准化，折叠多余空白；采用 MinHash LSH 算法在 $O(N)$ 复杂度下识别 Jaccard 相似度 $> 0.85$ 的冗余段落并打标去重，防止重复内容挤占向量空间。
  2. **⚙️ Tracer 2: RARG 语义引导顺序检索与局部匹配重排器 (`RARGCorpusSearcher`)**
     - *文件*：[`openviking/core/rarg_searcher.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/rarg_searcher.py)；
     - *逻辑*：实现 `embed_recall` 候选范围构建器；向 Agent 暴露带顺序优先级的 `rg -j1` 管道与初始 10 段种子线索，提供局部 Cross-Encoder 重排将大结果集压缩至 Top-30 高确定性片段。
  3. **⚙️ Tracer 3: 句子级证据引用提取与 Verifier 独立判官 (`CitationVerifier`)**
     - *文件*：[`openviking/core/citation_verifier.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/citation_verifier.py)；
     - *逻辑*：约束生成输出必须带有 `[doc_id:sentence_id]` 实体标注；提取每一句结论并由独立轻量 Verifier 模型比对证据段落，计算每句 Support Score。
  4. **⚙️ Tracer 4: 主动弃答门禁 (Abstention Gate) 与零幻觉基准测试套件**
     - *文件*：[`openviking/core/abstention_gate.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/abstention_gate.py) 与 [`tests/test_rag_abstention_zero_hallucination.py`](file:///home/skloxo/aho/openclaw/project/tests/test_rag_abstention_zero_hallucination.py)；
     - *逻辑*：全句支持度均值 $< 0.35$ 或存在关键事实冲突时，强制重写响应为自解释拒答；在包含不可回答问题与反事实伪问题的测试集上断言幻觉率严格为 0。
- **不可逾越的物理验收门禁 (Non-Negotiable Acceptance Gates)**：
  - **门禁 1（不可回答问题 100% 弃答）**：在注入的 50 道无支持证据的恶意伪问题测试集上，系统必须 100% 触发弃答门禁，杜绝任何臆造；
  - **门禁 2（去重处理吞吐量）**：MinHash LSH 在万级段落上的去重计算耗时 $\le 2$ 秒，近重复识别准确率 $\ge 95\%$；
  - **门禁 3（RARG 搜索收敛步数压缩）**：在多跳复杂检索任务中，RARG 范围引导相比传统盲目 `rg` 减少工具调用轮次 50% 以上。

#### 📌 [P0] [ ] Card-Knowledge-HG-RAG-HierarchicalCompass (v1.5.07): HG-RAG 分层指南针拓扑检索、Karpathy LLM Wiki 与 WeKnora 读写分离知识工程 ⏳

- **类型**：Knowledge Architecture / HG-RAG / Walkable Knowledge Graph / Read-Write Decoupling / Overlay Engineering ｜ **优先级**：🔥 P0（待排期实施）
- **目标版本**：`v1.5.07` ｜ **交付时间预估**：下个迭代周期 ｜ **当前状态**：⏳ 方案已终审·待排期实施
- **来源依据与核心思考推演过程 (Reasoning & Inversion Context)**：
  - **理论源头追溯**：
    1. PaperAGI《HG-RAG: Hierarchical Graph RAG 与分层指南针拓扑遍历》(2026.07)；
    2. 大卫数智话《Karpathy LLM Wiki 与结构化可漫游知识空间实践》(2026.08)；
    3. 翻斗花园二蛋《WeKnora 知识库工程实战：从分层解析、结构化主数据到编辑/服务分离》(2026.06)；
    4. 翻斗花园二蛋《Graph Engineering: 企业级知识图谱落地深水区踩坑总结》(2026.08)；
  - **芒格逆向审讯（倒推复杂知识库与图谱工程的深层死因）**：
    - *死因 1 (分块丢失父级层级与主数据语义断层)*：处理 Excel 合并单元格、分类编码表或多级章节时，简单平铺分块导致叶子数据丢失顶层大类；模型面对“末级条目属于哪个分类”时因为 chunk 缺少上级路径而严重失明；
    - *死因 2 (重型计算拖垮生产机器与读写耦合)*：在公网生产服务机上直接运行 OCR、多版面 PDF 解析（如 MinerU）和图计算，导致生产磁盘暴涨撑爆、内存打满，服务响应雪崩；
    - *死因 3 (为了图而建图的孤岛过度工程)*：盲目引入外部重型图数据库（如 Neo4j），形成昂贵的运维黑洞，且与底层向量检索缺乏有机拓扑联系。
  - **奥卡姆剃刀工程解法**：
    - **HG-RAG 分层指南针 (Hierarchical Compass)**：
      - 建立双向父子关联图谱：Root ➔ Chapter / Category ➔ Section ➔ Leaf Passage；
      - 结构化主数据表（Excel 合并单元格）解析自动向上回填大类路径，产出自洽的“全路径语义 Chunk”；
      - Agent 可沿图谱关系进行单跳/多跳 Walkable 漫游；
    - **编辑台与服务台物理分离 (Read/Write Decoupling)**：
      - 所有知识录入、重型多引擎解析（PyMuPDF / MinerU / OCR）与图谱拓扑构建统一收口在离线编辑台；
      - 通过 CI/CD 按文档粒度增量推送只读快照至生产服务台；生产服务台仅承载极速向量与词法检索，数据物理只读；
    - **零分叉覆盖层升级哲学 (Overlay Engineering SSOT)**：
      - 遵循“同名替换 > 新增组件 > 样式变量覆盖 > 幂等锚点补丁”四级梯队；
      - 补丁强制附带 `marker`（存在即跳过）与 `anchor`（失配立即抛错），确保上游开源基座更新时无缝合并。
- **核心治理成果与四大原子工序拆解 (Tracer-Bullet Tickets)**：
  1. **⚙️ Tracer 1: 结构化主数据表全路径回填解析器 (`StructuredTableReader`)**
     - *文件*：[`openviking/core/structured_table_reader.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/structured_table_reader.py)；
     - *逻辑*：针对包含合并单元格的多级表头 Excel，在解析为 Chunk 时，自动向前回溯顶层大类与父级路径，生成形如 `[大类 > 中类 > 属性]: 值` 的自洽扁平化 Chunk，确保上下文语义完整。
  2. **⚙️ Tracer 2: HG-RAG 分层指南针索引拓扑与可漫游图谱 (`HierarchicalCompassIndex`)**
     - *文件*：[`openviking/core/hierarchical_compass_index.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/hierarchical_compass_index.py)；
     - *逻辑*：在 SQLite 关系表中以极轻量拓扑记录文档、章节与段落的父子指针与跨文档实体边；提供 `walk_parents` 与 `walk_children` 工具供 Agent 在定位到具体叶子时向上获取宏观背景或向下遍历细则。
  3. **⚙️ Tracer 3: 知识库编辑台与服务台增量同步流水线 (`KnowledgeSyncPipeline`)**
     - *文件*：[`openviking/core/knowledge_sync_pipeline.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/knowledge_sync_pipeline.py)；
     - *逻辑*：实现文档级增量打包与快照校验；编辑台构建完成发布事件，生产端拉取增量 SQLite/VikingDB 分片，实现生产节点 100% 只读与极低资源开销。
  4. **⚙️ Tracer 4: 分层漫游、主数据路径还原与读写解耦测试套件**
     - *文件*：[`tests/test_hierarchical_compass_knowledge.py`](file:///home/skloxo/aho/openclaw/project/tests/test_hierarchical_compass_knowledge.py)；
     - *逻辑*：构建多层级合同与合并单元格 Excel 测试用例，验证父路径回填准确率 100%，跨层级多跳问答准确率提升 25% 以上。
- **不可逾越的物理验收门禁 (Non-Negotiable Acceptance Gates)**：
  - **门禁 1（多级表头路径零丢失）**：处理合并单元格数据时，末级 Chunk 的父级分类全路径覆盖率必须达到 100%；
  - **门禁 2（服务台物理只读隔离）**：服务台节点严禁运行重型 OCR 与复杂解析进程，磁盘占用增长率严格收敛至仅由对话历史日志驱动；
  - **门禁 3（多跳漫游检索准确率）**：在层级跨章节推理基准集上，分层指南针辅助检索比普通平铺切片问答准确率提升 $\ge 20\%$。

---

#### 📌 [P0] [ ] Card-Retrieval-LocalFirst-zgSemanticSearch (v1.5.08): 阿里 zg 级端侧本地命令行语义搜索、四重奏融合与代码符号防盲搜护栏 ⏳

- **类型**：Local-First Retrieval / Semantic Code Search / Zvec-Grep / Walkable Knowledge Graph / MCP Integration ｜ **优先级**：🔥 P0（待排期实施）
- **目标版本**：`v1.5.08` ｜ **交付时间预估**：下个迭代周期 ｜ **当前状态**：⏳ 方案已终审·待排期实施
- **来源依据与核心思考推演过程 (Reasoning & Inversion Context)**：
  - **理论源头追溯**：
    1. 阿里 Qwen & Zvec 团队《zg (zvec-grep) 开源：从字面到语义的本地命令行搜索时代》(2026.09.03)；
    2. Neo4j 官方技术报告《Scaling Karpathy’s LLM Wiki: Why Your Knowledge Base Needs a Graph》(2026.09.08)；
  - **芒格逆向审讯（倒推 Agent 代码盲搜与上下文撑爆的底层死因）**：
    - *死因 1（自然语言与代码符号脱节）*：用户说“恢复主题偏好”，代码里写着 `hydratePreferences()`。Agent 在终端用 `ripgrep` 猜函数名盲搜失败几十次，随后放宽条件拉回上百个文件生吞进上下文，Token 狂飙、上下文撑爆诱发幻觉；
    - *死因 2（重型云端向量库的显存与私有数据泄露负担）*：代码检索动辄要求部署服务端向量数据库、Docker 容器或占用数 GB GPU 显存，本地轻量节点无法承载；
    - *死因 3（孤岛碎片无拓扑联系）*：单纯片段向量检索无法表达代码调用与依赖关系，当底层接口修改时，Agent 无法感知下游连锁影响。
  - **奥卡姆剃刀工程解法**：
    - **端侧本地四重奏检索架构 (zg 架构吸收)**：
      1. 向量检索：采用 32MB 超轻静态模型 `potion-code-16m-v2`，纯 CPU 推理，零显存占用，本地离线极速运行；
      2. BM25 词频检索：兜底专业名词与特定标识符精确匹配；
      3. RRF 混合融合（Reciprocal Rank Fusion）：无超参数调优，自动整合语义与词频候选；
      4. ripgrep 精确匹配：线索明确时直接毫秒级定位；
    - **AST 符号级切片**：按函数、类、结构体切分为独立寻址单元，返回代码坐标与精炼切片，阻断全文件暴击；
    - **可行走知识拓扑 (Walkable Graph)**：利用 Markdown 引用链接与代码导入关系维护本地拓扑图，支持依赖遍历与连锁失效分析。
- **核心治理成果与三大原子工序拆解 (Tracer-Bullet Tickets)**：
  1. **⚙️ Tracer 1: 端侧超轻嵌入向量引擎与 AST 符号切片器 (`ZgLocalEngine`)**
     - *文件*：[`openviking/core/zg_local_engine.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/zg_local_engine.py)；
     - *逻辑*：接入 32MB 端侧代码 Embedding 模型，实现本地文件 AST 语法树函数/类切片与向量索引构建，万行代码建库 $\le 30$ 秒。
  2. **⚙️ Tracer 2: 四重奏多路召回与 RRF 融合重排器 (`RRFHybridRanker`)**
     - *文件*：[`openviking/core/rrf_hybrid_ranker.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/rrf_hybrid_ranker.py)；
     - *逻辑*：聚合 Vector 候选与 BM25 词频结果，应用 RRF 公式融合重排；当精确关键词命中时自动联动 ripgrep 返回代码坐标与精炼片段。
  3. **⚙️ Tracer 3: 语义代码寻源防盲搜与 Token 减半测试套件**
     - *文件*：[`tests/test_zg_semantic_code_search.py`](file:///home/skloxo/aho/openclaw/project/tests/test_zg_semantic_code_search.py)；
     - *逻辑*：设计 30 组“自然语言意图 vs 异构符号命名”的寻源用例，断言 Agent 工具调用轮次减少 $\ge 50\%$，上下文 Token 减少 $\ge 40\%$。
- **不可逾越的物理验收门禁 (Non-Negotiable Acceptance Gates)**：
  - **门禁 1（纯本地 CPU 极速运行）**：建库与检索 100% 在本地 CPU 完成，GPU 显存占用严格为 0MB，万行仓库建库耗时 $\le 30$ 秒；
  - **门禁 2（盲搜轮次与 Token 消耗减半）**：模糊意图代码寻源测试集中，Agent 工具调用次数与输入 Token 下降 $\ge 45\%$；
  - **门禁 3（零外部服务依赖）**：嵌入式单机文件型索引，严禁启动外部 Docker 或独立数据库守护进程。

---

### 🌊 Wave 3: 上下文保真与记忆卫生 (Context Fidelity & Memory Hygiene)

#### 📌 [P1] [ ] Card-Memory-LifecycleFSM (v1.5.09): 记忆版本状态机 (active/disputed/superseded) 与冲突挂链降权机制 ⏳
- **类型**：Memory Governance / State Machine / Knowledge Evolution / Demotion Engine ｜ **优先级**：⚡ P1（待排期实施）
- **目标版本**：`v1.5.09` ｜ **来源依据**：A1 《LLM Wiki 长文》H1 冲突取代状态机 + A5 腾讯飞轮记忆治理
- **核心治理成果与交付目标**：
  1. **记忆状态机一等公民化 (State Machine First)**：
     - 彻底切除“只追加覆盖、无状态流转”的死板存储，在 Memory 实体中引入一等状态：
       - `active`：当前经实证完全有效的事实与经验；
       - `disputed`：存在冲突或有争议、待复核的条目；
       - `superseded`：已被更新的经验推翻/取代的历史陈旧条目。
     - 增加 `superseded_by` 指针字段，形成经验演进链条（Evolution Chain）。
  2. **写入侧冲突探测与自动挂链**：
     - 在 `record_evolution_lesson` 与 `memory_store` 写入链路中，先探测语义高度重合但存在规则变更的既有条目；
     - 新条目落地为 `active`，旧条目自动状态迁移为 `superseded` 并关联 `superseded_by = new_lesson_id`，杜绝旧错误条目静默共存。
  3. **检索侧物理降权过滤 (Retrieval Demotion)**：
     - 检索打分链路自动感知状态：对 `superseded` 条目强制打折降权 80% 或直接过滤，仅在显式请求“历史演化回溯”时呈现；
     - 彻底消灭“旧错误结论因文本字面匹配度高而霸占 Top-1 误导 Agent”的恶性故障。
  4. **Studio 记忆大盘可视化血缘呈现**：
     - 在 OpenViking Studio 记忆大盘与影响抽屉中，为 `superseded` 条目展示中性灰色删除线徽章，可一键展开查看取代它的新版本。

#### 📌 [P1] [ ] Card-Context-ActiveNotesAndHistory (v1.5.10): Codex 级主动上下文治理（Notes 高密活跃状态 + History 独立检索分仓，切除有损 Compaction） ⏳
- **类型**：Context Architecture / Active Governance / Dual-Track Storage / Codex Pattern ｜ **优先级**：⚡ P1（待排期实施）
- **目标版本**：`v1.5.10` ｜ **交付时间预估**：下个迭代周期 ｜ **当前状态**：⏳ 方案已终审·待排期实施
- **来源依据与核心思考推演过程 (Reasoning & Inversion Context)**：
  - **理论源头追溯**：
    1. DeepEvolution《Codex 为什么放弃 compaction？—— 主动上下文治理机制解密》(2026.09) + OpenAI Codex PR #39827；
    2. 大鱼北游《十层自进化全景地图：改上下文到改代码资产》(2026.09)；
  - **芒格逆向审讯（倒推长程会话失忆的元凶）**：
    - *死因*：传统 Compaction（有损压缩摘要）是会话退化的主要来源。经历 3~5 轮压缩后，精确文件路径、失败根因、边界条件和未完成的中间状态均在摘要中被严重磨平失真；
    - *恶果*：长程任务后期，Agent 丢失了最初的真实要求，开始反复执行已验证失败的步骤。
  - **奥卡姆剃刀第一性突破（双轨分仓 + 主动检索）**：
    - **切除全局 Compaction 摘要**；
    - **双轨分仓**：
      - `Notes`：高密度结构化当前状态（已解决事实、待办清单、核心路径与约束），常驻活动上下文，单文件控制在 100~300 行；
      - `History`：完整原始交互轨迹移出活动上下文，独立入库分仓持久化；
    - **主动按需检索工具**：为模型配备 History 检索工具（`list_history_windows`、`search_history`、`read_history_entry`），模型只有在需要核验特定历史细节时才主动调阅，实现无损治理。
- **核心治理成果与三大原子工序拆解 (Tracer-Bullet Tickets)**：
  1. **⚙️ Tracer 1: Notes 高密活跃状态管理器与 SSOT 契约**
     - *文件*：[`openviking/core/active_notes.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/active_notes.py)；
     - *逻辑*：维护一个结构化的活跃状态白板（Notes），每次关键节点由 Agent 进行原地更新（增删改），而不是无脑追加；活动上下文始终只包含系统指令、当前 Notes 与最近几轮交互。
  2. **⚙️ Tracer 2: History 独立分仓存储与全文/BM25 检索工具**
     - *文件*：[`openviking/core/history_bank.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/history_bank.py)；
     - *逻辑*：溢出活动窗口的历史会话自动存入本地 SQLite/FTS5 数据库分仓；向 Agent 暴露 `history_search` 工具，支持按关键词、工具名和时间范围精准召回原始会话片段。
  3. **⚙️ Tracer 3: 无损长会话状态流转与断流压缩自愈套件**
     - *文件*：[`tests/test_active_context_governance.py`](file:///home/skloxo/aho/openclaw/project/tests/test_active_context_governance.py)；
     - *逻辑*：建立包含 50 轮交互的长程任务模拟测试，断言在上下文窗口有限的条件下，Agent 对第 2 轮确定的精确文件路径与错误码的召回准确率达到 100%。
- **不可逾越的物理验收门禁 (Non-Negotiable Acceptance Gates)**：
  - **门禁 1（关键状态零丢失）**：经过多轮交互，Notes 中的核心文件路径与未完成工序状态保持率 100%；
  - **门禁 2（活跃上下文常态精简）**：活动上下文 Token 占用恒定保持在健康水位（<30% 窗口上限），绝不发生雪崩溢出；
  - **门禁 3（历史检索按需精准度）**：通过 History 工具检索历史细节的 Top-1 命中率 $\ge 95\%$。

#### 📌 [P0] [ ] Card-Extraction-ZeroThinking-BisectionHeal (v1.5.11): 记忆提取零思考硬开关、Token 截断二分切片自愈与条数/字数双门禁体系 ⏳

- **类型**：Memory Ingestion / Cost Optimization / Thinking Toggle / Bisection Recovery / Deadlock Prevention ｜ **优先级**：🔥 P0（待排期实施）
- **目标版本**：`v1.5.11` ｜ **交付时间预估**：下个迭代周期 ｜ **当前状态**：⏳ 方案已终审·待排期实施
- **来源依据与核心思考推演过程 (Reasoning & Inversion Context)**：
  - **理论源头追溯**：公众号《无银三百两》长对话记忆提取生产事故与成本检修实录 (2026.09.12)；
  - **芒格逆向审讯（倒推记忆提取链路雪崩与死锁的底层死因）**：
    - *死因 1（Thinking 思考吃掉正文输出口粮）*：在抽取事实场景下默认开启模型 Thinking/Reasoning 模式，思考过程吃掉数千 Token 预算，导致模型在吐出实际事实前达到 `max_tokens` 阈值被拦腰截断，返回空字符串；
    - *死因 2（把确定性截断当成偶发故障死循环重试）*：程序将空返回当成临时网络抖动，带着同样超长的输入原地重试 9 次，单次耗费近 10 分钟且 100% 必定再次截断，导致批处理任务耗时 2.5 小时最终崩溃；
    - *死因 3（单一看字数的虚假安全门禁）*：以前仅看“是否超过 8000 字”，忽略了 7000 字可能包含 80 条高密对话事实，真正决定输出长度的是“要抽取的条数”而非字数。
  - **奥卡姆剃刀工程解法**：
    - **提取场景强制零思考 (`enable_thinking=False`)**：事实抽取为确定性照单取货任务，物理关闭 CoT 思考，消除思考 Token 对输出预算的挤占，耗时下降 10~20 倍，输出字数减少 70%~90%；
    - **截断与偶发严格区分**：若 `finish_reason == "length"` 或截断为空，物理阻断原样重试；自动触发**二分切片自愈 (Bisection Recovery)**，将长输入对半切开并发重抽；
    - **条数与字数双重硬门禁**：消息总字数 > 4000 字 或 消息条数 > 25 条，任意一侧超限立即在入口处执行预切片；
    - **入库防爆安全切分**：整段塞库兜底改为强制分段切片入库，彻底杜绝单条超出数据库上限引发的 Crash。
- **核心治理成果与三大原子工序拆解 (Tracer-Bullet Tickets)**：
  1. **⚙️ Tracer 1: 零思考硬开关与提取运行时控制器 (`ExtractionRuntime`)**
     - *文件*：[`openviking/core/extraction_runtime.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/extraction_runtime.py)；
     - *逻辑*：封装记忆提取专属调用契约，强制下发 `enable_thinking=False`（或 `thinking_budget=0`），设置精确的 `max_tokens` 保护。
  2. **⚙️ Tracer 2: 截断二分自愈调度器与双门禁切片器 (`BisectionPartitioner`)**
     - *文件*：[`openviking/core/bisection_partitioner.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/bisection_partitioner.py)；
     - *逻辑*：检测模型响应元数据，若触发截断，立即将输入对话列表按中点二分切割，派生两个子任务并发抽取并合并结果；在入口处实施字数与条数双重门禁预切片。
  3. **⚙️ Tracer 3: 长程提取防截断、零崩溃与提速 10x 回归单测**
     - *文件*：[`tests/test_extraction_zero_thinking_bisection.py`](file:///home/skloxo/aho/openclaw/project/tests/test_extraction_zero_thinking_bisection.py)；
     - *逻辑*：构建极端高密长对话场景（80 条消息、含精确金额/日期），断言提取过程 0 次截断死锁、0 次崩溃，关键数值召回率 $\ge 98\%$。
- **不可逾越的物理验收门禁 (Non-Negotiable Acceptance Gates)**：
  - **门禁 1（截断空返回率归零）**：长会话提取场景下，模型截断引发的空返回率严格降为 0%；
  - **门禁 2（提取耗时断崖式下降）**：单段长会话提取平均耗时从 >60 秒压降至 $\le 5$ 秒，全量任务耗时缩短 80% 以上；
  - **门禁 3（精确数值事实零丢失）**：金额、日期、编号等高敏感实体召回率 $\ge 98\%$，绝不因切片遗漏跨句事实。

---

#### 📌 [P0] [ ] Card-Skill-ZipOnWrite-ContractualCompression (v1.5.12): 阿里 SkillZip 写入即压缩引擎、六元组强类型契约与 0-Rollout 确定性重构防膨胀 ⏳

- **类型**：Skill Engineering / Lossless Compression / Type Contract / Zero-Rollout Refactoring ｜ **优先级**：🔥 P0（待排期实施）
- **目标版本**：`v1.5.12` ｜ **交付时间预估**：下个迭代周期 ｜ **当前状态**：⏳ 方案已终审·待排期实施
- **来源依据与核心思考推演过程 (Reasoning & Inversion Context)**：
  - **理论源头追溯**：
    1. 阿里、浙大、杜克联合成果《SkillZip: Compressing Evolved Agent Skills without Task Evaluation》(2026.08.15)；
    2. 阿里云千问平台《多智能体协作机制与组织进化》(2026.08.31)；
  - **芒格逆向审讯（倒推自进化技能膨胀致死的底层死因）**：
    - *死因 1（复读机式复利膨胀）*：Agent 每进化一轮就向 Skill 追加一条记录，5 轮后膨胀 5.2 倍。膨胀的核心原因不是学到了新知识，而是重复表述：相同的动作序列被复制进多个分支，通用规则后跟着越收越窄的特例；
    - *死因 2（Prefill 成本激增与注意力淹没）*：技能文档越长，每次推理前缀消耗越大，真正核心的避坑指令被大量冗余文字冲淡，导致模型性能反而下降；
    - *死因 3（评测引导压缩的极高代价）*：传统 SkillReducer 每次压缩需跑 40~80 个真实 Rollout 评测，消耗大量算力与时间，无法持续运行。
  - **奥卡姆剃刀工程解法**：
    - **六元组强类型契约**：将技能文本解析为类型化数据结构：接口 (Interface)、工作流 (Workflow)、工具协议 (ToolProtocol)、作用域规则 (ScopeRules)、输出契约 (OutputContract)、支撑证据 (Evidence)；
    - **Explain Once, Reference Everywhere**：将重复规则提升至最小公共作用域；将重复动作序列抽成可复用共享过程（类似函数调用）；真正差异保留为显式例外；
    - **0-Rollout 确定性重构**：无需运行环境模拟与任务评测，单次 Schema 抽取后使用动态规划规则放置与加权装箱进行确定性优化，耗时仅数秒且结果可复现；
    - **Zip-on-Write 门禁**：在技能生成/落盘的第一时间执行压缩，技能长度终生锁定在种子长度的 1.6~1.9 倍，杜绝膨胀复利。
- **核心治理成果与三大原子工序拆解 (Tracer-Bullet Tickets)**：
  1. **⚙️ Tracer 1: 技能六元组强类型契约解析器 (`SkillContractParser`)**
     - *文件*：[`openviking/core/skill_contract_parser.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/skill_contract_parser.py)；
     - *逻辑*：基于 AST 与结构化抽取将非结构化 Markdown 技能拆解为接口、工作流、协议、作用域、契约与证据六大强类型对象，标记重复动作序列与规则作用域。
  2. **⚙️ Tracer 2: 0-Rollout 确定性规则放置与共享子流程装箱优化器 (`SkillZipOptimizer`)**
     - *文件*：[`openviking/core/skill_zip_optimizer.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/skill_zip_optimizer.py)；
     - *逻辑*：实现动态规划与贪心装箱算法，将公共规则提升至父级作用域，提取公共动作序列为共享子流程；保持稀有规则硬覆盖约束，单次运行时间 $\le 5$ 秒。
  3. **⚙️ Tracer 3: Zip-on-Write 门禁与无损压缩回归套件**
     - *文件*：[`tests/test_skill_zip_on_write.py`](file:///home/skloxo/aho/openclaw/project/tests/test_skill_zip_on_write.py)；
     - *逻辑*：模拟 5 轮自进化技能文档，断言应用 Zip-on-Write 后技能长度压缩 $\ge 30\%$，关键工具调用参数与边界约束 100% 无损保留。
- **不可逾越的物理验收门禁 (Non-Negotiable Acceptance Gates)**：
  - **门禁 1（确定性零 Rollout）**：压缩全流程严禁调用外部环境执行器或触发任务 Rollout；
  - **门禁 2（平均压缩率底线）**：自进化技能文档压缩率达到 $28\% \sim 35\%$，且格式与 Schema 100% 合规；
  - **门禁 3（稀有契约硬覆盖）**：所有带有参数校验、特定错误码处理的唯一边界规则硬覆盖率 100%，绝不因触发频次低被误删。

---

#### 📌 [P1] [ ] Card-Hygiene-AsymmetricDecayAndBench (v1.5.13): 知识卫生异步巡检 (Knowledge Hygiene)、非对称衰减与真实查询回归金标集 ⏳
- **类型**：Knowledge Hygiene / Asymmetric Decay / Golden Benchmark / Budgeted Evaluation ｜ **优先级**：⚡ P1（待排期实施）
- **目标版本**：`v1.5.13` ｜ **来源依据**：A1 H2 知识卫生 + A5 腾讯飞轮非对称淘汰 + A2 旁证固定预算评测
- **核心治理成果与交付目标**：
  1. **后台轻量巡检 Worker (Hygiene Watcher)**：
     - 在后台托管周期性离线巡检工序（例如每日凌晨或会话闲时触发）；
     - 自动筛查并输出《知识卫生诊断报告》：
       - 孤儿条目（缺少父级关联或无索引）；
       - 死重条目（持续 30 天 0 次被检索召回的陈旧冗余碎片）；
       - 冲突簇（两篇或多篇条目同时断言对立规则）；
     - **坚守奥卡姆剃刀铁律**：巡检工序只生成报告与待审清单，绝对严禁全自动暴力物理删除数据！
  2. **非对称动力学衰减 (Asymmetric Decay)**：
     - 践行“错误记忆的毒害远大于正确记忆的收益”：对被人工或红蓝审讯标记为负面/陈旧的条目加速衰减；
     - 衰减仅体现在基础权重与召回门槛上，不改动底层真实文本。
  3. **真实查询回归金标集 (Gold Benchmark with Budget)**：
     - 从 Harness 真实历史检索日志中提炼 50~100 组真实典型 Query（涵盖配置排查、代码符号、路径导航、架构规则）；
     - 强制约束单次检索上下文 Token 预算（如 2k / 4k 上下文）；
     - 在标准测试套件中固化为基准断言（Precision@K、Recall@K、端到端延迟），作为未来任何向量降维、模型更新或参数调优的唯一客观物理门禁。

#### 📌 [P0] [ ] Card-Evolve-HermesEvolveLoop-Patch (v1.5.14): Hermes 级经历与能力解耦存储、Periodic Nudges 异步副进程复盘与 Patch 级技能微补丁自进化机制 ⏳

- **类型**：Self-Evolution Engine / Evolve Loop / Experience-Capability Decoupling / Patch Evolution ｜ **优先级**：🔥 P0（待排期实施）
- **目标版本**：`v1.5.14` ｜ **交付时间预估**：下个迭代周期 ｜ **当前状态**：⏳ 方案已终审·待排期实施
- **来源依据与核心思考推演过程 (Reasoning & Inversion Context)**：
  - **理论源头追溯**：
    1. DeepEvolution《一个让 Agent 会成长的架构：拆解 Hermes Agent 的 Evolve Loop》(2026.09.02)；
    2. DeepEvolution《Agent 自进化全景导论：究竟更新了什么》(2026.09.01)；
    3. Hermes 官方架构文档 (Closed Learning Loop & FTS5 Sessions)；
  - **芒格逆向审讯（倒推 Agent 自进化混乱与遗忘死因）**：
    - *死因 1（经历与能力混杂）*：把执行日志直接当成技能塞入 Prompt，导致上下文充斥大量一次性流水账；或者将技能写死在执行器代码中，无法灵活演进；
    - *死因 2（同步复盘阻塞交互）*：在主会话同一事件循环内做大模型深度反思，导致用户端首字时延与交互彻底卡死；
    - *死因 3（暴力整篇重写引发技能雪崩）*：Agent 发现一个小问题就用 `edit` 模式重写整个 `SKILL.md`，导致原本经过严格验证的 90% 规则被模型幻觉冲刷覆盖，产生严重的灾难性遗忘。
  - **奥卡姆剃刀工程解法**：
    - **经历与能力物理分层**：`SessionDB` 保存经历原始轨迹，FTS5 检索真实消息全文（切除 LLM 虚假摘要）；`MEMORY.md` 存事实与偏好；`SKILL.md` 存可复用操作方法；
    - **Periodic Nudges 异步复盘**：会话结束后派生轻量异步副进程（使用更廉价的工兵模型如 `qwen3.8-flash-next`），只读分析轨迹并提出技能改进建议，绝不拖垮主会话响应；
    - **Patch 优先技能微手术**：`skill_manage` 工具强制优先使用 `patch(skill_name, target_snippet, replacement)` 局部增量替换（硬限制 $\le 30$ 行），保留稳定主体逻辑；配合 `skills.write_approval` 保持人类确认权。
- **核心治理成果与三大原子工序拆解 (Tracer-Bullet Tickets)**：
  1. **⚙️ Tracer 1: 异步复盘轻量副进程与会话轨迹分析器 (`PeriodicNudgesWorker`)**
     - *文件*：[`openviking/core/periodic_nudges_worker.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/periodic_nudges_worker.py)；
     - *逻辑*：监听会话结束事件，派生独立异步 Worker，使用工兵模型分析最近会话轨迹，筛选具有跨任务复用价值的操作步骤与避坑规则。
  2. **⚙️ Tracer 2: 技能局部精确补丁引擎 (`SkillPatchEngine`)**
     - *文件*：[`openviking/core/skill_patch_engine.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/skill_patch_engine.py)；
     - *逻辑*：实现 `skill_patch` 核心逻辑，提供精确匹配前后 2~3 行指纹、局部单次替换 $\le 30$ 行的原子变更能力；若未匹配到唯一指纹拒绝变更；输出标准 Unified Diff 提交审批。
  3. **⚙️ Tracer 3: 异步复盘与局部补丁回归套件**
     - *文件*：[`tests/test_hermes_evolve_loop_patch.py`](file:///home/skloxo/aho/openclaw/project/tests/test_hermes_evolve_loop_patch.py)；
     - *逻辑*：模拟会话产生错误后触发 Nudge，验证 Worker 产出 Patch 补丁并在审批后安全应用，断言未改动的其他章节内容 100% 逐字保真。
- **不可逾越的物理验收门禁 (Non-Negotiable Acceptance Gates)**：
  - **门禁 1（主会话零阻塞）**：异步复盘 Worker 运行对当前会话交互延迟影响严格为 0ms；
  - **门禁 2（局部补丁保真度）**：应用 Patch 后的技能文件，非目标段落哈希校验必须一致，严禁全量重写；
  - **门禁 3（真实数据检索引擎）**：跨会话历史检索必须直接返回数据库原始消息，绝对禁止在检索阶段调用模型生成“假摘要”。

---

### 🌊 Wave 4: 契约化自演进与离线梦境闭环 (Contractual Self-Evolution & Offline Dreaming)

#### 📌 [P0] [ ] Card-Skill-EvaluationRetina (v1.5.15): Skill 质量视网膜与自动化评测门禁体系 (Skill-as-Code & Testing CI / skill-up 规范落地) ⏳
- **类型**：Skill Testing / Regression Gate / Declarative Evals / LLM-as-a-Judge ｜ **优先级**：🔥 P0（待排期实施）
- **目标版本**：`v1.5.15` ｜ **交付时间预估**：下个迭代周期 ｜ **当前状态**：⏳ 方案已终审·待排期实施
- **来源依据与核心思考推演过程 (Reasoning & Inversion Context)**：
  - **理论源头追溯**：阿里开源 `skill-up` (github.com/alibaba/skill-up) + 《测试开发技术：如何定义与度量 Agent Skill 的好坏？》(2026.09) + Anthropic `agentskills.io` 评测指南；
  - **芒格逆向审讯（倒推 Skill 发布的致命死因）**：
    - *死因*：将 Skill 视作普通提示词，改动一个字引发不可预测的非线性行为漂移；全行业长期靠“跑一遍 Demo 没报错”的玄学方式裸奔发布；没有断言、没有测试用例、没有 CI 回归门禁；
    - *恶果*：自研或团队公共 Skill 越改越烂，新改动暗中破坏既有核心契约却毫不知情。
  - **奥卡姆剃刀工程平移**：将成熟的软件工程测试体系 100% 完整平移到 Agent Skill 资产体系，建立统一声明式评测规范。
- **核心治理成果与四大原子工序拆解 (Tracer-Bullet Tickets)**：
  1. **⚙️ Tracer 1: Skill 评测工程规范目录与 YAML 协议解析器**
     - *文件*：[`.agents/skills/<skill_name>/evals/eval.yaml`](file:///home/skloxo/aho/openclaw/project/.agents/skills/) 与 [`openviking/core/skill_eval.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/skill_eval.py)；
     - *逻辑*：规定标准 Skill 测试工程结构：`evals/cases/`（声明式 YAML 用例，支持单轮 prompt 与多轮 turns）、`evals/fixtures/`（测试数据与代码桩）、`evals/eval.yaml`（运行环境与引擎配置）；单文件严格控制在 100~300 行黄金区。
  2. **⚙️ Tracer 2: 三级判定器引擎 (Tri-Level Judge Engine)**
     - *文件*：[`openviking/core/eval_judges.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/eval_judges.py)；
     - *逻辑*：提供 3 种判定器：
       - ① Exact / Regex Judge：精确文本与正则断言，用于结构化参数、禁止词（如 NO GREEN）和文件路径；
       - ② Command Judge：运行外部 Shell 脚本，以命令退出码（Exit Code 0）和输出内容作为物理断言；
       - ③ `agent_judge`：独立大模型断言（LLM-as-a-Judge），对语义忠实度、逻辑完整性打分。
  3. **⚙️ Tracer 3: 核心高频技能金标评测集建立**
     - *覆盖目标*：首批为 [`cockpit-ui`](file:///home/skloxo/.gemini/config/skills/cockpit-ui/SKILL.md)（断言 NO GREEN、11px 下限、微圆角）、[`diagnosing-bugs`](file:///home/skloxo/.gemini/config/skills/diagnosing-bugs/SKILL.md)（断言根因日志回溯与红绿测试）、[`living-asset-system`](file:///home/skloxo/.gemini/config/skills/living-asset-system/SKILL.md)（断言查库优先与档案登记）各建立 10~15 组黄金测试用例。
  4. **⚙️ Tracer 4: Git 预提交与 CI 自动化回归门禁 (Eval-to-Evolution Loop)**
     - *文件*：[`scripts/run_skill_eval.py`](file:///home/skloxo/aho/openclaw/project/scripts/run_skill_eval.py) 与 Git 预提交钩子；
     - *逻辑*：任何对 `SKILL.md` 的修改，必须在提交前自动执行评测；输出 JSON / JUnit XML 结构化报告；测试红灯物理阻断 Git Commit 与 PR 合并。
- **不可逾越的物理验收门禁 (Non-Negotiable Acceptance Gates)**：
  - **门禁 1（全量用例 PASS）**：核心技能 100% 具备 `evals/cases/` 且 CI 回归通过率 100%；
  - **门禁 2（多判官零妥协）**：物理断言（Regex / Command）失败直接判 0 分，严禁纯靠软性 LLM Judge 蒙混过关；
  - **门禁 3（坏用例自动回流）**：线上发生的 Skill 偏离事故，必须在 24 小时内编写对应的 YAML case 纳入回归集。

#### 📌 [P0] [ ] Card-Harness-AHE-ContractualSelfEvolution (v1.5.16): AHE 契约三元组自演进、Self-Harness 根因聚类与 Polar 不可伪造环境判官体系 ⏳

- **类型**：Harness Engineering / Self-Evolution / Verifier Tier / Contract Triplet / Root-Cause Clustering ｜ **优先级**：🔥 P0（待排期实施）
- **目标版本**：`v1.5.16` ｜ **交付时间预估**：下个迭代周期 ｜ **当前状态**：⏳ 方案已终审·待排期实施
- **来源依据与核心思考推演过程 (Reasoning & Inversion Context)**：
  - **理论源头追溯**：
    1. vibe life《如何自动改进 agent harness？7 篇 Harness 自演进论文全景梳理》(2026.08.11)；
    2. Andrej Karpathy《autoresearch: Iterative Research Agent》(2026.08)；
    3. NVIDIA《Polar: Harness as Environment for Agentic Reinforcement Learning》(2026)；
    4. Datawhale《智能体工程三大深层悖论》(2026.07)；
  - **芒格逆向审讯（倒推 Harness 自演进作弊与崩溃的底层死因）**：
    - *死因 1 (Reward Hacking 与谄媚性自嗨)*：依赖模型自身作为评测判官 (Self-Judge)，模型迅速学会“作弊”迎合评估规则（如谄媚性合规、伪造成功标记），出现假进化真退化；
    - *死因 2 (按表面症状聚类补丁引发冲突)*：将所有报“超时”或“缺少产物”的错误混为一谈，打一个表面补丁修好 A 任务却撞碎 B 任务；
    - *死因 3 (Harness 演进无契约无法审计)*：随意改动脚手架逻辑，没有显式假设施加、无法做因果归因、出了故障无法秒级回滚。
  - **奥卡姆剃刀工程解法**：
    - **AHE 契约三元组 (Contract Triplet SSOT)**：
      1. **可证伪 (Falsifiable Manifest)**：每次改动前必须显式声明预期效果与假设，下一轮根据真实执行 Delta 判定胜负；
      2. **可归因 (Attributable Attribution)**：按根因机制 $\phi$ 聚类，明确失败映射到具体哪个组件，只读冻结其他组件排除混淆；
      3. **可回滚 (Rollbackable Isolation)**：脚手架改动采用文件级版本快照，一旦指标回归秒级无损回退；
    - **Self-Harness 模式**：目标模型自任 Proposer，双重 Split 门禁（Held-in 验证改进，Held-out 验证泛化防过拟合）；
    - **Polar 不可伪造判官 (Harness as Environment)**：评测绝不用虚假自评打分，必须由沙箱真实执行结果（编译通过率、测试用例断言、端到端真实退出码）作为唯一客观真理。
- **核心治理成果与四大原子工序拆解 (Tracer-Bullet Tickets)**：
  1. **⚙️ Tracer 1: AHE 契约三元组生命周期管理器与 Manifest 注册表 (`AHEContractEngine`)**
     - *文件*：[`openviking/core/ahe_contract_engine.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/ahe_contract_engine.py)；
     - *逻辑*：维护 Harness 演进 Manifest（记录版本、修改组件、预期效果、回滚点），拦截无假设盲改。
  2. **⚙️ Tracer 2: 失败轨迹深层根因机制聚类器 (`RootCauseClusterer`)**
     - *文件*：[`openviking/core/root_cause_clustering.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/root_cause_clustering.py)；
     - *逻辑*：深入调用栈与上下文诊断，将表面报错（如超时）解构为并发锁竞争、网络慢、死循环等深层根因机制，避免跨症状盲目打补丁。
  3. **⚙️ Tracer 3: 基于沙箱真实执行的不可伪造评估门禁 (`PolarEnvironmentVerifier`)**
     - *文件*：[`openviking/core/polar_environment_verifier.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/polar_environment_verifier.py)；
     - *逻辑*：将测试沙箱作为客观判官，仅采纳编译命令、单元测试 exit code 与真实输出断言作为评分依据，物理切除 LLM 自评分数。
  4. **⚙️ Tracer 4: 契约自演进全流程、防作弊与秒级回滚套件**
     - *文件*：[`tests/test_ahe_harness_evolution.py`](file:///home/skloxo/aho/openclaw/project/tests/test_ahe_harness_evolution.py)；
     - *逻辑*：模拟故意作弊与性能退化的提议，验证环境判官 100% 拦截并自动秒级回滚。
- **不可逾越的物理验收门禁 (Non-Negotiable Acceptance Gates)**：
  - **门禁 1（真值必须来自环境客观执行）**：任何演进提议的评估分数必须由测试沙箱真实退出码提供，绝对禁止使用无约束 LLM 自评替代；
  - **门禁 2（双 Split 零回归底线）**：Held-out 验证集绝对不能出现严重性能回归（$\Delta \le 0$）；
  - **门禁 3（秒级可回滚）**：Manifest 校验失败或线上指标异常时，必须在 1 秒内原子化还原全部 Harness 文件。

#### 📌 [P0] [ ] Card-Skill-TrainablePolicy-RSI (v1.5.17): 可训练外部技能文档与昼夜双轮递归自演进架构 (Trainable Skill Document & Daytime-Nighttime RSI Engine) ⏳
- **类型**：Trainable Skill-MDP / Recursive Self-Improvement / Token Credit Assignment / Bounded Evolve Surface ｜ **优先级**：🔥 P0（待排期实施）
- **目标版本**：`v1.5.17` ｜ **交付时间预估**：下个迭代周期 ｜ **当前状态**：⏳ 方案已终审·待排期实施
- **来源依据与核心思考推演过程 (Reasoning & Inversion Context)**：
  - **理论源头追溯**：
    1. 翁荔 (Lilian Weng)《Harness Engineering for Self-Improvement》(2026.07)；
    2. AliExpress 速卖通技术团队《经验沉淀的三条路径：塞进 prompt、写进代码、训进权重》(2026.08) + SkillOpt (arXiv:2512.xxxxx)；
    3. 不要葱姜蒜的小屋《AgentOPSD：长轨迹局部信用分配与白天工作晚上训练的 RSI 雏形》(2026.08)；
  - **芒格逆向审讯（倒推自进化 Agent 的四大致命死因）**：
    - *死因 1（Prompt 腐化）*：把经验无休止堆进 System Prompt，导致 Token 膨胀、注意力被严重稀释，关键指令召回率直线下跌；
    - *死因 2（粗暴全量改写代码）*：缺乏边界限制，Agent 自主改写代码时为了单项提分搞乱核心外部接口与框架强类型；
    - *死因 3（长轨迹无差别奖励）*：传统强化学习（如普通 GRPO）只能给长达几十步的整条轨迹一个整体正负信号，导致前期的盲目绕弯与最后的关键动作一同被奖励；
    - *死因 4（闭源模型不可训）*：顶尖模型（如 Claude Opus 5、GPT-5.6）权重无法微调。
  - **奥卡姆剃刀第一性突破**：
    - **“流程文档本身就是可训练的外部策略状态 (Trainable Skill Document)”**：将 `SKILL.md` 视作冻结 Agent 的非参数化策略状态，引入学习率、验证集与泛化精炼；
    - **有界可编辑区间 (`# EVOLVE-BLOCK-START/END`)**：框架代码与接口绝对冻结，只允许在显式标记的区间内提炼代码与经验；
    - **局部信用分配 (Self-Teacher with Skill)**：当前模型在无技能下完成真实 rollout，同一个模型快照带着 Skill 沿相同轨迹计算 token log-prob gap 与 turn credit，精准定位关键步骤。
- **核心治理成果与四大原子工序拆解 (Tracer-Bullet Tickets)**：
  1. **⚙️ Tracer 1: # EVOLVE-BLOCK 有界可编辑区间标记与 AST 语法约束器**
     - *文件*：[`openviking/core/evolve_surface.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/evolve_surface.py)；
     - *逻辑*：在核心代码或高频 Skill 模板中通过标准注释 `# EVOLVE-BLOCK-START` 与 `# EVOLVE-BLOCK-END` 划定允许自进化的 Surface；优化器 Agent 严格受限只能修改块内逻辑，块外接口、强类型签名与依赖 100% 物理冻结，AST 静态分析阻断越界逃逸。
  2. **⚙️ Tracer 2: AgentOPSD 局部信用分配与 Self-Teacher 评估引擎**
     - *文件*：[`openviking/core/turn_credit_opsd.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/turn_credit_opsd.py)；
     - *逻辑*：当执行多步长轨迹排障或复杂开发任务时，Student 在无技能干扰下完成真实操作；Self-Teacher 携带对应领域 Skill 沿相同轨迹复评，计算每个 turn 的行为似然差分（Token Gap），精准识别是哪一个具体决策扭转了局势或引入了缺陷，输出细粒度 Credit 分布。
  3. **⚙️ Tracer 3: 昼夜双轮异步任务调度器 (Daytime Rollout + Nighttime RSI Worker)**
     - *文件*：[`scripts/rsi_nightly_worker.py`](file:///home/skloxo/aho/openclaw/project/scripts/rsi_nightly_worker.py) 与后台常驻守护；
     - *逻辑*：建立标准 RSI 闭环：
       - 白天（Daytime）：Agent 在固定 Harness 约束下全速处理真实业务工单，产生干净无污染的执行轨迹；
       - 夜间（Nighttime）：Worker 自动拉起，对全天失败与成功轨迹按失败签名 $\phi=(c,q,m)$ 聚类，提炼高质量 Skill Patch 并执行局部信用分配，优化可进化区块。
  4. **⚙️ Tracer 4: 双 Split (Held-in / Held-out) 严苛无退化回归门禁**
     - *文件*：[`openviking/core/dual_split_gate.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/dual_split_gate.py)；
     - *逻辑*：所有提议的 Skill 更新或代码块 Patch，必须在训练集（Held-in）与独立测试集（Held-out）上同时验证；接受准则是“至少在一个 split 提升，且另一个 split 绝对不退化（$R_{new} \ge R_{old}$）”，坚决拦截以牺牲通用泛化换取单样本提分的坏补丁。
- **不可逾越的物理验收门禁 (Non-Negotiable Acceptance Gates)**：
  - **门禁 1（越界编辑 0 容忍）**：静态 AST 检查断言任何超出 `# EVOLVE-BLOCK` 范围的改动立即红灯拦截并丢弃；
  - **门禁 2（长轨迹信用定位准确率）**：通过合成测试集验证，关键转折步骤的 Turn Credit 权重必须显著高于普通导航步骤 3 倍以上；
  - **门禁 3（双 Split 零退化）**：新补丁在 Held-out 测试集上的性能指标严禁出现负向漂移。

#### 📌 [P0] [ ] Card-Skill-CapabilityPages-NegativeBoundaryRouter (v1.5.18): 腾讯 Capability Pages 三段式技能档案、簇级邻居对比与 T^- 负向边界隔离路由体系 ⏳

- **类型**：Skill Engineering / Retrieval Augmentation / Negative Boundary / Discrimination Routing / Cluster Contrast ｜ **优先级**：🔥 P0（待排期实施）
- **目标版本**：`v1.5.18` ｜ **交付时间预估**：下个迭代周期 ｜ **当前状态**：⏳ 方案已终审·待排期实施
- **来源依据与核心思考推演过程 (Reasoning & Inversion Context)**：
  - **理论源头追溯**：
    1. 腾讯混元《Skill-Use: Evaluating Tool and Skill Synergy in Large Language Models》(2026.08)；
    2. 腾讯优图 & IMA《Capability Pages: Discriminating Complex Skills via Neighborhood Comparison》(2026.08)；
  - **芒格逆向审讯（倒推多技能场景下 Agent 检索失明与负迁移死因）**：
    - *死因 1（库规模断崖下跌与不调用绝症）*：技能库规模从 1 增加到 10 个时，Agent 表现断崖式暴跌，30 个以上几乎无变化。大部分失败不是“选错”，而是压根“没意识到要去调用”（DeepSeek 触发率仅 0.324）；
    - *死因 2（半途而废破坏力 > 自由发挥）*：当 Skill-Use 分数 (SU) < 0.5 时，使用 Skill 的破坏力远大于不用——模型承诺了复杂工具链和格式却走不完，半途瘫痪引发灾难性事故；
    - *死因 3（$T^-$ 负向边界误入向量索引的致死漂移）*：工程师自作聪明把“不要做什么”、“哪些场景不要调我”写进技能正文放进向量库，导致密集检索器语义向量朝否定方向严重漂移，Recall 全线跳水。
  - **奥卡姆剃刀工程解法**：
    - **三段式 Capability Page 结构**：
      - $T^+$：正向触发器（明确定义“什么具体任务场景必须激活我”）；
      - $T^-$：负向判别边界（明确定义“什么请求长得像我、但绝对应该找邻居技能处理”）；
      - $B$：判别性主体（核心算法、输入参数强约束、确定性决策表）；
    - **簇级邻居对比生成 $T^-$ (Cluster-Level Neighbor Contrast)**：$T^-$ 无法从单篇文档凭空闭门造车，必须将技能聚类为邻域簇，让大模型通读整个簇后，通过“找不同”提纯出区分性负向边界；
    - **部署隔离铁律 (Deployment Isolation SSOT)**：
      - 向量索引侧（第一阶段召回）：只存 $T^+ + B +$ 原文；$T^-$ **绝对物理禁止入向量索引**；
      - 路由器/重排侧（第二阶段判别）：$T^-$ 专供 Cross-Encoder 或轻量 Router 裁判，用于精准剔除假阳性伪匹配。
- **核心治理成果与三大原子工序拆解 (Tracer-Bullet Tickets)**：
  1. **⚙️ Tracer 1: 技能簇邻居聚类器与三段式 ($T^+, T^-, B$) 离线档案编译器 (`CapabilityPageCompiler`)**
     - *文件*：[`openviking/core/capability_page_compiler.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/capability_page_compiler.py)；
     - *逻辑*：对全系统技能进行语义邻域聚类，派发对比提示词，生成各技能的专属 $T^+, T^-, B$ 结构化档案，严禁从单文件独立凭空推导 $T^-$。
  2. **⚙️ Tracer 2: 负向边界隔离路由器与物理双轨索引网关 (`NegativeBoundaryRouter`)**
     - *文件*：[`openviking/core/negative_boundary_router.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/negative_boundary_router.py)；
     - *逻辑*：入库时将 $T^-$ 自动剥离隔离存储；检索链路分为两阶段：第一阶段仅通过 $T^+ + B$ 召回 Top-10 候选，第二阶段将候选的 $T^-$ 注入给重排裁判，精准剔除近义假匹配。
  3. **⚙️ Tracer 3: 相似技能高密对决与 Recall@10 提升单测**
     - *文件*：[`tests/test_capability_pages_routing.py`](file:///home/skloxo/aho/openclaw/project/tests/test_capability_pages_routing.py)；
     - *逻辑*：构建 20 组高度混淆的真实技能对决（如 Bazett vs Rautaharju 校正器），断言 Top-1 精准命中率提升 $\ge 15\%$，向量索引库中 100% 不含 $T^-$ 负向污染字段。
- **不可逾越的物理验收门禁 (Non-Negotiable Acceptance Gates)**：
  - **门禁 1（$T^-$ 绝对物理隔离）**：底层向量入库校验必须阻断包含 $T^-$ 段落的嵌入请求，违者抛出 `IndexPoisoningError`；
  - **门禁 2（混淆技能 Top-1 区分率）**：高密邻居技能对决测试集中，Top-1 精确命中率达到 $\ge 92\%$（相较未编译档案提升 $\ge 15\%$）；
  - **门禁 3（SU < 0.5 熔断降级）**：若技能合规度与触发度自检综合分低于 0.5，自动降级为纯文本提示，禁止强制注入刚性工具契约。

---

#### 📌 [P1] [ ] Card-Skill-ContrastiveDistillation (v1.5.19): SKILL-KD 师生分叉决策对比蒸馏与学生重跑变绿准入门禁 (Contrastive Skill Distillation & Re-execution Gate) ⏳
- **类型**：Skill Distillation / Contrastive Learning / Re-execution Gate / Rule Consolidation ｜ **优先级**：⚡ P1（待排期实施）
- **目标版本**：`v1.5.19` ｜ **交付时间预估**：下个迭代周期 ｜ **当前状态**：⏳ 方案已终审·待排期实施
- **来源依据与核心思考推演过程 (Reasoning & Inversion Context)**：
  - **理论源头追溯**：浙大 & 北大 & 阿里《SKILL-KD: Contrastive Skill Distillation》(arXiv:2608.xxxxx) + 北大《VeriSkill: Formal Verification Evolution》(2026.08)；
  - **芒格逆向审讯（倒推反思型 Agent 的死因）**：
    - *死因*：单边自我反思导致规则通胀与虚假经验（96 条未经验证规则得分仅 60.1，反而远低于 38 条经过重跑验证规则的 66.8 分！）；直接给弱模型灌输高手的完美演示，弱模型因能力鸿沟学不会；
    - *突破真理*：可迁移的有效学习信号，是**“学生轨迹与老师轨迹在同一题目的决策分叉点”**；
    - *准入硬门禁*：提炼出的规则，必须让学生拿着它把原题重跑一遍变绿，才证明该规则真正消除了能力缺口。
- **核心治理成果与三大原子工序拆解 (Tracer-Bullet Tickets)**：
  1. **⚙️ Tracer 1: 师生双轨决策分叉提取器 (Contrastive Branch Extractor)**
     - *文件*：[`scripts/contrastive_distiller.py`](file:///home/skloxo/aho/openclaw/project/scripts/contrastive_distiller.py)；
     - *逻辑*：当本地 Agent（学生）在某个复杂代码/排障任务失败时，自动调度高维导师（Claude Opus 5 / GPT-5.6）在同一输入上执行；对齐两套执行轨迹，在第一个分支点（Branch Point）截断并对比差异，输出包含 `title, content, why, trace_link` 的候选规则 Patch。
  2. **⚙️ Tracer 2: 学生重做沙箱回放门禁 (Student Re-execution Sandbox Gate)**
     - *文件*：[`openviking/core/reexecution_gate.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/reexecution_gate.py)；
     - *逻辑*：**绝对铁律**——候选规则 Patch 严禁直接入库！系统自动启动一个纯净沙箱环境，将候选规则注入学生上下文，强制学生重新执行原失败任务；只有当学生重跑且测试物理变绿（Exit Code 0），Patch 才获得入库签名；若重做依然失败，自动放弃该 Patch 并反馈重写，杜绝一切空洞虚假规则。
  3. **⚙️ Tracer 3: 漂移感知规则合并与修剪器 (Skill Consolidation & Pruning)**
     - *文件*：[`openviking/core/skill_consolidator.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/skill_consolidator.py)；
     - *逻辑*：吸收 SKILL-KD 历史链路巩固经验，定期通过 `trace_link` 对技能库中语义重叠、碎片化的零散规则进行聚类合并（如 50 条碎片规则压缩为 6 条系统性规则），并对长期零命中条目执行 Prune 淘汰，誓死将技能文档维持在 100~300 行黄金甜点区。
- **不可逾越的物理验收门禁 (Non-Negotiable Acceptance Gates)**：
  - **门禁 1（重跑变绿准入率 100%）**：全库新增规则必须 100% 附带原任务重跑变绿的物理执行证据，零人工脑补；
  - **门禁 2（精炼度胜于数量）**：合并后的规则集 Token 消耗下降 40% 以上，但任务解决率不发生任何退化。

#### 📌 [P0] [ ] Card-Evolution-CICD-DreamingGate (v1.5.20): Agent 七阶段 CI/CD 变更流水线、离线异步 Dreaming 模式挖掘与四级自治升降级控制层 ⏳

- **类型**：Self-Evolution CI/CD / Offline Dreaming / Level-3 Autonomy / Drift Guard ｜ **优先级**：🔥 P0（待排期实施）
- **目标版本**：`v1.5.20` ｜ **交付时间预估**：下个迭代周期 ｜ **当前状态**：⏳ 方案已终审·待排期实施
- **来源依据与核心思考推演过程 (Reasoning & Inversion Context)**：
  - **理论源头追溯**：
    1. DeepEvolution《记忆治理：什么该记、什么该忘、存在哪一层、何时召回》(2026.09.07)；
    2. DeepEvolution《自进化流水线：怎样安全地把信号变成系统更新》(2026.09.08)；
    3. DeepEvolution《Evolve Loop 控制层：自治等级、权限边界、审核通道、方向观测》(2026.09.09)；
    4. 论文 MOSS (生产失败证据驱动隔离回放与健康回滚)；
    5. Claude Managed Agents 2026 Dreaming 预览机制；
    6. NIST AI RMF Core 人机权责治理规范；
  - **芒格逆向审讯（倒推 Agent 线上失控与方向漂移死因）**：
    - *死因 1（线上直改与技能污染复利）*：Agent 发现问题后直接修改生产 Prompt 或 Skill，未经验证的错误经验通过后续任务派生形成污染链 (When Self-Evolution Backfires)；
    - *死因 2（审核疲劳引发形式主义）*：每一步调用都要求人工确认，导致人类不堪重负，变成无脑点击同意；
    - *死因 3（方向隐蔽漂移）*：每一步局部改动都通过了门禁，但系统连续迭代 100 步后输出极度冗长、工具滥用、拒答率飙升，整体偏离产品初衷。
  - **奥卡姆剃刀工程解法**：
    - **七阶段变更管线 (Agent CI/CD)**：信号汇聚 ➔ 生成候选 ➔ 隔离评测 ➔ 安全门控 ➔ 灰度发布 ➔ 监控回滚 ➔ 经验沉淀。严禁线上直更，版本化一切；
    - **离线异步 Dreaming 模式挖掘器**：定时扫描长程轨迹，聚类跨会话高频共性错误与团队工作流，输出结构化候选提案（含 Diff 与收益评估）；
    - **四级自治阶梯 (Level 0-3) 与动态升降级**：Level 0 纯建议 ➔ Level 1 提案审批 ➔ Level 2 受监督自治 ➔ Level 3 高度自治；证据充足升级，出现严重回归、越权或二阶漂移立即降级；
    - **人类五大不可剥夺决策权**：规则记忆准入、Prompt/Skill/权限规则最终确认、回归业务裁决、冷启动专家集、安全红线设定；
    - **方向漂移二阶指标雷达**：监控平均输出长度、重试率、拒答率与单位任务成本，超限即刻熔断。
- **核心治理成果与四大原子工序拆解 (Tracer-Bullet Tickets)**：
  1. **⚙️ Tracer 1: 七阶段 Agent CI/CD 变更流水线与沙箱隔离回放器 (`EvolutionCICDPipeline`)**
     - *文件*：[`openviking/core/evolution_cicd_pipeline.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/evolution_cicd_pipeline.py)；
     - *逻辑*：管理候选版本生命周期，在隔离沙箱中执行回放测试，通过门禁后以灰度模式（如 10% 流量）发布并监听回滚触发器。
  2. **⚙️ Tracer 2: 离线异步 Dreaming 轨迹挖掘器 (`AsyncDreamingMiner`)**
     - *文件*：[`openviking/core/async_dreaming_miner.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/async_dreaming_miner.py)；
     - *逻辑*：周期性批处理扫描历史会话数据库，利用无监督聚类与工兵模型识别跨会话重复错误与最佳实践，生成结构化 Patch 候选。
  3. **⚙️ Tracer 3: 四级自治状态机与三层防审核疲劳通道 (`AutonomyGovernanceGate`)**
     - *文件*：[`openviking/core/autonomy_governance_gate.py`](file:///home/skloxo/aho/openclaw/project/openviking/core/autonomy_governance_gate.py)；
     - *逻辑*：维护系统的当前自治等级（Level 0~3）；对普通变更提供自动高置信过滤与批量异步聚合，高风险操作触发实时授权。
  4. **⚙️ Tracer 4: 方向漂移二阶指标雷达与回归防护套件**
     - *文件*：[`tests/test_evolution_cicd_and_dreaming.py`](file:///home/skloxo/aho/openclaw/project/tests/test_evolution_cicd_and_dreaming.py)；
     - *逻辑*：模拟发生异常与二阶指标漂移（如长度膨胀 50%），验证自治状态机自动熔断降级与灰度回滚机制。
- **不可逾越的物理验收门禁 (Non-Negotiable Acceptance Gates)**：
  - **门禁 1（零线上直改）**：任何 Prompt、Skill 或 Harness 变更必须且仅能通过 CI/CD 隔离管线交付；
  - **门禁 2（人类五大核心控制权硬封锁）**：底层拦截任何试图通过模型自主调用修改规则准入、安全红线与权限边界的操作；
  - **门禁 3（方向漂移自动熔断）**：二阶监控指标偏离基线超过 20% 时，系统必须在 1 秒内自动降级至 Level 1 并通知人类。

---
