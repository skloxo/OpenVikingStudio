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
* **V1.0.0 规范化调整**：
  * Sidebar “连接与身份”上方新增 **V1.0.0** 版本标志声明。
  * 将语言切换 (中/EN) 与明暗模式切换组合整理至 Sidebar 区域。
  * 保持 Top Bar 极致干净整洁。
* **现代化技术栈**：使用 Vite 5 + React 18 + TypeScript 5 + Zustand + TanStack Query 打造高响应式底座。
* **高可用 API 客户端**：提供指数退避重试 (Exponential Backoff)、请求超时控制与安全容错降级。

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
