# 🧰 OpenViking Studio 全景通用组件与轮子资产档案库 (Component & Wheel Inventory SSOT)

> **物理真相源标识**：`OpenVikingStudio/docs/architecture/COMPONENT_AND_WHEEL_INVENTORY.md`  
> **制定时间**：2026-09-10  
> **核心工程铁律**：**【查库第一，禁止手搓 (Search First, Never Duplicate)】**  
> 任何 Agent（主 Agent、子代理、外部协作智能体）在开发新功能、新页面、新抽屉或新指标前，**必须 100% 强制先查阅本档案库**。凡能直接复用或微调复用的，严禁重新手搓野蛮代码！

---

## 🧭 研发准入三大铁律 (Three Golden Rules of Component Reuse)

```
       [用户需求 / 新功能规划]
                 │
                 ▼
     ┌───────────────────────┐
     │ 1. 查库 (本资产档案)   │ ── 发现已有现成轮子 ──► 直接 import 复用 (Direct Reuse)
     └───────────────────────┘
                 │ (未找到 100% 匹配)
                 ▼
     ┌───────────────────────┐
     │ 2. 微调 (Tuned Reuse) │ ── 扩展现有组件 Props ──► 保留单一真相源 (Single Source)
     └───────────────────────┘
                 │ (系统底层确实缺失)
                 ▼
     ┌───────────────────────┐
     │ 3. 提纯 (Harvest)     │ ── 编写新公共组件 ──► 必须回填本档案库并导出 (Harvest-as-You-Go)
     └───────────────────────┘
```

1. **查库第一 (Search First)**：开工写代码前，先按功能维度在本文档中检索，禁止不看档案就手搓样式、状态或工具函数；
2. **拒绝代码堆叠 (No Nested Layering)**：禁止在外层无脑再套一层私有 Wrapper，优先为底层公用组件补充规范 Props；
3. **完工回填入库 (Harvest-as-You-Go)**：开发中凡抽象出的通用能力，完工后必须沉淀入公共目录，并在本文档中登记档案，实现项目资产越滚越大、后续开发越写越快！

---

## 📦 一、 基础原子 UI 轮子资产 (`src/components/ui/` - 34 个现成组件)

全部基于 TailwindCSS + Radix/Base UI 精雕细琢，具备高可靠性、无障碍访问 (a11y) 与明暗双主题自适应。

| 组件名称 | 物理文件路径 | 核心功能与使用场景 | 常见 Props / 关键用法 |
|:---|:---|:---|:---|
| **Button** | `src/components/ui/button.tsx` | 系统标准按钮 | `variant`: `default` \| `destructive` \| `outline` \| `secondary` \| `ghost` \| `link`<br>`size`: `default` \| `sm` \| `lg` \| `icon` \| `xs` (高密优先) |
| **Badge** | `src/components/ui/badge.tsx` | 状态徽章与分类胶囊 | `variant`: `default` \| `secondary` \| `destructive` \| `outline`<br>⚠️ 字号必须保持 $\ge 11\text{px}$ (`text-[11px]`) |
| **Card** | `src/components/ui/card.tsx` | 基础卡片容器 | 子组件：`CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, `CardFooter`<br>高密规范：推荐 `p-3` 或 `p-3.5`，扁平无阴影 |
| **Dialog** | `src/components/ui/dialog.tsx` | 居中模态对话框 | 子组件：`DialogTrigger`, `DialogContent`, `DialogHeader`, `DialogTitle`, `DialogDescription`, `DialogFooter` |
| **Sheet** | `src/components/ui/sheet.tsx` | 侧滑抽屉 (Drawer) | 详情、日志、记忆影响、配置抽屉的标配底座。<br>`side`: `right` (默认) \| `left` \| `top` \| `bottom` |
| **AlertDialog** | `src/components/ui/alert-dialog.tsx` | 危险操作二次确认弹窗 | 清理历史、重置配置、删除资源必须使用此弹窗，禁止原生 `window.confirm` |
| **Select** | `src/components/ui/select.tsx` | 标准单选下拉框 | 子组件：`SelectTrigger`, `SelectValue`, `SelectContent`, `SelectItem`<br>支持 `size="sm"` 高密紧凑样式 |
| **DropdownMenu** | `src/components/ui/dropdown-menu.tsx` | 操作菜单下拉浮层 | 表格行操作、用户菜单、更多选项浮层 |
| **Table** | `src/components/ui/table.tsx` | 高密数据表格基座 | 子组件：`TableHeader`, `TableBody`, `TableHead`, `TableRow`, `TableCell`<br>高密规范：行高推荐 `py-1.5` |
| **Pagination** | `src/components/ui/pagination.tsx` | 原生分页控制器 | 子组件：`PaginationContent`, `PaginationItem`, `PaginationLink`, `PaginationPrevious`, `PaginationNext` |
| **Tooltip** | `src/components/ui/tooltip.tsx` | 悬停说明气泡 | `TooltipProvider`, `TooltipTrigger`, `TooltipContent`<br>所有仅有 Icon 的按钮必须配置 Tooltip 说明 |
| **Popover** | `src/components/ui/popover.tsx` | 复杂浮动卡片面板 | 筛选器弹出层、高级配置卡片 |
| **ScrollArea** | `src/components/ui/scroll-area.tsx` | 自定义滚动条容器 | 抽屉内长日志、长文本滚动推荐使用 |
| **Tabs** | `src/components/ui/` / Radix | 选项卡标签栏 | 页面多维度分类切换 |
| **Switch** | `src/components/ui/switch.tsx` | 开关控制器 | 自动刷新、暗黑模式、权限开关 |
| **Checkbox** | `src/components/ui/checkbox.tsx` | 复选框 | 表格批量选择、多选过滤 |
| **Input** | `src/components/ui/input.tsx` | 单行输入框 | 支持 `size="sm"` 高密样式 |
| **Textarea** | `src/components/ui/textarea.tsx` | 多行文本域 | 支持自适应高度与等宽字体 |
| **Skeleton** | `src/components/ui/skeleton.tsx` | 骨架屏占位块 | 数据加载中过渡，禁止裸转圈，推荐骨架屏 |
| **Spinner** | `src/components/ui/spinner.tsx` | 极简加载旋转指示器 | 按钮内部提交、行级微载入 |
| **Sonner (Toast)** | `src/components/ui/sonner.tsx` | 全局轻量通知吐司 | `toast.success()`, `toast.error()`, `toast.info()` |
| **Progress** | `src/components/ui/progress.tsx` | 进度条 | `value={percentage}`，用于上传、工序推进 |
| **Collapsible** | `src/components/ui/collapsible.tsx` | 折叠收起面板 | 可折叠代码块、高级选项折叠 |
| **Separator** | `src/components/ui/separator.tsx` | 语义分割线 | 水平/垂直分割 |
| **Alert** | `src/components/ui/alert.tsx` | 静态提示横幅 (Alert) | `AlertTitle`, `AlertDescription`，支持 default / destructive 样式 |
| **Breadcrumb** | `src/components/ui/breadcrumb.tsx` | 面包屑导航栏 | `BreadcrumbList`, `BreadcrumbItem`, `BreadcrumbLink`, `BreadcrumbPage`, `BreadcrumbSeparator` |
| **ButtonGroup** | `src/components/ui/button-group.tsx` | 紧凑按钮编组 | 多选切换、紧密并排操作栏 |
| **Combobox** | `src/components/ui/combobox.tsx` | 可搜索组合下拉框 | 复杂实体、大型字典搜索过滤下拉 |
| **ContextMenu** | `src/components/ui/context-menu.tsx` | 右键上下文菜单 | 资源树、表格行右键菜单 |
| **Field** | `src/components/ui/field.tsx` | 表单字段与校验包裹器 | `FieldLabel`, `FieldDescription`, `FieldError` 表单规范组件 |
| **InputGroup** | `src/components/ui/input-group.tsx` | 前后缀紧凑输入框组 | 带前缀图标、带单位/后缀按钮的高密输入组 |
| **Label** | `src/components/ui/label.tsx` | 规范表单文字标签 | 标准 accessible 表单 Label |
| **RadioGroup** | `src/components/ui/radio-group.tsx` | 单选框编组 | `RadioGroupItem`，互斥单选 |
| **Sidebar** | `src/components/ui/sidebar.tsx` | 侧边栏布局基座 | 响应式侧边栏系统组件，支持折叠与状态持久化 |

---

## 🏛️ 二、 应用级布局与中枢轮子 (`src/components/`)

面向整个 Studio 的跨页面应用级基础架构组件：

| 轮子组件 | 物理路径 | 核心价值与复用方式 |
|:---|:---|:---|
| **AppShell** | `src/components/app-shell.tsx` | **系统主框架总线**：集中管理左侧高密折叠侧边栏、顶部面包屑与标题、暗黑/明亮自适应主题切换、网络状态心跳感知与全局快捷键（`Cmd+K`）。所有页面自动继承此框架，严禁在页面内自建外壳。 |
| **CurrentUserMenu** | `src/components/current-user-menu.tsx` | **当前操作者与租户菜单**：展示当前鉴权角色、API Key 掩码、快速注销、系统版本号与诊断入口。 |
| **AccountSwitcher** | `src/components/account-switcher.tsx` | **多租户与身份切换器**：用于多节点、多受信任用户之间的无缝鉴权切换。 |
| **ServerDoctorDialog** | `src/components/server-doctor-dialog.tsx` | **服务端一键诊断体检中心**：集成 1933 端口连通性、2080Ti GPU 显存、WSL 探针、SQLite 锁状态排查，任何页面可一键唤起。 |
| **AccessRequiredGate** | `src/components/access-required-gate.tsx` | **鉴权阻断门禁容器**：对需要特定特权的页面自动拦截并引导输入凭据，保护敏感管理接口。 |

---

## ⚙️ 三、 通用数据面与通信客户端轮子 (`src/lib/`)

全系统统一的数据流转、协议解析与工具库：

| 纯函数 / 客户端轮子 | 物理路径 | 核心能力与规范契约 |
|:---|:---|:---|
| **`formatBytes` / `formatDurationMs` / `formatDurationSec`** | `src/lib/formatters.ts` | **通用标准化格式化库**：统一 1024 进制字节换算 (`B/KB/MB/GB/TB`)、毫秒/秒耗时自解释换算 (`ms/s/m/h`)、大数字紧凑格式化 (`k/M`)。 |
| **`copyTextToClipboard`** | `src/lib/clipboard.ts` | **全环境免疫安全复制**：原生优先 + 自动 `textarea` 降级，在局域网 HTTP（如 `10.x.x.x`）或远程 IP 下 100% 杜绝抛出 SecurityError 崩溃！ |
| **`VikingUri` 解析器** | `src/lib/viking-uri.ts` | **资源 URI 唯一解析底座**：统一解析 `viking://user/default/memories/...` 协议头、命名空间、分区与文件名，严禁业务代码手写正则切割。 |
| **`OKF Markdown` 解析器** | `src/lib/okf-markdown.ts` | **知识格式结构化引擎**：精准剥离与解析 YAML Frontmatter 元数据、TOC 目录大纲生成，已带自动化单测保护。 |
| **`SSE` 流式通道管理** | `src/lib/sse.ts` | **服务器推送流式连接池**：用于 Agent 思考吐字、任务工序实时推送，内置心跳检测与断线自动重连。 |
| **`QueryClient` 全局单例** | `src/lib/query-client.ts` | **TanStack React Query 单例**：统一配置 `staleTime: 15_000`、页面切后台断流休眠 (`refetchIntervalInBackground: false`)，阻断无脑高频轮询。 |

---

## 🚀 四、 核心业务通用高阶公共轮子清单 (`src/components/common/` & 专属轮子)

全系统已完成提纯并经受机器视网膜测试守护的系统级高阶轮子：

| 通用轮子名称 | 物理路径 | 核心能力与适用场景 | 状态与版本 |
|:---|:---|:---|:---:|
| **`CopyButton`** | `src/components/common/copy-button.tsx` | **带安全降级的一键复制按钮**：内部基于 `copyTextToClipboard`，自动维护 copied 状态、图标动态切换（CopyIcon ➔ CheckIcon 冰青色高亮）、支持自定义 label 与尺寸。彻底消灭全站散落手搓。 | ✅ 已交付 (v1.4.82) |
| **`UnifiedMemoryImpactView`** | `src/components/memory-impact/` | **通用记忆影响原子纯视图 (跨场景任意嵌入)**：<br>• 剥离所有 `<Sheet>` 抽屉包装，可无缝嵌入**页面 (Page)、抽屉内 (Nested Drawer-free)、弹窗 (Dialog/Modal)**；<br>• 统一汇总卡片 (`ImpactSummaryCards`)、分类 Tab 与差异条目 (`MemoryDiffItem`)；<br>• 支持受控快照模式 (Controlled) 与懒查询模式 (Lazy Query)；<br>• 彻底消灭抽屉套抽屉 (Nested Drawer) 的劣质体验。 | ✅ 已交付 (v1.4.88) |
| **`UniversalMemoryImpact`** | `src/components/memory-impact/` | **原子化开箱即用记忆影响卡片 (全站统一骨架与交互)**：<br>• 自包含标准卡片容器、标题、增量指示胶囊（+1 ~1）、折叠展开按钮与多分类 Diff 列表；<br>• 在门禁自解释抽屉、任务中心抽屉、会话中心中 1 行直接嵌入，彻底杜绝 ABCD vs ABCDEF 差异；<br>• 单点迭代，全站受益。 | ✅ 已交付 (v1.4.92) |
| **`UnifiedMemoryImpactDrawer`** | `src/components/memory-impact/` | **通用记忆增量审计快照抽屉 (轻量外壳包装)**：<br>• 仅作为 `UnifiedMemoryImpactView` 的轻量 Drawer 容器适配层；<br>• 对外保持 100% 向后兼容；<br>• 仅在顶层单页调用时使用，抽屉内严禁嵌套调用。 | ✅ 已交付 (v1.4.82) |
| **`UniversalPagination`** | `src/components/common/universal-pagination.tsx` | 统一分页控制器：条数切换 (`10/25/50/100`)、翻页按钮、等宽页码，严格 $\ge 11\text{px}$ 规范。 | ⏳ 规划中 |
| **`MetricTile`** | `src/components/common/metric-tile.tsx` | 统一 `p-3` 紧凑卡片、等宽大数字 (`tabular-nums font-mono`)、四态语义支持（冰青/湛蓝/琥珀/玫瑰红）。 | ⏳ 规划中 |
| **`EmptyState`** | `src/components/common/empty-state.tsx` | 极客风空状态展示，支持图标胶囊、主副标题、可选重置筛选按钮。 | ⏳ 规划中 |

---

## 🛠️ 五、 新功能开发标准复用流程 (Agent SOP)

```markdown
1. 【第一步·检索】：打开本文档 (`COMPONENT_AND_WHEEL_INVENTORY.md`)，搜索关键词（如 "复制", "卡片", "抽屉", "分页", "格式化"）；
2. 【第二步·复用】：
   - 需要画按钮 ➔ 引入 `Button` (优先 `size="xs"` / `variant="outline"`)；
   - 需要做分页 ➔ 引入 `UniversalPagination`；
   - 需要复制内容 ➔ 引入 `CopyButton`；
   - 需要请求后端 ➔ 引入 `ovClient`；
   - 需要格式化字节 ➔ 引入 `formatBytes`；
   - 需要展示记忆变更 ➔ 引入 `UnifiedMemoryImpactDrawer`；
3. 【第三步·扩展】：如果现有轮子缺少某个小参数，**修改轮子本身以支持该参数**，让全系统共享该增强，严禁另起炉灶写个私有版！
4. 【第四步·归档】：若确实开创了全新通用形态，完工后向本文档登记档案并提交！
```
