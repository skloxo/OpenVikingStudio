# OpenViking Studio 任务卡片化超细粒度重构计划 (Hyper-Detailed Task Card Roadmap - Single Source of Truth)

> **🎯 核心重构与唯一真相源 (Single Source of Truth)**
> 1. **三大工程哲学**: 严格遵守 [AGENTS.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/AGENTS.md) (第一性原理、奥卡姆剃刀、全生命周期“信达雅”)。
> 2. **SemVer 3 位版本号铁律**: 版本号锁定在 `1.1.Z`（v1.1.19 ➔ v1.1.20 ➔ v1.1.21 ➔ v1.1.22...），绝对单向递增，先开发哪个卡片，哪个版本号靠前！
> 3. **铁律 (⭐⭐⭐⭐⭐ 5 星强制关卡)**: **每次完成一个版本的迭代，必须第一时间将实际交付内容与验收成果回写至本卡片文档，标记为 `[x] 已验收通过 ✅`，确保本文档时刻为 100% 物理真理与唯一真相！**

---

## 📇 全量任务卡片超细粒度时间轴履历 (Sequential Task Cards)

### 🟢 阶段 1：已完成全量验收并上线卡片 (v1.1.8 ~ v1.1.21)

#### 📇 Task Card - [x] v1.1.8: AGENT PEER 记忆中枢看护看板高密重构（已验收通过 ✅）
- **修改目标**: 对齐 1934 官方看护看板，支持 9 大 Agent 节点全景监控。
- **修改内容**: 大标题纯净精简，副标题下移原中文/英文备注，三态命名（`活跃` / `空闲` / `休眠`），60s 焦点感知懒拉取。
- **修改文件**: `src/routes/home/-components/peer-memory-grid.tsx`
- **提交 Tag**: `v1.1.8` (Git Commit `e4537b5`)

#### 📇 Task Card - [x] v1.1.9: 监控大盘系统物理资源与 VikingDB 向量走势图 (SystemResourceChart)（已验收通过 ✅）
- **修改目标**: 在 `/monitoring` 页面新增 `SystemResourceChart` 4px 微圆角高密面积走势图。
- **修改内容**: 接入 Recharts 渲染 CPU / RAM 占用率与 VikingDB 向量增长双通道走势，应用 1px 微透明边框与等宽数字 (`tabular-nums`)。
- **修改文件**: `src/routes/monitoring/-components/system-resource-chart.tsx`
- **提交 Tag**: `v1.1.9` (Git Commit `00d4575`)

#### 📇 Task Card - [x] v1.1.10: 技能中心 (Skills) 搜索过滤与 Scope 高密标签卡片重构（已验收通过 ✅）
- **修改目标**: 重构 `/skills` 顶部的搜素过滤栏与 85 个技能网格卡片的排版密度。
- **修改内容**: Header 右侧增加客户端 `searchQuery` 实时匹配框，支持根据技能名称与描述进行 < 5ms 无抖动过滤。
- **修改文件**: `src/routes/skills/route.tsx`
- **提交 Tag**: `v1.1.10` (Git Commit `7edb47b`)

#### 📇 Task Card - [x] v1.1.11: 技能中心 (Skills) 渐进式 L0/L1/L2 语义摘要侧滑抽屉面板（已验收通过 ✅）
- **修改目标**: 为技能卡片增加点击抽屉/侧滑面板，分层展示 OpenViking L0/L1/L2 三级渐进式摘要。
- **修改内容**: 滑出 4px 微圆角 `Sheet` 抽屉，包含 `L0 (意图触发)` / `L1 (SOP 流程)` / `L2 (全量源码)` 三级 Tabs 选项卡。
- **修改文件**: `src/routes/skills/route.tsx`
- **提交 Tag**: `v1.1.11` (Git Commit `e2c16c5`)

#### 📇 Task Card - [x] v1.1.16 ~ v1.1.17: 关系图谱 (/graph) 2D/3D 可视化与 4 大维度切片抽屉（已验收通过 ✅）
- **修改目标**: 建设 1,458 个全量 `viking://` 节点 3D/2D 动态力导向拓扑关系图。
- **修改内容**: 实现轻量级 Canvas 渲染，包含 4 大切片过滤器 (`GraphToolbar.tsx`) 与节点 Inspector 侧滑抽屉 (`NodeDetailsDrawer.tsx`)。
- **修改文件**: `src/routes/graph/route.tsx`
- **提交 Tag**: `v1.1.17`

#### 📇 Task Card - [x] v1.1.18: 资源管理 (/resources) 虚拟文件系统与图形化编辑器（已验收通过 ✅）
- **修改目标**: 实现 `viking://` 虚拟文件系统文件树浏览、在线文件编辑与资源上传。
- **修改内容**: 包含 `DirBrowser`、`FilePreview`、`CodeEditor`、`FindPalette` 与资源上传对话框。
- **修改文件**: `src/routes/resources/route.tsx`
- **提交 Tag**: `v1.1.18`

#### 📇 Task Card - [x] v1.1.19: 任务中心 (/tasks) 双卡片平齐、术语统一与真数据解耦（已验收通过 ✅）
- **修改目标**: 任务中心可观测性升级与第一性原理物理层序交换。
- **修改内容**: 按照物理因果主控在左排列：左卡片 `任务队列状态` (50%)，右卡片 `工序队列状态` (50%)。消灭全部假数据与调试按钮，统一领域语言为 `任务` (剔除同义词 `工单`)，三态配色全面遵循 `NO GREEN EVER`。
- **修改文件**: `src/routes/tasks/route.tsx`、`src/routes/monitoring/-components/queue-status-card.tsx`
- **提交 Tag**: `v1.1.19` (Git Commit `e780a73`)

#### 📇 Task Card - [x] v1.1.20: 任务中心 (/tasks) 工序队列与流水线 1-to-1 物理数量对齐（已验收通过 ✅）
- **修改目标**: 解决顶部工序卡片统计与底部任务流水线步骤数量对不上的问题。
- **修改内容**: 统一工序步骤统计逻辑，确保顶部【工序队列状态】累计值 (8) 与底部任务列表流水线展开图标数 (8) 物理 1-to-1 绝对精确对齐。
- **修改文件**: `src/routes/tasks/route.tsx`
- **提交 Tag**: `v1.1.20` (Git Commit `5b5b0ca`)

#### 📇 Task Card - [x] v1.1.21: 任务中心 (/tasks) 祛除“队列”冗余后缀与名称全盘统一（已验收通过 ✅）
- **修改目标**: 贯彻奥卡姆剃刀原则，切除表头下方重复的“队列”后缀。
- **修改内容**: 表头已有 `队列名称`，下方条目全盘简化为 `嵌入向量`、`语义处理`、`外部解析`、`会话提交`、`语义节点`，与底部流水线步骤名称 100% 字符级对齐。
- **修改文件**: `src/i18n/locales/zh-CN.ts`、`src/routes/tasks/route.tsx`
- **提交 Tag**: `v1.1.21` (Git Commit `a4f0988`)

---

### 🟡 阶段 2：待执行后续任务卡片 (v1.1.22 ~ v1.1.26)

#### 📇 Task Card - ⏳ v1.1.22: 首页 (/home) 6 大卡片微圆角与极客极简视觉重构
- **修改目标**: 遵循 `USER_DESIGN_RULES.md` 重构 `/home` 页面 6 大核心卡片。
- **修改内容**:
  1. 重构 `上下文资产分布` 卡片微圆角与信达雅对齐。
  2. 重构 `今日 Token 消耗` 与 `今日检索次数` 统计行。
  3. 重构 `14 天 Token 趋势` 面积图与 `365 天提交热力图` 网格。
  4. 优化 `知识库全景与 6 大 Agent 协同网`。
- **修改文件**: `src/routes/home/route.tsx` 及 `-components/` 下所有面板
- **验收标准**: 首页 6 大卡片无视觉瑕疵，等宽数字对齐，符合 TideTrading 极客终端调性。

#### 📇 Task Card - ⏳ v1.1.23: 资源库 (/resources) 历史版本追踪与一键回滚控制台
- **修改目标**: 增强 `/resources` 文件的历史版本追溯能力。
- **修改内容**:
  1. 显示 OpenViking 资源版本的 Commit 历史时间轴。
  2. 提供 Version Diff 差异校验面板。
  3. 支持一键回滚至指定历史版本。
- **修改文件**: `src/routes/resources/-components/version-timeline-drawer.tsx`
- **验收标准**: 能清晰查看资源历史版本点并成功发起回滚。

#### 📇 Task Card - ⏳ v1.1.24: 检索测试台 (/retrieval) Score 相似度得分滑动阈值筛选器与命中文档高亮
- **修改目标**: 升级 `/retrieval` 交互体验。
- **修改内容**:
  1. 加入 `0.0~1.0` 滑块，实时无抖动过滤低分检索结果。
  2. 对搜索命中的文本关键字进行 OKLCH 亮色高亮。
- **修改文件**: `src/routes/retrieval/-components/retrieval-controls.tsx`
- **验收标准**: 滑块过滤响应流畅，命中关键字高亮精准。

#### 📇 Task Card - ⏳ v1.1.25: 会话中心 (/sessions) 跨 Agent 共享会话历史与长效记忆沉淀透视
- **修改目标**: 重构 `/sessions` 会话透视。
- **修改内容**:
  1. 展示 Antigravity、OpenClaw、Hermes 等不同 Agent 的对话记录。
  2. 在右侧 Memory Impact 面板展现对话提炼并沉淀入 OpenViking 的 URI 节点。
- **修改文件**: `src/routes/sessions/route.tsx`
- **验收标准**: 能够清晰预览不同 Agent 的对话链及记忆沉淀结果。

#### 📇 Task Card - ⏳ v1.1.26: 设置页面 (/settings) 本地 1933/1936 反向代理健康诊断与 API Key 管理器
- **修改目标**: 重构 `/settings` 全景鉴权与网络健康诊断。
- **修改内容**:
  1. 自动探测 1933 端口与 1936 Vite Proxy 的代理连通性状态。
  2. Dev 模式显示 `Root 权限短路授权已激活`，非 Dev 模式提供 API Key 录入与测试。
- **修改文件**: `src/routes/settings/route.tsx`
- **验收标准**: 准确呈现当前系统的代理连通性与 API 鉴权状态。
