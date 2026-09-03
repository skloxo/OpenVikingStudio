# 🗺️ OpenViking 项目主线重构与原子化任务卡片总看板 (Master Task Cards Kanban - SSOT)

> **关联主蓝图与白皮书**：[BLUEPRINT.md (研发大蓝图与白皮书)](file:///home/skloxo/aho/openclaw/project/.agents/BLUEPRINT.md) ｜ [DELIVERY_ARCHIVE.md (交付履历库)](file:///home/skloxo/aho/openclaw/project/DELIVERY_ARCHIVE.md)  
> **唯一真相源 (SSOT)**：所有主线任务卡片、包含此前规划的所有活跃工单与远期 Epic，均在此统筹物理收口，严禁遗漏散落。

---

## 🛠️ TideTrading 架构第一性原理重构看板 (TideTrading Refactoring Roadmap)

| 任务卡片 ID | 模块与重构目标 | 物理重构方案 (第一性原理) | 当前状态 |
| :--- | :--- | :--- | :---: |
| **Card-TT-01** | **`initialize_history_data.py` 纯程序化计算改造** | 彻底切除用大模型扫描 1 年历史数据的滥用工程，重构为 100% 纯 Python (Pandas/NumPy/SQL) 历史行情指标与因子算法计算。 | ⏳ 待实施 (已断模型) |
| **Card-TT-02** | **Crontab 盘中监控与选股程序化优先** | 遵守“能用程序实现 100% 用程序，只在最终文本输出时按需使用 LLM”。重构 `intraday_monitor.py` 与 `daily_screening_v5.py`。 | ⏳ 待实施 (已断模型) |
| **Card-TT-03** | **Paperclip (回形针) 彻底卸载与进程清理** | 已从 PM2 中物理 `delete` 终止 `paperclip` 进程，清空内存占用。 | [x] 已完成 ✅ |

---

## 🗺️ 一、 上游 OpenViking 全景原子化合并与深度代码治理专区 (176 Commits Roadmap - 先合并后开发)

> **核心原则**：全系统严格遵循“**先合并上游，后开发新功能**”与“**彻底切除代码堆叠与掩盖式补丁**”铁律。
> **代码治理四大哲学**：(1) 能用公用方法组件的 100% 用公用组件；(2) 有成熟现成轮子的 100% 用现成轮子；(3) 能复用必复用，不能复用找轮子适配；(4) 极致简洁，直击物理根因，严禁写新方法掩盖旧隐患。

| 任务工单 ID | 模块与合并主题 | 涵盖上游核心特性与 Commits / 治理范围 | 物理验收与测试条件 | 计划 Tag 版本 | 当前状态 |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **Task-Clean-00** | **全盘源码深度审查、死代码清理与公用轮子统一收口** | 清理历史遗留废弃文件/Mock/幽灵客户端，消除多层嵌套 Wrapper，将零散方法收敛至统一 Shared 工具库与官方轮子，根治发包失效与深坑隐患 | 全局单测 100% PASS，零冗余胶水脚本，构建打包耗时缩短，代码极简自解释 | 贯穿全生命周期 | 🚀 执行中 |
| **Merge-Card-01** | **存储底座、CacheRuntime 与锁自愈** | DynamicProvider C ABI (`e7f58639`)、Redis CacheRuntime (`3123e8d8`)、阿里云 OSS (`63c25306`)、PathLock 恢复 (`9262df7a`)、分桶上传 (`550ef796`) | `pytest tests/storage/` PASS，Redis 缓存与小时分桶上传测试正常 | `v1.4.7` | [x] 已验收通过 ✅ |
| **Merge-Card-02** | **记忆提纯、会话解耦与 URI 规范** | 记忆度量 (`b1780a4d`)、Event Page 复用 (`6248d4e4`)、Token 移出事件循环 (`ed4bb192`)、图片脱敏 (`78962c32`)、Windows URI (`76ab53ac`)、Session 结束 Hook (`7200cdb1`) | `pytest tests/session/` PASS，主事件循环零卡顿，图片字节彻底脱敏 | `v1.4.8` | [x] 已验收通过 ✅ |
| **Merge-Card-03** | **AnyDoc 0.2 文档解析与语义检索升级** | AnyDoc 0.2 统一文档模型 (`7ee75611`, `1c954ea9`)、稀疏嵌入降级 (`41044af7`)、Reranker `top_n` (`687167f1`)、概览摘要缓存复用 (`42c0ee13`) | `pytest tests/parse/` & `pytest tests/retrieve/` PASS，Office 解析无异常 | `v1.4.9` | [x] 已验收通过 ✅ |
| **Merge-Card-04** | **企业级权限系统与资源 ACL** | 资源 ACL 与用户组授权 (`e357af6a`)、向量检索权限过滤、账号级授权开关 (`170e17c1`)、禁用认证锁 (`66dc4c6a`) | `pytest tests/auth/` PASS，向量多租户权限隔离验证成功 | `v1.4.10` | ⏳ 待开始 |
| **Merge-Card-05** | **双模态 MCP 架构重构与 Monorepo 物理收口** | 1. **核心 MCP (Core)**：本地主 Agent 全量 30+ 接口（全量记忆读写、VikingFS 控制、技能治理、图谱、服务端快照）；<br>2. **卫星 MCP (Satellite)**：3070 / Mac 等远程节点精简安全模式（远程知识召回、经验上报、抖动自愈，隔离底层危险指令）；<br>3. `mcp-openviking/` 物理纳入 Monorepo 随 Git 统一版本化迭代；<br>4. 合并 MCP 原生多模态内容块 (`0e77cd4e`) 与 OpenClaw 2026.8.1 契约 (`2c88269d`)。 | `pytest tests/server/test_mcp_endpoint.py` PASS，本地 Core 与远程 Satellite 双模自适应拉起 | `v1.4.11` | ⏳ 待开始 |
| **Merge-Card-06** | **CLI 命名 Zip 下载与多语言 SDK 对齐** | `ov get` 目录 ZIP 下载 (`crates/ov_cli`)、CLI 终端明暗自适应主题 (`33210990`)、Go/TS SDK 批量写入对齐 (`36931716`) | `cargo test -p ov_cli` PASS，Go/TS/Python SDK 单元测试全绿 | `v1.4.12` | ⏳ 待开始 |
| **Merge-Card-07** | **Web Studio 前端能力合并与视觉对齐** | 搜索模式切换与 JSONL 渲染 (`303e1172`)、L0/L1 Sidecar 元数据 (`30ef75ce`)、受信任用户切换 (`460f57c1`)、上下文树键盘导航 (`4738df66`) | 前端 `pnpm build` PASS，严格符合 **NO GREEN EVER**、双主题与 $\ge 11\text{px}$ 规范 | `v1.4.13` | ⏳ 待开始 |

---

## ⚡ 二、 当前活跃与待调度 Studio 原子工单 (Scheduled Active Task Cards)

### 📌 P0: [x] Merge-Card-01 (v1.4.7): 存储底座、统一 CacheRuntime、阿里云 OSS 与 PathLock 空锁自愈 ✅
- **类型**：Core Storage & Infrastructure ｜ **优先级**：🔴 P0（底层存储与缓存中枢）
- **Git Commit**：`7c1222c4` ｜ **Git Tag**：`v1.4.7`
- **交付内容**：
  1. `crates/ragfs/src/cache_runtime/`：统一 CacheRuntime 与 Redis 后端 CacheFS/QueueFS，解耦底层存储；
  2. `crates/ragfs/src/cache_runtime/dynamic/`：实现 DynamicProvider C ABI 动态加载与版本化扩展 (`openviking_cache_provider_v1.h`)；
  3. `crates/ragfs/src/plugins/s3fs/client.rs`：新增阿里云 OSS 原生适配与 AGFS 签名配置；
  4. `crates/ragfs/src/lock/provider.rs`：PathLock 过期空锁 Token 自动回收与抢锁自愈；
  5. `openviking/server/temp_upload_store.py`：UTC 小时分桶 (`YYYYMMDDHH`) 隔离上传与后台非阻塞异步防爆盘清扫；
  6. 验证：存储与配置单测 101/101 100% PASS，Vite 生产构建 31.84s 成功。
- **验收结果**：已验收通过 ✅

---

### 📌 P0: [x] Merge-Card-02 (v1.4.8): 记忆提纯、会话解耦、Token移出事件循环与图片脱敏 ✅
- **类型**：Core Session & Memory Architecture ｜ **优先级**：🔴 P0（会话吞吐量与记忆安全）
- **Git Commit**：`f8606692` ｜ **Git Tag**：`v1.4.8`
- **交付内容**：
  1. `openviking/session/session.py` & `openviking/utils/token_estimation.py`：Token 估算完全移出主事件循环（`asyncio.to_thread` 异步化），Quarter-unit 极速整数算法，彻底消灭长文本/高并发下 1933 FastAPI 事件循环假死毛刺；
  2. `openviking/session/session.py` & `test_wm_v2_guards.py`：内联 Base64 多模态图片字节提取脱敏，彻底杜绝兆级 raw base64 污染提纯上下文与日志；
  3. `openviking/session/memory/utils/uri.py`：Windows 反斜杠与盘符脏路径安全规范化与跨平台自愈；
  4. `openviking/session/memory/extract_loop.py` & `page_id_map.py`：Event Page 内存缓冲复用机制，消解 GC 抖动；
  5. `openviking/metrics/collectors/telemetry_bridge.py`：记忆提取度量指标跟踪（created/merged/deleted/skipped/failed）；
  6. `examples/codex-memory-plugin/`：升级 0.8.1 版本，支持 SessionEnd hook 自动提交与原子锁防竞争；
  7. `openviking/pyagfs/async_client.py`：修复 AGFS Client `auto_pathlock` 签名缺陷与默认锁自愈；
  8. `src/routes/skills/route.tsx`：优化 L2 全量源码查看器，去除 `max-h-[520px]` 嵌套滚动，源码全高度展开一滚到底；技能卡片徽章自解释为 `SOP 规约 (标准件)`，彻底消解与抽屉文件数的歧义；
  9. 验证：149/149 会话核心单测 + 40/40 长程并发锁测试 100% PASS，Vite 编译 18.68s 成功。
- **验收结果**：主人人肉测试验收通过 ✅

---

### 📌 P0: [x] Merge-Card-03 (v1.4.9): AnyDoc 0.2 文档解析、Rerank 自愈、真实 GPU 探针与依赖地毯式排查 ✅
- **类型**：Core Parser, Semantic Retrieval & Hardware Reliability ｜ **优先级**：🔴 P0（解析底座与模型安全）
- **Git Commit**：`6bc31701` ｜ **Git Tag**：`v1.4.9`
- **交付内容**：
  1. `openviking/parse/parsers/anydoc.py`, `anydoc_converter.py`, `anydoc_renderer.py`：统一 Office (Word/Excel/PPT)、EPUB 解析管线，内联媒体图片保留，支持表格 GFM 规范转换，并正式安装补齐 `firecrawl-anydoc>=0.2.4` 轮子；
  2. `openviking/models/rerank/openai_rerank.py`：对齐上游 `top_n` 请求体参数传递，并实施第一性原理自愈机制：若 `api_base` 缺少 `/rerank` 后缀自动补全，消灭 404 静默降级；
  3. `openviking/server/routers/system.py`：新增 `/api/v1/system/gpu` 真实硬件探针，调用 `nvidia-smi` 实时采集 2080Ti VRAM 与利用率，彻底消灭前端每 10 秒轮询产生的虚假 404 报警；
  4. `openviking/models/embedder/`：稀疏嵌入针对复杂多模态视频/二进制的纯文本降级保护；
  5. 提前安装补齐 `python-jose[cryptography]`、`boto3`，对全盘 27 个解析器和 24 个模型模块完成地毯式 import 扫描，零依赖缺失；
  6. 验证：477 项解析与检索单测 100% PASS，Vite 编译 18.37s 成功。
- **验收结果**：主人人肉测试验收通过 ✅

---

### 📌 P0: [x] TASK-VL-DEPLOY-01 (v1.4.4): 2080Ti (22GB) 本地 Qwen3-VL 双模型自主拉起、INT8显存治理与全系统对接闭环 ✅
- **类型**：Core Infrastructure ｜ **优先级**：🔴 P0（知识库与多模态检索中枢）
- **目标**：在 Windows 宿主机 2080Ti (22GB) 上完成 Qwen3-VL-Embedding-8B-W8A16 与 Qwen3-VL-Reranker-2B 双模型拉起，进行算子层与 INT8 显存治理，保留 2.8GB+ 动态空间，打通 11432 统一 REST 服务，完成 OpenViking 与 OpenClaw 全系统对接。
- **验收结果**：已验收通过 ✅ ｜ **服务端口**：`http://127.0.0.1:11432`

---

### 📌 P0: [x] TASK-VL-OPTI-02 (v1.4.5): RTX 2080 Ti 显存防溢出硬顶锁定 (<20.0GB)、双层门禁准入与 MCP 桥梁全栈自愈加固 ✅
- **类型**：Core Infrastructure & Reliability ｜ **优先级**：🔴 P0（系统稳定性与防雪崩中枢）
- **物理根因消解**：根治了 WDDM 驱动在显存 21.8G 触顶时向系统 RAM 分页溢出 31.0GB 导致的 100% CPU 颠簸雪崩。
- **交付清单与核心参数**：
  1. `C:\models\run_emb_service.py`：锁顶 14.625GB (`fraction: 0.65`)，`CUDA_MANAGED_FORCE_DEVICE_ALLOC=1`，Dual-Gate 32 并发门禁，1920×1920 HD 视觉支持，Hot-Standby 深度预热；
  2. `C:\models\run_rer_service.py`：锁顶 5.400GB (`fraction: 0.24`)，Dual-Gate 32 并发门禁，Hot-Standby 深度预热；
  3. `C:\models\daemon_watchdog.py`：单例 11439 互斥锁，5秒探活自愈，开局先杀后拉；
  4. `~/.openviking/ov.conf`：放宽 `overview_max_chars: 8000`，对齐 32K/8K 窗口；
  5. `mcp-openviking/mcp_openviking_server.py`：100% REST-First 动态自愈，清洗 FastMCP `FieldInfo` 序列化崩溃，归一化全格式 Level；
  6. 运维与排障 SSOT 手册：`docs/EMBEDDING_RERANKER_VK_OPERATIONS_MANUAL.md` 及 `viking://resources/master_memory/` 同步。
- **验收结果**：已验收通过 ✅ ｜ **实测指标**：显存严格锁在 12.18GB 峰值，RAM 0 溢出，Embedding 延迟 ~350ms，MCP 6 大接口 100% PASS。

---

### 📌 P0: [x] TASK-MAC-AUTOHEAL-03 (v1.4.6): Mac Studio (M3 Ultra) 无头双网卡智能分流、8大LaunchDaemons守护矩阵与远程黑屏秒级唤醒闭环 ✅
- **类型**：Core Infrastructure & High Availability ｜ **优先级**：🔴 P0（远程算力与无头自愈中枢）
- **物理根因消解**：
  1. 根治了 FRP 客户端在开机网络未就绪时因 `loginFailExit=true` 单次超时直接自杀退出的问题；
  2. 根治了插内网网线抢占 `0.0.0.0/0` 默认网关导致公网 SSH/FRP 掉线的问题（部署 Host Route Pinning 与 `com.mac.dualroute` 热插拔监听）；
  3. 根治了热拔插显示器导致 WindowServer 物理 Framebuffer 销毁呈现远程黑屏的问题（部署 `wake_headless_display.sh` SIGHUP 虚拟屏幕重协商）。
- **交付清单与核心参数**：
  1. `/Users/fsk/.config/frp/frpc.toml`：固化 `loginFailExit = false`，收口 13100 (SSH), 13389 (LLM), 18000 (GMP)；
  2. `/Users/fsk/bin/auto_dual_route.sh` + `/Library/LaunchDaemons/com.mac.dualroute.plist`：系统事件热插拔监听，公网锁定 Wi-Fi，内网 `10.x`/`172.x` 走网线；
  3. `/Users/fsk/bin/system_watchdog.sh` + `/Library/LaunchDaemons/com.mac.watchdog.plist`：60s 定时全栈巡检 13389/18001/18002/8000 端口并秒级 kickstart 自愈；
  4. `/Library/LaunchDaemons/com.pm2.fsk.plist`：开机 Headless 自动 `pm2 resurrect` 园区平台 (`8000`/`3000`)；
  5. `/Users/fsk/bin/wake_headless_display.sh`：一键 SIGHUP WindowServer 重新协商虚拟屏幕，RayLink 画面秒级唤醒；
  6. 运维 SSOT 沉淀：更新 `proxy/Mac_Studio运维档案.md`、`.agents/skills/mac-studio-remote-ops/SKILL.md` 并全量同步至 OpenViking Master Memory (`viking://resources/master_memory/mac_studio_remote_ops_and_headless_self_healing.md`)。
- **验收结果**：已验收通过 ✅ ｜ **实测指标**：公网 SSH 零抖动直连，`https://api.tide.red/v1/models` (1.1s 直出)、`https://fsk.tide.red` (200 OK)、内网直连 (`10.128.226.5`) 双轨并发 100% 满血运行。
- **Git Commit**：`ec2b039` ｜ **Git Tag**：`v1.4.6`

---

### 📌 P1-1: [ ] v1.1.23c：检索测试台 `/retrieval` 页 L0/L1 白盒检索轨迹树与得分渲染
- **类型**：Feature ｜ **优先级**：P1
- **目标**：在 `/retrieval` 页面为每次检索结果渲染可折叠的 **L0/L1 白盒检索轨迹树**，可视化展示 Viking 向量匹配路径与相似度分值（如 `Score: 0.985`）。
- **数据契约**：使用 `POST /api/v1/search/find` 返回的 `uri`、`score` (保留3位小数) 与 `level` (`'L0' | 'L1' | 'L2'`)。
- **验收标准**：
  - [ ] 检索响应后，列表项右侧展现 `Level (L0/L1)` 徽章与 `Score: 0.985` 标签；
  - [ ] 展开轨迹树节点可查看 URI 继承关系；
  - [ ] 符合 `cyan-500` 冰青与 NO GREEN EVER 视觉规约；
  - [ ] `npm run build` 无报错。

---

### 📌 P1-2: [ ] v1.1.23d：监控页 `/monitoring` Token 节省率与 SLA 时延对比折线图
- **类型**：Feature ｜ **优先级**：P1
- **目标**：在 `/monitoring` 页新增双折线对比图，动态渲染有无 L0/L1 避坑拦截机制下的 Token 节省率（如 `82.4%`）及 P95 响应时延变化趋势。
- **数据契约**：消费 `GET /api/v1/system/status` 的 `token_saved_rate` 与 `latency_p95_ms`。
- **验收标准**：
  - [ ] 成功绘制对比折线图，无数据点处显示虚线平滑过渡；
  - [ ] 符合 `cyan-500` 冰青主题与响应式自适应宽度。

---

### 📌 P0: [ ] v1.1.36a/b：核心服务心跳采集与健康探针模型
- **类型**：Infrastructure ｜ **优先级**：P0
- **目标**：在首页和控制台新增核心服务心跳探针，展示健康状态徽章与 CLI 降级告警。
- **验收标准**：
  - [ ] 消费 `/system/status` 输出 27ms 心跳徽章；
  - [ ] 异常时触发哑光红告警。

---

### 📌 P1: [ ] v1.1.35：图谱节点性能 Spike 探查与 LOD 优化
- **目标**：优化 3D/2D 知识图谱在高密度节点下的 LOD 渲染性能，防止卡顿。

---

### 📌 P2: [ ] v1.1.34：任务时间范围自定义筛选能力
- **目标**：在 Task Center 增加自定义 Date-picker 时间筛选器。

---

### 📌 P0: [x] TASK-EVALUATOR-01: OpenViking 大模型 5 场景工业级准入评估标准化体系 (Model Evaluator SSOT) ✅
- **类型**：Core Infrastructure / Evaluation ｜ **优先级**：🔴 P0（大模型选型与准入中枢）
- **交付内容**：
  1. `openviking_model_evaluator.py`：实现 S1~S5 真实业务管道拟真评测（资源分级提纯、意图重写、跨会话主记忆提纯、图谱拓扑推导、技能规范审计）；
  2. 标准答案客观断言链 (Ground Truth)：格式合规 (25分) + 标准答案命中 (40分) + 端到端速率 (20分) + 正文纯净度 (15分)；
  3. 欧尼 35B 实机测试：**94.0 分** 满分命中标准答案，固化为官方黄金基准；
  4. 评测注册表：自动沉淀至 `docs/benchmarks/openviking_model_evaluator_registry.json` 与 `.agents/skills/openviking-model-evaluator/SKILL.md`。

---

### 📌 P0: [ ] TASK-STUDIO-MODELS-MONITOR-01：Models 监控大屏真数据驱动重构与双主题对齐
- **类型**：Observability / Feature ｜ **优先级**：🔴 P0
- **目标**：重构 Studio `/monitoring` 中 Models 监控卡片，彻底切除任何静态数字与假 Mock，100% 绑定后端 `models_observer.py` 的真实模型状态、显存与时延接口；严格遵守 NO GREEN EVER 与双主题。

---

### 📌 P1-3: [ ] Card-Studio-01：Agent Evolution (演进轨迹) 可视化看板集成
- **类型**：Feature ｜ **优先级**：P1
- **目标**：在 Studio 导航中新增 “Evolution / 演进看板”，调用 `/api/v1/agent-evolution/outcomes` 渲染 Agent 经验演进轨迹树与成效对比。
- **关联后端**：Task Card 2 (`v1.3.3`)
- **验收标准**：
  - [ ] 双主题自适应切换正常；
  - [ ] 严格遵守 NO GREEN EVER 与三态语义色彩；
  - [ ] 中英文 i18n 100% 对等覆盖；
  - [ ] `pnpm build` PASS。

---

### 📌 P1-4: [ ] Card-Studio-02：Context Assembler 检索测试台白盒分层调优面板
- **类型**：Feature ｜ **优先级**：P1
- **目标**：在 `/retrieval` 检索测试台中支持 `mode="context"` 模式切换，可视化展示 Tier 分层、Token 预算消耗与去重冷却状态。
- **关联后端**：Task Card 5 (`v1.3.6`)
- **验收标准**：
  - [ ] 检索轨迹树节点支持折叠/展开与分层标记；
  - [ ] 动态展示 Token 预算与实际消耗比率。

---

### 📌 P2-1: [ ] Card-Studio-05：全局配置与数据源管理中心 (Settings & Sources)
- **类型**：Feature ｜ **优先级**：P2
- **目标**：在 Studio 设置中提供可视化动态配置面板，直观查看与管理 `ov.conf` 中的全域技能源、模型端点与存储驱动。

---

### 📌 P2-2: [ ] Card-Studio-06：RAG 评测实验室可视化面板 (RAGAS Benchmark)
- **类型**：Feature ｜ **优先级**：P2
- **目标**：在控制台集成 RAG 检索召回率、准确率与忠实度 (Faithfulness) 评测实验室。

---

### 📌 P2-3: [ ] Card-Studio-07：策略强化训练台 (Policy Trainer)
- **类型**：Feature ｜ **优先级**：P2
- **目标**：可视化展示 Agent 策略反馈日志与奖励信号分布。

---

### 📌 P2-4: [ ] Card-Studio-08：隐私脱敏治理中心 (Privacy Gov)
- **类型**：Feature ｜ **优先级**：P2
- **目标**：对齐后端隐私过滤接口，提供敏感字段查看脱敏与审计日志导出。

---

### 📌 P2-5: [ ] Card-Studio-09：知识大脑迁移打包中心 (OVPack Hub)
- **类型**：Feature ｜ **优先级**：P2
- **目标**：提供图形化 `ovpack` 导出、导入与 VikingFS 快照恢复界面。

---

### 📌 P0: [x] Card-Studio-04：全自动配置驱动技能扫描与自愈同步引擎 (SSOT Skill Scanner) ✅
- **类型**：Infrastructure / Resilience ｜ **优先级**：P0
- **目标**：彻底消除 Ad-hoc 临时脚本漏扫问题。将全域技能扫描源固化在 `ov.conf` 配置文件中作为唯一真相源 (SSOT)，引入服务端自动化扫描器与后台自愈同步定时器，支持 API/启动自动加载。
- **交付内容**：
  - [x] **配置固化 SSOT**：在 `~/.openviking/ov.conf` 的 `skills.sources` 中固化全域 10 大源路径；
  - [x] **自动化扫描模块**：`openviking/server/skill_scanner.py` 实现配置驱动的递归扫描、YAML 解析与原子分发；
  - [x] **服务端 Lifespan 注入**：`openviking/server/app.py` 服务启动时自动执行全量扫描，并在后台按 300s 周期自愈同步；
  - [x] **提供标准 API**：`POST /api/v1/skills/rescan` 和 `POST /api/v1/skills/sync` 随时可零配置手动/程序化刷新；
  - [x] **资产全景验收**：准确索引去重后的全量 **682** 项技能，前端实时同步展示。
- **修改文件**：
  - `openviking/server/skill_scanner.py` [NEW]
  - `openviking/server/routers/skills.py` [MODIFY]
  - `openviking/server/app.py` [MODIFY]
  - `~/.openviking/ov.conf` [MODIFY]
  - `OpenVikingStudio/src/routes/skills/route.tsx` [MODIFY]

---

### 📌 P1: [x] Card-VK-02：WikiSkill & SKILL.state 技能原子化上架与中枢广播 ✅
- **类型**：Core Architecture / Meta-Skill ｜ **优先级**：🔴 P1
- **三维评估**：效果 ⭐⭐⭐⭐⭐ ｜ 风险 ⭐ 零风险 ｜ 工程量 ⭐ 极小
- **目标**：将 Google 2026 双顶会论文核心成果直接提炼为 `wikiskill-evolution`（知识提纯与自演进）与 `skill-state-fsm`（确定性状态机）两大元技能，挂载至 OpenViking 共享技能中心并同步体外大脑记忆中枢。
- **交付内容**：
  1. 编写封顶两大标准技能，分发至 `/home/skloxo/.gemini/config/skills/` 与 `.agents/skills/`；
  2. 标准化部署至 `viking://agent/skills/` 与 `viking://user/default/skills/`，通过 `GET /api/v1/skills` 100% 验收；
  3. 物理入脑至 `viking://resources/master_memory/wiki_skills/` 并完成向量语义重索引；
  4. 跨 Agent 盲测 100% 成功激活 FSM 状态机流转与【技能可回滚、知识不回滚】。
- **验收结果**：已验收通过 ✅

---

### 📌 P1: [ ] Card-VK-01：Harness Lesson 知识镜像双写至 Master Memory
- **类型**：Core Infrastructure / Resilience ｜ **优先级**：🔴 P1
- **三维评估**：效果 ⭐⭐⭐⭐⭐ ｜ 风险 ⭐ 极低 ｜ 工程量 ⭐ 极小
- **目标**：在现有 `openviking_record_evolution_lesson` 逻辑中增加 ~15 行代码，当追加写入目标 `SKILL.md` 时，自动在 `viking://resources/master_memory/evolution_lessons/` 双写一份纯 Markdown 镜像。
- **验收标准**：
  - [ ] 现有 35 条 lessons 兼容无损；
  - [ ] 新触发演进时，知识自动入脑，后续即便代码回滚，客观排坑知识永久留存。

---

### 📌 P2: [ ] Card-VK-03：Mac Studio 离线知识编译批处理脚本 (`offline_wiki_compiler.py`)
- **类型**：AI Tooling / Automation ｜ **优先级**：🟡 P2
- **三维评估**：效果 ⭐⭐⭐⭐ ｜ 风险 ⭐ 零在线风险 ｜ 工程量 ⭐⭐ 中等
- **目标**：编写纯外挂批处理脚本，定期通过只读 API 拉取 VK 中沉淀的 lessons，由 Mac Studio 本地 Qwen 3.8 Flash Next (125B MoE) 进行聚类去重，输出精炼 Recipes/Anti-patterns 写回 VK。
- **验收标准**：
  - [ ] 纯后台只读批处理，绝不阻塞或干扰 1933 生产请求；
  - [ ] 成功生成结构化经验周报并存入 VK。

---

### 📌 P2: [ ] Card-VK-04：Mac Studio 定时排程与自愈守护 (`LaunchDaemon`)
- **类型**：Infrastructure / High Availability ｜ **优先级**：🟡 P2
- **三维评估**：效果 ⭐⭐⭐ ｜ 风险 ⭐ 极低 ｜ 工程量 ⭐ 小
- **目标**：在 Mac Studio 部署 `com.mac.wikicompiler.plist`，每周日凌晨低峰期自动唤醒执行，低优先级 nice 运行不抢占推理资源。
- **验收标准**：
  - [ ] `launchctl list` 正常注册并自愈守护；
  - [ ] 日志输出至 `/var/log/wiki_compiler.log`。

---

### 📌 P3: [ ] Card-VK-05：通用确定性 FSM 接口抽象与 JSON 补丁校验器
- **类型**：Core Framework ｜ **优先级**：🟣 P3
- **三维评估**：效果 ⭐⭐⭐⭐⭐ ｜ 风险 ⭐⭐ 中低 ｜ 工程量 ⭐⭐ 中等
- **目标**：将 `GenericFSM` 封装为轻量通用 Python 工具包，提供标准的 `(P, Σ, o) -> (ΔΣ, a)` 单步状态推进接口，彻底阻断上下文堆叠。
- **验收标准**：
  - [ ] 单元测试验证非法状态转移 100% 阻断；
  - [ ] 合法补丁原子合并，单步完成后物理销毁推理链。

---

### 📌 P3: [ ] Card-VK-06：单场景外挂试点与 Token 降本基准实测
- **类型**：Evaluation / Benchmark ｜ **优先级**：🟣 P3
- **三维评估**：效果 ⭐⭐⭐⭐ ｜ 风险 ⭐ 极低 ｜ 工程量 ⭐ 小
- **目标**：在 watchdog 巡检或非核心长程批处理脚本中实测对比 Token 消耗与自愈表现，形成实测白皮书后再向全系统推广。
- **验收标准**：
  - [ ] 拿到真实对比数据（Token 消耗压降比例、0步自愈恢复能力）。

---

## 🧪 三、 主线课题与 Epic 远期规划卡片 (Far-Term Architecture Task Cards)

### 💳 [ ] Task Card 1 (Far-Term): 记忆治理物理灾备与快照还原机制
- **目标**：在物理数据清理/合并前调用 `VikingFS.commit` 产生版本 Tag，支持 `POST /api/v1/snapshot/restore` 秒级还原。

### 💳 [ ] Task Card 2 (Far-Term): 奥卡姆剃刀轻量级入口查重与冲突消解引擎
- **目标**：在 `memory_store` 入口增加相似度 > 0.90 查重碰撞检测，防源头熵增。

### 💳 [ ] Task Card 3 (Far-Term): 依托 ov_dream 的离线记忆蒸馏与垃圾回收
- **目标**：接入每日 3:00 `ov_dream` 离线蒸馏任务，将 30 天以上的碎片 Context 提纯为领域文档。

### 💳 [ ] Task Card 4 (Far-Term): 多端分布式算力肢体挂载 (M3 + 2080Ti)
- **目标**：挂载 Apple Silicon M3 (256G) 与 RTX 2080Ti / 3070 节点分流。

### 💳 [ ] Task Card 5 (Far-Term): 多模态凭证与上下文死锁保存
- **目标**：截图/聊天记录/凭证单据多模态 Embedding 挂载与 Markdown 自动生成。

### 💳 [ ] Task Card 6 (Far-Term): 高并发 LRU 本地二级缓存
- **目标**：实现本地 0.8ms 极速命中与 TTL 缓存机制。

### 💳 [ ] Task Card 7 (Far-Term): 5 驱上下文压缩分流与 Stanford DSPy SOP 编译引擎
- **关联白皮书**：[PROMPT_COMPRESSION_AND_COMPILER_BLUEPRINT.md](file:///home/skloxo/aho/openclaw/project/.agents/docs/PROMPT_COMPRESSION_AND_COMPILER_BLUEPRINT.md)
- **目标**：实现 Native Caching + LLMLingua-2 + TokenShift + 500xCompressor + Stanford DSPy MIPO 编译器的上下文解耦路由分流。

### 💳 [ ] Task Card 8 (Far-Term): Epic-SKILL-LOOP 自进化闭环引擎 (`LOOP-01 ~ 07`)
- **目标**：实现反思 ➔ Lesson 自动萃取 ➔ `SKILL.md` 审阅与 Git 自动回滚。

### 💳 [ ] Task Card 9 (Far-Term): Epic-SKILL-OPT 质量门禁引擎 (`SKILLOPT-01 ~ 03`)
- **目标**：构建微软 SkillOpt 论文 Attempt 执行 + Judge 门禁评分与权重动态微调。

### 💳 [ ] Task Card 10 (Far-Term): Epic-LIVE-GEN 在线技能创生 (`LIVEGEN-01 ~ 03`)
- **目标**：Monaco 编辑器集成、YAML 语法校验、沙盒验证与一键发布。

### 💳 [ ] Task Card 11 (Far-Term): Epic-PRIVACY-GOV 数据隐私治理 (`PRIVACY-01 ~ 03`)
- **目标**：服务端敏感字段二次过滤与前端脱敏展示。

---

## 🏆 四、 最近已交付版本履历 (Delivered Release Ledger)

### [x] v1.3.2 补丁版本已通过单测验证 (待验收) 🚀
- **Git Commit**: `6dd325b2` (openviking-shallow), `33e9c0f` (OpenVikingStudio)
- **Git Tag**: `v1.3.2`
- **补丁版本升级交付内容**：
  1. **TaskTracker 细粒度并发锁重构**：合并上游 commit `7038ba06`，彻底移除全局单点 `asyncio.Lock` 阻塞，引入分片并发锁池 `KeyedAsyncLockPool`、`StoreIOLimiter(max_concurrent=8)` 与 `OwnerLoopDispatcher`；
  2. **终态生命周期 Guard 保护**：统一终态防护逻辑（`_TERMINAL_STATUSES`），确保 `COMPLETED` / `CANCELLED` / `FAILED` 状态绝对不被并发迟到的回调异常篡改；
  3. **MCP 无状态 HTTP 与超时控制**：合并 `9113fc92` 与 `b8738e05`，保障多实例负载均衡部署与长连接超时可配置；
  4. **技能描述自动 Enrich**：在技能列表解析时自动安全读取 `SKILL.md` 补全 YAML 元数据中的 `description` 字段；
  5. **自动化测试 100% 绿灯**：`tests/test_task_tracker_concurrency.py` 35/35 全套并发与生命周期回归单测全部 100% PASS。

### [x] v1.4.4 补丁版本已验收通过 🎉
- **Git Commit**: `f5df0d3` (`nim_tester`)
- **Git Tag**: `v1.4.4`
- **交付内容**：
  1. **零 Token 消耗与零过度工程**：彻底切除开局死板预抓取 100 个模型元数据的开销，100% 采用纯 TS 正则与内嵌字典，毫秒级解析，无任何大模型 Token 消耗；
  2. **按需延迟加载 (On-Demand / Lazy Meta)**：只在模型成功通过测试算分或用户主动查询详情时按需计算；对大量报错/熔断/不可用的损坏模型直接跳过，零网络请求、零资源占用。

### [x] v1.4.3 补丁版本已验收通过 🎉
- **Git Commit**: `5de164a` (`nim_tester`)
- **Git Tag**: `v1.4.3`
- **交付内容**：
  1. **彻底打掉“不可用模型得高分”漏洞**：重构 `scoreModel`，引入 `is_available` 硬性一票否决门禁。凡基础可用性失败或通过率 < 50% 的模型，得分上限物理封顶于 30 分以内，评级强制置为 D/F 级；
  2. **可用性绝对优先排序**：重构 `rankCategory`，在榜单中确保所有【可用模型】物理 100% 绝对排在前面，【不可用模型】一律压制至榜尾垫底。

### [x] v1.3.3 版本已验收通过 🎉
- **Git Commit**: `4d14832` (OpenVikingStudio), `feat/task-center-stats-autohealing-v2` (openviking-shallow)
- **Git Tag**: `v1.3.3`
- **v1.3.3 升级交付内容**：
  1. **SSOT 配置化技能发现与全量元数据引擎**：重构底层 `SkillScanner` 与 `ov.conf` 动态源配置，自动全量扫描 10 大源目录，稳定汇聚 682 项技能，杜绝手动补充与漏扫；
  2. **技能关联文件解析与兜底强化**：重构前端技能详情解析，兼容字符串数组与字典对象双格式，保底单文件精简规范，彻底消除“文件: 0”展示缺陷；
  3. **性冷淡极客美学与 NO GREEN EVER 全面遵从**：剔除监控大屏全部多余的紫/绿装饰色块，100% 贯彻数据正常态中性素雅 (`bg-muted/20`)、偏差态冰青/湛蓝与玫瑰红语义，字号硬下限严格 $\ge 11\text{px}$；
  4. **任务中心假 404 路由清除与指标恢复**：修复 FastAPI 静态路由前置优先级与任务统计 API，消除 3,000+ 冗余 404 请求；
  5. **1936 毫秒级 HMR 热更新与 1933 正式环境双轨架构**：常驻 Vite Dev Server（1936 端口，50ms 热替换 + 1933 API 真实透明代理），建立 dist 软链接提升发布体验。

### [x] v1.4.2 补丁版本已验收通过 🎉
- **Git Commit**: `7818e96` (`nim_tester`)
- **Git Tag**: `v1.4.2`
- **交付内容**：
  1. **彻底修复降级日志重复刷屏问题**：优化 `CircuitBreaker` 状态切换检测，单模型在达到连续 3 次异常时仅精确触发 1 次降级通知，彻底消除了并发导致的重复 4 次提示；
  2. **日志体验极大提升**：推流控制台日志层次清晰自解释，毫无赘字噪音。

### [x] v1.4.1 补丁版本已验收通过 🎉
- **Git Commit**: `d120a6e` (`nim_tester`)
- **Git Tag**: `v1.4.1`
- **交付内容**：
  1. **彻底切除离线 131/191 静态数据残存**：重构 `/api/catalog/stats` 接口与 `metaFetcher.ts`，取消读取离线静态文件的死板逻辑；
  2. **100% 动态数据驱动**：未从 API 动态获取到数据前，界面 Banner 统一优雅展示 `--` 占位符 (`📦 官方在线模型: -- | 元数据就绪: --`)；
  3. **数据真实性保障**：只在点击测试或网络 API 真实下发数据后，才以英伟达 API 下发的真实动态数量填充展现。

### [x] v1.4.0 次版本发布已验收通过 🎉
- **Git Commit**: `08be9f2` (`nim_tester`)
- **Git Tag**: `v1.4.0`
- **次版本升级交付内容**：
  1. **前端极客双主题与信达雅视觉走查**：全面支持暗色 🌙 / 亮色 ☀️ 自适应切换，实现 100% NO GREEN EVER 物理三态色彩归一（冰青/湛蓝 `#06b6d4` / `#0284c7`，玫瑰红，沉静灰）；字号物理硬下限 $\ge 11\text{px}$，表格数值采用 `font-mono tabular-nums`；
  2. **KeyRotator 配额解冻死锁修复**：修正时间戳预扣时间点，解决多协程排队竞争引发的 44.8s 虚假死锁；
  3. **按模型隔离熔断器 (`PerModelCircuitBreaker`)**：废除粗暴的全局连坐熔断，单模型连续 3 次异常仅跳过该损坏模型，绝不影响全盘 100+ 个正常模型；
  4. **遥测日志精炼与降噪**：彻底清除啰嗦刷屏文本，统一 `🛡️ [模型降级]`、`⏳ [平滑控速]`、`✖ [异常]` 等极客精炼自解释日志；
  5. **API 分页去重与严格对齐**：通过 `seenSet` 和多参探测防死循环，实现前端/后端与真实在线 100 个模型 100% 物理真实连贯对齐；
  6. **Web 安全与缓存 HTTP Header**：全盘注入 `X-Content-Type-Options: nosniff`、`X-Frame-Options` 等高标准响应头；
  7. **持久终端守护**：服务已通过 Persistent Background Terminal 常驻托管于端口 `28080`。

### [x] v1.3.1 补丁版本已验收通过 🎉
- **Git Commit**: `bb3d151f` (openviking-shallow)
- **Git Tag**: `v1.3.1`
- **补丁版本升级交付内容**：
  1. **对齐上游 PR #3538 反馈**：完善 TaskTracker 生命周期终态 Guard 防护，保留 `resource_id` 参数兼容。
  2. **消除硬编码物理落盘与盲吞 Exception**：切除绕过 AGFS 配置的 `~/.openviking` 物理落盘与 `try...except` 盲吞代码，统一走 `self._store.update()` 存储抽象。
  3. **自动化测试**：43/43 全套 Task Tracker 单元测试全部 Pass。
  4. **1933 正式环境无 Bug 确保**：已通过 1933 端口 Root Key 健康探针物理校验，系统输出 `status: ok`，无中断运行。

### [x] v1.3.0 次版本发布已验收通过 🎉
- **Git Commit**: `v1.3.0` Tag (OpenVikingStudio & OpenViking)
- **Git Tag**: `v1.3.0`
- **次版本升级交付内容**：
  1. **完整多语言 i18n 体系**：100% 覆盖全部 9 大监控卡片与导航词条，默认启用 `zh-CN` 界面；
  2. **Parser CJK Token 准确估算**：将 CJK 字符估算系数设为 `1.0`，与 Embedder `-b 2048` 容量完全物理对齐，彻底擦除 `[:1800]` 假截断 fallback；
  3. **任务自愈重新入队引擎**：将 `reindex` 重试模式修复为 `semantic_and_vectors`，打破死重试循环；
  4. **Agent 入口唯一真相源 (SSOT)**：构建 `.agents/AGENTS.md`、`docs/PHILOSOPHY.md`、`docs/UI_DESIGN_SPEC.md` 与 `docs/ARCHITECTURE_BLUEPRINT.md` 规范矩阵；
  5. **物理级灾备与秒级回滚机制**：整合底层 VikingFS Git 级快照与 `ovpack` 导出能力；
  6. **更新 Git 主页与版本号**：物理升级 `package.json` 版本至 `1.3.0`，发布 GitHub Release。

### [x] v1.2.42 已验收通过 ✅
- **Git Commit**: `5aa6b13` (OpenVikingStudio), `549dc824` (OpenViking)
- **Git Tag**: `v1.2.42`
- **交付内容**：
  1. 补齐全系统 100% 缺失的多语言词条字典（`zh-CN.ts` 与 `en.ts`），将默认语言置为 `zh-CN`；
  2. 修复任务中心“重新入队”的 `reindex` 模式为 `semantic_and_vectors`，打破重试死循环；
  3. 创建 Agent 开局统一 SSOT 文档体系（`AGENTS.md` / `PHILOSOPHY.md` / `UI_DESIGN_SPEC.md` / `ARCHITECTURE_BLUEPRINT.md`）；
  4. 物理更新 `package.json` 版本号为 `1.2.42`。
