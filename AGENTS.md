# 🤖 OpenViking (VK) Agent 研发开局第一法则与通用规范 (AGENTS.md SSOT)

> **"The Single Source of Truth for Any Agent Entering This Codebase."**  
> 本文档是接手此项目的所有 Agent（主 Agent、子代理、跨会话 Agent）的**唯一开局入口与物理规则真相源**。

---

## 📌 一、 唯一真相源 3 大主文档矩阵 (Master SSOT Matrix)

全项目所有开发规范、演进蓝图与任务卡片物理收口在以下 3 个 Master 文档中，彻底禁止多头散落：

| 物理主文档 | 存放内容与功能 | 关联路径 |
|:---|:---|:---|
| 🤖 **`AGENTS.md`** | **唯一研发法则**：开发哲学、UI 视觉规范、绝对红线 | `.agents/AGENTS.md` |
| ��️ **`BLUEPRINT.md`** | **唯一研发大蓝图**：课题演进蓝图、多引擎压缩白皮书、基准测试 SOP | `.agents/BLUEPRINT.md` |
| 📋 **`REFACTORING_PLAN.md`**| **唯一任务卡片总看板**：所有活跃工单、课题卡片、已交付版本履历 | `REFACTORING_PLAN.md` |

---

## ⚡ 二、 研发六大绝对红线 (Non-Negotiable Baseline Rules)

1. **绝对禁止盲目修改代码 (Disaster Recovery First)**：
   - 任何敏感数据/记忆/架构重构，必须先做可行性与安全性评估；
   - 必须先调用 `VikingFS.commit` 物理快照，确保可通过 `snapshot/restore` 100% 回滚还原后再推进。

2. **奥卡姆剃刀 (Occam's Razor) 与极简降维**：
   - 切除一切过度工程；如无必要，勿增实体；
   - 拒绝复杂的动态定时器与冗余逻辑，优先采用极简入口拦截与离线后台蒸馏。

3. **性冷淡视觉克制铁律（详见第四节）**：
   - UI 中颜色是信号，不是装饰；默认一切中性，异常/告警才上色。

4. **全局最小字号硬性下限 (>= 11px)**：
   - 物理封杀禁用 text-[8px], text-[9px], text-[10px] 等微小字体；
   - 任何 Badge、属性说明字号硬下限为 11px (text-[11px])，高密正文统一使用 12px (text-xs)。

5. **Agent 编码单文件行数硬性安全红线与黄金甜点区 (Agent-Friendly File Size SSOT)**：
   - **第一性原理**：单文件超过 1,500 行触发 LLM 注意力 U 型衰减（Lost in the Middle）；超过 800 行超出单次 `view_file` 视野上限导致割裂；超过 500 行极易诱发工具调用行号漂移与补丁套叠；
   - **黄金甜点区 (Sweet Spot)**：**`100 ~ 300 行`**（Working Memory 100% 激活，零工具漂移，极简单测覆盖）；
   - **绝对物理硬上限**：**严禁任何新增或重构文件超过 `500 行`**（违者物理阻断并强制拆解）；
   - **分类型分级阶梯规范**：
     - **入口路由/胶水层 (`route.tsx`, `__init__.py`)**：**`≤ 150 行`**（纯容器装配，只管数据流转，不写业务逻辑）；
     - **UI 展示与卡片组件 (`-components/*.tsx`)**：**`100 ~ 250 行`**（硬上限 300 行）；
     - **数据模型与强类型 DTO (`types.ts`, `models.py`)**：**`100 ~ 300 行`**（硬上限 400 行）；
     - **领域核心服务/算法管线 (`service.py`, `pipeline.ts`)**：**`200 ~ 350 行`**（物理硬上限 500 行）；
     - **工具函数/纯辅助库 (`utils/*.py`, `lib/*.ts`)**：**`≤ 200 行`**（硬上限 300 行）；
   - **预警自愈机制**：一旦任何文件生长达到 400 行，Agent 必须主动停下识别领域接缝 (Seam) 拆分子模块，绝对禁止继续堆叠代码！

6. **代码库凭据绝对物理隔离与 Git 零泄密铁律 (Zero-Secret & Credential Isolation SSOT) ⭐⭐⭐⭐⭐**：
   - **绝对零容忍**：全代码库（源码、文档、脚本、测试、Demo）**100% 严禁出现任何真实 API Key、密码、私有 IP (如 FRP/公网真实 IP)、账号或私钥**；
   - **纯动态环境解析**：所有敏感凭据与网络端点统一通过 `os.environ.get()` 或本地 `chmod 600` 的 `.env`（严格由 `.gitignore` 阻断）动态读取；
   - **Git 物理阻断门禁**：必须常驻安装 `.git/hooks/pre-commit` 联动 `scripts/security_check.py`，检测到敏感字符物理拒绝 Commit；
   - **衍生资产自动脱敏**：由扫描器或脚本生成的本地缓存与 JSON 资产，严禁打包真实节点密码与私有配置，且必须加入 `.gitignore` 物理隔离。

---

## 📜 三、 核心工程与设计哲学 (Engineering & Design Philosophy)

### 核心纲领一：站在巨人的肩膀上 —— 官方轮子优先

- **官方原生优先**：100% 优先基于官方底层原生 API 与算子。
- **按需补充构建**：官方没有提供时，才编写 Adapter 适配器。

### 核心纲领二：全生命周期"信、达、雅"

- **【信】准确严谨**：逻辑严谨，尊重物理契约；绝不掩盖异常、绝不返回虚假 fallback；专有名词全盘统一不混用。
- **【达】自解释通顺**：变量名/函数名见名知意；UI 文案契合开发者直觉，无拗口晦涩。
- **【雅】极客雅致无赘**：架构高内聚低耦合，遵循 DRY/KISS；UI 性冷淡克制，颜色有且仅有语义价值。

### 核心纲领三：代码复用与深度整合优先 (Reuse & Deep Consolidation Principle) ⭐

- **能复用必复用**：能复用的代码尽量复用，能复用的函数尽量复用，能复用的数据尽量复用，能复用的方法尽量复用。绝不换个写法随意创造新轮子，防止系统陷入紊乱。
- **深度对比后合并整合**：重构治理绝非盲目、匆忙、草率地删，而是必须**对比两套代码与方法的差异，取其精华深度整合**，收口为单一真相源 (SSOT)。
- **统一通信层与协议**：全前端统一收口 `ovClient`，严禁散落裸 `fetch` 和幽灵废弃客户端，杜绝 401 鉴权失效与伪造假数据 fallback。
- **双模态 MCP 智体桥梁物理收口 Monorepo (Dual-Mode MCP Architecture)**：
  - MCP 是各个 Agent 连接 Wiki 的唯一物理桥梁，必须物理收口在 Git Monorepo 仓库内与 Wiki 源码一同版本化迭代；
  - **1. 核心 MCP (Core MCP - 本地模式)**：用于本地主 Agent，全量 30+ 接口（全量记忆存储/检索、VikingFS 底层控制、技能生命周期治理、图谱拓扑、服务端快照与灾备）；
  - **2. 卫星 MCP (Satellite MCP - 远程模式)**：用于 3070 / Mac Studio 等远程卫星节点，精简安全模式（专注远程知识召回 `find`/`search`、经验提纯上报 `record_lesson`、网络抖动自愈与超时容错），物理隔离危险的底层运维与文件写指令。

### 核心纲领四：数据治理第一性原理与合并防丢铁律 (Data Governance SSOT Rule) ⭐

- **数据绝对安全（合并防丢）**：系统重构、升级或迁移过程中，**必须进行物理数据合并，绝对禁止删除数据**；
- **唯一物理真相源 (SSOT)**：彻底切除“内存单例 + 磁盘数据库”双轨割裂模型，全生命周期统一收口 SQLite 物理数据库；
- **绝对数据真实性**：100% 真实后端数据驱动，严禁伪造假数字或硬编码 Mock；接口缺失或异常时优雅展示 `--` 占位符。

### 核心纲领五：彻底切除 Agent 代码堆叠与掩盖式补丁 (Anti-Layering & Clean Codebase SSOT) ⭐⭐⭐⭐⭐

> **背景教训**：Agent 编写代码极易陷入“无脑代码叠代码”与“用新方法掩盖旧隐患”的恶性循环，导致代码库越来越脏、发包失效、深坑积聚。必须用以下四条硬核哲学彻底根治：

1. **绝对严禁无脑代码叠代码 (No Nested Layering)**：
   - 需求变更或新增功能时，**绝对禁止在原有臃肿代码外层无脑再套一层 Wrapper / Adapter**；
   - 必须深入原有逻辑，精简、重构并消除中间冗余层，让调用链路直截了当。
2. **绝对严禁写新方法掩盖旧隐患 (Root-Cause Fix, No Patching Over Flaws)**：
   - 遇到 Bug、异常或接口失效，**绝对禁止新写一个旁路函数/fallback 逻辑来“绕过”或“掩盖”原有问题**；
   - 必须直击物理根因，彻底修复或重写底层有缺陷的模块，根治隐患，严禁埋下隐蔽定时炸弹。
3. **公用组件与现成轮子四法则 (Shared Utilities & Wheel-First Logic)**：
   - **(a) 能用公用方法组件的，100% 优先使用公用方法组件**；
   - **(b) 有成熟现成轮子的，100% 优先使用成熟现成轮子与官方 API**；
   - **(c) 能复用的坚决复用，不能复用的寻找成熟轮子，严禁闭门造野生新轮子**；
   - **(d) 极致简洁（KISS 原则）**：能用 10 行写清楚的逻辑绝不写 50 行，代码必须自解释、干净利落、零杂质。

### 核心纲领六：第一性原理 —— 主干核心服务绝对优先，观测大屏解耦为异步次要仆人 (Core Service Priority & Observability Decoupling) ⭐⭐⭐⭐⭐

- **主干服务第一优先级**：OpenViking 的核心物理价值在于 FastMCP、VikingFS、VectorDB、语义检索与记忆持久化。观测大屏、监控卡片与数据大盘严格定位为**次要、异步、人肉消费端**，必须在主服务有余力、有资源时才提供服务；
- **削峰填谷与快照隔离**：后端所有 observer 与 system 资源探针强制采用轻量单调时钟快照缓存（5s~10s TTL），无论前端并发多高，0.1ms 直接从内存快照返回，严禁高频轮询争抢 CPU、GIL 或 SQLite 锁，严禁高频 fork `nvidia-smi` 进程；
- **异常平滑降级**：观测指标计算偶发异常时，优先返回上一次有效快照或 `--` 占位符，绝不允许监控异常拖垮主进程。

### 核心纲领七：奥卡姆剃刀与极简防线 —— 严格单例守卫与前端断流休眠 (Occam's Razor & Thread Lifecycle SSOT) ⭐⭐⭐⭐⭐

- **如无必要，勿增实体**：切除过度工程与孤独工程化，不引入无意义的 Redis、消息队列或外部 sidecar 进程；能用 10 行原生代码解决的逻辑绝不写 50 行包装；
- **常驻 Worker 线程必须严格单例**：全系统凡是包含后台 Worker 守护线程的类（如 `TelemetryStore`），必须在 `__new__` 层强制实施双检锁单例控制，严禁裸暴露普通构造函数导致反复实例化泄露线程；业务代码强制使用 `.get_instance()`；
- **前端观测大屏断流休眠**：监控页面与趋势图表强制配置 `refetchIntervalInBackground: false` 与 `staleTime: 15_000`，轮询拉长至 30s~60s；标签页切后台或离开大屏即刻物理断流休眠，零无效网络与 CPU 开销。

### 核心纲领八：提升 Agent 编码能力、效能、质量与注意力的十大工程铁律 (Ten Iron Laws of Agent Coding) ⭐⭐⭐⭐⭐

> 详见技能规范：[`agent-friendly-code-org`](file:///home/skloxo/.gemini/config/skills/agent-friendly-code-org/SKILL.md) 第 9 节。全项目所有会话 Agent 强制遵行以下十项物理铁律：

1. **【渐进展开律 (Progressive Disclosure)】**：严禁开局全量通读大文件！必须遵循 `code_outline` / `tree` ➔ `grep` ➔ `view_file` 切片 (50~100 行) 三级精密寻源，保护工作记忆；
2. **【上下文脱水与静音律 (Context Dehydration)】**：运行终端命令强制带简短参数（如 `pytest -q`, `git status -s`），严禁海量控制台日志冲刷刷屏污染上下文；
3. **【强类型有轨电车律 (Strict Typed DTO Rails)】**：Python 100% 封杀 Raw `dict`（强制 `Pydantic` / `@dataclass`），TS 100% 封杀 `any`，为 Agent 提供防幻觉轨道；
4. **【深模块窄接口律 (Deep Modules, Narrow Interfaces)】**：内部实现高内聚，对外暴露参数 $\le 4$ 个，大幅降低调用方认知负荷；
5. **【紧邻指纹锚点编辑律 (Tight Fingerprint Anchor Editing)】**：调用 `replace_file_content` 必须附带目标行前后 2~3 行唯一指纹特征，单次编辑 10~30 行，彻底杜绝匹配漂移；
6. **【红绿测试为视网膜律 (Test-First Sensory Organ)】**：测试套件是 Agent 唯一的物理感官，修 Bug 先写失败用例 (Red) 再改实现变绿 (Green)；
7. **【即时构建门禁律 (Immediate Build Gate)】**：修改单个文件后立即构建/编译验证，绝对禁止连续修改 5 个文件才首次验证引发错误雪崩；
8. **【直击根因零遮盖律 (Root-Cause Fix, Zero Masking)】**：严禁写新的 Adapter / if-else / try-except 来绕过底层缺陷，必须直击物理故障点；
9. **【原子化小步快跑律 (Tracer-Bullet Atomic Commits)】**：改完一个接缝、测试通过立即 Commit，保障 Git 历史干净且秒级可回滚；
10. **【踩坑事实体外沉淀律 (Evolution Lessons Persisted)】**：遇到非显而易见的坑点，根治后必须调用 `openviking_record_evolution_lesson` 写入体外大脑，形成跨会话智力复利。

### 核心纲领九：CPA 体外智囊导师与无限算力自动下意识触发铁律 (Subconscious CPA Reflex & Council Dispatch SSOT) ⭐⭐⭐⭐⭐

> **核心物理公理**：Antigravity 是总控战地指挥官（大脑），CPA 模型群是专属参谋、导师与无限打工人（四肢与智囊）。严禁事事等待用户手动提醒！Antigravity 必须形成如臂使指的下意识本能反射：

1. **【工兵型任务 ➔ 自动下意识派发给 CPA 快速工兵】**：
   - **打工人模型**：`qwen3.8-flash-next` / `mimo-v2.5-pro` (1M 上下文)；
   - **自动触发场景**：海量文档抓取/提纯（如 72 篇官方文档）、大批文件格式转换、长日志/报错全量扫描、批量测试数据与 L0/L1 摘要抽取；
   - **行为规范**：严禁把万级 Token 的纯搬砖数据塞入 Antigravity 自身有限上下文！必须下意识直接调用 `scripts/cpa_worker.py` 在后台静默高并发消化，Antigravity 仅需阅读几十行脱水成果进行审查与落地；
2. **【架构疑难与极端死锁 ➔ 自动下意识向 CPA 导师参谋请教】**：
   - **参谋导师模型**：`claude-opus-5` (Claude 5.0) 与 `gpt-5.6`；
   - **自动触发场景**：重大系统架构设计、多方案选型权衡、状态机死循环/死锁排查、复杂边界竞态分析、第一性原理数学/算法推导；
   - **行为规范**：遇到真正的难题，绝不闭门造车或主观硬猜，必须自动调用 `scripts/cpa_consult.py` 带着严密的上下文与物理证据，主动向 Claude 5.0 / GPT 5.6 组织多脑研讨与解法请教；
3. **【战地指挥与落地闭环铁律】**：
   - 导师提供高维思路，工兵提供充足原料，**Antigravity 负责战地统筹与物理落地**：结合项目实际规范（信达雅、单文件 100~300 行黄金甜点区、NO GREEN EVER、双轨任务中心），编写最严密的代码、单测并通过 Git Tag 交付闭环；
   - **失职判定**：凡遇大规模机械扫描却自己硬啃、或遇重大死锁难题却不向导师请教而等待用户提醒使用 CPA 者，视为违反自动化执行铁律！

---

1. **第一性原理**：剥离表象假象，直击物理根因。
2. **奥卡姆剃刀**：如无必要，勿增实体；切除装饰噪音。
3. **$X / Y$ 物理进度度量与工序流转铁律 (Strict Completed/Total Progress Contract)**：
   - **$X$ 与 $Y$ 的唯一物理语义**：$X$ 严格代表【已完成数 (Completed Count)】，$Y$ 严格代表【总数 (Total Count)】；
   - **完成才 $+1$，进行中严禁预支 $+1$**：只有当某项计算/处理真正物理完成落地后，$X$ 才会 $+1$；在执行中 (Running) 阶段，$X$ 必须严格展示当前真实的已完成量（从 0 开始累计，如 1 节点任务在执行中严格展示 `0/1 节点`，严禁预支写成 `1/1 节点` 产生已完成假象）；
   - **$X = Y \iff 100\%$ 完成**：当且仅当 $X = Y$ 时，才代表该工序 100% 结束；
   - **自动流转下一工序**：当一道工序 $X = Y$ 结束时，系统必须立即自动流转到下一道未完成工序并展示下一工序的 $0/N$ 进度，严禁死卡在已完成工序名下。

---

## 🎨 四、 UI/UX 视觉规范 —— 唯一收口于 cockpit-ui 技能 (SSOT)

> **核心世界观**：界面是数据的容器，不是画布。颜色是信号，不是装饰。  
> 全系统视觉系统、人机工效与高密排版规范已全面**结晶收口至 `cockpit-ui` 技能**，彻底切除分散多头说教。

1. **唯一真相源 (SSOT)**：所有涉及前端 Web、UI 组件、座舱大盘与监控卡片的开发与重构，**必须挂载并严格遵循 [`cockpit-ui`](file:///home/skloxo/.gemini/config/skills/cockpit-ui/SKILL.md) 技能**；
2. **三大物理公理常驻潜意识**：
   - **NO GREEN EVER 🚫**：全系统绝对禁止使用绿色，正常运行数据默认中性哑光灰，仅偏离基线才上色（正向冰青 `cyan-500`、告警琥珀 `amber-400`、异常玫瑰红 `rose-500`）；
   - **座舱级最高信息密度律**：最小字号硬下限 $\ge 11\text{px}$，高密基准字号 $12\text{px}$ (`text-xs`)，数值严格 `font-mono tabular-nums`，卡片内边距收敛为 `p-3`~`p-3.5`，图标尺寸锁定为 `size-2.5`~`size-3.5`，小微圆角统一 6px (`rounded-md`)；
   - **$X/Y$ 物理进度契约**：$X$ 严格代表已完成数，$Y$ 严格代表总数，执行中严禁预支 $+1$，$X=Y$ 自动流转。

---

## 🔄 五、 干活必留痕流转 SOP

每完成一个迭代版本，必须完成以下三步，缺一不可：
1. **物理更新 package.json 版本号**；
2. **立即打 Git Tag 并推送**：`git tag -a v1.x.y -m "..." && git push origin v1.x.y`；
3. **物理更新 REFACTORING_PLAN.md**：标记 `[x] 已验收通过 ✅`，记录 Commit Hash 和交付清单。

---

## 🌐 六、 标准服务端口与极速运维矩阵 (SSOT Service Matrix)

| 端口/节点 | 角色与功能 | 常驻方式 | 极速管理指令 |
|:---|:---|:---|:---|
| **`1933`** | OpenViking 核心中枢 (FastMCP / REST / `/studio` Web UI) | `systemd --user openviking.service` | `systemctl --user restart openviking` |
| **`13100`** | Mac Studio (M3 Ultra 256G) 远程算力节点 | FRP 穿透 (`tunnel.internal`) | `ssh -p 13100 fsk@tunnel.internal` |

---

## 🔬 七、 大模型准入与适配评估标准规范 (OpenViking Model Evaluator SSOT)

> **核心原则**：全系统严格禁止脱离真实工况的空泛评测，统一收口标准技能 [`openviking-model-evaluator`](file:///home/skloxo/aho/openclaw/project/.agents/skills/openviking-model-evaluator/SKILL.md)。

1. **统一思考分离契约**：所有候选大模型统一在“思考分离模式（Thinking Separation Mode）”下进行全量 5 场景评测（内部深度推导 + 外部 100% 裸 JSON / YAML 纯净正文）；
2. **标准答案（Ground Truth）与物理断言链**：
   - **S1 资源分级提纯 (L0/L1/L2)**：必须检出 3 大隐藏架构安全风险（MITM下载、暴力替换、时间戳缓存失效）；
   - **S2 检索意图推导与语义重写**：必须精准捕获 8 大核心系统实体与 3 路正交重写 Query；
   - **S3 跨会话主记忆提纯**：必须 100% 还原 5 大不可变工程事实（NO GREEN、429降级、Priority降序、别名分级展示、Git Tag）；
   - **S4 知识图谱关联推导**：必须推导出标准因果拓扑与耦合维度（`depends_on` + `traffic_routing`）；
   - **S5 技能规范审计与修复**：必须覆盖 4 大硬性配置参数并输出标准 YAML Frontmatter；
3. **官方基准线 (Golden Baseline)**：
   - **欧尼 (Ornith 1.5 35B 本地实机)**：综合得分 **`94.0 分`**（格式 25/25，标准答案命中 40/40 满分，纯净度 15/15 满分，总耗时 63.32s）。

---

## 🚀 八、 Antigravity 核心 MCP + Hook 极速复用指引 (Onboarding SSOT)

任何开发者或新环境拉取本仓库代码后，只需**执行一行初始化脚本**，即可 100% 自动对齐 Antigravity 核心 MCP 与 Hook：

```bash
bash scripts/setup_antigravity.sh
```

### 极速复用实现机制（零手动门槛）：
1. **工作区级 Hook 原生内置**：
   - 配置收口在 [`.agents/hooks.json`](file:///home/skloxo/aho/openclaw/project/.agents/hooks.json)，采用相对路径执行 [`.agents/hooks/ov_pre_invocation.py`](file:///home/skloxo/aho/openclaw/project/.agents/hooks/ov_pre_invocation.py)；
   - 随 Git 仓库直接分发，任何人在 Antigravity 打开此目录时**自动静默激活**，零配置；
2. **核心 MCP 幂等注入**：
   - `scripts/setup_antigravity.sh` 会自动检测当前机器的绝对路径，并将 `[CORE]` 模式的 `openviking` 54 个全量工具无损合并注入到开发者的 `~/.gemini/config/mcp_config.json` 中；
3. **连通性极速验证**：
   - 运行后自动发起 `/health` 探针，3 秒内完成环境闭环验证。

---

## 🛰️ 九、 全集群卫星节点 Hook 与 MCP 职责边界架构规范 (Satellite Hook & MCP Boundary Spec) ⭐⭐⭐⭐⭐

> **核心物理公理**：Hook 为开局轻量只读约束（递小抄），MCP 为思考推理动态工具（伸出双手）。二者严格正交接力，彻底杜绝职责膨胀、回车假死与重复盲搜。

### 9.1 四大物理军规 (Four Non-Negotiable Laws)
1. **职责严格解耦律**：Hook 专职负责开局轻量预取；大文件深读、代码拓扑解析与双写存盘 100% 留给 MCP 动态工具；
2. **毫秒预算熔断律**：命中本地意图缓存 < 5ms，网络请求超时上限硬卡 2.5s（本地 1.5s）。遇到网络抖动或超时，必须在 50ms 内静默返回 `{}` 并以退出码 0 退出，绝不阻塞用户界面；
3. **零扰动静默降级律**：Hook 严格只在 `PreInvocation`（或 `UserPromptSubmit`）单点挂载，严禁滥挂 `PostInvocation`/`ToolCall`；对于 `continue`、`ok`、`？` 等无实质语义的单字步进词，自动向前寻源或静默跳过；
4. **权威专区隔离律**：Hook 探针限定只检索 `master_memory/` 权威脱水专区（Top-2 结果，单条截断 ≤ 200 字符），严禁递归遍历全量海量未脱水代码树。

### 9.2 Hook 与 MCP 接力协同契约（防盲搜与防内耗）
- **事实已知效应**：上下文头部已注入【OpenViking 记忆预取】摘要时，模型天然将其视为已知既定事实直接推理，**严禁使用相同关键词再次发起 `openviking_find` 盲搜**；
- **由搜转读 (Find ➔ Read)**：若小抄摘要不足以支撑复杂操作，模型必须拿着注入文本中的 URI，直接调用 `openviking_read` 深读全文；
- **只读与沉淀权责**：Hook 绝对只读；Agent 产生的踩坑经验与新规则，统一通过 MCP `openviking_record_evolution_lesson` 双向写入体外大脑。

### 9.3 权限分层与安全防线
- **Hook 端侧**：仅允许使用卫星专用只读 `User API Key`（`auth_mode=trusted`），**绝对禁止在 Hook 脚本或工作区环境变量中硬编码 Root Admin Key**；
- **MCP 侧**：卫星节点仅暴露已通过实测的 **16 大精简安全工具矩阵**（4 检索 + 6 排障 + 6 拓扑），切除 `server_control`、`backup`、`restore` 等特权运维接口。

### 9.4 全集群卫星智能体自动化同频与自愈 (Fleet Ops SSOT) ⭐⭐⭐⭐⭐
- **技能与工具深度绑定**：[`satellite-fleet-ops`](file:///home/skloxo/aho/openclaw/project/.agents/skills/satellite-fleet-ops/SKILL.md) 技能与 OpenViking 原生 MCP 运维工具深度绑定：
  - `openviking_fleet_check(target_node="all")`：并发巡检全集群（2080Ti, 3070, Mac Studio）的 SSH、403 防线、规则存在性与真实数据探针；
  - `openviking_fleet_sync(target_node="all")`：一键自动向各节点下发最新 `satellite_mcp_server.py` 与全局 `AGENTS.md`，彻底消灭逐台手工改代码与粘配置。
- **自动触发铁律**：当用户提出“卫星运维”、“节点巡检”、“集群同频”、“3070/2080Ti 节点排障”等诉求时，Agent **100% 自动下意识直接调用上述 MCP 工具与技能闭环交付**，严禁让用户手动维护！

---

## 📱 十、 微信公众号文章高反爬免验证码自动读取契约 (WeChat Reader Anti-Ban SSOT) ⭐⭐⭐⭐⭐

> **核心物理公理**：微信公众号文章反爬 WAF 对外部搜索引擎 Referer（如 Google）及缺少微信移动端指纹的请求下发 302 重定向至 `wappoc_appmsgcaptcha` 滑块验证码；若短链 Base64 Key 长度超过 22 位则返回“参数错误”。

1. **下意识自动触发铁律**：
   - 只要用户提供 `mp.weixin.qq.com` 链接，**100% 下意识直接调用系统原生固化工具 `wechat-read <URL>`**；
   - **绝对禁止**使用通用 `read_url_content` 或普通爬虫裸抓；
   - **绝对禁止**等待用户手动提醒如何绕过反爬风控！
2. **底层实现与防线固化**：
   - 工具路径：`~/.local/bin/wechat-read`（软链接至 `scripts/wechat_reader.py`）；
   - **自动纠偏**：自动识别短链 Key 并截取合法 22 位，消除复制多字符引发的“参数错误”；
   - **指纹注入**：禁用默认 google referer，强制 `referer: https://mp.weixin.qq.com/`，伪装 Android 14 真实微信客户端指纹（MicroMessenger/8.x、XWEB内核），等待 `#js_content` 挂载，零滑块穿透率 100%。





