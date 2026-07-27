# OpenViking Studio 🚀 (v1.1.0)

**OpenViking Studio** 是针对 **OpenViking 上下文数据库与多智能体记忆中枢** 的现代化控制台管理前端。支持对上下文数据流、会话追踪、底层 VikingDB 资源树、全局 Task 任务调度以及模型 Token 消耗进行全方位实时监控与可视化管理。

---

## 🌟 核心特性 (Features)

### 1. 🏠 控制台 Dashboard (`/home`)
- **上下文统计**：实时掌控文件、技能与记忆总数。
- **Token 消耗分析**：全方位统计 VLM 输入/输出 Tokens 及 Embedding 消耗。
- **探活与权限判定**：自动识别连接身份（Root / Admin / User），主页状态无缝兼容 `/api/v1/health`。

### 2. 📋 任务中心 Task Center (`/tasks`)
- **全自动消费流转**：后台 Task Consumer 秒级自动拾取，实现 `pending` ➔ `running` ➔ `completed` 无感全流转。
- **队列自愈与滤重**：针对重新入队的 Task 自动做隐去滤重，避免失败列表污染。
- **双重实时刷新**：支持对 Top 统计卡片与任务列表的并发 refetch 响应。

### 3. 📁 资源管理器 Resource Explorer (`/resources`)
- **Viking Graph 图谱可视化**：以图形化方式直观展示 `viking://resources/` 节点拓扑。
- **文本与片段查看器**：可深度调阅任意 L0 / L1 / L2 数据切片及 Embedding 向量关联。

### 4. 💬 会话查看器 Session Inspector (`/sessions`)
- **多智能体轨迹追踪**：支持 Antigravity IDE、Hermes、MIMO Code 等多 Smart Agent 的 Session 会话全量回溯。

### 5. 🔍 检索 RAG Playground (`/retrieval` & `/playground`)
- **语义匹配与距离调试**：可在线对向量数据库发起 Find / Search 查询，测试准确度与延迟。

---

## 📦 快速开始 (Quick Start)

### 1. 安装依赖
```bash
npm install
```

### 2. 本地开发
```bash
npm run dev
```
控制台默认将在 `http://127.0.0.1:1936/studio` 启动。

### 3. 构建生产包
```bash
npm run build
```

---

## 📄 Release v1.1.0 更新日志 (Release Notes)

- ⚡ **前端架构全量重构完成**：基于 React 18 + TypeScript + Vite + Tailwind CSS 重构。
- 🛠️ **任务中心自动消费机**：解决高并发 Task 堵塞与枚举判定 Bug，全局 3,000+ 任务处理进度达 100%。
- 🛡️ **网络代理防抓包隔离**：兼容 `NO_PROXY` 隔离，完美配合底层 OpenViking 引擎。
- 🎨 **UI 界面布局优化**：精简重复侧边栏菜单，响应式抽屉与卡片流展示。

---

## 📜 许可证 (License)

Apache-2.0 License.
