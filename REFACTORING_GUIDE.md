# OpenViking Studio 重构与开发规范文档 (Architecture & Refactoring Guide)

> **⚠️ 重要提示 (Agent 必读规则)**
> 后续任何 AI Agent 或开发者在对 OpenViking Studio 项目进行功能迭代或修改前，**必须优先阅读并严格遵守本文档**。
> 1. **严禁修改或污染 1933 正式环境任何代码和文件。**
> 2. 1936 开发环境统一采用 **Vite HMR 热更新调试模式**，实现 < 50ms 保存增量秒级生效。
> 3. **完成一个功能点 → 迭代一个 z 版本号 → 部署到 1936 → 等用户验收通过 → 再开始下一个。**

---

## 一、核心架构原则与环境隔离

### 端口与职责分工

| 端口 | 角色 | 说明 |
| :--- | :--- | :--- |
| **1933** | 生产环境（Production） | OpenViking 核心后端 + 官方原始 Web 静态托管。**绝对不可触碰。** |
| **1936** | 开发调试环境（Dev） | 独立 Vite Dev 热更新服务，前端源码修改 < 50ms 即时生效 |

### 隔离规则

- **1933 静态文件路径**（绝对禁止修改）：
  `/home/skloxo/.local/lib/python3.12/site-packages/openviking/web_studio/dist/`
- **1936 开发源码路径**（唯一允许修改的位置）：
  `/home/skloxo/aho/openclaw/project/OpenVikingStudio/`
- 1936 Vite Dev 服务通过 `vite.config.ts` 反向代理将所有后端 API 请求透传给 1933 后端，**1936 不持有任何后端数据，1933 代码文件不受任何影响**。

---

## 二、Vite Proxy 代理配置（关键！）

### 背景与问题根因

OpenViking 后端 API 路径**不全在 `/api` 前缀下**，部分核心路径在根路径：

| 路径 | 用途 |
| :--- | :--- |
| `/health` | **服务器健康检查与 auth_mode 探测（最关键！）** |
| `/ready` | 就绪检查 |
| `/api/**` | 主要业务 API |
| `/bot/**` | Bot 对话 API |
| `/admin/**` | 管理 API |
| `/console/**` | 控制台 API（Usage/Audit 数据） |
| `/sessions/**`、`/tasks/**`、`/system/**` | 会话、任务、系统 |
| `/search/**`、`/resources/**`、`/skills/**` | 搜索、资源、技能 |
| `/fs/**`、`/webdav/**` | 文件系统 |
| `/content/**`、`/relations/**`、`/privacy/**` | 内容、关系、隐私 |
| `/pack/**`、`/metrics/**` | 备份、指标 |

**曾出现的 Bug**：早期 proxy 只配置了 `/api`，导致 `/health` 请求打到 Vite 本身（404），
前端 `detectServerMode()` 拿不到 `auth_mode: "dev"` 响应 → 降级为 `'offline'` →
所有 Usage/Audit 数据显示"当前连接未获取到 admin/root 权限"。

### 当前 vite.config.ts 代理配置（正确版）

所有 OpenViking 后端路径均已在 `vite.config.ts` 中完整代理至 `http://127.0.0.1:1933`，
见 [vite.config.ts](./vite.config.ts)。

### Auth 机制说明

当 `/health` 返回 `auth_mode: "dev"` 时，前端代码 `resolveConnectionRoleProbeState()` 直接短路返回
`role: 'root'`，**无需 API Key 鉴权**，所有 admin/root 数据全量展示。

---

## 三、极速开发调试流程

### 启动 1936 开发服务器

```bash
# 项目目录：/home/skloxo/aho/openclaw/project/OpenVikingStudio
npx vite --port 1936 --host 0.0.0.0

# 或后台运行
nohup npx vite --port 1936 --host 0.0.0.0 > vite_dev.log 2>&1 &
```

- 修改 `src/` 下任何 `.tsx` / `.ts` / `.css` 文件 → 浏览器 **< 50ms 热重载**
- **修改 `vite.config.ts` 后必须重启 Vite 服务**（配置变更不支持 HMR）

### 重启 Vite 服务（修改 vite.config.ts 后必须执行）

```bash
# 杀掉旧进程
kill $(ps aux | grep "vite.js --port 1936" | grep -v grep | awk '{print $2}')

# 重新启动
nohup npx vite --port 1936 --host 0.0.0.0 > vite_dev.log 2>&1 &

# 验证代理正常（应返回 auth_mode: "dev"）
curl http://127.0.0.1:1936/health
```

### 发布至 1933（仅在用户明确下令时执行）

```bash
# 1. 构建静态产物
npx vite build

# 2. 覆盖至 1933 生产路径
cp -rf ./dist/* /home/skloxo/.local/lib/python3.12/site-packages/openviking/web_studio/dist/
```

---

## 四、版本功能清单（Changelog）

| 版本号 | 功能点描述 | 源码实现位置 | 验收状态 |
| :--- | :--- | :--- | :--- |
| **v1.0.1** | 移除顶部整条 Header，释放纵向展示空间 | `src/components/app-shell.tsx` | ✅ 已验收 |
| **v1.0.2** | 侧边栏标题区添加版本号副标题 | `src/components/app-shell.tsx` | ✅ 已验收 |
| **v1.0.3** | 语言切换移至侧边栏底部，UI 统一 | `src/components/app-shell.tsx` | ✅ 已验收 |
| **v1.0.4** | 主题切换移至侧边栏底部；侧边栏收起/展开按钮修复；请求日志路由修复 | `src/components/app-shell.tsx` | ✅ 已验收 |
| **v1.0.5** | **Vite Proxy 完整修复**：补全所有 OpenViking 后端路径代理（含 `/health`），修复"admin/root 权限缺失"问题 | `vite.config.ts`、`src/hooks/use-app-connection.tsx` | ❌ 未通过（Playground 崩溃） |
| **v1.0.6** | **修复 Playground 缺失 Icon 导入导致的渲染崩溃**：在 `terminal-panel.tsx` 中补全 `TerminalIcon` 导入 | `src/routes/playground/-components/terminal-panel.tsx` | ✅ 已验收 |
| **v1.0.7** | **侧边栏账号切换器 Dev 模式防护**：在 `account-switcher.tsx` 增加 `serverMode !== 'dev'` 拦截，消除单租户后端 `/admin/accounts` 500 告警 | `src/components/account-switcher.tsx` | ✅ 已验收 |
| **v1.0.8** | **Home 基础指标卡片高密对齐 (Task-v1.0.8)**：重构 `panel.tsx` 与 `metric-panels.tsx`，应用 `UI_SPECIFICATION` 高密 4px 微圆角与汉化 | `src/routes/home/-components/panel.tsx`、`metric-panels.tsx` | ✅ 已验收 |
| **v1.0.9** | **Home Token 趋势图表高密重构 (Task-v1.0.9)**：重构 `token-trend-panel.tsx` 与 `token-trend-chart.tsx`，渲染高度压缩至 240px，图表/Tooltip 全面应用 4px 硬朗微圆角 | `src/routes/home/-components/token-trend-panel.tsx`、`token-trend-chart.tsx` | ✅ 已验收 |
| **v1.0.10** | **Home Context Commits 热力图高密重构 (Task-v1.0.10)**：重构 `context-commits-heatmap.tsx`，将热力图浮层与右侧统计数据全量落地 4px 微圆角与 font-mono 紧凑对齐，去除底部图例条 | `src/routes/home/-components/context-commits-heatmap.tsx` | ✅ 已验收 |
| **v1.0.11** | **检索搜索栏与控制栏 4px 硬朗高密重构 (Task-v1.0.11)**：重构 `search-bar.tsx` 与 `retrieval-controls.tsx`，应用 4px 硬朗微圆角、快捷键标示与紧凑字体布局 | `src/routes/retrieval/-components/search-bar.tsx`、`retrieval-controls.tsx` | 🔄 待验收 |
| **v1.0.12** | **检索结果列表高密卡片化重构 (Task-v1.0.12)**：重构 `retrieval-results.tsx`，将结果卡片全量落地 4px 实线微边框、`px-3 py-2.5` 紧凑行高与 2px `rounded-xs` 得分 Tag | `src/routes/retrieval/-components/retrieval-results.tsx` | ✅ 已验收 |
| **v1.0.13** | **技能卡片与资源浏览高密重构 (Task-v1.0.13)**：重构 `skills/route.tsx` 与 `item-column.tsx`，应用 4px 卡片微圆角与 `font-mono` Scope 标签 | `src/routes/skills/route.tsx`、`resources/-components/item-column.tsx` | 🔄 待验收 |

---

## 五、关键文件索引

| 文件 | 用途 |
| :--- | :--- |
| `UI_SPECIFICATION.md` | **视觉与高密布局规范文档**（参照 `tedtrading` 风格） |
| `REFACTORING_PLAN.md` | **全量微拆分重构计划文档**（划分 30+ 个微小迭代版本） |
| `vite.config.ts` | Vite 配置：端口 1936、base `/studio/`、全量 API 代理 |
| `index.html` | 预注入 `ov_console_connection` 到 localStorage（含 root API Key） |
| `src/hooks/use-app-connection.tsx` | 连接状态管理，含 `ROOT_API_KEY_FALLBACK` 兜底 |
| `src/hooks/use-server-mode.ts` | 检测 `auth_mode`，`dev` 模式直接授予 root 权限 |
| `src/components/app-shell.tsx` | 主布局：侧边栏、导航、语言/主题切换 |
| `REFACTORING_GUIDE.md` | 本文档，项目根规范 |
| `AGENTS.md` | AI Agent 工作规则，强制阅读本文档 |

---

*文档更新时间：2026-07-27 19:44*
*当前版本：v1.0.8*
*文档状态：已生效，持久化保存于项目根目录*
