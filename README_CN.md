# ⚔️ OpenViking Studio

<div align="center">

**面向多 Agent 系统的专业级全景座舱、层次化上下文数据库与实时遥测工作台**

[![Version](https://img.shields.io/badge/version-1.5.0-00E5FF.svg?style=flat-square)](https://github.com/skloxo/OpenVikingStudio)
[![Tests](https://img.shields.io/badge/tests-2173%20passed%20%7C%20100%25-00E5FF.svg?style=flat-square)](https://github.com/skloxo/OpenVikingStudio)
[![Frontend](https://img.shields.io/badge/web--studio-React%2019%20%2B%20Vite-00E5FF.svg?style=flat-square)](https://github.com/skloxo/OpenVikingStudio)
[![Backend](https://img.shields.io/badge/backend-FastAPI%20%2B%20FastMCP-00E5FF.svg?style=flat-square)](https://github.com/skloxo/OpenVikingStudio)
[![Native](https://img.shields.io/badge/native-Rust%20AGFS%20%2B%20VikingDB-00E5FF.svg?style=flat-square)](https://github.com/skloxo/OpenVikingStudio)
[![License](https://img.shields.io/badge/license-Apache--2.0-muted.svg?style=flat-square)](LICENSE)

[演进蓝图](#-架构演进大蓝图-strategic-roadmap) | [系统架构](#-系统架构拓扑-architecture-topology) | [核心特性](#-核心特性矩阵) | [极速上手](#-极速上手-quick-start) | [开源说明](#-开源致敬与说明)

</div>

---

## 🌟 什么是 OpenViking Studio？

**OpenViking Studio** 是基于开源 [OpenViking (volcengine/OpenViking)](https://github.com/volcengine/OpenViking) 深度演进打造的**专业级多智能体全景座舱与上下文控制台 (Multi-Agent Context Cockpit & Observability Console)**。

OpenViking 原项目是由**火山引擎 / 字节跳动团队**开源的下一代 Agent-Native 层次化上下文数据库。在此坚实基座之上，**OpenViking Studio** 专注于解决多 Agent 长程交互中的**“状态不可见、上下文易遗忘膨胀、交互黑盒难以追踪、调试排障成本高”**等工程痛点，为开发者和各类智能体提供开箱即用、高密清晰的可视化观测与治理体验：

- 🧠 **跨会话持久化体外大脑 (`viking://`)**：统一收口长程记忆、开发者偏好、工程决策与踩坑教训；
- ⚡ **L0 / L1 / L2 层次化分级检索**：支持毫秒级摘要拦截 (Abstract)、SOP 流程概览 (Overview) 到精准切片 (Detail) 的分层召回；
- 📊 **座舱级实时遥测大盘 (Telemetry Console)**：多维度精确审计 Token 消耗分布（VLM / Embedding / Rerank）、检索成功率以及会话上下文写入热力图；
- 🖥️ **沉浸式实验场与工作台 (`/playground`)**：提供全景资源文件树、分级预览画布、多轮会话回溯与工程技能索引；
- 🔌 **标准 FastMCP 智能体桥梁**：原生无缝对接 Claude Code、Cursor、OpenClaw 等主流 Agent 客户端，实现零成本插拔接入。

---

## 🗺️ 架构演进大蓝图 (Strategic Roadmap)

> OpenViking 坚持第一性原理，持续推进面向多 Agent 复杂长程交互的自我进化与确定性执行生态：

| 阶段里程碑 | 演进方向与核心课题 | 交付状态 |
| :--- | :--- | :--- |
| **Phase 1: 核心基座与座舱全景**<br>*(Foundation & Observability)* | <ul><li>**原生内核对齐**：完整支持 AGFS 虚拟文件系统、VikingDB 与标准 FastMCP 协议</li><li>**沉浸式 Web Studio**：提供 Focus 画布、多轮会话回溯与工程技能索引</li><li>**座舱级遥测大盘**：Token 分类精准审计（Embedding / Rerank / VLM）与上下文热力图</li><li>**全单仓物理收口**：前后端工程与多语言 SDK 物理收口，一键构建运行</li></ul> | `✅ 已落地交付` |
| **Phase 2: 确定性运行时与智能压缩**<br>*(Deterministic Loop & Compression)* | <ul><li>**两层事件循环 (Two-Tier Loop)**：外层生命周期重试保护 + 内层工具链快速收敛与协同打断</li><li>**$\Pi$ 状态快速感知器**：基于 Merkle Tree 结构实现亚毫秒级（$< 2\text{ms}$）上下文哈希差异检测</li><li>**自适应长上下文脱水**：语义无损提纯与渐进压缩矩阵，彻底杜绝长程会话 Token 膨胀</li><li>**客户端弹性防护**：失效 Session 轮询智能熔断与网络抖动退避机制</li></ul> | `⚡ 活跃演进中` |
| **Phase 3: 自主进化飞轮与协作网格**<br>*(Self-Evolving Flywheel & Mesh)* | <ul><li>**踩坑经验自提纯入脑**：Agent 解决复杂难题后自动提纯结晶 SOP 并持久化回填体外大脑</li><li>**多智能体对等协作网格**：跨节点、跨工作区无缝记忆流交换与分布式联合检索</li><li>**企业级零信任上下文网关**：敏感凭据自动化阻断防御与细粒度租户权限隔离</li></ul> | `🔮 战略规划中` |

---

## 🏛️ 系统架构拓扑 (Architecture Topology)

```mermaid
flowchart TD
    subgraph Client ["客户端与 Agent 接入层"]
        Web["🖥️ Web Studio 控制台"]
        CLI["⌨️ OpenViking CLI"]
        SDK["📦 Multi-Lang SDKs (Python / TS / Go)"]
        IDE["🤖 IDE Agents (Claude Code / OpenClaw / Cursor)"]
    end

    subgraph Server ["OpenViking 核心服务 (Port 1933)"]
        API["FastAPI 统一 REST 网关"]
        MCP["FastMCP 标准跨会话端点"]
        Auth["轻量安全鉴权与多租户隔离"]
        TaskEngine["TaskTracker 异步任务追踪器"]
        Studio["内嵌 Web Studio 控制台 (/studio)"]
    end

    subgraph Engine ["存储与检索内核"]
        VikingFS["AGFS & VikingFS 虚拟分级文件系统"]
        VectorDB["VikingDB 语义向量检索引擎"]
        Queue["QueueFS 异步任务调度队列"]
        Observability["Telemetry & Audit 实时遥测审计引擎"]
    end

    subgraph Models ["大模型与推理生态 (正交解耦)"]
        CloudLLM["云端主流大模型 (OpenAI / Claude / DeepSeek 等)"]
        LocalLLM["本地私有化模型 (Ollama / vLLM / 兼容推理服务)"]
    end

    Client -->|"HTTP / SSE / FastMCP"| Server
    Server --> Engine
    Engine -.->|"标准 OpenAI 兼容协议"| Models
```

---

## ✨ 核心特性矩阵

### 1. 🖥️ 全景 Web Studio 沉浸式座舱
- **智能实验场 (`/playground`)**：整合资源库与沙箱，提供上下文目录树、L0/L1/L2 分级实时预览与时间线回溯；
- **任务中心真实吞吐看板 (`/tasks`)**：微观工序与宏观业务双轨展示，以严密的物理完成契约追踪分片并发进度，杜绝静态假死；
- **长程会话追踪器 (`/sessions`)**：支持跨会话历史上下文回溯，结构化呈现消息流、工具调用与提取的记忆切片；
- **技能控制中心 (`/skills`)**：配置化驱动发现与索引全域技能，支持 TOC 结构化索引与源码快速调阅。

### 2. 📊 高密座舱视觉与零虚假数据治理
- **克制性冷淡工业设计**：严格遵循信号语义色彩规范，关键数值采用等宽字体高密对齐，杜绝无意义装饰噪音；
- **100% 物理真实数据驱动**：前后端数据严丝合缝，彻底消除前端伪造数字或硬编码 Mock，接口无数据时优雅降级。

### 3. 🛡️ 稳固解耦的模型与运行时架构
- **计算与存储完全正交**：系统关注上下文数据库、向量检索与记忆持久化，与外部大模型完全解耦；
- **全协议兼容**：无论使用云端主流商业模型，还是本地私有化推理引擎，均可通过标准接口无缝接入，零硬件绑定门槛。

---

## 🌐 统一服务端口矩阵 (SSOT Service Matrix)

系统全面推行奥卡姆剃刀原则，所有能力收口于单一统一服务端口，杜绝多端口维护混乱：

| 端口 | 角色与功能 | 协议与入口 | 常驻推荐管理指令 |
| :--- | :--- | :--- | :--- |
| **`1933`** | **OpenViking 核心服务** (REST API、FastMCP 端点与内嵌 Web Studio 控制台一体化) | `http://127.0.0.1:1933`<br>控制台入口: `http://127.0.0.1:1933/studio` | `systemctl --user restart openviking.service` |

---

## ⚡ 极速上手 (Quick Start)

### 1. 克隆仓库与安装依赖

```bash
git clone https://github.com/skloxo/OpenVikingStudio.git
cd OpenVikingStudio

# 安装 Python 后端核心引擎 (建议在虚拟环境中执行)
pip install -e .

# 安装前端依赖 (可选，仅在需要二次开发前端时使用)
pnpm install
```

### 2. 启动核心服务

```bash
# 启动 OpenViking 核心引擎 (统一监听 1933 端口)
openviking-server --config ~/.openviking/ov.conf --host 0.0.0.0 --port 1933
```

启动完成后，直接在浏览器中打开 **`http://127.0.0.1:1933/studio`**，即刻进入 OpenViking Studio 全景控制台。

### 3. 运行质量保障测试

```bash
# 运行后端全量单元与检索测试 (2,170+ 项用例)
pytest tests/unit tests/parse tests/agfs

# 前端生产打包校验
npm run build
```

---

## 🤝 开源致敬与说明

- **内核致敬**：感谢火山引擎开源的 [OpenViking](https://github.com/volcengine/OpenViking) 核心体系，为大模型 Agent 上下文管理树立了优秀的规范与基础。
- **定位原则**：本项目作为社区深度演进的控制台与工作台版本，坚持与上游协议 100% 兼容，代码高内聚、依赖极简、向光演进。

---

## 📄 许可证 (License)

本项目基于 [Apache-2.0 License](LICENSE) 协议开源。
