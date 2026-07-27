# OpenViking Studio 任务卡片化微拆分重构计划 (Task-Card Refactoring Roadmap)

> **🎯 核心重构与视觉规范**
> 1. **关联规范**：所有视觉改动严格遵守 [UI_SPECIFICATION.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/UI_SPECIFICATION.md)（参照 `tedtrading` 高密风格：圆角收紧为 `rounded-md`/`rounded-sm`，Padding 从 `p-6` 减半至 `p-3`，大幅提升信息显示密度）。
> 2. **渐进式卡片发布**：每个任务独立卡片 ➔ 编码改动 ➔ 部署 `1936` ➔ 喊用户单点验收 ➔ 通过后再进行下一张卡片。

---

## 📇 任务卡片列表 (Task Cards)

### 阶段 1：App Shell 侧边栏与基础修复

#### 📇 Task Card - v1.0.7: 侧边栏账号切换器 (AccountSwitcher) Dev 模式防错封装
- **修改目标**：优化侧边栏顶部 `AccountSwitcher` 在单租户/Dev 模式下的容错展示。
- **修改逻辑**：在 Dev 单租户模式下，后端 `GET /api/v1/admin/accounts` 会返回 500。在 `AccountSwitcher` 中增加 `serverMode === 'dev'` 短路拦截，直接降级展示默认 Dev 账号，避免在控制台报 500 告警干预。
- **关联规范**：[REFACTORING_GUIDE.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/REFACTORING_GUIDE.md#二vite-proxy-代理配置关键) Section 二、[UI_SPECIFICATION.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/UI_SPECIFICATION.md)
- **修改文件**：`src/components/account-switcher.tsx`
- **验收标准**：在 1936 打开页面，侧边栏账号切换器正常显示且 Network 中不再产生 `/admin/accounts` 500 告警日志。

---

### 阶段 2：控制台主页 (Home / Dashboard) 模块高密重构

#### 📇 Task Card - [x] v1.0.8: Home 基础指标卡片 (MetricPanels) 高密对齐（已通过 ✅）
- **修改目标**：重构 Home 主页顶部指标卡片的外观与排版密度。
- **修改逻辑**：将原 `rounded-xl`/`rounded-2xl` 圆角收紧为 `rounded-md` (6px)，内边距由 `p-6` 缩减为 `p-3.5`，按照 `tedtrading` 风格强化数字与 Label 的对比度。
- **关联规范**：[UI_SPECIFICATION.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/UI_SPECIFICATION.md#1-设计-token-标准) Section 1
- **修改文件**：`src/routes/home/-components/metric-panels.tsx`
- **验收标准**：访问 `http://127.0.0.1:1936/studio/home`，指标卡片高度收紧，空间利用率提升。

#### 📇 Task Card - [x] v1.0.9: Home Token 趋势图表 (TokenTrendPanel) 紧凑排版与 4px 硬朗微圆角重构（已通过 ✅）
- **修改目标**：重构 Token 消耗趋势图表容器与 Recharts 渲染高度。
- **修改逻辑**：压缩图表 Header padding，收紧 Card 圆角至 `rounded-md`，提升纵向信息显示效率。
- **关联规范**：[UI_SPECIFICATION.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/UI_SPECIFICATION.md)
- **修改文件**：`src/routes/home/-components/token-trend-panel.tsx`
- **验收标准**：Token 趋势图表更紧凑，首屏显示更多下方数据。

#### 📇 Task Card - v1.0.10: Home Context Commits 热力图 (ContextCommitsHeatmap) 样式微调
- **修改目标**：重构提交热力图单元格间距与 Tooltip 样式。
- **修改逻辑**：将热力图容器设为紧凑高密布局，对齐全局 6px 圆角风格。
- **关联规范**：[UI_SPECIFICATION.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/UI_SPECIFICATION.md)
- **修改文件**：`src/routes/home/-components/context-commits-heatmap.tsx`
- **验收标准**：热力图展示精致规范，交互 Tooltip 响应流畅。

---

### 阶段 3：检索/搜索 (Retrieval) 模块重构

#### 📇 Task Card - v1.0.11: 检索搜索栏 (SearchBar) 紧凑化重构
- **修改目标**：重构 `/retrieval` 页面的搜索输入框与按钮组。
- **修改逻辑**：输入框圆角收紧为 `rounded-sm` (4px)，按钮 padding 调紧，参考 terminal 命令行精致风格。
- **关联规范**：[UI_SPECIFICATION.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/UI_SPECIFICATION.md)
- **修改文件**：`src/routes/retrieval/-components/search-bar.tsx`
- **验收标准**：搜索栏输入框及控件更紧凑精细。

#### 📇 Task Card - v1.0.12: 检索结果列表 (RetrievalResults) 高密卡片化
- **修改目标**：重构搜索结果条目的展示密度与得分 Badge。
- **修改逻辑**：缩减每个 result item 的 padding (`py-2 px-3`)，分数 Tag 设为 `rounded-xs` 微圆角。
- **关联规范**：[UI_SPECIFICATION.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/UI_SPECIFICATION.md)
- **修改文件**：`src/routes/retrieval/-components/retrieval-results.tsx`
- **验收标准**：单屏可展示更多检索匹配条目。

---

*(后续 Task Cards v1.0.13 ~ v1.0.30 依此卡片标准按序推进)*

*文档保存路径：`/home/skloxo/aho/openclaw/project/OpenVikingStudio/REFACTORING_PLAN.md`*
*更新时间：2026-07-27*
