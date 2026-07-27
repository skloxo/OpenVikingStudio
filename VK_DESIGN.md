# OpenViking Studio (VK) 视觉规范与设计契约 (VK_DESIGN.md)

本规范参考并沿袭 **TideTrading (潮汐投研) 视觉设计体系**，专为 **OpenViking Studio (VK Studio)** 企业级 AI 基础设施工作站量身打造。所有前端组件、CSS 样式、扩展脚本与技术重构必须**无条件遵守**本规范，确保界面极致数据密度、高保真对比度、无缝明暗切换与像素级对齐。

---

## 🪐 1. Brand Identity & Design Atmosphere (品牌调性与设计内核)

- **定位 (Positioning)**：**"Enterprise AI Infrastructure Workstation" (企业级 AI 基础设施工作站)**。
- **视觉风格 (Style)**：数据密集、紧凑平整、高清晰度字体排版、硬朗轻盈。
- **空间利用 (Elevation & Boundaries)**：
  - **扁平无阴影**：完全扁平化设计，**禁用重阴影 (`box-shadow: none`)**。
  - **低透明度边框**：全站卡片与侧边栏采用 `1px` 微细低透明度边框 (`border-slate-200/70` / `border-slate-800/80`) 隔离空间。
  - **纵向空间最大化**：完全隐藏顶部 `<header>` 栏，将纵向屏幕展示高度最大化利用至 `100vh`。

---

## 📐 2. Headerless Space-Maximizing Layout (无顶栏空间最大化布局)

```
+-------------------------------------------------------------------------------+
| OpenViking Studio                                                            |
| v1.0.x (纯文本副标题, 与 Logo 字母 left: 16px 像素级精准左对齐)              |
+-------------------------------------------------------------------------------+
| 首页                                                                         |
| 实验场                                                                       |
| 检索                                                                         |
| 请求日志                                                                     |
| 会话                                                                         |
|                                                                               |
|                                                                               |
| 连接与身份                                                                   |
| OAuth 验证                                                                   |
| [中 / EN]   (位置 1：原生语言切换胶囊按钮, 物理平移归位)                     |
| [ 🌙 / ☀️ ] (位置 2：原生主题色切换图标按钮, 物理平移归位)                    |
| GitHub                                                                        |
| 文档站                                                                       |
+-------------------------------------------------------------------------------+
```

### 侧边栏折叠/展开联动规范：

- **展开状态 (`expanded`)**：显示完整标题 `OpenViking Studio`、副标题 `v1.0.x` 及底部 `中 / EN` 胶囊与主题图标。
- **折叠状态 (`collapsed`)**：副标题 `v1.0.x` 与文本标题自动隐退 (`display: none`)，图标安全列对齐，无任何溢出或挤压。

---

## 🎨 3. Color Palette & Dark/Light Semantic System (配色与语义色彩矩阵)

全站严格使用语义化配色方案，支持明亮 (`light`) 与暗黑 (`dark`) 真实双模式无缝切换。中性黑/纯灰禁止乱用。

| 语义角色 (Semantic Role)      | 明亮模式 (Light Hex / Tailwind)       | 暗黑模式 (Dark Hex / Tailwind)        | 用途说明 (Usage)               |
| :---------------------------- | :------------------------------------ | :------------------------------------ | :----------------------------- |
| **Viewport Background** | `#f8fafc` (`bg-slate-50`)         | `#090d16` (`bg-[#090d16]`)        | 页面整框底色                   |
| **Card Surface**        | `#ffffff` (`bg-white`)            | `#0f172a` (`bg-slate-900`)        | 指标卡片、ECharts 图表容器背景 |
| **Sidebar Surface**     | `#f1f5f9` (`bg-slate-100/70`)     | `#0b1120` (`bg-[#0b1120]`)        | 左侧 Sidebar 容器背景          |
| **Primary Accent**      | `#2563eb` (`text-blue-600`)       | `#3b82f6` (`text-blue-500`)       | 选中导航、主按键、重点标注     |
| **VLM Input Trend**     | `#0284c7` (`text-sky-600`)        | `#38bdf8` (`text-sky-400`)        | ECharts VLM 输入折线与填充色   |
| **VLM Output Trend**    | `#0d9488` (`text-teal-600`)       | `#2dd4bf` (`text-teal-400`)       | ECharts VLM 输出折线与填充色   |
| **Embedding Trend**     | `#3b82f6` (`text-blue-600`)       | `#60a5fa` (`text-blue-400`)       | ECharts Embedding 折线与填充色 |
| **Heatmap Active**      | `#059669` (`bg-emerald-600`)      | `#34d399` (`bg-emerald-400`)      | 365 天提交热力图活跃波段       |
| **Border Low-Opacity**  | `#e2e8f0` (`border-slate-200/70`) | `#1e293b` (`border-slate-800/80`) | 干净细分割线                   |
| **Primary Text**        | `#0f172a` (`text-slate-900`)      | `#f8fafc` (`text-slate-50`)       | 主数字、大标题、选中文字       |
| **Secondary Text**      | `#64748b` (`text-slate-500`)      | `#94a3b8` (`text-slate-400`)      | 标签说明、版本副标题`v1.0.x` |

---

## 🔡 4. Typography & Monospace Tabular Rules (字体排版与数字规范)

1. **界面字体**：`Inter`, `-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, `Roboto`, `sans-serif`。
2. **等宽表格数字 (Tabular Figures)**：
   - 所有数值统计（Token 数、上下文计数、检索次数、热力图 Hover 浮层数据、版本号 `v1.0.x`）必须使用 **等宽字体 (Monospace)**：
     ```css
     font-family: 'JetBrains Mono', 'Fira Code', ui-monospace, monospace;
     font-variant-numeric: tabular-nums;
     ```
   - *目的*：防止数据实时刷写或切换时发生左右跳动与像素移位。

---

## 📦 5. Non-Destructive DOM Modification Rules (非侵入式 DOM 微调原则)

1. **100% 官方原版底座**：
   - 以 `openviking/web_studio/dist` 官方编译构建产物为底座。
   - 所有页面模块 (Playground, Search, Logs, Sessions, ECharts, Heatmap) **100% 保持由 1933 真实 API 后端数据驱动**，绝不假造或硬编码任何 MVP 数据。
2. **节点物理平移 (DOM Relocation)**：
   - 平移 Header 原生按钮（`中 / EN` 胶囊与 `🌙 / ☀️` 图标）时，使用 `appendChild` 将原生 DOM 节点整体物理移入侧边栏底部，**完全保留 React 原生 Fiber 节点与 `onClick` 事件监听器**。
3. **HTML 嵌套禁忌**：
   - 严禁把原生 `<button>` 嵌套进另一个 `<button>` 标签中，规避浏览器的事件拦截。

---

## ⚡ 6. Incremental Iteration & Acceptance SOP (渐进式重构与阶段验收 SOP)

1. **原子任务拆分**：一个微小功能点 ➡️ 一个独立任务。
2. **版本号自然增长**：每次重构或微调，均递增 `z` 版本号 (`V1.0.1` ➡️ `V1.0.2` ➡️ `V1.0.3`...)，并同步至 `package.json`、`server.js`、`/health` 响应与侧边栏副标题。
3. **部署上线与等待指示**：
   - 部署至 `1936` 端口 ➡️ 使用 `browser_subagent` 进行截屏/测量校验 ➡️ 发送报告等待用户验收。
   - **只有收到用户明确的“验收通过”指令后，才能开始下一个任务**。
3.
