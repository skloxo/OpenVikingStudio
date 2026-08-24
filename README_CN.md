# ⚔️ OpenViking (v1.4.0)

<div align="center">

**面向多 Agent 系统的下一代上下文数据库、体外大脑 (Exocortex) 与全景智能工作台**

[![Version](https://img.shields.io/badge/version-1.4.0-00E5FF.svg?style=flat-square)](https://github.com/skloxo/OpenVikingStudio)
[![Tests](https://img.shields.io/badge/tests-2173%20passed%20%7C%20100%25-00E5FF.svg?style=flat-square)](https://github.com/skloxo/OpenVikingStudio)
[![Frontend](https://img.shields.io/badge/web--studio-React%2019%20%2B%20Vite-00E5FF.svg?style=flat-square)](https://github.com/skloxo/OpenVikingStudio)
[![Backend](https://img.shields.io/badge/backend-FastAPI%20%2B%20FastMCP-00E5FF.svg?style=flat-square)](https://github.com/skloxo/OpenVikingStudio)
[![Native](https://img.shields.io/badge/native-Rust%20AGFS%20%2B%20VikingDB-00E5FF.svg?style=flat-square)](https://github.com/skloxo/OpenVikingStudio)
[![License](https://img.shields.io/badge/license-Apache--2.0-muted.svg?style=flat-square)](LICENSE)

[English](./README.md) | [中文说明](./README_CN.md) | [架构大蓝图](./.agents/BLUEPRINT.md) | [研发规范 SSOT](./.agents/AGENTS.md) | [任务总看板](./REFACTORING_PLAN.md)

</div>

---

## 🌟 什么是 OpenViking？

**OpenViking (VK)** 是专为大模型与多 Agent 协作系统打造的 **Agent-Native 层次化上下文数据库与全天候体外大脑 (Exocortex Context Database)**。

它打破传统单会话与无状态模型的局限，为 Agent 提供：
- 🧠 **跨会话持久化体外大脑 (`viking://`)**：统一归集长期记忆、偏好、经验与踩坑教训；
- ⚡ **L0 / L1 / L2 层次化语义检索**：从毫秒级 Abstract 拦截、Overview SOP 引导到精准 Detail 切片分级召回；
- 🧩 **全域工程技能资产管理**：配置驱动自动发现与索引 748+ 实体技能；
- 🖥️ **全景可视化 Web Studio**：提供沉浸式实验场、切片级任务调度中心、全系统深层遥测大屏；
- 🚀 **分布式私有化双脑算力 (Dual-Brain Gateway)**：深度整合 Mac Studio (M3 Ultra 256GB MLX) 与本地 GPU 算力集群。

---

## 🚀 v1.4.0 重大里程碑核心演进 (Major Highlights in v1.4.0)

`v1.4.0` 是 OpenViking 演进史上的里程碑版本，完成了**全栈单仓库物理归一**、**上游 14 大核心特性深度同步**、**2,173 项测试 100% 全绿** 以及 **全景 Web Studio 沉浸工作台** 的全面交付：

### 1. 🏗️ 全栈工程 Monorepo 物理收口归一
- 彻底终结前后端双仓库切换的摩擦，将 Python 后端引擎 (`openviking`, `openviking_cli`)、Rust Native 内核 (`ragfs`, `vikingdb`)、React 19 Vite Web Studio (`src/`)、多语言 SDK (`sdk/python`, `sdk/typescript`, `sdk/go`) 与 Agent 插件矩阵 (`examples/`, `agent-plugins/`) 完整融合收口在统一单仓库中，协同开发一键编译。

### 2. ⚡ 14 大上游核心特性全量同步与 100% 测试全绿
- **多模态与 VLM 网关**：PDF MinerU 官方解析、CJK 中文字符 Token 预算硬核保护、OpenAI/Gemini/VLM 向量维度自适应；
- **QueueFS 流式调度与并发 Reindex**：语义流式任务队列、延迟内容实体化、过期任务有界自动清扫；
- **Session 自动提交 V2 与 Memory V3 提取**：非阻塞异步记忆归档、JSONL 纯物理换行切分、多块补丁无损合并；
- **2,173 项测试 100% 绿灯回归**：`tests/unit`, `tests/parse`, `tests/agfs` 全量 2,173 项用例 0 失败通过。

### 3. 🖥️ 全景 Web Studio 沉浸式工作台 (1933/1936 双轨架构)
- **智能实验场 (`/playground`)**：整合资源库与实验场，提供 Context Explorer 目录树、L0/L1/L2 分级预览、全屏聚焦画布模式 (Focus Canvas Mode) 与 Git 版本时间线对比；
- **任务中心真实吞吐度量 (`/tasks`)**：50/50 独立双卡设计，实时呈现 QueueFS 切片级真实吞吐量（$X/Y$ 防虚标物理流转），彻底根除静态假死；
- **多轮会话管理器 (`/sessions`)**：回溯 1,000+ 跨会话历史上下文，结构化呈现对话流气泡与记忆卡片；
- **技能控制中心 (`/skills`)**：配置化驱动扫描 748+ 实体技能，支持 TOC 结构化目录索引与源码高亮抽屉。

### 4. 🧠 Mac Studio (M3 Ultra 256G) 本地原生算力挂载与 Dual-Brain 网关
- **双模型全精度物理常驻**：奥尼 35B (Ornith-1.5-35B-A3B) 50+ Tok/s 承载代码与数学推理 + 千问 27B-VL 承载视觉 OCR；
- **四重无损智能网关 (`gateway.py` 端口 13389)**：Metal 预编译预热、思维链 `<think>` 与 Tool Calling 格式解耦、多模态自动分流。

### 5. 🎨 极客性冷淡视觉规范 (NO GREEN EVER SSOT)
- 全系统 100% 封杀绿色（正向冰青 `cyan-500`、负向玫瑰红 `rose-500`、基线中性灰 `muted`）；
- 字号严格遵守 $\ge 11\text{px}$ 物理硬下限，并排卡片通过 `mt-auto` 达成像素级物理平齐。

---

## 🏛️ 系统全景架构拓扑 (Architecture Topology)

```mermaid
graph TD
    subgraph Client [客户端与接入层]
        Web["🖥️ Web Studio (1936/1933)"]
        CLI["⌨️ Rust CLI (ov)"]
        SDK["📦 Multi-Lang SDKs (Go / TS / Python)"]
        IDE["🤖 IDE Agent (Claude Code / OpenClaw / Hermes)"]
    end

    subgraph Server [OpenViking 核心服务 (Port 1933)]
        API["FastAPI 统一 REST 网关"]
        MCP["FastMCP 跨会话协议端点"]
        Auth["企业级认证 (Trusted / Root Key / OIDC)"]
        TT["TaskTracker 分片并发任务追踪器"]
    end

    subgraph Engine [计算与存储引擎]
        Queue["QueueFS 异步语义调度队列"]
        RagFS["AGFS & Rust Native Core (VikingFS / Pathlock)"]
        VikingDB["VikingDB 向量检索引擎 (HNSW/Flat)"]
        Parser["多模态解析矩阵 (MinerU / Scrapy / VLM)"]
    end

    subgraph Compute [分布式私有化算力节点]
        Mac["🍏 Mac Studio M3 Ultra 256G (MLX Dual-Brain 13100)"]
        LocalGPU["⚡ 本地 RTX 2080Ti (Embedding & Rerank)"]
    end

    Client -->|HTTP / SSE / FastMCP| Server
    Server --> Engine
    Engine --> Compute
```

---

## 🌐 标准服务端口矩阵 (SSOT Service Matrix)

| 端口/节点 | 角色与功能 | 协议与入口 | 常驻管理指令 |
| :--- | :--- | :--- | :--- |
| **`1933`** | OpenViking 核心引擎 (FastAPI / FastMCP / `/studio`) | `http://127.0.0.1:1933` | `systemctl --user restart openviking.service` |
| **`1936`** | OpenVikingStudio Vite 热更开发测试环境 | `http://127.0.0.1:1936` | `systemctl --user restart openviking-studio-dev.service` |
| **`13100`** | Mac Studio M3 Ultra 256G 远程算力节点 | FRP 隧道 (`8.129.0.26`) | `ssh -p 13100 fsk@8.129.0.26` |
| **`8317`** | CPA 集中智能网关 (auto-router) | `http://127.0.0.1:8317/v1` | `cpa status` |

---

## ⚡ 快速上手 (Quick Start)

### 1. 克隆与安装依赖

```bash
git clone https://github.com/skloxo/OpenVikingStudio.git
cd OpenVikingStudio

# 安装 Python 后端可编辑依赖
pip install -e .

# 安装前端依赖
pnpm install
```

### 2. 启动服务

```bash
# 启动后端核心引擎 (Port 1933)
openviking-server --config ~/.openviking/ov.conf --host 0.0.0.0 --port 1933

# 启动前端 Web Studio (Port 1936)
pnpm run dev
```

浏览器打开 `http://127.0.0.1:1936`，即刻进入 OpenViking Studio 全景控制台。

### 3. 运行全套自动化测试

```bash
# 运行后端全量测试套件 (2,173 项用例)
pytest -o addopts="" tests/unit tests/parse tests/agfs

# 执行前端生产打包验证
npm run build
```

---

## 📚 研发规范与工程法则 (SSOT Documents)

| 物理主文档 | 核心内容 | 关联路径 |
| :--- | :--- | :--- |
| 🤖 **`AGENTS.md`** | **唯一研发法则**：开发哲学、性冷淡视觉规范、四大绝对红线 | [`.agents/AGENTS.md`](.agents/AGENTS.md) |
| 🗺️ **`BLUEPRINT.md`** | **唯一研发大蓝图**：信息熵治理、分布式算力、多引擎压缩与基准测试 SOP | [`.agents/BLUEPRINT.md`](.agents/BLUEPRINT.md) |
| 📋 **`REFACTORING_PLAN.md`** | **唯一任务卡片总看板**：所有活跃工单、11 大可视化专项矩阵、版本交付履历 | [`REFACTORING_PLAN.md`](REFACTORING_PLAN.md) |

---

## 📄 许可证 (License)

Apache-2.0 License © 2026 OpenViking Team & Contributors.
