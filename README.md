# OpenViking Studio V1.0.0

> 🚀 **OpenViking Studio 官方原版技术重构与扩展监控控制台 (Official Refactored Edition)**

![Version](https://img.shields.io/badge/version-V1.0.0-blue.svg)
![React](https://img.shields.io/badge/React-18-blue)
![TypeScript](https://img.shields.io/badge/TypeScript-5.2-blue)
![Vite](https://img.shields.io/badge/Vite-5.1-purple)

---

## 📖 项目简介 (Introduction)

**OpenViking Studio V1.0.0** 是基于 ByteDance OpenViking 官方 1933 原版 Web 界面进行底层纯技术架构重构的前端工程。

在**1:1 像素级复刻**官方视觉外观与交互逻辑的基础上，针对大型监控数据看板与实时指标卡片场景进行了深度的底层重构与性能优化。

---

## ✨ 核心特性 (Key Features)

* **像素级原汁原味 UI**：完美继承 1933 官方浅色淡雅 UI、原生 ECharts 图表、上下文提交热力图与 Sidebar 布局。
* **全局向量化处理进度看板 (Global Progress Banner)**：实时计算并渲染全量（30,000+）向量任务大盘进度，精确统计已完成、进行中、等待中与失败数量。
* **单任务百分比与流光进度条 (Per-Task Progress)**：针对 `running` 状态任务，将后端 `stage` 状态机映射为 `25%`、`50%`、`75%` 实时百分比与流光动画。
* **智能重新入队 (Smart Re-queue)**：自动识别 `viking://resources/` 图谱 URI 并路由至 `/content/reindex` 接口，完美消除重试报错。
* **OpenViking 后端自愈补丁 (Auto-Healing Core Patch)**：
  - `TaskTracker._record_from_payload()` 数据自愈机制，彻底根除服务重启引发的 90%“伪进行中幽灵任务”。
  - 高效全局统计 API `GET /api/v1/tasks/stats`。
* **V1.0.0 规范化调整**：
  * Sidebar “连接与身份”上方声明 **V1.0.14** 版本。
  * 将语言切换 (中/EN) 与明暗模式切换组合整理至 Sidebar 区域。
  * 保持 Top Bar 极致干净整洁。
* **现代化技术栈**：使用 Vite 5 + React 18 + TypeScript 5 + Zustand + TanStack Query 打造高响应式底座。

---

## 🚀 向上游开源贡献 (Upstream PR Contribution)

本项目作为 OpenViking 官方生态的高高级增强控制台，包含针对 OpenViking Core (`volcengine/openviking`) 的核心补丁与前端增强方案：

- **Repository**: [https://github.com/skloxo/OpenVikingStudio](https://github.com/skloxo/OpenVikingStudio)
- **Upstream PR Description Template**:

```markdown
### Summary
This PR introduces the high-density Task Center progress monitoring and auto-healing TaskTracker mechanism from [skloxo/OpenVikingStudio](https://github.com/skloxo/OpenVikingStudio).

### Key Enhancements & Bug Fixes
1. **Auto-Healing TaskTracker (`openviking/service/task_tracker.py`)**:
   - Automatically heals task status to `COMPLETED`/`FAILED` when loading persisted task payloads where `stage` is `completed`/`failed`, eliminating ghost running task records caused by service restarts.
2. **Global Task Stats Endpoint (`openviking/server/routers/tasks.py`)**:
   - Adds `GET /api/v1/tasks/stats` returning real-time global task counts (`total`, `completed`, `pending`, `running`, `failed`) in milliseconds.
3. **Task Center Progress Banner & Smart Requeue (`OpenVikingStudio`)**:
   - Renders precise global vectorization progress banner and stage-to-percentage progress bars.
   - Automatically routes `viking://resources/` URI retries to `/content/reindex`.
```

---

## 🛠️ 快速启动 (Quick Start)

### 1. 安装依赖
```bash
pnpm install
```

### 2. 本地开发调试
```bash
npm run dev
```
访问开发服务：`http://localhost:1936/studio/home`

### 3. 打包构建
```bash
npm run build
```

---

## 📄 开源许可 (License)

Apache-2.0 License © 2026 OpenViking Team & Contributors.
