# OpenViking Studio 任务卡片化微拆分重构计划 (Task-Card Refactoring Roadmap)

> **🎯 核心重构与视觉规范**
> 1. **第一性原理与哲学**: 严格遵守 [USER_DESIGN_RULES.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/docs/USER_DESIGN_RULES.md) (TideTrading 极客终端调性、奥卡姆剃刀、按需焦点感知 60s 懒加载、绝无阴影、全量纯净 i18n)。
> 2. **版本号铁律**: 主版本与次版本号锁定在 `1.1.X`，任何新功能与微重构严格在 Z 位按序增长 (v1.1.9, v1.1.10, v1.1.11...)。
> 3. **卡片化流程**: **所有需求必须先写入本卡片文档拆细 ➔ 单张卡片小步编码 ➔ 1936 热更新部署 ➔ 喊用户验收通过 ➔ 再解锁下一张卡片**。

---

## 📇 细粒度任务卡片列表 (Task Cards)

### 阶段 1：控制台与监控大盘 (Home & Monitoring) 细粒度卡片

#### 📇 Task Card - [x] v1.1.8: AGENT PEER 记忆中枢看护看板高密与纯净 i18n 重构（已验收通过 ✅）
- **修改目标**: 对齐 1934 官方看护看板，支持 9 大 Agent 节点全景监控。
- **修改逻辑**: 大标题纯净精简，副标题下移原中文/英文备注，三态命名（`活跃` / `空闲` / `休眠`），通道命名（`本地直连` / `网络远程` / `原生中枢`），60s 焦点感知懒拉取。
- **修改文件**: `src/routes/home/-components/peer-memory-grid.tsx`
- **验收结果**: 已验收并提交 Git `e4537b5`。

#### 📇 Task Card - 🔄 v1.1.9: 监控大盘系统物理资源与 VikingDB 向量走势图 (SystemResourceChart)（进行中 🔄）
- **修改目标**: 在 `/monitoring` 页面新增 `SystemResourceChart` 4px 微圆角高密面积走势图。
- **修改逻辑**: 接入 Recharts 渲染 CPU / RAM 占用率与 VikingDB 向量增长双通道走势，应用 1px 微透明边框与等宽数字 (`tabular-nums`)。
- **修改文件**: `src/routes/monitoring/-components/system-resource-chart.tsx`、`src/routes/monitoring/route.tsx`
- **验收标准**: 在 1936 查看监控大盘，高密面积图平滑渲染，无布局抖动。

---

### 阶段 2：技能中心 (Skills Center) 细粒度卡片拆解

#### 📇 Task Card - ⏳ v1.1.10: 技能中心 (Skills) 搜索过滤与作用域 Scope 高密标签卡片重构
- **修改目标**: 重构 `/skills` 页面的搜索过滤栏与 Skill 卡片网格。
- **修改逻辑**: 应用 `rounded` (4px) 微圆角卡片，搜索框内嵌 `Ctrl+K` 快捷键标示，将 `scope` 标签收紧为 `rounded-xs` (2px) + `font-mono`，展示 85 个顶级技能精美卡片。
- **修改文件**: `src/routes/skills/route.tsx`
- **验收标准**: 技能搜索响应毫秒级，卡片排版信息密度与对比度符合 TideTrading 极客终端风格。

#### 📇 Task Card - ⏳ v1.1.11: 技能中心 (Skills) 渐进式 L0/L1/L2 语义摘要抽屉面板
- **修改目标**: 为技能卡片增加点击抽屉/弹层，展示 OpenViking L0/L1/L2 三级渐进式摘要。
- **修改逻辑**: 点击卡片弹出高密侧滑抽屉，分层展示意图触发词(L0)、SOP 流程(L1)与源码全量(L2)。
- **修改文件**: `src/routes/skills/-components/skill-detail-drawer.tsx`
- **验收标准**: 点击技能卡片抽屉顺畅滑出，支持 L0/L1/L2 分级切换。

---

### 阶段 3：检索与测试工作台 (Retrieval Workbench) 细粒度卡片拆解

#### 📇 Task Card - ⏳ v1.1.12: 检索测试台 (Retrieval) ETag / Score 分数阈值筛选器高密重构
- **修改目标**: 重构 `/retrieval` 检索筛选控制栏。
- **修改逻辑**: 增加 Score 相似度得分滑动条/阈值过滤框，应用 `rounded-sm` 紧凑尺寸与全量中文/英文纯净 i18n。
- **修改文件**: `src/routes/retrieval/-components/retrieval-controls.tsx`
- **验收标准**: 筛选滑动条响应精确，控制栏空间利用率显著提升。

#### 📇 Task Card - ⏳ v1.1.13: 检索测试台 (Retrieval) 命中文档高亮与代码块预览卡片化
- **修改目标**: 重构搜索结果匹配内容的预览视图。
- **修改逻辑**: 匹配关键字应用 OKLCH 文本高亮，代码块采用 JetBrains Mono 等宽字体，卡片边框收紧至 `rounded-md` (4px)。
- **修改文件**: `src/routes/retrieval/-components/retrieval-results.tsx`
- **验收标准**: 检索结果卡片无缝呈现高亮代码与分数 Badge。

---

*文档保存路径：`/home/skloxo/aho/openclaw/project/OpenVikingStudio/REFACTORING_PLAN.md`*
*更新时间：2026-07-28*
