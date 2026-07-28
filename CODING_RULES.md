# OpenViking Studio — Agent 编码规范 (CODING RULES)
> **版本**: v1.1 | **最后更新**: 2026-07-28  
> **这是一份活文档 (Living Document)**，随项目迭代持续更新。  
> ⚠️ **所有 Agent 在每次开发任务前，必须将本文档加载到上下文中，逐条确认后方可动工。**

---

## 🔴 第零章：开发前强制检查 (Before You Touch Any Code)

每次开启新任务前，Agent 必须按顺序完成以下检查，才允许编写任何代码：

```
1. ✅ 已读取本文档 (CODING_RULES.md) 全文
2. ✅ 已读取视觉规范 (VK_DESIGN.md) 全文
3. ✅ 已确认当前任务已获得用户明确批准
4. ✅ 已确认 1936 开发服务正在运行，未触碰 1933 生产环境
5. ✅ 已确认上一个 Task 已终验通过并已 git push
```

---

## 一、 项目定位与边界 (Project Scope)

### 1.1 我们在做什么
- **项目**: OpenViking Studio 前端控制台 (`/home/skloxo/aho/openclaw/project/OpenVikingStudio`)
- **定位**: 针对 OpenViking 后端 API (`http://127.0.0.1:1933`) 的现代化 Web 管理控制台
- **核心方向**: **只迭代前端 (Frontend Only)**。OpenViking 后端是成熟的大团队产品，能不动尽量不动。

### 1.2 我们不碰什么
- ❌ 禁止修改 OpenViking 后端源码
- ❌ 禁止修改 `http://127.0.0.1:1933` 生产部署目录下的任何文件
- ❌ 禁止向后端添加新 API 接口（只使用已有接口）
- ❌ 如果某个功能必须修改后端才能实现，**必须先暂停并向用户报告，不得擅自行动**

---

## 二、 开发环境铁律 (Environment Rules)

| 环境 | 地址 | 用途 | 权限 |
| :--- | :--- | :--- | :--- |
| 开发环境 | `http://127.0.0.1:1936/studio` | 本地热更新调试与用户中验 | ✅ 唯一允许操作的环境 |
| 生产环境 | `http://127.0.0.1:1933/studio/` | 用户实际使用环境 | ❌ 严禁触碰 |

**版本号 z 递增规则**:
- 每个 Task 终验通过后，将 `package.json` 中 `z` 位 +1（如 `v1.1.1` → `v1.1.2`）
- 仅在终验通过后、git push 前更新，**禁止在开发中途随意改动版本号**

---

## 三、 任务卡片闭环 SOP (Task Card SOP)

```
┌─────────────────────────────────────────────────────────┐
│  Agent 发出任务卡片（明确目标文件、功能描述、验收标准）   │
└────────────────────────┬────────────────────────────────┘
                         │ 等待用户批准（禁止提前动工）
                         ▼
┌─────────────────────────────────────────────────────────┐
│  编写代码（单一组件，单次改动 ≤ 3 个文件）               │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│  AI 初验：npm run build 通过 + 自检清单全部 ✅           │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│  向用户汇报："Task X.X 已完成，请在 1936 端口中验"       │
└────────────────────────┬────────────────────────────────┘
                         │ 用户给出中验反馈
                         ▼
┌─────────────────────────────────────────────────────────┐
│  按反馈修改 → 重新构建 → 再次提交中验（如有改动）         │
└────────────────────────┬────────────────────────────────┘
                         │ 用户明确说"终验通过"
                         ▼
┌─────────────────────────────────────────────────────────┐
│  递增 z 版本号 → git add → git commit → git push        │
└────────────────────────┬────────────────────────────────┘
                         ▼
                  启动下一个 Task Card
```

---

## 四、 技术栈规范 (Tech Stack Rules)

### 4.1 当前技术栈清单 (锁定，禁止替换)

| 层级 | 技术 | 版本 | 备注 |
| :--- | :--- | :--- | :--- |
| 构建工具 | Vite | ^7.3.1 | 热更新极速 |
| 视图框架 | React | ^19.2.0 | 函数式组件 + Hooks |
| 类型系统 | TypeScript | ^5.7.2 | 严格模式，防止 AI 出错 |
| 样式 | Tailwind CSS v4 | ^4.1.18 | 内联样式，Agent 友好 |
| 图标 | Lucide React | ^0.545.0 | 统一图标库 |
| 路由 | TanStack Router | latest | 文件路由，自动生成 |
| 数据请求 | TanStack Query | ^5.x | useQuery 统一模式 |
| 全局状态 | Zustand | ^5.0.14 | 仅 25 行，极简 |
| 国际化 | react-i18next | ^17.x | 双语 zh-CN / en |

### 4.2 关于 TanStack Router 的特别说明 ⚠️
- `src/routeTree.gen.ts` 是**自动生成文件**，Agent **严禁手动修改**
- 新增路由：只需在 `src/routes/` 下创建对应目录和 `route.tsx`，Vite 插件会自动更新 `routeTree.gen.ts`
- 路由组件固定格式：
  ```tsx
  export const Route = createFileRoute('/page-name')({ component: PageComponent })
  ```

### 4.3 引入新依赖的规则
- 引入任何新 npm 包，必须在任务卡片中提前说明，经用户确认后方可安装
- 安装命令必须加 `--legacy-peer-deps` 防止冲突：`npm install xxx --legacy-peer-deps`
- 禁止引入：任何新路由库、新状态管理库、新 CSS 框架

---

## 五、 视觉规范 (Visual Design Rules)
> 完整规范见 [VK_DESIGN.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/VK_DESIGN.md)，以下是核心强制条款：

### 5.1 颜色系统
**禁止硬编码任何颜色**。必须使用 CSS 语义变量或以下 VK_DESIGN.md 规定的 Tailwind 配色：

| 用途 | 明亮模式 | 暗黑模式 |
| :--- | :--- | :--- |
| 页面背景 | `bg-slate-50` | `bg-[#090d16]` |
| 卡片背景 | `bg-white` | `bg-slate-900` |
| 侧边栏背景 | `bg-slate-100/70` | `bg-[#0b1120]` |
| 主要文字 | `text-slate-900` | `text-slate-50` |
| 次要文字 | `text-slate-500` | `text-slate-400` |
| 边框 | `border-slate-200/70` | `border-slate-800/80` |
| 主题色 | `text-blue-600` | `text-blue-500` |
| 成功/健康色 | `text-emerald-600` | `text-emerald-400` |
| ECharts 折线 VLM输入 | `text-sky-600` | `text-sky-400` |
| ECharts 折线 Embedding | `text-blue-600` | `text-blue-400` |

### 5.2 排版规范
- **禁用任何 box-shadow**（扁平化设计）
- **数值统计必须使用等宽字体**：`font-mono font-variant-numeric: tabular-nums`，防止数字刷新时跳动
- **界面字体**：Inter / -apple-system / Roboto / sans-serif（系统默认，无需额外引入）
- **边框**：全站卡片统一 `1px` 微细低透明度边框，不得使用重边框或装饰性边框

### 5.3 布局规范
- 无顶部 Header 栏，纵向空间最大化至 `100vh`
- 侧边栏支持折叠/展开两种状态，折叠时只显示图标，展开时显示图标 + 文字
- 卡片间距与圆角与现有 v1.1.0 页面保持像素级一致（参考 `/monitoring`、`/resources` 现有组件）

### 5.4 数据真实性规范 ⚠️
- **所有页面数据 100% 由 1933 真实 API 后端驱动**
- **严禁硬编码任何 mock 数据或假数据在生产代码中**
- 开发阶段如 API 未就绪，允许使用默认值 props，但需在代码注释中标明 `// TODO: 接入真实 API`

---

## 六、 国际化规范 (i18n Rules) ⚠️ 高频易错项

1. **JSX 中禁止直接写中文或英文字符串**：
   - ✅ 正确：`{t('monitoring.queue.processing')}`
   - ❌ 错误：`<span>处理中</span>`

2. **新增任何用户可见文字，必须同时在两个文件中添加对应 Key**：
   - `src/i18n/locales/zh-CN.ts`（中文）
   - `src/i18n/locales/en.ts`（英文）

3. **遗漏翻译 Key 属于严重 Bug**，会导致界面直接显示 Key 路径字符串（如 `monitoring.queue.title`）

4. 翻译 Key 命名规则：`页面名.组件名.字段名`，如 `monitoring.queue.processing`

---

## 七、 API 与数据请求规范 (API Rules)

1. **所有 API 请求函数统一封装在 `src/lib/ov-client.ts`**，禁止在组件内直接写 URL 字符串
2. **组件中使用 `useQuery` 发起请求**，不得裸写 `fetch()` 或 `axios()`：
   ```tsx
   const { data, isLoading } = useQuery({
     queryKey: ['queue-status'],
     queryFn: () => getQueueStatus(),
     refetchInterval: 10_000,
   })
   ```
3. **API 基础地址**来自 `useAppConnection` hook，禁止硬编码 `http://127.0.0.1:1933`
4. **处理 loading 与 error 状态**：每个使用 useQuery 的组件都必须处理 `isLoading` 和 `isError` 场景，不得直接裸渲染 `data`

---

## 八、 代码质量规范 (Code Quality Rules)

1. **单一职责**：每个 `.tsx` 文件只负责一个组件或一个页面，禁止混用
2. **单次改动上限**：一个 Task 最多改动 3 个文件，超出必须拆分为多个 Task
3. **组件 Props 用 interface 定义**（不用 type），与项目 `types/index.ts` 风格统一
4. **禁止把业务逻辑堆入 JSX return 块**：数据格式化、计算逻辑提取为独立 `const` 或辅助函数
5. **注释语言**：代码注释使用中文，与项目整体风格一致

---

## 九、 提交前自检清单 (Pre-submit Checklist)

向用户汇报"可中验"之前，Agent 必须逐项自查：

- [ ] `npm run build` 构建成功，**零** TypeScript 报错
- [ ] 新增用户可见文字已在 `zh-CN.ts` 和 `en.ts` 均添加 Key
- [ ] 未硬编码任何颜色值，全部使用 VK_DESIGN.md 规定的语义配色
- [ ] 未修改 `src/routeTree.gen.ts`（自动生成，禁止手动改）
- [ ] 未修改 1933 生产环境任何文件
- [ ] 单次 Task 改动文件数量 ≤ 3 个
- [ ] 所有数据通过 `useQuery` + `ov-client.ts` 封装函数获取，无裸写 URL
- [ ] 处理了 `isLoading` 和 `isError` 状态
- [ ] 数字统计使用了 `font-mono tabular-nums`

---

## 十、 文档维护规范 (Document Maintenance)

本文档是**活文档 (Living Document)**，随项目迭代不断完善。

- 每当发现新的易错点或踩坑经验，必须更新本文档对应章节
- 每当项目引入新技术或调整架构决策，必须同步更新技术栈清单
- 更新本文档不需要递增版本号，但需在文档顶部更新"最后更新"日期
- 重要变更在文档顶部用 `> ⚠️ 变更记录` 注明
