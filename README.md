# ⚔️ OpenViking Studio (v1.3.0)

> **面向多 Agent 系统的下一代上下文、记忆中枢与技能管理工作台**  
> **Current Version**: `v1.3.0` (Minor Release 次版本号升级) | **License**: Apache-2.0

---

## 📌 1. v1.3.0 核心演进与重大特性 (Major Features in v1.3.0)

OpenViking Studio `v1.3.0` 是一个里程碑级别的次版本升级，在系统完整性、记忆治理、底层 Parser 对齐及国际化呈现上完成了全面重构：

- 🚀 **100% 完整多语言体系 (i18n SSOT)**：补齐全系统所有 9 大观测卡片与侧边栏的完全中文 (`zh-CN`) / 英文 (`en`) 词条，默认启用流畅中文界面，彻底消除 Key 路径乱码。
- 🛠️ **CJK Token 估算精准对齐**：纠正 Markdown Parser 中 CJK 字符估算系数（`0.7` ➔ `1.0`），使其与 Embedder 物理批次容量 (`-b 2048`) 100% 对齐；彻底删除 `[:1800]` 假截断 fallback，保障记忆数据 100% 完整入库。
- 🛡️ **任务自愈重新入队引擎**：优化任务中心“重新入队”重试机制为 `semantic_and_vectors` 模式，自动重新生成精简摘要并向量化，打破死重试循环。
- 🤖 **Agent 开局唯一真相源 (Agent SSOT)**：在工程中构建 `.agents/AGENTS.md`、`docs/PHILOSOPHY.md`、`docs/UI_DESIGN_SPEC.md` 与 `docs/ARCHITECTURE_BLUEPRINT.md`，任何 Agent 开局第一眼即可感知项目设计哲学与规范。
- 🔒 **物理级灾备与秒级回滚**：集成底层 VikingFS Git 级硬快照（`POST /api/v1/snapshot/commit`）与 `ovpack` 导出能力，任何敏感数据治理前均可秒级还原。

---

## 🏛️ 2. 架构演进路线 (Iteration Roadmap)

```text
  Phase 1: 基础构建 (v1.2.x)              Phase 2: 架构标准化 (v1.3.0 Current)       Phase 3: 高级扩展 (v1.4.x / v2.0)
+--------------------------------+   +---------------------------------------+   +--------------------------------+
| 技能托管与事件感知             |   | 100% 全量多语言 i18n 覆盖             |   | 记忆熵减 Hot/Warm/Cold 引擎    |
| 真实遥测数据链                 | ➔ | Parser CJK 1.0 Token 准确切片         | ➔ | 在线技能沙盒与 Monaco 编辑器   |
| IDE 与 OpenViking 会话同步     |   | 任务中心 SSOT 工序流转 (外部解析/嵌入)  |   | 分布式算力节点自动负载均衡     |
+--------------------------------+   +---------------------------------------+   +--------------------------------+
```

---

## 📚 3. 开发者与 Agent 规范文档 (Documentation Matrix)

项目所有的核心评估、研发蓝图与规范均收口在 `docs/` 目录中：

| 规范文档 | 内容说明 | 路径 |
|:---|:---|:---|
| **🤖 开局导航** | 接手项目的 Agent 第一眼必读入口与四大绝对红线 | [`.agents/AGENTS.md`](.agents/AGENTS.md) |
| **📜 哲学原则** | 第一性原理、奥卡姆剃刀、信达雅、NO GREEN EVER、字号 $\ge 11\text{px}$ | [`docs/PHILOSOPHY.md`](.agents/docs/PHILOSOPHY.md) |
| **🎨 视觉规范** | 极客暗黑风、`mt-auto` 底边物理平齐、50/50 独立卡片 | [`docs/UI_DESIGN_SPEC.md`](.agents/docs/UI_DESIGN_SPEC.md) |
| **🗺️ 研发大蓝图** | 课题一(信息熵治理)、课题二(分布式算力)、课题三(多模态)、课题四(双级缓存) | [`docs/ARCHITECTURE_BLUEPRINT.md`](.agents/docs/ARCHITECTURE_BLUEPRINT.md) |
| **📋 任务卡片看板** | 唯一真相源 Task Cards、Git Tag 物理锚定、更新履历 | [`REFACTORING_PLAN.md`](REFACTORING_PLAN.md) |

---

## ⚡ 4. 快速开始 (Quick Start)

### 1. 启动 OpenViking 核心服务
```bash
openviking-server --config ~/.openviking/ov.conf --host 0.0.0.0 --port 1933
```

### 2. 启动 OpenViking Studio
```bash
pnpm install
pnpm run dev
```
打开 `http://localhost:5173` （或正式部署地址 `https://vk.tide.red`）体验最新 `v1.3.0` 工作台。

---

## 📄 许可证

Apache-2.0 License
