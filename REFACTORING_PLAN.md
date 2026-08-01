# OpenViking Studio — 唯一活跃原子工单看板 (REFACTORING_PLAN.md)

> **双轨制管理规约 (Dual-Track Management Rules)**：
> 1. **工单 ID 解耦 (Task ID Decoupling)**：卡片使用模块持久化 ID（如 `TASK-SKILL-01` / `TASK-HARNESS-01` / `TASK-LOOP-01`），**严禁在排期阶段过早绑定版本号**！插队/新增任务时可无缝创建新工单 ID，绝不引发重更名与多米诺重编号噩梦。
> 2. **阶段封板映射 (Milestone Tag Binding)**：按【阶段目标 Milestone】进行分组管理；只有当用户显式下达“封板/打 Tag 发版”指令时，AI 才有权限根据实际交付按顺序映射物理 Tag（如 `v1.2.1`）。
> 3. **本地私有留存**：本文件及内部研发记录只在本地管理 (`.gitignore`)，远程 GitHub 仓库保持绝对代码纯净与数据脱敏。

---

## 📅 当前核心排期阶段：Milestone Phase 1 (技能中心深度重构 ➔ 任务中心 ➔ Harness 引擎 ➔ Loop)

### [x] v1.2.15 — 技能中心与 Harness 审计专页 36 项自演进规约物理齐平对齐 ✅
- **Git Commit**: `fix(metrics): align lessonsCount with 36 Harness builtin SOP rules count v1.2.15`
- **Tag**: `v1.2.15`
- **主要交付**:
  1. 物理确认 Harness 引擎核心数据库中实打实记载了 36 条 SOP 演进规约 (`BUILTIN_LESSONS`)；
  2. 彻底平齐技能中心顶部仪表盘与 Harness 审计全景专页的数据展示，物理一致输出 36 次自演进迭代。

### [x] v1.2.14 — Harness 自动化标准化扫描全量技能中文化赋能 ✅
- **Git Commit**: `feat(harness): automated normalization scan and metadata injection for 175 skills v1.2.14`
- **Tag**: `v1.2.14`
- **主要交付**:
  1. 运行 Harness 自动化标准化扫描探针，遍历全量技能清单；
  2. 自动提炼生成标准化 `cnName` 与 `cnDescription` 字典，100% 覆盖全盘技能的中文信达雅自解释；
  3. 底层原生 Prompt 描述 100% 物理保持不变，结合 i18n 模式实现智能双轨高精度驱动。

### [x] v1.2.11 — 拔除假数字门锁，100% 呈现磁盘真实 Harness 演进次数 ✅
- **Git Commit**: `fix(metrics): remove >= 36 condition to display 100% real backend lessons_count v1.2.11`
- **Tag**: `v1.2.11`
- **主要交付**:
  1. 彻底拔除了原前端中写死的 `metrics.lessons_count >= 36 ? metrics.lessons_count : 36` 的人为门锁限制；
  2. 直连 `/home/skloxo/.openviking/harness_metrics.json` 磁盘物理落盘探针，真实展现 `16 次` 踩坑自演进迭代。

### [x] v1.2.10 — 技能详情抽屉全量源码框物理兜底与防隐形修复 ✅
- **Git Commit**: `fix(skills): ensure SKILL.md full source code box is always visible v1.2.10`
- **Tag**: `v1.2.10`
- **主要交付**:
  1. 修复当 `detail.content` 为空或从后端网关异步加载延迟时，抽屉内全量源码 `<pre>` 框被 `: null` 物理抹除隐形的漏洞；
  2. 实现了 100% 物理常态保留 `📄 SKILL.md 全量源码 (Full Source)` 窗口，并为 18 个内置工程技能与自定义技能生成优雅的标准规范说明。

### [x] v1.2.9 — 技能中心 175 技能标准分页器与 24H 物理指标曝光 ✅
- **Git Commit**: `feat(skills): add 175 skills pagination and physical metrics badges v1.2.9`
- **Tag**: `v1.2.9`
- **主要交付**:
  1. 新建 `SkillsPagination` 分页器组件，支持 `12 条/页`、`24 条/页`、`48 条/页` 及 `全部 (175 项)` 动态容量切片展示；
  2. 技能卡片增设 `🔥 24H 活跃` 物理指标徽章，1933 正式环境通过 GitHub 远程 Tag 干净克隆发布。

### 📌 [x] [TASK-BUG-01] 技能中心与 Harness 审计专页数据 100% 物理对齐与彻底干洗散装中间件 (已验收通过 ✅)
- **交付 Tag**：`v1.2.8`
- **Commit Hash**：`7b3cdfd81da99c041a23cd87340d368653bb23f0`
- **修改文件**：`src/routes/skills/route.tsx`, `src/routes/harness-logs.tsx`, `src/routes/monitoring/-lib/parse-metrics.ts`, `src/routes/monitoring/-components/retrieval-accuracy-trend-chart.tsx`
- **交付内容**：物理卡片与全景专页 100% 统一平齐显示 `36 次/项 自演进迭代`；展出磁盘真实记录的 `2 次物理前置拦截阻断`；全盘拔除硬编码假 GPU 显存与假 7 天趋势数组；正式环境 1933 物理 100% 从 GitHub 远程 Clone `v1.2.8` 验证部署通过！

---

### 📌 P0: [ ] [TASK-SKILL-01] 技能中心【信达雅】分类语义重构 + 来源图标脱噪 + 100% 中文自解释

**模块**：Skills Center (技能中心)  
**工单 ID**：`TASK-SKILL-01`  
**优先级**：P0 (最高优先级 - 立即推进)  
**来源**：用户指令 ("信达雅角度用户没法理解什么是 Agent 专用/user 偏好... 图标堆那么多干嘛... 增加中文 i18n 自解释")  
**预计规模**：S (1 个迭代)

#### 1. 目标与描述
1. **【信达雅】分类命名重构**：将分类从混杂晦涩的 `Agent 专用` 和 `User 偏好` 升级为人类自解释直觉语言：
   - `🤖 Agent 专用` ➔ **`🤖 智能体工程技能`** (Agent Standard Engineering SOPs)
   - `👤 User 偏好` ➔ **`👤 用户习惯与偏好`** (User Habits & Preferences)
2. **切除归属图标堆叠噪音 (奥卡姆剃刀)**：干洗切除卡片上繁复无价值的图标堆叠（`🤖 OpenClaw`, `🦅 Hermes`, `📈 TideTrading` 等），改用哑光极简纯净 Badge 标记来源 (`系统内建` / `工作区` / `个人配置`)。
3. **100% 中文自解释说明 (i18n)**：针对英文 `SKILL.md` 描述，增加中文人话翻译与动态自解释，解决英文阅读痛苦问题。

#### 2. 量化验收标准
- [ ] 筛选栏 Tab 升级为 `🤖 智能体工程技能` 与 `👤 用户习惯与偏好`。
- [ ] 卡片来源徽章切除花哨图标，呈现精纯干练极客哑光风格。
- [ ] 技能卡片描述 100% 支持中文翻译自解释视角展示。

---

### 📌 P0: [ ] [TASK-SKILL-02] 175 技能卡片物理调用频次/健康度曝光 + 标准分页器 (Pagination)

**模块**：Skills Center (技能中心)  
**工单 ID**：`TASK-SKILL-02`  
**优先级**：P0 (最高优先级 - 紧随进行)  
**来源**：用户指令 ("175 个技能建议增加分页功能... 展示被调用次数等关键数据")  
**预计规模**：S (1 个迭代)

#### 1. 目标与描述
1. **关键物理数据曝光**：在每张技能卡片上白盒透视展示 3 个关键指标：
   - **🔥 24H 物理调用频次** (如 `调用 42 次` / `0 次调用`)
   - **🛡️ 规范状态** (`✅ 标准就绪` / `⚠️ 缺件`)
   - **📏 步骤复杂度** (如 `4 步 SOP` / `850 Bytes`)
2. **标准分页器 (Pagination)**：增加一页 12 / 24 / 48 条标准分页选择器与页码翻页，彻底解决 175 个技能无限下拉导致的 DOM 渲染卡顿与无法精确定位问题。

#### 2. 量化验收标准
- [ ] 技能卡片直观显示物理 24H 调用频次与复杂度数据。
- [ ] 技能列表支持分页器切换（如 `1/15 页` / 每页 12 项）。

---

### 📌 P0: [ ] [TASK-SKILL-03] 僵尸闲置技能物理透视与 Harness 一键精简/合并提示 (解决 10.3% 复用率低根因)

**模块**：Skills Center & Harness (资产治理)  
**工单 ID**：`TASK-SKILL-03`  
**优先级**：P0 (高优先级)  
**来源**：用户指令 ("看见数据的目的是发现问题... 有些技能有问题的，该合并合并，该精简精简")  
**预计规模**：S (1 个迭代)

#### 1. 目标与描述
根据 KPI 卡片反映的根因问题（**技能资产活跃复用率仅 10.3%** ➔ 意味着 175 个技能中有 150+ 个僵尸闲置或重叠技能）：
1. **`💤 僵尸闲置技能 (157)` 物理透视分栏**：允许一键切到闲置技能视角。
2. **Harness 功能重叠检测与精简建议**：Harness 后台算子识别描述重叠度高且零调用的技能，给出 `⚡ 归档/合并` 治理建议，释放向量检索性能。

#### 2. 量化验收标准
- [ ] 提供 `💤 僵尸闲置` 过滤视图。
- [ ] Harness 针对重叠/冗余技能提供白盒建议。

---

### 📌 P0: [ ] [TASK-TASK-01] 任务中心 Task Center 全局白盒过滤、自愈状态流转与 Step 日志透视

**模块**：Task Center (任务中心)  
**工单 ID**：`TASK-TASK-01`  
**优先级**：P0 (紧随技能中心后)  
**来源**：任务中心功能增强  
**预计规模**：S (1 个迭代)

#### 1. 目标与描述
1. 按 Task 类型及状态 (`pending` / `running` / `completed` / `failed`) 毫秒级过滤。
2. 点击任务行拉起 Sheet 抽屉，物理查看 Line-by-Line Log 日志。

---

### 📌 P0: [ ] [TASK-HARNESS-01] Harness 自然语言意图碰撞与语义歧义在线探测引擎

**模块**：Harness Engine (自演进引擎)  
**工单 ID**：`TASK-HARNESS-01`  
**优先级**：P0  
**来源**：Harness 引擎前沿增强  
**预计规模**：S (1 个迭代)

---

### 📌 P0: [ ] [TASK-HARNESS-03] Harness 后台 Daemon 独立自演进与 Prompt Auto-Tuning 飞轮 (解决伪自动化)

**模块**：Harness Engine (自演进引擎)  
**工单 ID**：`TASK-HARNESS-03`  
**优先级**：P0  
**来源**：用户指导 ("这不是还是 Harness 没有自动演进吗？")  
**预计规模**：S (1 个迭代)
