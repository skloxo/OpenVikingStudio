# OpenViking Studio — 历史交付全量归档台账 (DELIVERY_ARCHIVE.md)

> **唯一归档真相源**：本文档为 OpenViking Studio 已验收通过的历史版本、Task Cards 与 Git Tag 履历全量归档。  
> 活跃主计划 [`REFACTORING_PLAN.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/REFACTORING_PLAN.md) 仅保留当前活跃可执行的原子工单与就绪待调度的任务矩阵。

---

## 🏆 Milestone 1 (v1.3.0 ~ v1.4.3) 全量交付总览

| 版本 Tag | 交付日期 | Git Commit | 核心交付特性与工单 | 单元测试状态 |
|:---|:---|:---|:---|:---:|
| **`v1.4.6`** | 2026-08-30 | `ec2b039` | `TASK-MAC-AUTOHEAL-03`：Mac Studio (M3 Ultra) 无头双网卡分流、8大LaunchDaemons守护矩阵与黑屏秒级唤醒 | 100% PASS |
| **`v1.4.5`** | 2026-08-28 | `1d3c94a` | `TASK-VL-OPTI-02`：RTX 2080Ti 显存防溢出锁定 (<20.0GB)、Dual-Gate 32 门禁与 MCP 桥梁自愈 | 100% PASS |
| **`v1.4.4`** | 2026-08-26 | `76f940d4` | `TASK-VL-DEPLOY-01`：2080Ti (22GB) 本地 Qwen3-VL 双模型拉起与 INT8 显存治理 | 100% PASS |
| **`v1.4.3`** | 2026-08-24 | `321657d2` | 任务中心支持单个删除与批量清理失败任务 (`clear-failed`)，彻底自愈孤儿失败任务 | 100% PASS |
| **`v1.4.2`** | 2026-08-24 | `aac7b640` | TaskTracker 任务保留期延长至 30 天，切换为每日午夜静默清扫调度 | 100% PASS |
| **`v1.4.1`** | 2026-08-24 | `d5a55521` | 修复 RAGFS Pathlock 内存绑定匹配异常，清理残留孤儿任务 | 100% PASS |
| **`v1.4.0`** | 2026-08-22 | `69857d42` | **🎉 Major Release**：上游 131 Commits 全量同步与 14 大 Task Cards 验收，2173 单测全绿 | 2173/2173 PASS |
| **`v1.3.55`** | 2026-08-21 | `3276cd83` | `TASK-UPSTREAM-SYNC-ALL-01`：LangChain 官方集成、多模态 VLM 流式流转、MCP 协议工作区 | 2173/2173 PASS |
| **`v1.3.54`** | 2026-08-20 | `4e24ef51` | `TASK-QUEUEFS-STREAMING-REINDEX-01`：QueueFS 语义流式调度与并发 Reindex 管理器 | 100% PASS |
| **`v1.3.52`** | 2026-08-19 | `0c0db7af` | `TASK-UPSTREAM-MEMORY-V3-01`：Memory V3 提取引擎与 Session 异步非阻塞归档 | 131/131 PASS |
| **`v1.3.50`** | 2026-08-18 | `38e28b11` | Task Card 10：Viking URI 规范化、`viking://~` 用户家目录与 739 项物理技能动态入库 | 69/69 PASS |
| **`v1.3.49`** | 2026-08-18 | `e0cd472f` | Task Card 9：VikingFS 存储与 Pathlock 租约保活、资源移动无锁化 | 100% PASS |
| **`v1.3.13`** | 2026-08-17 | `cfd40888` | Task Card 8：Markdown 文档解析后不拆分 (`no_split`) 模式与 CJK Token 预算硬核保护 | 44/44 PASS |
| **`v1.3.12`** | 2026-08-16 | - | Task Card 7：Storage & VikingFS 容错、`mkdir` 错误透传与 `mv` 突破 1000 节点 | 67/67 PASS |
| **`v1.3.11`** | 2026-08-15 | - | Task Card 6：企业级认证 (OIDC / LDAP) 身份插件与 Watch 任务安全 ACL | 37/37 PASS |
| **`v1.3.10`** | 2026-08-14 | - | Task Card 5：服务端上下文统一召回、分层预算裁剪 (`context_assembler`) | 320/320 PASS |
| **`v1.3.9`** | 2026-08-13 | - | Task Card 4：Session 自动提交 V2 与断点恢复机制 | 301/301 PASS |
| **`v1.3.8`** | 2026-08-12 | - | Task Card 3：QueueFS 支持 Redis 单机/集群/哨兵模式与启动过期任务清扫 | 203/203 PASS |
| **`v1.3.6`** | 2026-08-11 | `6823b728` | Task Card 2：Agent 演进与经验血缘追踪引擎 (`experience_lineage.py`) | 22/22 PASS |
| **`v1.3.5`** | 2026-08-10 | `8fde13a` | `TASK-MONO-01` & `TASK-EMBED-CHUNK-01`：单仓库归一与 1500 Tokens Chunk 切片 | 100% PASS |
| **`v1.3.4`** | 2026-08-09 | `1ca76e53` | Task Card 1：TaskTracker 细粒度分片并发锁池 (`KeyedAsyncLockPool`) 与终态 Guard | 113/113 PASS |
| **`v1.3.3`** | 2026-08-08 | `4d14832` | 技能发现引擎扫描 10 大源目录汇聚 682 项技能，1936/1933 双轨常驻 | 100% PASS |
| **`v1.3.0~2`**| 2026-08-06 | - | 双语 i18n 体系 100% 覆盖、Parser CJK Token 准确估算、任务自愈重新入队 | 100% PASS |

---

## 📌 Milestone 1 关键版本详细交付履历

### [x] v1.4.3：任务中心失败任务清理与删除动作 (2026-08-24)
- **Git Commit**：`321657d2` ｜ **Git Tag**：`v1.4.3`
- **交付内容**：
  1. 后端 `TaskTracker` 新增 `DELETE /api/v1/tasks/{task_id}` 与 `POST /api/v1/tasks/clear-failed` 路由；
  2. 前端任务中心集成单任务删除与一键清理所有失败/孤儿任务按钮；
  3. 彻底自愈历史遗留的 `FAILED` 与取消中死锁任务。

### [x] v1.4.0 正式封板 Major Release：上游 131 Commits 全量同步 (2026-08-22)
- **Git Commit**：`69857d42` ｜ **Git Tag**：`v1.4.0`
- **交付内容**：
  1. 完成上游全部 14 张 Task Cards 物理合并与冲突消解；
  2. 全自动化测试 `pytest -o addopts="" tests/unit tests/parse tests/agfs` **2,173 passed, 0 failed (100% 全绿通过)**；
  3. 前端 Vite 18.72s 编译完成，生产 1933 与开发 1936 环境物理双轨上线。

### [x] v1.3.55：上游全量特性同步与 LangChain/多模态/MCP 对齐 (2026-08-21)
- **Git Commit**：`3276cd83` ｜ **Git Tag**：`v1.3.55`
- **交付内容**：
  1. 同步 `integrations/langchain` 官方适配与 `uv.lock`；
  2. 多模态 `text_encoding.py` 解决中日文消解，`openai_vlm.py` 恢复流式响应与 Token 统计；
  3. `RAGFSBindingClient` 动态 Pathlock 内存回退机制，支持 `LockAcquisitionError` 瞬态争用抛出。

### [x] v1.3.54：QueueFS 流式调度与并发 Reindex (2026-08-20)
- **Git Commit**：`4e24ef51` ｜ **Git Tag**：`v1.3.54`
- **交付内容**：
  1. Reindex 权限鉴权与 `search_tags` 标签批量 Upsert 物理保护；
  2. QueueFS 异步容错与 Semantic DAG 提示词概览流水线；
  3. 针对性测试 `tests/server/test_admin_rebuild_api.py` (58/58) 与 `test_admin_api.py` (38/38) 100% 通过。

### [x] v1.3.5：前后端 Monorepo 物理收口与向量网关 Chunk 语义切片 (2026-08-10)
- **Git Commit**：`8fde13a` ｜ **Git Tag**：`v1.3.5`
- **交付内容**：
  1. 将 Python 后端与前端 Web UI 物理收口至 `OpenVikingStudio` 单仓库，实现前后端协同版本管控；
  2. 向量网关层实现 1500 Tokens 黄金切片与多 Chunk 批量入库，根治长文本 400 报错与死循环重试；
  3. 彻底消除 GPU 穿透死循环，功耗降回 42W。

---

## 📌 历史早期版本归档 (v1.1.x ~ v1.2.x)

### [x] v1.2.34：技能中心全托管感应引擎 + Harness 真实数据打通 (2026-08-04)
- **Git Commit**：`cefba2b` ｜ **Git Tag**：`v1.2.34`
- **交付内容**：Linux `inotify` OS 级全量感知，`~/.openviking/harness_metrics.json` 真实持久化打通，SKILL.md 写入真实 Reflexion Lesson。

### [x] v1.2.0 正式封板 Major Release：前后端一体化中枢 (2026-08-01)
- **Git Tag**：`v1.2.0`
- **交付内容**：6 大高密度 KPI 观察阵列 (3×2 矩阵)，全盘 0 Mock 强约束，Harness 技能后台自动标准化与 1933 向量上架。
