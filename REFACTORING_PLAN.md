# OpenViking Studio 任务卡片化超细粒度重构计划 (Hyper-Detailed Task Card Roadmap - Single Source of Truth)

> **🎯 唯一真相源 (Single Source of Truth) — 5 星强制铁律 ⭐⭐⭐⭐⭐**
>
> **每次完成一个版本的迭代，必须第一时间将实际交付内容与 Git 证据回写至本卡片文档，标记为 `[x] 已验收通过 ✅`。本文档必须时刻与 Git 历史 100% 物理对齐，是项目的唯一真相！**
>
> 1. **三大工程哲学**: 严格遵守 [AGENTS.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/AGENTS.md) (第一性原理、奥卡姆剃刀、全生命周期"信达雅")。
> 2. **SemVer 3 位版本号铁律**: 版本号锁定在 `1.1.Z`，绝对单向递增。先开发哪个卡片，哪个版本号靠前！
> 3. **版本与 Commit 强绑定**: 每个 Task Card 完成后必须推送带版本号的 Git Commit 消息（如 `feat: v1.1.22 ...`）并打 `v1.1.xx` Release Tag，不得遗漏！

---

## 📇 全量任务卡片基于 Git 物理证据的时间轴

### ✅ 阶段 0：v1.0.x 基础建设（v1.0.0 ~ v1.0.12，Tag: `V1.0.0`）

已在 v1.0.x 系列中完成并上线的核心功能（**非 1.1.x 卡片体系，是更早期基建**）：

| 版本 | Git Commit 消息（摘录） | 内容摘要 |
| :--- | :--- | :--- |
| V1.0.0 | `release: V1.0.0 official refactored studio release` | 全站视觉重构，Sessions/Resources/Tasks/Retrieval 路由完整建立 |
| v1.0.8 | `release: v1.0.8 - Home MetricPanels high-density` | 首页 MetricPanels 4px 微圆角与等宽数字对齐 |
| v1.0.9 | `release: v1.0.9 - Home TokenTrendPanel` | 首页 14 天 Token 趋势面积图 |
| v1.0.10 | `release: v1.0.10 - Home ContextCommitsHeatmap` | 首页 365 天上下文提交热力图 |
| v1.0.11 | `release: v1.0.11 - Retrieval SearchBar 4px radius` | 检索测试台搜索栏 4px 高密重构 |
| v1.0.12 | `release: v1.0.12 - RetrievalResults 4px radius` | 检索结果列表 4px 高密卡片重构 |
| — | `feat: add task Re-queue button` | 任务中心一键重排队按钮 |
| — | `feat: add task execution duration and live elapsed time` | 任务耗时与实时秒表列 |
| — | `feat: implement progressive pagination for sessions` | 会话中心渐进式分页加载 |

---

### ✅ 阶段 1：v1.1.0 监控大盘建设（v1.1.0 ~ v1.1.7，Tag: `v1.1.0`）

**【Git 证据】Tag `v1.1.0`，后续 commits 命名含 v1.1.2~v1.1.7（未独立打 Tag）**

| 版本标记 | Git Commit | 内容摘要 |
| :--- | :--- | :--- |
| v1.1.0 | `8278ff2` | 版本号升至 1.1.0 |
| v1.1.2 | `12b418a` `0ac5c25` | 监控大盘 QueueStatusCard（工序队列健康状态卡片） |
| v1.1.3 | `96fe309` | VikingDbCard（VikingDB 向量库卡片） |
| v1.1.4 | `1d9fbae` | RetrievalStatusCard（检索状态卡片） |
| v1.1.5 | `bf19143` | ModelMonitoringCard（模型使用监控卡片） |
| v1.1.6 | `6ad7e3b` | HttpStatusChart（HTTP 状态码甜甜圈图） |
| v1.1.7 | `4a4842d` | KnowledgeBaseOverview（知识库全景概览组件） |

---

### ✅ 阶段 2：v1.1.x 任务卡片体系建设（v1.1.8 ~ v1.1.11，已提交未打 Tag）

**【Git 证据】Commit 消息明确标注版本号，但未打 Release Tag（补录历史）**

#### 📇 Task Card - [x] v1.1.8: AGENT PEER 记忆中枢看护看板高密重构（已验收通过 ✅）
- **Git Commit**: `e4537b5` `feat(home): v1.1.8 complete AGENT PEER memory dashboard grid with clean i18n`
- **修改内容**: 9 大 Agent 节点全景监控网格，三态命名（活跃/空闲/休眠），60s 焦点感知懒拉取。
- **修改文件**: `src/routes/home/-components/peer-memory-grid.tsx`

#### 📇 Task Card - [x] v1.1.9: 监控大盘系统物理资源走势图 (SystemResourceChart)（已验收通过 ✅）
- **Git Commit**: `00d4575` `feat(monitoring): v1.1.9 complete SystemResourceChart area chart`
- **修改内容**: CPU / RAM 占用率与 VikingDB 向量增长双通道面积走势图。
- **修改文件**: `src/routes/monitoring/-components/system-resource-chart.tsx`

#### 📇 Task Card - [x] v1.1.10: 技能中心 (Skills) 搜索过滤与高密标签卡片重构（已验收通过 ✅）
- **Git Commit**: `7edb47b` `feat(skills): v1.1.10 complete skills client search filtering and 4px high density cards`
- **修改内容**: 技能名称/描述 < 5ms 无抖动实时过滤，4px 微圆角高密网格卡片。
- **修改文件**: `src/routes/skills/route.tsx`

#### 📇 Task Card - [x] v1.1.11: 技能中心 (Skills) 渐进式 L0/L1/L2 语义摘要侧滑抽屉面板（已验收通过 ✅）
- **Git Commit**: `e2c16c5` `feat(skills): release v1.1.11 with Occam's razor UI, L0/L1/L2 drawer`
- **修改内容**: L0 (意图触发) / L1 (SOP 流程) / L2 (全量源码) 三级 Tabs 侧滑 Sheet，YAML 解析防空兜底。
- **修改文件**: `src/routes/skills/route.tsx`

---

### ✅ 阶段 3：断电中断会话期间完成的功能（v1.1.12 ~ v1.1.18，代码已上线但无独立版本 Tag）

> **【重要说明】**: 以下功能代码已全部存在于 main 分支并正常运行，但因开发期间断电中断，**Commit 消息未留下 v1.1.12~v1.1.18 的版本标记，也未打 Release Tag**。
> 现在基于代码文件物理存在作为证据，补录如下：

#### 📇 Task Card - [x] v1.1.15-A/B/C: 监控中心高级图表全套（已代码上线 ✅，无 Tag 记录）
- **代码证据**: `src/routes/monitoring/-components/` 下存在：
  - `gpu-vram-chart.tsx` (RTX 2080Ti 显存走势折线图)
  - `embedding-latency-chart.tsx` (Embedding 延迟分位柱状图)
  - `sla-trend-chart.tsx` (SLA 成功率趋势折线图)
  - `retrieval-accuracy-trend-chart.tsx` (召回准确率趋势)
  - `token-breakdown-pie-chart.tsx` (Token 构成饼图)
  - `deep-metrics-grid.tsx` (引擎状态与记忆提炼 8 大高级卡片)

#### 📇 Task Card - [x] v1.1.16 ~ v1.1.17: 关系图谱 (/graph) 2D/3D 力导向可视化（已代码上线 ✅，无 Tag 记录）
- **代码证据**: `src/routes/graph/` 下存在：
  - `knowledge-graph-canvas.tsx` (1,458 节点 2D/3D Canvas 动态力导向图)
  - `graph-toolbar.tsx` (4 大维度切片过滤器)
  - `node-details-drawer.tsx` (节点 Inspector 侧滑抽屉)

#### 📇 Task Card - [x] v1.1.18: 资源管理 (/resources) 虚拟文件系统与在线编辑器（已代码上线 ✅）
- **代码证据**: `src/routes/resources/-components/` 下存在 `DirBrowser`、`CodeEditor`、`FindPalette`、上传对话框等全套组件。

---

### ✅ 阶段 4：任务中心迭代（v1.1.19 ~ v1.1.21，正式打 Tag ✅）

#### 📇 Task Card - [x] v1.1.19: 任务中心 (/tasks) 双卡片平齐、术语统一、真数据解耦（已验收通过 ✅）
- **Git Tag**: `v1.1.19` (Commits: `6d6d1b3`, `6d98258`, `e780a73`)
- **修改内容**: 第一性原理物理序（左=任务队列，右=工序队列），消灭假数据与调试按钮，统一领域语言为"任务"，NO GREEN EVER 配色。
- **修改文件**: `src/routes/tasks/route.tsx`、`src/routes/monitoring/-components/queue-status-card.tsx`

#### 📇 Task Card - [x] v1.1.20: 任务中心 工序队列与流水线 1-to-1 物理数量对齐（已验收通过 ✅）
- **Git Tag**: `v1.1.20` (Commit: `5b5b0ca`)
- **修改内容**: 顶部工序卡片统计合计 (8) 与底部任务列表流水线图标数 (8) 物理完全对齐。

#### 📇 Task Card - [x] v1.1.21: 任务中心 祛除"队列"冗余后缀与名称全盘统一（已验收通过 ✅）
- **Git Tag**: `v1.1.21` (Commit: `a4f0988`)
- **修改内容**: 按奥卡姆剃刀切除"嵌入向量**队列**"等 5 条冗余后缀，与流水线步骤名字符级 100% 对齐。

---

### 🟡 阶段 5：后续待执行任务卡片（v1.1.22 起）

#### 📇 Task Card - ⏳ v1.1.22: 首页 (/home) 6 大卡片信达雅视觉精修
- **修改目标**: 对照 `USER_DESIGN_RULES.md`，审查首页 6 大数据卡片的布局、颜色、字体与圆角是否 100% 合规。
- **修改文件**: `src/routes/home/route.tsx` 及 `-components/` 下各面板
- **验收标准**: 无视觉瑕疵，等宽数字对齐，三态色合规，NO GREEN EVER。

#### 📇 Task Card - ⏳ v1.1.23: 资源库 (/resources) 历史版本追踪与一键回滚
- **修改文件**: `src/routes/resources/-components/version-timeline-drawer.tsx`
- **验收标准**: 能清晰查看资源历史版本并成功发起回滚。

#### 📇 Task Card - ⏳ v1.1.24: 检索测试台 (/retrieval) Score 滑动阈值筛选器与命中高亮
- **修改文件**: `src/routes/retrieval/-components/retrieval-controls.tsx`
- **验收标准**: 0.0~1.0 滑块实时过滤，命中关键字高亮精准。

#### 📇 Task Card - ⏳ v1.1.25: 会话中心 (/sessions) 跨 Agent 共享会话历史与记忆透视
- **修改文件**: `src/routes/sessions/route.tsx`
- **验收标准**: 能查看 Antigravity/OpenClaw/Hermes 各 Agent 对话链及 OpenViking 记忆沉淀节点。

#### 📇 Task Card - ⏳ v1.1.26: 设置页面 (/settings) 1933/1936 反向代理健康诊断与 API Key 管理
- **修改文件**: `src/routes/settings/route.tsx`
- **验收标准**: 准确呈现代理连通性与 Dev/Production 模式鉴权状态。
