# 🤖 OpenViking (VK) Agent 研发开局第一法则与通用规范 (AGENTS.md SSOT)

> **"The Single Source of Truth for Any Agent Entering This Codebase."**  
> 本文档是接手本项目所有 Agent（主 Agent、子代理、跨会话 Agent）的**唯一研发入口规范**；`.agents/AGENTS.md` 与根目录 `AGENTS.md` 保持 100% 同步。

---

## 📌 一、 三大文档分工矩阵 (Master SSOT Matrix)

| 物理主文档 | 存放内容与边界 | 关联路径 |
| :--- | :--- | :--- |
| 🤖 **`AGENTS.md`** | **唯一研发法则**：开发哲学、视觉规范、工程红线 | [`.agents/AGENTS.md`](file:///c:/Users/Skl/Desktop/Workspace/coding/OpenVikingStudio/.agents/AGENTS.md) |
| 🗺️ **`BLUEPRINT.md`** | **研发大蓝图**：课题演进蓝图、多引擎压缩白皮书、基准测试 SOP | [`.agents/BLUEPRINT.md`](file:///c:/Users/Skl/Desktop/Workspace/coding/OpenVikingStudio/.agents/BLUEPRINT.md) |
| 📋 **`REFACTORING_PLAN.md`** | **战地冲刺微步看板**：当前仓库模块级实现微步与已交付版本履历（业务与 OKR 全局任务收口在 Tududi `todo.tide.red`） | [`REFACTORING_PLAN.md`](file:///c:/Users/Skl/Desktop/Workspace/coding/OpenVikingStudio/REFACTORING_PLAN.md) |

---

## ⚡ 二、 研发八大绝对红线 (Non-Negotiable Baseline Rules)

1. **绝不盲目破坏数据 (Disaster Recovery First)**：
   - 敏感数据/记忆/架构重构前，必须先通过 `VikingFS.commit` 或目录快照落盘备份，确保可 100% 回滚后再推进。
2. **奥卡姆剃刀 (Occam's Razor) 与极简降维**：
   - 如无必要，勿增实体；拒绝复杂动态定时器与冗余包装层，优先采用简洁入口拦截与离线后台蒸馏。
3. **性冷淡视觉克制与 NO GREEN EVER 铁律**：
   - 颜色是信号不是装饰，默认中性哑光灰，偏离基线才上色（正向 `cyan-500`、告警 `amber-400`、异常 `rose-500`）；全界面与输出**严禁使用绿色**。
4. **全局最小字号硬性下限 (`>= 12px` / `text-xs`)**：
   - 物理封杀 `text-[8px]` ~ `text-[11px]` 微小字体；一切正文、Badge、属性标签严格对齐 **`>= 12px` (`text-xs`)**，紧凑标签统一 `text-xs font-mono px-1.5 py-0`。
5. **Agent 编码单文件行数甜点区与硬上限**：
   - **黄金甜点区**：**`100 ~ 300 行`**；**绝对硬上限**：**严禁任何文件超过 `500 行`**（400 行预警即按 Seam 拆解）；
   - 分级：入口路由 `<= 150` 行；UI 组件 `100 ~ 250` 行（上限 300）；DTO/Model `100 ~ 300` 行（上限 400）；核心服务 `200 ~ 350` 行（上限 500）；工具纯函数 `<= 200` 行。
6. **代码库凭据物理隔离与 Git 零泄密铁律**：
   - 全仓库源码、文档、脚本、测试严禁硬编码真实 API Key、密码、私有 IP、账号或私钥；
   - 凭据统一由 KeePass (`keepass-vault`)、`os.environ.get()` 或受 `.gitignore` 保护的 `.env` 动态注入；提交前强制跑 [`scripts/security_check.py`](file:///c:/Users/Skl/Desktop/Workspace/coding/OpenVikingStudio/scripts/security_check.py)。
7. **全项目统一开发协作范式 A 与动静分离门禁 (`Paradigm A & Clean Verification SSOT`)**：
   - **职责边界**：Windows 负责代码编辑、架构设计与 Git 追踪；WSL2 (`/home/skloxo/services/openviking`) 负责原生 ext4 前端构建与生产服务运行。
   - **9P 防卡死**：严禁在 `/mnt/c/...` 跨盘直接跑 `vite build` / `npm install`，前端打包统一用 `python scripts/sync_to_wsl.py -b`。
   - **极速单测**：日常业务单测执行 `wsl python3 -m pytest -o addopts='' -q --tb=short tests/unit/test_xxx.py`（~0.5s 反馈）。
   - **防滥用热重启**：日常微步编码**严禁反复重启常驻后台或重复前端构建**（同步脚本带 `--skip-build`），仅在全量测试通过、封板打 Tag 前重启/构建验活 1 次；发布统一走 `scripts/release_step.py`。
   - **Windows 探针安全**：严禁裸写未带 `-UseBasicParsing` 的 `Invoke-WebRequest`，本地 HTTP 探针统一使用 `curl.exe --noproxy "*" -s -m 3`（WSL 端口在 `wsl curl -s -m 3` 内探）。
8. **知识分层与虚拟投影透明路由 (`Knowledge Hierarchy & SkillAliasingRouter`)**：
   - 顶层领域大包高内聚收敛，底层细分工序收口在 `scenarios/*.md`，由文件系统 Glob 自动扫描生效，并通过 `SkillAliasingRouter` 对历史单体名执行零破坏回退。

---

## 📜 三、 核心工程与设计哲学 (12 条精炼纲领)

1. **官方原生优先**：100% 优先使用官方原生 API 与成熟高星轮子，确有缺失时才编写精专 Adapter。
2. **全生命周期“信、达、雅”**：逻辑严谨不遮盖异常（信）；命名与结构自解释（达）；高内聚低耦合、UI 齐平克制（雅）。
3. **代码复用与一核三端 Monorepo 收口**：
   - 全前端统一通信客户端 `ovClient`，严禁散落裸 `fetch` 与伪造 Mock fallback；
   - 插件母本收口于 `packages/plugins/<name>/`（`plugin.json` 为版本 SSOT，通过 `scripts/sync_all_plugins.py` 级联发布）；Core MCP 暴露全量核心工具矩阵，卫星节点仅暴露精简只读/上报安全工具。
4. **数据治理与合并防丢**：结构重构必须保留并物理合并有效数据；运行态存储唯一收口 SQLite；100% 真实后端数据，无数据时显示 `--`。
5. **切除代码堆叠与掩盖式补丁**：严禁在臃肿逻辑外层再套 Wrapper，严禁写旁路 fallback 掩盖 Bug，必须深入故障点根治。
6. **主干核心服务优先 + 观测解耦**：FastMCP、VikingFS、VectorDB 与记忆读写拥有绝对优先权；所有系统探针采用 `5s ~ 10s` 单调时钟快照缓存，严禁高频 fork 外部进程拖垮 GIL。
7. **单例守卫与前端断流休眠**：含后台线程的 Store 强制双检锁单例（`.get_instance()`）；监控页配置 `refetchIntervalInBackground: false` 与 `staleTime: 15_000`，后台切页立即物理断流。
8. **Agent 编码十大铁律 (`agent-friendly-code-org`)**：渐进展开（`code_outline` ➔ `grep` ➔ 切片读）➔ 上下文脱水（`-q`）➔ 强类型 DTO（禁 Python `dict` 传参 / TS `any`）➔ 深模块窄接口（参数 `<= 4`）➔ 紧邻指纹编辑与 Windows CRLF 避坑 ➔ TDD 红绿视网膜 ➔ 即时单点验证 ➔ 直击根因 ➔ 原子小步 ➔ 踩坑写 `evolution_lessons/`。
9. **CPA 智囊工兵自动协同 + 红队实证门禁（遵循 `cpa_squad`）**：
   - **工兵批处理**：海量扫描/提纯优先调用 `scripts/cpa_worker.py` 派发给 `mux-flash`、Qwen、DeepSeek、SenseNova 等非限速工兵（**日常批量严禁滥用限速的 MIMO**）；
   - **智囊参谋**：复杂架构权重与疑难死锁请教 Claude / GPT 系列；
   - **红队实证铁律**：所有 CPA 产出落盘或修改实机前，必须由主智体逐条对照真实文件/库表/日志核验，剔除幻觉与错位前提。
10. **前置客观指标锚定与对比核验**：卡片开工前声明待改善的前端或链路客观指标，交付时实测对比证明正向收益。
11. **开工前四阶熔炼 + $X/Y$ 物理进度契约**：
    - 梳理原方案 ➔ CPA 补盲 ➔ 第一性/奥卡姆拷问 ➔ 红蓝对抗重构卡片；
    - 进度展示中 $X$ 严格为实际已完成量、$Y$ 为总量，**进行中严禁预支 `+1`**，$X=Y$ 方自动流转下一工序。
12. **代码 AST 事实唯真与三维无悬空交付**：接口与数据读写关系优先用 `ast` 静态提取（`30s TTL` 缓存）；对业务与智能体有价值的新能力需同步闭环「后端路由 + FastMCP 工具 + Web UI 指标/交互」。

---

## 🎨 四、 UI/UX 视觉规范 (收敛于 `cockpit-ui`)

- 所有前端页面与组件开发必须遵循全局 `cockpit-ui` 技能：
  1. **NO GREEN EVER 🚫**：默认中性哑光灰，正向 `cyan-500`、告警 `amber-400`、异常 `rose-500`；
  2. **高密排版硬下限**：全局字号 **`>= 12px` (`text-xs`)**，数值 `font-mono tabular-nums`，圆角 6px (`rounded-md`)，图标 `size-2.5` ~ `size-3.5`，卡片内边距 `p-3` ~ `p-3.5`；
  3. **真实物理进度**：严格遵守 $X/Y$ 物理完成度展示规范。

---

## 🔄 五、 标准迭代交付与五位一体回显 SOP

每次发布或卡片完工，按以下五步留痕验收（不出现任何禁用绿勾符号）：
1. **同步版本与 Git Tag**：原子递增 `package.json` 与 `openviking/_version.py`，打标 `git tag -a v1.x.y -m "..." && git push origin v1.x.y`；
2. **更新 `REFACTORING_PLAN.md`**：将当前卡片标记为 `[x] 已验收通过`，登记 Commit Hash 与修改文件（全局 OKR/跨期任务保留在 Tududi）；
3. **自动化测试与安全构建门禁**：附上可复现单测命令、新增/回归用例明细、真实通过/失败数与耗时、`python scripts/security_check.py` 零泄密回显及必要时 `vite build` 状态；
4. **人工肉眼可视化验收清单**：给出直达 URL、操作步骤、关键数字/文字预期及负向排查（**零绿色、无 `<12px` 微字、无 `--`/`NaN`/白屏/假数据**）；
5. **客观指标对比**：列明优化前基线 vs 优化后实测值及页面对应展示位置。

---

## 🌐 六、 标准服务与集群运维入口

| 端口 / 端点 | 角色与功能 | 运行与管理方式 |
| :--- | :--- | :--- |
| **`1933`** (`https://vk.tide.red`) | OpenViking 核心中枢 (FastMCP / REST / Web UI) | WSL2 `systemd --user openviking.service` (`systemctl --user restart openviking`) |
| **`13100`** (`10.128.226.5`) | Mac Studio M3 Ultra 算力与业务节点 | FRP / 内网 SSH (`ssh -p 13100 fsk@tunnel.internal`) |
| **卫星与插件协同** | 统一由 `packages/plugins/openviking-memory/` 驱动，多端同频遵循 `satellite-fleet-ops`、`openviking-plugin-ops` 技能与 `scripts/sync_all_plugins.py`；大模型评测统一遵循 `openviking-model-evaluator` 技能及各场景真实数据基准。 |

---

## 📋 七、 跨智能体建卡 (`AIFP`) 与小步快跑刹车门禁

1. **异步建卡 (`AIFP`)**：现场遇服务端报错或回归隐患，使用 `openviking_file_task_card` 提交 6 要素客观凭据（`title`/`priority`/`module`/`symptom`/`hypothesis`/`reproduce_steps`），由指纹去重并在确认非 4xx 客户端误调后入库，禁止卫星端直改 `REFACTORING_PLAN.md`；主控通过 `openviking_list_pending_cards` 定期清理分诊。
2. **一卡一命一停手**：单轮会话严格只推进 1 张原子卡片；测试变绿、Tag 推送并更新文档后**立即停止工具调用向人类交棒**，严禁连续黑盒连跑多卡。
3. **规划与编码物理分回合**：拆卡/规划回合严格只输出方案与清单，严禁碰触业务源码；巡检/测试回合严格只检不修。
4. **单轮 25 步预算与零盲目轮询**：连续工具调用硬上限 25 步（20 步阶段汇报），严禁死循环轮询后台任务或反复重读同一大日志。
