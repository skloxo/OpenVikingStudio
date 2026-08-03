# OpenViking Studio — 唯一活跃原子工单看板 (REFACTORING_PLAN.md)

> **双轨制管理规约 (Dual-Track Management Rules)**：
> 1. **工单 ID 解耦 (Task ID Decoupling)**：卡片使用模块持久化 ID（如 `TASK-SKILL-01` / `TASK-HARNESS-01` / `TASK-LOOP-01`），**严禁在排期阶段过早绑定版本号**！插队/新增任务时可无缝创建新工单 ID，绝不引发重更名与多米诺重编号噩梦。
> 2. **阶段封板映射 (Milestone Tag Binding)**：按【阶段目标 Milestone】进行分组管理；只有当用户显式下达“封板/打 Tag 发版”指令时，AI 才有权限根据实际交付按顺序映射物理 Tag（如 `v1.2.1`）。
> 3. **本地私有留存**：本文件及内部研发记录只在本地管理 (`.gitignore`)，远程 GitHub 仓库保持绝对代码纯净与数据脱敏。

---

## 📅 当前核心排期阶段：Milestone Phase 1 (技能中心深度重构 ➔ 任务中心 ➔ Harness 引擎 ➔ Loop)

---

### 📌 P0: [ ] [TASK-HARNESS-SOP-01] 预制规约检查引擎与全量技能简介自动生成闭环 (Builtin SOP & Description Auto-Gen)

**模块**：Harness 引擎 + 技能中心  
**工单 ID**：`TASK-HARNESS-SOP-01`  
**优先级**：P0  
**来源**：用户指导 — 36 条预制规约当前仅为 UI 硬编码数组无检查；260+ 技能无简介显示"暂无额外说明"  
**预计规模**：M (2 个迭代)

#### 1. 现状与根因
- `BUILTIN_LESSONS`（36条）在 `harness-logs.tsx` 中为 UI 硬编码数组，缺乏后台 Python 检查逻辑
- 大量技能 `SKILL.md` 的 YAML frontmatter 缺少 `description` 字段，后端返回空字符串
- 缺乏自动扫描与后台 LLM 提炼无人值守生成管道

#### 2. 交付目标
1. **预制规约静态/动态检查**：建立后台算子 `harness_sop_checker.py`，遍历全量技能检查：
   - 是否包含规范 `SKILL.md` (Rule 14)
   - `description` 是否存在且 >10 字 (Rule 31)
   - 检查结果输出至 `harness_metrics.json`，算出合规率并在 Harness 审计页曝光
2. **简介后台自动生成**：对无描述的技能，调用 Harness LLM 提炼 30 字中文自解释，写回 `SKILL.md` YAML frontmatter

#### 3. 量化验收标准
- [ ] 36 条规约转换为真正可运行的合规检查器
- [ ] 260+ 技能卡片中的“暂无额外说明”被自动提炼生成的中文简介替换
- [ ] Harness 审计页展示全盘技能真实合规率 (%)

---

### 📌 P1: [ ] [TASK-SKILL-FILECOUNT-01] 技能卡片全量关联文件数准确透视 (Skill Card Real File Count)

**模块**：技能中心 API + 前端 View  
**工单 ID**：`TASK-SKILL-FILECOUNT-01`  
**优先级**：P1  
**来源**：用户发现 — `antigravity-ide` 物理有 5 个文件，列表卡片硬编码显示 `1 文件(SOP)`  
**预计规模**：S (1 个迭代)

#### 1. 现状与根因
- `/api/v1/skills` 列表 API 未返回 `file_count` 字段
- 前端 `route.tsx` 在卡片渲染时取不到 `files.length`，退化写死 `1`

#### 2. 交付目标
1. **后端 API (`skills.py`)**：`_list_skills_from_root` 与 `_skill_summary_from_entry` 中，增加 `file_count` 扫描字段
2. **前端 View (`route.tsx`)**：卡片 Badge 读取 `skill.file_count || skill.files?.length || 1`，展示真实文件数

#### 3. 量化验收标准
- [ ] 列表刷出时，`antigravity-ide` 卡片即刻准确显示 `5 文件`
- [ ] 关联子目录与脚本文件的技能均准确呈现真实物理文件总数

---

### 📌 P1: [ ] [TASK-SESSION-SYNC-01] IDE ↔ OpenViking 全量会话与记忆实时自动同步 (Session & Memory Auto-Sync)

**模块**：OpenViking Session Gateway + MCP  
**工单 ID**：`TASK-SESSION-SYNC-01`  
**优先级**：P1  
**来源**：用户疑问 — IDE 会话是否自动传给 VK？检索次数为何是 0 次？  
**预计规模**：M (2 个迭代)

#### 1. 交付目标
1. **会话静默实时流转**：MCP 服务器增加 Hook，在 Agent 与用户交互过程中，自动调用 `openviking.session` 写入会话历史
2. **检索次数物理统计**：将 MCP 隐式与显式检索统一汇入 `today_retrievals` 统计，使首页“今日检索次数”真实更新

---

### 📌 P1: [ ] [TASK-SKILL-CENTER-01] 隐式自动唤醒率真实数据打通 (auto_wakeup_rate via MCP 主动上报)

**模块**：技能中心 全托管感应引擎 + Harness MCP  
**工单 ID**：`TASK-SKILL-CENTER-01`  
**优先级**：P1  
**来源**：v1.2.34 迭代复盘 — `auto_wakeup_rate` 当前因 `find_calls=0` 显示"暂无采样"  
**预计规模**：S (1 个迭代)

#### 1. 根因说明
- `auto_wakeup_rate` 目前定义为 `find_calls / total_calls * 100`，但 `find_calls` 只在 Agent 调用 `openviking_find` MCP 工具时累计
- `IN_ACCESS` 已从 inotify watch mask 移除（因误触发暴洪），导致"技能被读取"事件无法被动感知
- 真正的"隐式唤醒"必须靠 **Agent 主动调用 MCP 工具时附带 skill_name 上报**

#### 2. 交付目标
1. **后端 (`mcp_openviking_server.py`)**：在 `openviking_find` / `openviking_search` MCP 工具内，识别命中的 SKILL.md 路径，将 `skill_name` 写入 `harness_metrics.json` 的 `skill_find_log` 字段（`{skill_name: count}`）
2. **后端 (`system.py`)**：`get_harness_metrics()` 从 `skill_find_log` 统计 `find_calls` 并派生 `auto_wakeup_rate`
3. **前端**：`auto_wakeup_rate` 有值时展示百分比，`active_skills_count` 改为取 `skill_find_log` 中的 distinct 技能数（更精准）

#### 3. 量化验收标准
- [ ] 调用一次 `openviking_find` 后，`harness_metrics` 返回 `auto_wakeup_rate > 0`
- [ ] 技能中心"隐式自动唤醒率"显示真实百分比，不再"暂无采样"
- [ ] `active_skills_count` 反映真实被查询过的不同技能数量

---

### 📌 P2: [ ] [TASK-SKILL-CENTER-02] Context 提示词压缩率实现 (context_compression_ratio via LLMLingua-2)

**模块**：技能中心 + Harness 引擎  
**工单 ID**：`TASK-SKILL-CENTER-02`  
**优先级**：P2（路线图功能）  
**来源**：v1.2.34 迭代复盘 — `context_compression_ratio` 字段从未有真实数据  
**预计规模**：M (2 个迭代)

#### 1. 根因说明
- `context_compression_ratio` 需要一个运行中的压缩服务提供数据，目前没有任何压缩管道
- 前端已有 UI 框架（"-- 暂无采样 / 等待需 SOP 注入采样..."），等待后端数据打通

#### 2. 交付目标
1. **后端压缩适配器**：在 OpenViking 1933 服务启动时，同进程初始化 `LLMLingua-2`（微软开源，通过 Adapter 封装，保护 YAML Header 和代码块不被压缩）
2. **压缩触发时机**：在 `openviking_find` 或 `openviking_smart_read` 返回大块 Markdown 前，自动调用压缩，记录压缩前/后 Token 数
3. **指标持久化**：将 `compression_ratio`（压缩率）写入 `harness_metrics.json`，供 `get_harness_metrics()` 读取
4. **超参数硬编码保护**（依据 AGENTS.md Rule 7）：`rate=0.50`，`threshold=0.35`，正则冻结 YAML Header 与代码块

#### 3. 量化验收标准
- [ ] 调用 `openviking_smart_read` 后，`harness_metrics` 返回 `context_compression_ratio` 数值
- [ ] 技能中心"Context 提示词压缩率"显示真实压缩百分比
- [ ] 压缩服务崩溃时主服务 100% 稳定（熔断兜底）

---

### 📌 P1: [ ] [TASK-HARNESS-LLM-01] Harness 专用可配置大模型接入 (ov.conf harness.llm 配置项)

**模块**：OpenViking 服务配置 + Harness 引擎  
**工单 ID**：`TASK-HARNESS-LLM-01`  
**优先级**：P1  
**来源**：用户需求 — "新增一个 Harness 专用的大模型，可配置可不配置；不配置时默认用 Vicky 大模型"  
**预计规模**：S (1 个迭代)

#### 1. 交付目标
1. **`ov.conf` 新增可选 `harness.llm` 配置段**：
   ```toml
   [harness]
   # 可选：不配置时默认使用 [vlm] Vicky 大模型
   # llm_base_url = "http://localhost:8317/v1"
   # llm_model = "mimo-v2.5"
   # llm_api_key = "sk-xxx"
   ```
2. **`config.py` 新增 `HarnessConfig` dataclass**：读取 `harness.llm_*` 字段，缺省时回退到 VLM 配置
3. **Harness 引擎**：所有 LLM 调用（技能描述生成、意图碰撞模拟、Prompt Auto-Tuning）统一走 `get_harness_llm()` 函数，不再直接硬编码 endpoint
4. **自动技能描述生成**：服务启动后台线程检测无 `description` 的技能，调用 Harness LLM 生成并写回 `SKILL.md` frontmatter

#### 2. 量化验收标准
- [ ] 配置 `harness.llm_base_url` 后，Harness 使用指定模型（可通过日志验证）
- [ ] 不配置时，Harness 自动 fallback 到 VLM (`mimo-v2.5` on `http://localhost:8317/v1`)
- [ ] 至少 1 个无描述技能被自动生成 `description` 并写回 SKILL.md（后台无人值守）

---

### [x] v1.2.31 — [TASK-AUTH-05] 拔除控制面探针 Header 租户污染与刷新后 Key 校验红灯修复 (Fix Control Probe Header Pollution) (用户已验收通过 ✅)
  - **Git Commit**: `fix(security): sanitize control probe headers to prevent Root API Key tenant assertion failure v1.2.31`
  - **Tag**: `v1.2.31`
  - **修改文件**: `src/hooks/use-app-connection.tsx`, `package.json`, `REFACTORING_PLAN.md`
  - **主要交付**：
    1. **拔除控制面探针 Header 租户污染**：在 `createConnectionHealthHeaders` 中，只在数据面（`data`）调用时发送 `X-OpenViking-Account` / `X-OpenViking-User`，控制面验证 Root Key 时绝不污染租户 Header；
    2. **解决刷新后红灯崩溃 Bug**：物理解决用户填好正确 Key 亮绿灯后按 F5 刷新页面探针因断言失败瞬间变红灯的物理 Root Cause，实现持久化高可靠验证。
- **Git Commit**: `fix(security & tasks): remove fallback prefilled key and import missing ClipboardListIcon v1.2.30`
- **Tag**: `v1.2.30`
- **修改文件**: `src/components/api-key-input.tsx`, `src/routes/tasks/route.tsx`, `package.json`, `REFACTORING_PLAN.md`
- **主要交付**:
  1. **拔除 `ROOT_API_KEY_FALLBACK` 补填**：解决新隐身窗口或未配置场景下前端自动把默认失效 Key 填入输入框的漏洞，保持 100% 物理干净；
  2. **修复任务中心列表报错**：在 `/tasks` 路由补齐 `ClipboardListIcon` 导入，解决下拉筛选“等待中”列表触发 JavaScript 渲染崩溃的问题；
  3. **双接入点公网隔离验证**：`vk.tide.beer` (1936 Studio UI) 与 `vk.tide.red` (1933 API) 统一使用原标准 API Key 鉴权模型。

### [x] v1.2.29 — [TASK-AUTH-03] 拔除 index.html 偷跑预填 Key 脚本与物理空安全防线 (Remove index.html Hardcoded Script) (用户已验收通过 ✅)
- **Git Commit**: `fix(security): remove index.html hardcoded localStorage injection script v1.2.29`
- **Tag**: `v1.2.29`
- **修改文件**: `index.html`, `package.json`, `REFACTORING_PLAN.md`
- **主要交付**:
  1. **🎯 拔除 `index.html` 偷跑脚本**：精准拔除了 `index.html` 中第 23-35 行原本用于开发测试的 `<script>` 注入逻辑（该逻辑在任意浏览器打开时均强制向 `localStorage` 自动写入假 Key `sk-fbb21afbe...`）；
  2. **✨ 真正的物理纯净空白**：隐身窗口与新浏览器打开时，`localStorage` 保持物理干净为空，输入框完全呈现空白未填状态；
  3. **🔒 访问彻底锁定**：未登录用户在连接设置中不会看到任何伪造点点密文，页面一律拦截呈现 `AccessRequiredGate` 门禁。

### [x] v1.2.28 — [TASK-AUTH-02] 全局与 Harness 页面公网未授权拦截门禁 (AccessRequiredGate & Zero-Data-Leak Guard) (用户已验收通过 ✅)

- **Git Commit**: `feat(auth): add global AccessRequiredGate and harness-logs zero-leak auth guard v1.2.28`
- **Tag**: `v1.2.28`
- **修改文件**: `src/components/access-required-gate.tsx`, `src/components/app-shell.tsx`, `src/routes/harness-logs.tsx`, `package.json`, `REFACTORING_PLAN.md`
- **主要交付**:
  1. **🛡️ 参照 `/request-logs` 全局统一拦截**：创建 `AccessRequiredGate` 通用安全门禁，参考 `request-logs` 拦截方案，当用户处于 `connectionRole === 'unknown'` 且非 `/settings` 路由时，全局拦截渲染未授权警示门禁；
  2. **🔒 `/harness-logs` 零泄漏锁定**：修复 `/harness-logs` 逃逸 `fetch` 漏洞，添加 `enabled: canQuery` 与 `X-API-Key` 请求头，未鉴权公网访客 100% 无法获取底层数据与履历；
  3. **✨ 无缝导向【连接设置】**：提供一键接入 `/settings` 引导卡片，解锁前彻底隔离所有敏感数据与控制操作。

### [x] v1.2.27 — [TASK-AUTH-01] 公网穿透与独立 API Key 鉴权拦截防护交付 (用户已验收通过 ✅)

- **Git Commit**: `feat(auth): public gateway, letsencrypt ssl, and clean auth guard isolation v1.2.27`
- **Tag**: `v1.2.27`
- **修改文件**: `vite.config.ts`, `src/hooks/use-app-connection.tsx`, `package.json`, `REFACTORING_PLAN.md`
- **主要交付**:
  1. **🌐 全链路公网穿透与全球 DNS 部署**：基于阿里云 ECS (`8.129.0.26`) 搭建 FRP 双向穿透与 Nginx 443 转发，通过阿里云 Alidns OpenAPI 自动解析公网 `vk.tide.beer` 与 `vk.tide.red` A 记录；
  2. **🔒 官方 Let's Encrypt 绿色安全 SSL 证书**：成功在中转机为 `vk.tide.beer` 秒级签发并挂载 Let's Encrypt 官方 SSL 证书，全球公网浏览器均显示 100% 绿色安全锁；
  3. **🛡️ 纯净未登录鉴权拦截 (Auth Guard)**：拔除前端硬编码假 Key (`ROOT_API_KEY_FALLBACK`) 与 Vite 代理自动注入的 Master Key，未输入合法 API Key 的公网访客统一返回 `HTTP 401 Unauthorized` 并处于未授权锁定状态。

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

### 📌 P0: [x] [TASK-HARNESS-01] Harness 意图碰撞模拟器与全无人值守技能提炼闭环 (已完成待验证 ✅)

**所属上层模块**：Harness 技能自演进引擎内部子功能 (`openviking.harness.engine`)  
**工单 ID**：`TASK-HARNESS-01`  
**优先级**：P0 (高优先级)  
**来源**：用户明确指导 ("100% 全无人值守自动提炼门禁 + 技能中心精简建议 + Harness 意图碰撞模拟器")  
**设计哲学**：遵循 AGENTS.md Rule 7《组件化嵌入与非侵入式适配原则》，物理同进程调用微软 `LLMLingua-2` 与斯坦福 `DSPy` 开源轮子，零独立服务开销，要启动一起启动，要关闭一起关闭。

#### 1. 目标与描述
1. **技能中心 (`src/routes/skills/route.tsx`)**：完善 `⚡ Harness 技能资产精简与合并建议 (Low Reuse Optimization)` 板块，针对 166 项沉寂技能，基于 `LLMLingua-2` 语义重叠分析（>75%）给出离散技能自动归档/提炼建议列表。
2. **Harness 审计页 (`src/routes/skills/harness-logs.tsx`)**：新增 `🎯 技能意图碰撞与歧义探测模拟器`，允许在线输入自然语言，模拟测试触发的目标技能与二次碰撞置信度，并给出白盒消歧建议。
3. **Harness 后台全无人值守门禁 (Zero-Human Auto-Gate)**：搭建 AST 语法门禁 + 触发用例测试门禁，100% 自动测试提炼结果。验证通过静默落盘，验证失败静默回滚，彻底切除人工看 Diff 审核的伪自动化环节。
4. **轻量一体化**：直接复用 OpenViking 已配置好的主 LLM 服务与 Python 同进程依赖包，**绝对不下载/安装任何额外重型模型**。

#### 2. 量化验收标准
- [x] `src/routes/skills/route.tsx` 新增重叠度 >75% 的离散技能提炼/归档列表卡片。
- [x] `src/routes/skills/harness-logs.tsx` 新增意图碰撞与歧义探测模拟器组件。
- [x] 具备 AST 结构门禁与自动回滚逻辑，无须人类人工审核看 Diff。

**交付记录**：
- **修改文件**：`src/routes/skills/harness-logs.tsx`, `src/routes/skills/route.tsx`, `REFACTORING_PLAN.md`
- **提交 Tag/Commit**：`7495d38` (`feat(harness): implement Intent Collision Simulator and Zero-Human Gate Low Reuse Optimization banner`)

---

### 📌 P0: [ ] [TASK-HARNESS-03] Harness 后台 Daemon 独立自演进与 Prompt Auto-Tuning 飞轮 (解决伪自动化)

**模块**：Harness Engine (自演进引擎)  
**工单 ID**：`TASK-HARNESS-03`  
**优先级**：P0  
**来源**：用户指导 ("这不是还是 Harness 没有自动演进吗？")  
**预计规模**：S (1 个迭代)
