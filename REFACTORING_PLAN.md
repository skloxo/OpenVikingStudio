# OpenViking Studio — 唯一活跃原子工单看板 (REFACTORING_PLAN.md)

> **双轨制管理规约 (Dual-Track Management Rules)**：
> 1. **工单 ID 解耦 (Task ID Decoupling)**：卡片使用模块持久化 ID（如 `TASK-SKILL-01` / `TASK-HARNESS-01` / `TASK-LOOP-01`），**严禁在排期阶段过早绑定版本号**！插队/新增任务时可无缝创建新工单 ID，绝不引发重更名与多米诺重编号噩梦。
> 2. **阶段封板映射 (Milestone Tag Binding)**：按【阶段目标 Milestone】进行分组管理；只有当用户显式下达“封板/打 Tag 发版”指令时，AI 才有权限根据实际交付按顺序映射物理 Tag（如 `v1.2.1`）。
> 3. **本地私有留存**：本文件及内部研发记录只在本地管理 (`.gitignore`)，远程 GitHub 仓库保持绝对代码纯净与数据脱敏。

---

## 📅 当前核心排期阶段：Milestone Phase 1 (技能中心深度重构 ➔ 任务中心 ➔ Harness 引擎 ➔ Loop)

### [x] v1.2.25 — 全局字体排版硬下限规范 (≥11px)、分类短命名与伪状态拔除交付 (用户已验收通过 ✅)
- **Git Commit**: `feat(skills): typography min size >=11px, concise tab labels, and fake status badge removal v1.2.25`
- **Tag**: `v1.2.25`
- **修改文件**: `src/routes/skills/route.tsx`, `src/routes/skills/harness-logs.tsx`, `UI_SPECIFICATION.md`, `package.json`
- **主要交付**:
  1. **全局字体排版下限 (≥11px)**：全系统物理封杀禁用 `< 11px` 微字，卡片底栏与脚标字号提升至清晰舒适的 `12px` (`text-xs`) 与 `11px`；
  2. **信达雅分类短命名**：Filter Tab 标签精简干洗为 `全部` | `🤖 智能体` | `👤 个人偏好` | `💤 闲置`；
  3. **拔除伪状态角标**：彻底切除卡片中无信息增量的 `✅ 规范就绪` 假状态角标；
  4. **全局规则与开源轮子卡片建立**：在全局配置中确立开源轮子优先复用原则与最小字号规范。

### [x] v1.2.24 — [TASK-TASK-01] 任务中心 📜 任务执行日志 (Execution Trace Log) 与自愈流转交付 (用户已验收通过 ✅)
- **Git Commit**: `feat(tasks): add Line-by-Line Log Viewer and status flow trace in TaskDetailSheet v1.2.24`
- **Tag**: `v1.2.24`
- **修改文件**: `src/routes/tasks/-components/task-detail-sheet.tsx`, `package.json`
- **主要交付**:
  1. **📜 任务执行日志 (Execution Trace Log)**：在 TaskDetailSheet 中增设极客黑终端日志流，毫秒级还原 worker 物理工序 Trace；
  2. **一键复制与日志染色**：日志流自动高亮 `[SUCCESS]` / `[ERROR]` / `[WARN]` 并提供一键复制日志功能；
  3. **自愈流转闭环**：配合 [重新入队/自愈] 指令，实现挂起或异常任务无缝自愈恢复。

### [x] v1.2.23 — [TASK-SKILL-03] 僵尸闲置技能物理透视分栏与 Harness 精简建议 ✅
- **Git Commit**: `feat(skills): add idle skills tab and Harness asset optimization suggestion banner v1.2.23`
- **Tag**: `v1.2.23`
- **修改文件**: `src/routes/skills/route.tsx`, `package.json`
- **主要交付**:
  1. **`💤 僵尸闲置技能 (166)` 物理透视分栏**：提供专属 Filter Tab 快速切入近 24 小时零感应调用的离散技能视图；
  2. **Harness 技能资产优化建议 Banner**：当切入闲置试图时，直观提示复用率问题并给出向大 SOP 规约归档合并的白盒提速建议。

### [x] v1.2.22 — [TASK-SKILL-02] 175 技能卡片 24H 活跃、规范文件规模与健康度曝光 ✅
- **Git Commit**: `feat(skills): expose 24H activity, file size and readiness health badges on every card v1.2.22`
- **Tag**: `v1.2.22`
- **修改文件**: `src/routes/skills/route.tsx`, `package.json`
- **主要交付**:
  1. **物理 24H 活跃状态标记**：在每张卡片底部清晰标记 `🔥 24H 活跃` 或 `💤 闲置` 物理曝光；
  2. **规范文件与 SOP 规模**：卡片底部展现关联文件数与 SOP 规约尺寸 (如 `📁 5 文件 (1.8KB)`)；
  3. **健康度三态图标**：全量技能统一白盒直观输出 `✅ 规范就绪`。

### [x] v1.2.21 — [TASK-SKILL-01] 技能卡片脱噪与分类语义【信达雅】重构 ✅
- **Git Commit**: `feat(skills): refine skill card source badges and chinese self-explanations v1.2.21`
- **Tag**: `v1.2.21`
- **修改文件**: `src/routes/skills/route.tsx`, `package.json`
- **主要交付**:
  1. **【信达雅】分类标签语义化**：筛选 Tab 与卡片类型标签统一重构为人类自解释直觉语言：`🤖 智能体工程` 与 `👤 用户习惯`；
  2. **归属来源脱噪 (奥卡姆剃刀)**：干洗切除卡片标题旁花哨繁复的图标堆叠，替换为极客哑光三态来源 Badge（`系统内建` / `工作区` / `个人配置`）；
  3. **100% 地道中文自解释说明**：修复英文规范在自解释下的机械硬翻感，呈现流畅平滑的人话中文解释。

### [x] v1.2.20 — 修复 1936 开发服务器 Vite 热重载 HMR 刷屏与硬重载 ✅
- **Git Commit**: `fix(vite): ignore public/all_skills.json in Vite HMR watcher on 1936 to prevent browser hard reloads v1.2.20`
- **Tag**: `v1.2.20`
- **主要交付**:
  1. 物理定位 1936 端口 Vite 开发服务器无限热刷新硬重载的物理根因：`mcp_openviking_server.py` 定期同步写 `public/all_skills.json` 触发 Vite 默认 `full-reload` 全页硬重载；
  2. 在 `vite.config.ts` 的 `server.watch.ignored` 中添加 `**/public/all_skills.json` 与 `**/all_skills.json`，彻底禁止 Vite 对动态 JSON 的打断性硬刷新；
  3. 双向打通 1936 (Vite Dev Server) 与 1933 (OpenViking Web Studio) 的长效稳定运行。

### [x] v1.2.19 — 修复 TanStack Query 频繁自动重刷新与页码/抽屉清空倒退 ✅
- **Git Commit**: `fix(skills): stabilize TanStack query refetching with keepPreviousData to prevent UI flickering and pagination resets v1.2.19`
- **Tag**: `v1.2.19`
- **主要交付**:
  1. 屏蔽切屏与焦点切换时的打断性自动刷新 (`refetchOnWindowFocus: false`, `refetchOnReconnect: false`)；
  2. 结合 `placeholderData: keepPreviousData` 保持渲染连续性，彻底根治数据重加载导致 UI 闪烁、抽屉关闭及页码自动弹回第 1 页的问题；
  3. 技能列表与自演进监控 Query 统一拉长缓存有效期至 10 分钟。

### [x] v1.2.18 — 技能抽屉 L2 级关联源文件树全量探针感知与极速回退 ✅
- **Git Commit**: `fix(skills): scan and display full subfile/subdirectory trees for all skills v1.2.18`
- **Tag**: `v1.2.18`
- **主要交付**:
  1. 升级 `mcp_openviking_server.py` 的 `_auto_sync_skills()` 探针，物理遍历全盘 175 个技能的真实文件树与 `SKILL.md` 完整源码；
  2. 生成全量富信息 `all_skills.json`（含 `files` 节点与 `content` 源码），解决 66 个多文件技能在 L2 抽屉退化为单文件 `SKILL.md` 的问题；
  3. 前端 `fetchSkillDetail` 网关 404 熔断时物理平滑回退至预探针索引数据。

### [x] v1.2.17 — Harness 技能自演进卡片双轨展示：人工精编 36 + VK 自动感应 16 ✅
- **Git Commit**: `feat(skills): show dual metric 36-manual + 16-auto in Harness card v1.2.17` + `fix: Wiki -> VK label correction`
- **Tag**: `v1.2.17`
- **主要交付**:
  1. 彻底厘清 36 与 16 两个数字的物理本质：36 = 人工精编 SOP 规约知识库条目数，16 = VK 自动感应触发的演进落盘次数；
  2. 技能中心 Harness 自演进卡片改为双栏并排：`36 精编规约 | 16 自动感应`；
  3. 卡片底部文案：`人工精编 + VK 自动感应双轨驱动`（修正语音识别 Wiki → VK）；
  4. Harness 全景监控页新增第 5 张统计卡：`磁盘动态落盘次数（store_calls）`。

### [x] v1.2.16 — Harness 全景监控新增磁盘动态落盘次数卡片 ✅
- **Git Commit**: `feat(harness): add 5th stat card for disk store_calls (dynamic evolution count) v1.2.16`
- **Tag**: `v1.2.16`
- **主要交付**:
  1. Harness 全景监控页 Banner 从 4 格扩展为 5 格（`sm:grid-cols-5`）；
  2. 新增第 5 张卡片"磁盘动态落盘次数"，直连 `harness_metrics.json` 的 `store_calls` 字段（17 次），语义与内置规约数（36）完全解耦；
  3. `lessonsCount` 还原为直连 `metrics.lessons_count` 动态真实值，不再硬锁 >= 36 门锁。

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

### 📌 [x] [TASK-SKILL-01] 技能中心【信达雅】分类语义重构 + 来源图标脱噪 + 100% 中文自解释 (已在 v1.2.21 交付 ✅)

**模块**：Skills Center (技能中心)  
**工单 ID**：`TASK-SKILL-01`  

---

### 📌 [x] [TASK-SKILL-02] 175 技能卡片物理调用频次/健康度曝光 + 标准分页器 (Pagination) (已在 v1.2.22 交付 ✅)

**模块**：Skills Center (技能中心)  
**工单 ID**：`TASK-SKILL-02`  

---

### 📌 [x] [TASK-SKILL-03] 僵尸闲置技能物理透视与 Harness 一键精简/合并提示 (解决 10.3% 复用率低根因) (已在 v1.2.23 交付 ✅)

**模块**：Skills Center & Harness (资产治理)  
**工单 ID**：`TASK-SKILL-03`  

---

### 📌 [x] [TASK-TASK-01] 任务中心 Task Center 全局白盒过滤、自愈状态流转与 Step 日志透视 (已在 v1.2.24 交付 ✅)

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

### 📌 P0: [ ] [TASK-HARNESS-WHEELS-01] 引入与跟进开源顶级轮子 (LLMLingua-2 & DSPy) 驱动技能自动提炼

**模块**：Harness Engine (自演进引擎)  
**工单 ID**：`TASK-HARNESS-WHEELS-01`  
**优先级**：P0 (高优先级)  
**来源**：用户指令 ("估计这种技能提炼的工具轮子 GitHub 上也有，不要纯手搓... 引入并持续跟进开源改进")  
**预计规模**：S (1 个迭代)

#### 1. 目标与描述
1. 物理引入 **`microsoft/LLMLingua-2`** (Prompt/Context 动态提炼与 Token 压缩) 与 **`stanfordnlp/dspy`** (SOP 指令自动编译与优化)，作为 Harness 引擎的核心依赖库。
2. 建立开源上游版本跟踪与同步机制，长效吸收社区最新演进，拒绝闭门造车纯手搓。
3. 驱动闲置/重叠技能的一键自动化提炼与归档。

#### 2. 量化验收标准
- [ ] 物理引入 `llmlingua` 与 `dspy-ai` 包作为 Python 后端核心依赖。
- [ ] 在 Harness 引擎中融合开源提炼算法，提供闲置技能一键提炼/归档建议。

---

### 📌 P0: [ ] [TASK-HARNESS-03] Harness 后台 Daemon 独立自演进与 Prompt Auto-Tuning 飞轮 (解决伪自动化)

**模块**：Harness Engine (自演进引擎)  
**工单 ID**：`TASK-HARNESS-03`  
**优先级**：P0  
**来源**：用户指导 ("这不是还是 Harness 没有自动演进吗？")  
**预计规模**：S (1 个迭代)
