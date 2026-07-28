# OpenViking Studio 任务卡片化超细粒度重构计划 (Hyper-Detailed Task Card Roadmap)

> **🎯 核心重构与视觉规范**
> 1. **第一性原理与哲学**: 严格遵守 [USER_DESIGN_RULES.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/docs/USER_DESIGN_RULES.md) (TideTrading 极客终端调性、奥卡姆剃刀、按需焦点感知 60s 懒加载、绝对无阴影、纯净 i18n 多语言)。
> 2. **版本号铁律**: 主版本与次版本号锁定在 `1.1.X`，任何新功能与微重构严格在 Z 位按序增长 (v1.1.10, v1.1.11, v1.1.12...)，坚决不擅自更改 Y 位！
> 3. **卡片化流程**: **所有需求必须先写入本卡片文档拆细 ➔ 丰富每个字段与交互 ➔ 单张卡片编码 ➔ 1936 部署 ➔ 用户显式验收通过 ➔ 再解锁下一张卡片**。

---

## 📇 全量任务卡片超细粒度履历 (Detailed Task Cards)

### 阶段 1：控制台与监控大盘 (Home & Monitoring) 已完成卡片

#### 📇 Task Card - [x] v1.1.8: AGENT PEER 记忆中枢看护看板高密与纯净 i18n 重构（已验收通过 ✅）
- **修改目标**: 对齐 1934 官方看护看板，支持 9 大 Agent 节点全景监控。
- **修改逻辑**: 大标题纯净精简，副标题下移原中文/英文备注，三态命名（`活跃` / `空闲` / `休眠`），通道命名（`本地直连` / `网络远程` / `原生中枢`），60s 焦点感知懒拉取。
- **修改文件**: `src/routes/home/-components/peer-memory-grid.tsx`
- **验收结果**: 已验收并提交 Git `e4537b5`。

#### 📇 Task Card - [x] v1.1.9: 监控大盘系统物理资源与 VikingDB 向量走势图 (SystemResourceChart)（已验收通过 ✅）
- **修改目标**: 在 `/monitoring` 页面新增 `SystemResourceChart` 4px 微圆角高密面积走势图。
- **修改逻辑**: 接入 Recharts 渲染 CPU / RAM 占用率与 VikingDB 向量增长双通道走势，应用 1px 微透明边框与等宽数字 (`tabular-nums`)。
- **修改文件**: `src/routes/monitoring/-components/system-resource-chart.tsx`、`src/routes/monitoring/route.tsx`
- **验收结果**: 已验收并提交 Git `00d4575`。

---

### 阶段 2：技能中心 (Skills Center) 细粒度卡片

#### 📇 Task Card - [x] v1.1.10: 技能中心 (Skills) 搜索过滤与 Scope 高密标签卡片重构（当前验收中 🔄）
- **修改目标**: 重构 `/skills` 顶部的搜素过滤栏与 85 个技能网格卡片的排版密度。
- **修改逻辑**:
  1. 在 Header 右侧增加客户端 `searchQuery` 实时匹配框，支持根据技能名称与描述进行 < 5ms 无抖动过滤。
  2. 卡片容器应用 4px 微圆角 (`rounded border-border/60 bg-card hover:border-cyan-500/40`)，去除阴影。
  3. 将 `scope` 属性（`agent` / `user`）使用 2px 微圆角 (`rounded-xs font-mono`) Tag 区分展示，配以图标 `UsersRoundIcon` / `UserRoundIcon`。
- **修改文件**: `src/routes/skills/route.tsx`
- **验收标准**: 在 1936 查看 `/skills`，搜索过滤无延迟，卡片高密精美。

#### 📇 Task Card - ⏳ v1.1.11: 技能中心 (Skills) 渐进式 L0/L1/L2 语义摘要侧滑抽屉面板（待用户单点下令验收 🔄）
- **修改目标**: 为技能卡片增加点击抽屉/侧滑面板，分层展示 OpenViking L0/L1/L2 三级渐进式摘要。
- **修改逻辑**:
  1. 点击任意 Skill 卡片，右侧滑出 4px 微圆角 `Sheet` 抽屉。
  2. 抽屉顶部包含 4px `L0 (意图触发)` / `L1 (SOP 流程)` / `L2 (全量源码)` 三级 Tabs 选项卡。
  3. **`L0` 页**: 展示短句匹配描述（Intent Description）、语义 Tags (`tags`) 及作用域 Scope。
  4. **`L1` 页**: 展示 SOP 流程规范大纲 (`overview`) 与允许使用的 MCP 工具组 (`allowedTools`)。
  5. **`L2` 页**: 展示关联源文件清单 (`files: [{path, isDir}]`) 及全量 `SKILL.md` Markdown 代码块。
- **修改文件**: `src/routes/skills/route.tsx`
- **验收标准**: 抽屉滑出平滑，Tabs 切换精准展示 L0/L1/L2 资源。

#### 📇 Task Card - ⏳ v1.1.12: 技能中心 (Skills) 关联资源树与文件依赖结构树视图
- **修改目标**: 在技能抽屉中增强对 `scripts/`, `examples/`, `references/` 子文件树的图形化查看。
- **修改逻辑**:
  1. 调用 OpenViking `GET /api/v1/skills/{name}` 中的 `files` 节点树。
  2. 将包含多层级的子文件排版为形如 `tree` 命令的紧凑节点行，文件夹图标与文件图标加亮区分。
  3. 支持点击单一脚本文件预览其代码行数与简要路径。
- **修改文件**: `src/routes/skills/-components/skill-tree-viewer.tsx`
- **验收标准**: 技能关联文件呈现极客树状排版，层级结构清晰。

---

### 阶段 3：检索与测试工作台 (Retrieval Workbench) 细粒度卡片

#### 📇 Task Card - ⏳ v1.1.13: 检索测试台 (Retrieval) Score 相似度得分滑动阈值筛选器
- **修改目标**: 重构 `/retrieval` 页面顶部搜索控制栏的分数过滤。
- **修改逻辑**:
  1. 在 `RetrievalControls` 中加入以 OKLCH 渐变色标识的 Score 滑动条 (`threshold: 0.0 ~ 1.0`)。
  2. 实时过滤相似度低于设定阈值的检索结果。
  3. 控件采用 4px 微圆角 (`rounded-sm`) 与 `font-mono tabular-nums` 紧凑尺寸。
- **修改文件**: `src/routes/retrieval/-components/retrieval-controls.tsx`
- **验收标准**: 拖动滑动条时下方结果集实时根据相似度得分精准过滤。

#### 📇 Task Card - ⏳ v1.1.14: 检索测试台 (Retrieval) 命中文档高亮与代码块预览卡片化
- **修改目标**: 重构搜索结果匹配内容的视觉展示。
- **修改逻辑**:
  1. 检索命中的匹配关键字应用 `bg-cyan-500/20 text-cyan-400 font-semibold` 高亮标示。
  2. 结果条目采用 4px 实线微边框与 2px Score Badge。
  3. 代码块与向量 URI 使用 JetBrains Mono 等宽字体，避免布局抖动。
- **修改文件**: `src/routes/retrieval/-components/retrieval-results.tsx`
- **验收标准**: 搜索结果匹配词高亮清晰，评分 Tag 与 URI 字体规范对齐。

---

### 阶段 4：任务中心 (Task Center) 细粒度卡片

#### 📇 Task Card - ⏳ v1.1.15: 任务中心 (/tasks) 静态历史与后台动态队列全量统一收口 (Unified Task Convergence)
- **修改目标**: 遵循全系统任务收口的第一性原理，打破 DB 静态任务与后台守护进程内存队列的壁垒，将“4 运行中 / 6 排队中”等所有后台任务 100% 统一收口呈现至任务中心。
- **修改逻辑**:
  1. 同时聚合 `GET /api/v1/tasks` (SQLite 数据库静态任务) 与 `GET /api/v1/observer/queue` (守护进程动态内存队列)。
  2. 顶部新增 **`🔥 当前活跃队列 (Active Daemon Workers)`** 卡片组件，实时展现 `session_commit` / `reindex_queue` 的运行与等待动画。
  3. 全局进度条合并计算：`进行中` = 内存队列 In Progress 任务 + DB running 任务，绝不错漏任何一个后台处理任务！
  4. 列表行采用高密缩紧 (`py-2 px-3`)，Task ID 与 Runtime 时间使用 `font-mono tabular-nums` 呈现。
- **修改文件**: `src/routes/tasks/route.tsx`、`src/routes/tasks/-components/active-queue-card.tsx`
- **验收标准**: 在 `/tasks` 页面既能看到 1146 条历史任务，也能实时看到正在后台提炼排队的动态队列任务。

#### 📇 Task Card - ⏳ v1.1.16: 任务中心 (/tasks) 异常任务日志抽屉与一键重试控制台
- **修改目标**: 针对执行失败或中途中断的任务提供深度的日志诊断与一键重试能力。
- **修改逻辑**:
  1. 点击失败任务行，弹出 4px 终端风格 Log 抽屉。
  2. 解析 OpenViking 后端 `task_id` 抛出的 `stderr` / `stack_trace`。
  3. 提供 `重新重试` (Re-run Task) 按钮，发起 HTTP POST 请求。
- **修改文件**: `src/routes/tasks/-components/task-log-drawer.tsx`
- **验收标准**: 异常日志高亮格式化展示，重试命令成功透传给后端。

---

### 阶段 5：会话与系统设置 (Sessions & Settings) 细粒度卡片

#### 📇 Task Card - ⏳ v1.1.17: 会话中心 (/sessions) 跨 Agent 共享会话历史视图
- **修改目标**: 重构 `/sessions` 页面，展示 Antigravity、OpenClaw、Hermes 等不同 Agent 的对话记录与共享 Memory 链。
- **修改逻辑**: 侧边栏展示会话 Session 列表，右侧区域呈现对话气泡与调用的 OpenViking 记忆点 (`uriNode`)。
- **修改文件**: `src/routes/sessions/route.tsx`
- **验收标准**: 会话列表加载顺畅，右侧能够精准预览该 Session 沉淀入 OpenViking 的记忆节点。

#### 📇 Task Card - ⏳ v1.1.18: 设置页面 (/settings) 本地 1933/1936 反向代理健康诊断与 API Key 管理器
- **修改目标**: 重构 `/settings` 页面，提供系统连接与权限鉴权全景诊断。
- **修改逻辑**:
  1. 自动探测 1933 端口与 1936 Vite Proxy 的代理连通性状态。
  2. 在 Dev 模式下显示 `Root 权限短路授权已激活`，非 Dev 模式下提供 API Key 输入框与凭据测试。
- **修改文件**: `src/routes/settings/route.tsx`
- **验收标准**: 设置页面清晰展示当前连接模式（Dev 模式 / Production 模式）与代理延迟。

---

*全量超细粒度文档保存路径：`/home/skloxo/.gemini/antigravity-ide/brain/eb762217-74ad-4e82-9b0d-1fcbc5567e21/implementation_plan.md`*
