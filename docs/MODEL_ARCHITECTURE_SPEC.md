# 🏛️ OpenViking 向量、模型与上下文工程架构白皮书 (SSOT)

> **物理真相源声明 (Single Source of Truth)**  
> 本文档是全系统关于 **OpenViking 向量模型、重排模型、推理上下文 (`n_ctx`)、向量维度 (`dimension`)、分块切片阈值 (`chunk_tokens`) 及服务自愈治理** 的唯一物理基线规范。  
> 任何后续架构审计、代码重构、配置修改必须严格对齐本文档，严禁多头散落记录。

---

## 📊 一、 模型服务矩阵与拓扑全景 (Model Matrix & Topology)

```text
                               ┌──────────────────────────────────────────────┐
                               │           OpenViking Server (:1933)          │
                               │          (VikingFS + VikingDB 向量中枢)       │
                               └───────┬──────────────────────────────┬───────┘
                                       │                              │
                    1. 写入/重索引 (切片 <= 1500t)                 2. 检索精排 (Query + Chunk)
                                       │                              │
                                       ▼                              ▼
                 ┌───────────────────────────┐  ┌───────────────────────────┐
                 │  llama-server (EMB :11432) │  │  llama-server (RER :11433) │
                 │  Qwen3-Embedding-8B-Q8_0   │  │  qwen3-reranker-0.6b-q8_0 │
                 │  • n_ctx = 4096 (per slot)│  │  • n_ctx = 4096 (per slot)│
                 │  • Total Context = 16384  │  │  • Total Context = 16384  │
                 │  • Parallel Slots = 4     │  │  • Parallel Slots = 4     │
                 │  • Vector Dim = 4096      │  │  • FlashAttention ON      │
                 └───────────────────────────┘  └───────────────────────────┘
                                       ▲                              ▲
                                       └──────────────┬───────────────┘
                                                      │
                                   ┌──────────────────┴──────────────────┐
                                   │  硬件宿主: RTX 2080 Ti (22GB VRAM)   │
                                   │  显存占用: ~10.5GB (充裕空余 11.5GB) │
                                   └─────────────────────────────────────┘
```

### 1.1 在线模型参数明细表

| 角色 | 部署端口 | 选用模型 | 量化格式 | 向量维度 (`dimension`) | 单路上下文 (`n_ctx`) | 并发通道数 | 硬件显存开销 |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **Dense Embedding** | `:11432` | `Qwen3-Embedding-8B` | `Q8_0` | **4096** | **4096 Tokens** | 4 Slots | ~8.5GB 权重 + 1.2GB KV |
| **Reranker** | `:11433` | `qwen3-reranker-0.6b` | `Q8_0` | N/A (评分输出) | **4096 Tokens** | 4 Slots | ~0.8GB 权重 + 0.6GB KV |
| **VLM / Agent LLM** | `:8317` | `command-r-plus` / Gateway | API / 上游 | N/A | 32K~128K | 8 | 外部/网关代理 |

---

## 🔍 二、 三大核心参数解耦与第一性原理推演

全系统必须严格区分以下 3 个完全解耦的概念：

```text
 ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
 │ 1. dimension: 4096    ➔ 几何特征空间维度 (模型结构固定，输出 4096 个 float 浮点数坐标)           │
 │ 2. n_ctx: 4096        ➔ 模型推理吞吐上限 (llama-server 硬件窗口，单次最多吃进 4096 Tokens)       │
 │ 3. chunk_tokens: 1500 ➔ 向量网关切片阈值 (入库前自动拆解粒度，留出 2500+ Tokens 缓冲，信噪比最高)│
 └─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 为什么向量维度固定为 4096？
- **数学本质**：由 `Qwen3-Embedding-8B` 神经网络的输出层权重结构物理决定，模型输出一个长度为 4096 的向量数组存入 VikingDB。
- **与输入长度完全无关**：无论输入 1 个字还是 1500 个字，生成的向量长度永远是 4096。

### 2.2 为什么推理底座统一放开至 4096？(`-c 16384 --parallel 4`)
- **硬件充裕支撑**：RTX 2080Ti 拥有 22GB 物理显存，两台服务合计仅占用 10.5GB，显存处于绝对安全区；
- **消除 400 溢出硬红线**：历史曾因部分长段落（2068 Tokens）在旧 2048 窗口下发生 `exceed_context_size_error` 报错。提升至 4096 后，底层具备了极强的容错弹性。

### 2.3 为什么切片阈值锁定为 1500 Tokens（搭配 150 Tokens Overlap）？
1. **语义完整性 (Semantic Integrity)**：
   - 1500 Tokens 恰好能完整包含一个完整的二级 Markdown 章节、代码逻辑块或复杂对比表格，杜绝粗暴碎切；
2. **向量信噪比峰值 (Optimal Signal-to-Noise Ratio)**：
   - 信息论与 RAG 实践证明：稠密向量在超过 2000 Tokens 时，多主题会发生互相冲淡稀释（Information Dilution）；1000~1500 Tokens 是几何距离区分度最高、检索召回率最好的黄金区间；
3. **下游 Rerank 完美协同**：
   - Rerank 阶段需要组装 `[Query (200t)] + [Chunk (1500t)] = 1700 Tokens`，在 4096 的 Rerank 窗口下处理速度极快（~80ms），无需任何截断。

---

## 🛠️ 三、 守护治理、看门狗与自愈架构 (Ops & Self-Healing SSOT)

所有模型服务治理 100% 收口于 Windows 宿主机 [`C:\llama-server\`](file:///mnt/c/llama-server/)：

### 3.1 核心脚本清单与分工

| 脚本文件 | 路径 | 核心职责 |
| :--- | :--- | :--- |
| **`start_emb.bat`** | `C:\llama-server\start_emb.bat` | Embedding 启动参数真相源（4096 n_ctx, 16384 ctx, 4 parallel, FlashAttn） |
| **`start_rer.bat`** | `C:\llama-server\start_rer.bat` | Reranker 启动参数真相源（4096 n_ctx, 16384 ctx, 4 parallel, FlashAttn） |
| **`service_manager.ps1`** | `C:\llama-server\service_manager.ps1` | **统一服务总控**：严格幂等探活防野生重复拉起、端口占用清理、静默后台拉起 |
| **`setup_tasks.ps1`** | `C:\llama-server\setup_tasks.ps1` | Windows 任务计划注册器（开机自启、每日重启、看门狗） |
| **`watchdog.bat`** | `C:\llama-server\watchdog.bat` | 5 分钟周期静默探活与故障自愈入口 |

### 3.2 任务计划守护矩阵 (Windows Task Scheduler)

| 任务名称 | 触发时机 | 动作指令 | 目标与效果 |
| :--- | :--- | :--- | :--- |
| `llama-emb-startup` | 系统开机启动 | `service_manager.ps1 -Action start-emb` | 100% 隐藏黑窗开机自启 |
| `llama-rer-startup` | 系统开机启动 | `service_manager.ps1 -Action start-rer` | 100% 隐藏黑窗开机自启 |
| `llama-daily-restart` | 每日 `06:00` | `service_manager.ps1 -Action restart-all` | 定时清理释放显存碎片 |
| `llama-watchdog` | 每 `5 分钟` 循环 | `service_manager.ps1 -Action watchdog` | 探活自愈，进程崩溃 5 分钟内自动恢复 |

---

## 📜 四、 历史决策履历 (Architecture Decision Records - ADR)

- **2026-08-18 (v1.3.5)**:
  1. **死循环熔断修复**：切除 Fallback 向量写入后的穿透 `re-enqueue` 分支，根除单任务重试 15526 次导致的 GPU 98% 满载故障；
  2. **向量网关透明分块**：实现 `split_embedding_chunks`（1500 Tokens 窗口 + 150 Tokens 重叠），在向量层自动拆分为多 Chunk 批量入库，保持文件系统 URI 唯一性；
  3. **模型底座参数统一**：将 `llama-server` 的 `-c` 从 8192 上调至 16384（每个 Slot 上下文达到 4096 Tokens），实现全链路 0 溢出。
