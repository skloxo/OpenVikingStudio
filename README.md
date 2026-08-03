# OpenViking Studio

中文 / [English](README_EN.md)

OpenViking Studio 是面向多 Agent 系统的上下文与技能管理工作台。它连接底层 OpenViking 引擎，为 Antigravity、OpenClaw、Hermes 等 Agent 提供长期记忆存储、上下文监控、SOP 质量门禁与技能自演进服务。

---

## 核心功能

- **文件系统事件感知**：基于 Linux `inotify` 物理事件引擎，实时感知技能文件的读取与修改，无需手动触发更新。
- **记忆遥测与日志沉淀**：直连底层持久化数据存储。Agent 沉淀经验时，自动提取结构化 Lesson 并更新技能配置。
- **原生接口适配**：对接 OpenViking 0.4.x/0.5.x 原生 FastMCP 接口、WorkMemory v2 内存机制及 `ov dream` 增量同步。
- **上下文 Token 优化**：集成微型 LLMLingua-2 筛选模型，在保护 YAML 头部与代码块结构完整的前提下，平均减少 35% 提示词开销。

---

## 架构与演进路线

```text
  Phase 1: 当前基线 (v1.2.35+)         Phase 2: 渐进演进 (v1.3.x)          Phase 3: 架构拓展 (v2.0)
+--------------------------------+   +--------------------------------+   +--------------------------------+
| 技能托管与事件感知             |   | Skill-Loop 经验提取飞轮        |   | 在线技能创建与沙盒验证        |
| 真实遥测数据链                 | ➔ | SkillOpt 质量评分与门禁        | ➔ | Monaco 编辑器集成             |
| IDE 与 OpenViking 会话同步     |   | 动态权重与自动排名             |   | 敏感字段过滤与脱敏             |
+--------------------------------+   +--------------------------------+   +--------------------------------+
```

---

## 快速开始

### 1. 启动 OpenViking 服务
```bash
openviking-server --config ~/.openviking/ov.conf --host 0.0.0.0 --port 1933
```

### 2. 启动 Web Studio
```bash
npm install
npm run dev
```
打开 `http://localhost:5173` 访问工作台。

---

## 许可证

Apache-2.0 License
