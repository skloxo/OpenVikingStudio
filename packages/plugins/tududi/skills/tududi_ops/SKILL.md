---
name: tududi_ops
description: Tududi (todo) 任务管理系统生产级运维、OKR+GTD 五层标准架构、Agent 三大自动作业反射、原生 FastMCP 65 算子实战调用 SOP 与防标签滥用标准化技能 (Tududi Ops & OKR-GTD Governance SOP)。
---

# 📋 Tududi (todo) 全域任务管理与 OKR+GTD 生产力中枢规约契约 (Tududi Agent Rules SSOT)

本规约是全集群智能体（Google Antigravity、DeepSeek Harness、Pi Agent）在涉及任务、待办、项目、习惯、目标与收集箱管理时的常驻潜意识法则。

---

## 一、 意图识别与工具分流第一公理 (Intent Routing Axiom)
1. **自然语言第一反射**：凡人类提及 **“Tududi”、“todo”、“待办”、“任务清单”、“今日任务”、“收集箱 (Inbox)”、“习惯打卡”、“项目进度”、“周报/月报/OKR进度”** 时，必须 **100% 路由至 `tududi` (`tududi_core`) MCP 工具集**，并遵循 `tududi_ops` 技能规范；
2. **职责边界清晰**：
   - **Tududi (`https://todo.tide.red`)**：统管全集群与人类的 **OKR 目标 (Goals)、业务项目 (Projects)、日常/研发任务 (Tasks & Subtasks)、周期习惯 (Habits)、收集箱 (Inbox) 与参考笔记 (Notes)**，是人类网页端零 Token 感知进度与导出周报/月报/OKR 的唯一事实源；
   - **代码仓库 `REFACTORING_PLAN.md`**：仅记录单仓库内部文件级编码微步，模块级与业务级任务一律在 Tududi 统管。

---

## 二、 OKR + GTD 五层标准映射定式 (5-Layer Hierarchy SSOT)
全系统实体严格遵循「上半截管 OKR 战略交账、下半截管 GTD 落地执行」的五层咬合结构，严禁混层：

1. **L1 `Area (领域)` —— 公私最高物理边界（永不结案）**：
   - 全系统仅设 2 个顶级领域：**`工作`** (`id: 6, uid: "bchf3cj1tr44xv7"`) 与 **`个人`** (`id: 7, uid: "f9hshwtupevwy8q"`)。
2. **L2 `Goal (目标)` —— 对应公司年度/季度 OKR 考核大项 (`O`)**：
   - 仅在 `工作` 领域下建立，100% 严格对齐公司提交的 OKR 原文名称：**`O1：数字化产品创新建设`**、**`O2：后勤服务系统建设`**、**`O3：行政办公 AI 辅助系统`**、**`O4：部门例行工作`**（`个人` 领域无需建 OKR 目标）；
   - **严禁加额外括号解释或将软件小迭代版本号建成 Goal**。
3. **L3 `Project (项目)` —— 具体业务系统/专案主体（直接承接核心 `KR` 载体）**：
   - **线上 Tududi 项目命名定式 (`Ox-KRx 业务名称`)**：
     - **工作领域项目**：必须且仅允许采用 **`Ox-KRx 业务名称`** 格式！
       - O1: `O1-KR1 网格化管理平台` #1
       - O2: `O2-KR1 寓+干部公寓` #2、`O2-KR2 智能门锁` #22、`O2-KR3 物业系统` #23、`O2-KR4 安防监控` #24
       - O3: `O3-KR1 AI监控` #17、`O3-KR2 安防监控中台` #21、`O3-KR3 任务调度中枢 (Tududi)` #20
       - O4: `O4-KR1 技术运维与例行保障` #15、`O4-KR2 滴滴企业打车` #16、`O4-KR3 园区门户` #19、`O4-KR4 仓储方案` #18
       - **物理根因**：通过 `Ox-KRx` 前缀，让所有工作项目自动按 O1 ➔ O4 严格聚合，与上方【目标 (4)】达成 1:1 垂直对齐，同时保全业务中文自解释性，**绝对禁止纯代号（如裸写 `O1KR1`）**！
     - **个人领域项目**：遵循「1 个代码项目 ≡ 1 个 Todo 专案」第一性原理，采用 `P01` ~ `P12` 前缀（`P01 OpenViking (VK)`、`P02 mop 移动小脑`、`P03 CPA 算力网关`、`P04 Komari 统一监控` 等），自动与工作 OKR 隔离沉底；
   - **本地磁盘物理文件夹命名定式 (Local Folder SSOT)**：
     - **绝对禁止在本地文件夹名重复叠加 `Ox-KRx`**（杜绝 `Work/O2_.../O2-KR1_...` 路径口吃与长度超标）；
     - 本地文件夹坚决保持树形纯净层级：`Work/Ox_考核目标名/0y_业务名称/`（例如：`Work/O2_后勤服务系统建设/01_寓+干部公寓/`）；
     - **两端映射公理**：线上与本地通过自然编号直接 1:1 映射：`01 ≡ KR1`、`02 ≡ KR2`、`03 ≡ KR3`、`04 ≡ KR4`；
   - **严禁将单个功能开发卡（如 `TASK-042`）提拔建成独立 Project**。
4. **L4 `Tag (标签)` —— 横切区分任务的「工作性质」**：
   - **核心四正交标签**：严格收敛且锁死为 4 个：**`开发`**、**`运维`**、**`规划`**、**`缺陷`**（数据库内保持 `pinned: false` 纯净沉底，禁止置顶到侧栏「书签」栏与项目混杂）；
   - **绝对封杀时间标签**：🚫 **严禁使用 `today` 或 `someday`**（Tududi 原生拥有 Defer Until 推迟时间与 Today 智能四分区，打时间标签属于老旧纸质 GTD 陋习，造成双重维护与认知污染）；
   - **绝对封杀动作/状态标签**：🚫 **严禁使用 `汇报` 标签**（汇报为任务完工后的总结动作，沉淀入 `note`，并非任务工种属性）；
   - **绝对封杀业务标签**：🚫 **严禁创建或使用项目名（如 `园区门户`）、技术栈（如 `Vue`）或优先级标签**。
5. **L5 `Task ➔ Subtask (两层任务)` —— 落地执行动作**：
   - **任务标题极致脱水 (8 ~ 18 字动宾短语)**：
     - **绝对禁止标题前缀中括号**：🚫 严禁在标题手写 `[运维]`、`[开发]` 等前缀（由下方 Tag 直观呈现）；
     - **绝对禁止标题硬编码软编号**：🚫 严禁在标题手写 `(T04-0004)`、`(TASK-045)` 等伪编号（充分复用系统全局唯一递增自增 ID `#ID` 与 UID）；
     - **绝对禁止标题重复项目名**：🚫 在 `O1-KR1 网格化平台` 下，严禁标题写 `网格化平台：...`，直接以精准动词开头（如 `编制业务指引手册与网格员培训`）；
   - **任务详情 (Task.note) 结构化承接**：
     - 标题放动宾靶心，全部技术细节、背景和验收标准统一下沉到 `note`，采用标准三段式：
       - `【业务背景】`：简述业务诉求、痛点与前置来龙去脉；
       - `【实施要点】`：分点列出模块设计、排查路径或代码改造点；
       - `【关联编号/验收指标】`：历史文档编号（如 `T04-0004`）与量化验收指标；
   - **执行人 (assigned_to) 强制注入**：
     - 智能体新建或更新任务时，100% 默认注入 `assigned_to="07mah9uku662d6u"`（用户 `skloxo`），确保侧边栏“分配给我”视图满血可用；
   - **子任务 (Subtasks) 边界与版本迭代定式**：
     - **何时建 Subtask**：单次专注会话无法完工、需要拆解为 2~6 个阶段性检查点（Checklist）的复杂任务；
     - **版本迭代任务定式**：软件集中发版或中型专题攻坚时，创建父级 `Task`（如 `发布网格化平台 v0.1.150`），将具体的若干个微修复与独立模块作为 `Subtasks` 挂在下方；通过 Subtask 原生进度条直观推进，严禁在 Project 根部散落海量微型碎片工单。

---

## 三、 Agent 三大自动作业神经反射 (Three Agent Reflexes)
1. **开局自动领活 (Read on Start)**：新会话提及具体项目或询问下一步任务时，Agent 自动调用 `list_tasks(project_id=..., status="in_progress")` 与 `list_tasks(project_id=..., status="planned")` 盘点当前进度，免除人类翻找文档负担；
2. **过程随手记分支 (Capture on the Fly)**：开发或排障中途发现顺带缺陷、分支问题或新优化点时，不打断当前主线，立即调用 `create_task` 挂入对应 `Project`（设 `status="not_started"`，打 `缺陷` 或 `开发`/`运维` 标签，默认分配给 `skloxo`），确保 100% 零遗忘；
3. **完工强制留双行汇报锚点 (Quantified Closure)**：任务达成调用 `complete_task` 前，必须通过 `update_task` 在任务 `note` 中写入结构化交付总结（供周报/月报/OKR 直接抽取）：
   - `【达成成果】`：量化交付物与真实物理锚点（具体模块、接口数、设备数、单测通过数）；
   - `【解决挑战】`：解决的业务痛点、技术难点或理顺的跨部门协同机制。

---

## 四、 65 项 MCP 工具入参异构避坑铁律 (Parameter Contract Guardrails)
1. **主键字段名异构律 (`id` vs `uid`)**：
   - **Task（任务）专属主键为 `id`**：调用 `get_task`、`update_task`、`complete_task`、`delete_task`、`skip_task_occurrence`、`add_task_comment`、`list_task_comments`、`create_task_relation`、`list_task_relations`、`remove_task_relation` 时，主键参数名一律为 **`id`**；`add_subtask` 父任务参数名为 **`parent_id`**；
   - **其余全部实体主键为 `uid`**：调用 Area、Project、Goal、Habit、Inbox、Note、Person、Tag、View 的 `get_*`、`update_*`、`delete_*`、`log_habit_completion`、`process_inbox_item` 时，主键参数名一律为 **`uid`**（15 位字符串）。
2. **外键关联字段律**：
   - `create_task` / `update_task` 绑定项目传 **`project_id`**（数字 ID），绑定领域传 **`area_id`**（数字 ID）或 **`area_uid`**（字符串 UID），执行人传 **`assigned_to`**；
   - `create_project` / `update_project` 绑定领域传 **`area_id`**（数字 ID），绑定目标传 **`goal_id`**（数字 ID）或 **`goal_uid`**（字符串 UID）；`create_goal` 绑定领域传 **`area_id`**（数字 ID）。
3. **优先级 (`priority`) 类型异构律**：
   - **任务与习惯 (`create_task` / `update_task` / `add_subtask` / `create_habit`)**：`priority` 为**字符串枚举** `"none" | "low" | "medium" | "high"`（🚫 **绝对禁止传 `"urgent"`**）；
   - **项目 (`create_project` / `update_project`)**：`priority` 为**数字枚举** `0` (低)、`1` (中)、`2` (高)。
4. **状态 (`status`) 枚举律**：
   - 任务与项目的 `status` 严格限定为：**`"not_started" | "planned" | "in_progress" | "waiting" | "done" | "cancelled"`**（🚫 **绝对禁止传 `"todo"`**）；
   - 目标 (`Goal`) 的 `status` 限定为：**`"active" | "achieved" | "paused" | "dropped"`**，周期 `horizon` 限定为 **`"season" | "year"`**。

---

## 五、 Tududi PWA Service Worker 缓存穿透与 i18n 热更新 SOP (SW Cache Penetration SSOT)
1. **PWA 缓存死锁物理真因**：
   - Tududi 前端注册常驻 `sw.js`，采用 Cache-First 策略将非 navigation GET 请求（包括 `/locales/zh/translation.json?v=2`）永久缓存在客户端 `CacheStorage`（如 `tududi-v3`）；
   - 常规浏览器刷新（F5 / Ctrl+F5）由于请求被本地 Service Worker 截胡，不会到达服务端，造成“服务端已更新但浏览器永远渲染旧英文”的假死现象；
2. **三阶解耦与彻底穿透规范**：
   - **阶 1（SW 版本跃迁）**：服务端更新 `sw.js` 中的 `CACHE_VERSION`（如 `tududi-v3` ➔ `tududi-v4`），强制触发浏览器端 SW `install` ➔ `skipWaiting` ➔ `activate`，自动调用 `caches.delete(...)` 物理销毁旧缓存；
   - **阶 2（SW 请求旁路白名单）**：在 `sw.js` 的 `fetch` 事件中，针对 `n.pathname.startsWith("/locales/")` 强制执行 `e.respondWith(fetch(t))`，彻底封杀对多语言字典的本地缓存；
   - **阶 3（云端网关双保险）**：Nginx 对 `/sw.js` 与 `/locales/` 强制下发 `add_header Cache-Control "no-store, no-cache, must-revalidate, max-age=0";`；
3. **i18n 前端双层 Fallback 完备性铁律**：
   - 前端代码采用 `t('domain.key', 'Default English')`，缺失 key 时自动 fallback 到英文。必须结合 AST/正则提取全量键值（如 `admin.insights.*` 28 个动态模板、`admin.trends.*`、`common.goal/priority/due/tags`），杜绝局部盲猜翻译。


---

## 六、 Tududi 全域健康巡检与任务批量规范化清洗 SOP (Global Audit & Batch Sanitization SSOT)
1. **双网端点直连公理 (Dual-Link Endpoint Axiom)**：
   - 凡在非 Mac 本地局域网宿主（如 2080Ti / 3070 / 云端机器）执行批量脚本或自动化探针时，**强制优先直连公网 443 穿透端点 (`https://todo.tide.red/api/mcp`)**；
   - 严禁在远程或外网环境盲猜绑定 `10.128.226.5:3002` 局域网 IP，杜绝因 `ConnectTimeoutError` 导致大批量任务执行死锁。
2. **数据契约真实映射律 (Schema Truth Axiom)**：
   - **Task 任务主键与标题**：更新与查询主键为 `id` (数字)，标题键名为 `name` (并非 `title`)，所属项目对象为大写 `Project`；
   - **执行人强制绑定**：未指派执行人的任务必须批量补齐 `assigned_to="07mah9uku662d6u"` (用户 `skloxo`)，保障“分配给我”视图 100% 满血可用。
3. **标题与详情深度脱水规范 (Title & Note Decoupling)**：
   - **绝对封杀中括号**：必须通过正则 `^[\[【](开发|运维|规划|缺陷|汇报|待办|测试)[\]】]\s*` 剥离方括号工种前缀，由下方正交 Tag Badge 自解释；
   - **软编号与链接下沉**：标题中手写的 `TASK-xxx` 软编号及超长 URL (如微信文章) 必须下沉存入详情 `note` 中的 `【关联编号】` 与 `【参考资料】`，标题只留 8~18 字精炼动宾短语。
4. **自定义视图死引用排查律 (View Dead-Reference Scrubbing)**：
   - 凡系统执行标签废黜（如删除 `汇报`、`today`）后，必须同步审计自定义视图 (`list_views`)，彻底移除过滤条件中已失效的标签死引用。

---

## 七、 单一真相源彻底收敛与严禁双向抄写铁律 (Single Source of Truth & Zero Two-Way Sync Axiom)
1. **任务态单一收口公理 (Task State SSOT)**：
   - 全集群所有工作与研发任务的【生命周期、排期、责任人、进度与交付状态】100% 且仅允许在 Tududi 线上调度中枢 (`https://todo.tide.red`) 维护；
   - 人类与智能体找任务、领活、查待办，第一条件反射直奔 Tududi，严禁在本地代码仓或个人笔记中建立分散的待办副本。
2. **严禁双向抄写与伪对账铁律 (Zero Two-Way Sync Invariant)**：
   - 在 Tududi 创建或流转任务后，**绝对禁止跑回代码仓 Markdown（如 REFACTORING_PLAN.md、README.md）把 Todo 任务编号与状态反向抄写一遍**；
   - 代码仓内的文档严格限定为战地单测与技术实现微步，杜绝因机械式“两头抄”引发的文档漂移、格式冲突与死数据熵增。
3. **跨 Agent 调度总线身份契约 (Agent Dispatching Identity)**：
   - 服务类智能体（Antigravity, DSH, MOP, Komari, CPA Ops）作为独立协作者纳入 Tududi 调度体系；
   - 任务被指派给智能体后，智能体全自动领活并按【一卡一命一停手】施工，结案强制留双行交付总结回填至 task.note。

