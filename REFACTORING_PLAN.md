# OpenViking Studio 任务卡片化微拆分重构计划 (Task-Card Implementation Plan)

> **🎯 核心重构与视觉规范**
> 1. **第一性原理与哲学**: 严格遵守 [USER_DESIGN_RULES.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/docs/USER_DESIGN_RULES.md) (TideTrading 极客终端调性、奥卡姆剃刀、按需焦点感知 60s 懒加载、绝无阴影、全量纯净 i18n)。
> 2. **版本号铁律**: 主版本与次版本号锁定在 `1.1.X`，任何新功能与微重构严格在 Z 位按序增长 (v1.1.9, v1.1.10, v1.1.11...)。
> 3. **卡片化流程**: **所有需求必须先写入本卡片文档拆细 ➔ 单张卡片小步编码 ➔ 1936 热更新部署 ➔ 喊用户验收通过 ➔ 再解锁下一张卡片**。

---

## 📇 全量任务卡片完整履历 (Task Cards Roadmap)

### 阶段 1：App Shell 基础框架与修缮

- [x] **v1.0.1**: 移除顶部整条 Header，释放纵向展示空间 (`src/components/app-shell.tsx`) ✅
- [x] **v1.0.2**: 侧边栏标题区添加版本号副标题 (`src/components/app-shell.tsx`) ✅
- [x] **v1.0.3**: 语言切换移至侧边栏底部，UI 统一 (`src/components/app-shell.tsx`) ✅
- [x] **v1.0.4**: 主题切换移至侧边栏底部；侧边栏收起/展开按钮修复；请求日志路由修复 (`src/components/app-shell.tsx`) ✅
- [x] **v1.0.5**: Vite Proxy 完整修复：补全所有 OpenViking 后端路径代理（含 `/health`），修复 admin/root 权限缺失问题 (`vite.config.ts`) ✅
- [x] **v1.0.6**: 修复 Playground 缺失 Icon 导入导致的渲染崩溃 (`src/routes/playground/-components/terminal-panel.tsx`) ✅
- [x] **v1.0.7**: 侧边栏账号切换器 (AccountSwitcher) Dev 模式防错封装 (`src/components/account-switcher.tsx`) ✅

---

### 阶段 2：控制台 (Home / Dashboard) 高密重构

- [x] **v1.0.8**: Home 基础指标卡片 (MetricPanels) 高密对齐，圆角收紧为 6px，内边距 `p-3.5` (`src/routes/home/-components/metric-panels.tsx`) ✅
- [x] **v1.0.9**: Home Token 趋势图表 (TokenTrendPanel) 紧凑排版与 4px 硬朗微圆角重构 (`src/routes/home/-components/token-trend-panel.tsx`) ✅
- [x] **v1.0.10**: Home Context Commits 热力图 4px 终端圆角与高密重构 (`src/routes/home/-components/context-commits-heatmap.tsx`) ✅

---

### 阶段 3：检索与测试工作台 (Retrieval Workbench) 基础重构

- [x] **v1.0.11**: 检索搜索栏 (SearchBar) 与控制栏 (RetrievalControls) 4px 硬朗高密重构 (`src/routes/retrieval/-components/search-bar.tsx`) ✅
- [x] **v1.0.12**: 检索结果列表 (RetrievalResults) 高密卡片化重构 (`src/routes/retrieval/-components/retrieval-results.tsx`) ✅

---

### 阶段 4：监控大盘与核心数据卡片 (Monitoring & Data Cards)

- [x] **v1.1.0**: 监控大盘总体重构与强收敛中英文框架 (`src/routes/monitoring/route.tsx`) ✅
- [x] **v1.1.1**: 顶部运行环境探测与 Root 鉴权看板 (`src/components/app-shell.tsx`) ✅
- [x] **v1.1.2**: 任务中心 (Task Center) 状态解析与异常抛错修复 (`src/routes/tasks/route.tsx`) ✅
- [x] **v1.1.3**: VikingDbCard 向量数据库卡片高密重构 (`src/routes/monitoring/-components/viking-db-card.tsx`) ✅
- [x] **v1.1.4**: RetrievalStatusCard 检索状态卡片重构 (`src/routes/monitoring/-components/retrieval-status-card.tsx`) ✅
- [x] **v1.1.5**: ModelMonitoringCard AI 模型消耗监控卡片重构 (`src/routes/monitoring/-components/model-monitoring-card.tsx`) ✅
- [x] **v1.1.6**: HttpStatusDonutChart HTTP 状态分布与成功率走势图 (`src/routes/monitoring/-components/http-status-chart.tsx`) ✅
- [x] **v1.1.7**: KnowledgeBaseOverview 知识库全景大盘重构 (`src/routes/home/-components/knowledge-base-overview.tsx`) ✅
- [x] **v1.1.8**: AGENT PEER 记忆中枢看板高密重构与通俗化命名 (已提交 Git `e4537b5`) ✅

---

### 阶段 5：当前与后续细粒度任务卡片 (Current & Future Task Cards)

- [x] **v1.1.9**: 监控大盘系统物理资源与 VikingDB 向量走势图 (`SystemResourceChart`)（已完成并提交 Git `00d4575`） ✅
- [x] **v1.1.10**: 技能中心 (`/skills`) 搜索过滤与 Scope 高密标签卡片重构（已完成 1936 打包验证 🔄）
- [ ] **v1.1.11**: 技能中心 (`/skills`) 渐进式 L0/L1/L2 语义摘要抽屉面板
- [ ] **v1.1.12**: 检索测试台 (`/retrieval`) Score 相似度得分滑动阈值筛选器
- [ ] **v1.1.13**: 检索测试台 (`/retrieval`) 命中文档 OKLCH 高亮与代码块预览
- [ ] **v1.1.14**: 技能中心 (`/skills`) 关联资源树结构查看器
- [ ] **v1.1.15**: 任务中心 (`/tasks`) 异步任务执行进度高密流式列表
- [ ] **v1.1.16**: 任务中心 (`/tasks`) 异常任务重试与 Log 查看器面板
- [ ] **v1.1.17**: 会话中心 (`/sessions`) 跨 Agent 共享会话图谱查看器
- [ ] **v1.1.18**: 设置页面 (`/settings`) 本地 1933 / 1936 反向代理健康诊断面板

---

*全量文档保存路径：`/home/skloxo/.gemini/antigravity-ide/brain/eb762217-74ad-4e82-9b0d-1fcbc5567e21/implementation_plan.md`*
