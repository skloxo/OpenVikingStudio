# OpenViking Studio 视觉规范与高密设计语言 (UI Visual & High-Density Design System)

> **🎯 核心设计哲学：参考 tedtrading / High-Density Trading Terminal 风格**
> 1. **极致信息密度 (Maximum Information Density)**：严格控制 padding 和 gap，在有限视口内呈现更多关键指标与明细数据，拒绝无效空白。
> 2. **硬朗微圆角 (4px Micro-Radius Token)**：全站锁定 4px 微圆角质感（从大圆角 `rounded-xl/2xl` 全面重构），展现极简、专业、硬朗的 Developer/Trading 工具范。
> 3. **无缝多语言 (Instant i18n)**：对页面上所有硬编码英文进行即时汉化收录，确保界面国际化表达准确统一。
> 4. **零冗余视觉 (No Visual Noise)**：精简不必要的自解释视觉元素（如无必要的色彩图例、装饰性无用图标），突出核心数据与操作。

---

## 📐 1. Design Tokens 统一标准

### 1.1 边框圆角 Token (Border Radius Scale)
全站以 `--radius: 0.25rem` (4px) 为基准，严格分级应用：

| 适用组件 / 场景 | Token 名称 | CSS 属性 / Tailwind Class | 像素值 (Px) | 视觉说明 |
| :--- | :--- | :--- | :--- | :--- |
| **容器 / 面板 / 卡片** | `--radius-lg` | `rounded` | `4px` | 锁定 4px 主面板结构微圆角 |
| **按钮 / 输入框 / 选框** | `--radius-md` | `rounded-sm` | `3px - 4px` | 精细交互控件圆角 |
| **标签 / 角标 / Tooltip / 图例方块** | `--radius-sm` | `rounded-xs` | `2px` | 极小微圆角，精细紧凑 |

### 1.2 字体排版 Token (Typography System)
强调「标签与数值」的清晰对比，提升大量数据浏览时的扫视效率：

| 元素 | 字体规范 (Font Family & Weight) | 字号 (Font Size) | 色彩 (Color) |
| :--- | :--- | :--- | :--- |
| **指标数值 (Metrics)** | `font-mono font-semibold tabular-nums` | `text-xl` / `text-2xl` | `text-foreground` |
| **标签/属性名 (Labels)** | `font-sans font-medium` | `text-[11px]` / `text-xs` | `text-muted-foreground` |
| **时间戳/哈希/代码** | `font-mono` | `text-xs` | `text-muted-foreground/80` |
| **标题 (Headings)** | `font-sans font-semibold` | `text-sm` / `text-base` | `text-foreground` |

### 1.2.1 字体字号下限与排版硬性守则 (Typography Minimum Size Specification)

为了确保信息在高分辨率屏幕（High-DPI / 4K）与常规显示器上的白盒直观可读性，全系统 100% 遵循以下字体字号硬性守则：

1. **绝对字号下限 (Absolute Minimum Font Size: 11px)**：
   - **全系统 100% 物理禁用任何 `< 11px` 的微字**（如 `text-[8px]`, `text-[9px]`, `text-[10px]` 彻底封杀！）。
   - 即使最极简紧凑的辅助标签、卡片脚标、状态 Dot 提示或代码属性，最小也必须为 **`text-[11px]` (11px)**。

2. **系统字号阶梯 (Typography Hierarchy Scale)**：
   - **`11px` (`text-[11px]`)**：极紧凑的辅助标签、表格次要说明（物理硬下限）。
   - **`12px` (`text-xs`)**：标准卡片正文、属性 Label、标准 Badge 徽章、按钮文字（高密开发基准字号）。
   - **`13px - 14px` (`text-sm`)**：卡片标题、输入框文字、常规正文、导航链接。
   - **`16px` (`text-base` / `text-lg`)**：板块主标题、关键明细卡片头。
   - **`20px+` (`text-xl` / `text-2xl`)**：顶部大牌 Banner 核心数值。

### 1.3 间距与布局 Token (Density & Spacing Scale)
收紧整体组件与页面边距，相比传统 WEB 减半空白占用：

| 区域 | Tailwind Standard Class | 间距尺寸 (Px) | 优化说明 |
| :--- | :--- | :--- | :--- |
| **主面板内边距 (Panel Padding)** | `p-3` ~ `p-3.5` | `12px - 14px` | 相比原 `p-6` (24px) 提升 50%+ 空间利用率 |
| **卡片间距 (Grid / Flex Gap)** | `gap-2.5` ~ `gap-3` | `10px - 12px` | 面板之间保持紧凑有序的间隙 |
| **内容组件距 (Content Gap)** | `space-y-2` / `gap-2` | `8px` | 元素与文本组紧密组合 |
| **表格/列表行高 (Row Height)** | `h-8` / `py-1.5` | `32px` | 列表单行紧凑高密对齐 |

### 1.4 色彩与暗黑模式 (Colors & Dark Mode)
* **边框与分割线**：使用 `border-border/60` 或 `border-border/70` 极细微透明边框，避免粗重线条割裂页面。
* **浮层与 Tooltip**：使用 `bg-popover/95 backdrop-blur-md` 结合 `shadow-xl` / `ring-1 ring-foreground/5`，增强高质感暗黑/亮色悬浮体验。
* **趋势与状态色**：对比度鲜明的 OKLCH 色彩（如 Token 增长蓝、成功绿、警告黄）。

---

## 🧩 2. 页面组件级重构规范

### 2.1 指标卡片 (Metric Panels)
* 面板容器使用 `rounded` (4px) + `border border-border/60`。
* 每一个指标均包含清晰的 `text-[11px]` 标题与 `text-xl/2xl font-mono` 数值。
* 状态 Dot 或图标尺寸统一限定在 `size-3.5` 或 `size-4`，配以 `rounded-sm` 背景。

### 2.2 图表与趋势面板 (Trend & Recharts Panels)
* Recharts AreaChart 渲染高度收紧至 `200px - 240px` (`h-50` / `h-60`)。
* 图表 Tooltip 采用 `rounded-sm` (4px) 容器，内衬 `font-mono` 明细与 `rounded-xs` 色块。
* 顶部筛选/日期 Badge 采用 `rounded-sm` 紧凑尺寸。

### 2.3 热力图与点阵网格 (Heatmap Grid)
* 热力图 Rect Cell 设置 `rx: 2` (2px 圆角)，间距 `space={3}`。
* 省略自解释或低价值的图例控件（如「少...多」指示条），保持视野清爽。
* Tooltip 浮层采用 `rounded-sm` (4px) 边界 + 底部 `rotate-45` 指针。

---

## 🔄 3. 版本迭代与规范落地流程

1. **小步快跑微版本号 ($v1.0.z$)**：每个独立的 Task Card 重构完成后，同步在 `app-shell.tsx` 中递增版本号。
2. **每次修改后喊用户验收**：在 Vite Dev 端口 (`http://127.0.0.1:1936/studio/home`) 上供用户测试，获得明确通过指令后才推进下一个 Card。
3. **代码远程同步**：验收通过后立即执行 `git commit` 与 `git push origin main`，同步最新版本代码到 Git 远程仓库。

---

*文档路径：`/home/skloxo/aho/openclaw/project/OpenVikingStudio/UI_SPECIFICATION.md`*  
*最新更新版本：`v1.0.10`（2026-07-27）*
