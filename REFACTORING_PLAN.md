# 🗺️ OpenViking 项目主线重构与原子化任务卡片总看板 (Master Task Cards Kanban - SSOT)

> **关联主蓝图**：[OpenViking 研发迭代大蓝图 (`viking://resources/home_projects/openviking_blueprint/OpenViking_R_and_D_Iteration_Blueprint.md`)](file:///home/skloxo/.openviking/data/viking/default/resources/home_projects/openviking_blueprint/OpenViking_R_and_D_Iteration_Blueprint.md)  
> **关联远期 Epic**：[ROADMAP.md (Studio 远期路线图)](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/ROADMAP.md) | [DELIVERY_ARCHIVE.md (交付履历库)](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md)  
> **唯一真相源 (SSOT)**：所有主线任务卡片、包含此前规划的所有活跃工单与远期 Epic，均在此统筹物理收口，严禁遗漏散落。

---

## 🛠️ TideTrading 架构第一性原理重构看板 (TideTrading Refactoring Roadmap)

| 任务卡片 ID | 模块与重构目标 | 物理重构方案 (第一性原理) | 当前状态 |
| :--- | :--- | :--- | :---: |
| **Card-TT-01** | **`initialize_history_data.py` 纯程序化计算改造** | 彻底切除用大模型扫描 1 年历史数据的滥用工程，重构为 100% 纯 Python (Pandas/NumPy/SQL) 历史行情指标与因子算法计算。 | ⏳ 待实施 (已断模型) |
| **Card-TT-02** | **Crontab 盘中监控与选股程序化优先** | 遵守“能用程序实现 100% 用程序，只在最终文本输出时按需使用 LLM”。重构 `intraday_monitor.py` 与 `daily_screening_v5.py`。 | ⏳ 待实施 (已断模型) |
| **Card-TT-03** | **Paperclip (回形针) 彻底卸载与进程清理** | 已从 PM2 中物理 `delete` 终止 `paperclip` 进程，清空内存占用。 | [x] 已完成 ✅ |

---

## 🗺️ 上游 OpenViking 全景合并与演进原子化看板 (112 Commits Full Roadmap)

| 任务卡片 ID | 模块领域 | 包含上游核心特性 | 上游 Commits | 物理验收条件 | 计划 Tag 版本 | 当前状态 |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **Task Card 1** | **并发锁与 TaskTracker 融合 + Studio v1.3.4** | TaskTracker 细粒度锁池 (`KeyedAsyncLockPool`)、Store I/O 限制、终态 Guard 统一、Studio 视觉瓦片修复 | `7038ba06`, `9113fc92`, `b8738e05`, `bb82c376` | `test_task_tracker_concurrency.py` PASS, 113/113 测试通过, 1933 健康上线 | `v1.3.4` | [x] 已验收并交付 ✅ (Commit: `1ca76e53`, Tag: `v1.3.4`) |
| **Task Card 2** | **Agent 演进与经验记忆** | Agent 演进服务、经验血缘追踪 (`experience_lineage.py`)、OpenClaw 经验工具 | `61c42e3b`, `73a70195`, `2ced3f15` | `test_api_agent_evolution.py` PASS | `v1.3.3` | ⏳ 待开始 |
| **Task Card 3** | **QueueFS & Redis 集群化** | QueueFS 支持 Redis 单机/集群/哨兵模式、启动有界过期任务清扫 (0/30/60) | `8c9c2282`, `758fc7f0` | `test_config_validation.py` PASS | `v1.3.4` | ⏳ 待开始 |
| **Task Card 4** | **Session 自动提交 V2** | Session 自动提交服务 (`SessionAutoCommitService`)、局部捕获异常断点恢复 | `d2056e97`, `0ab48f96`, `8e98a3c7` | `test_session_auto_commit.py` PASS | `v1.3.5` | ⏳ 待开始 |
| **Task Card 5** | **服务端上下文统一召回** | `/search mode="context"` 组装、分层预算裁剪 (`context_assembler`)、Rerank L1 对齐 | `2cc96e39`, `674f5e60`, `cbc39077` | `test_context_assembler_pipeline.py` PASS | `v1.3.6` | ⏳ 待开始 |
| **Task Card 6** | **企业级认证 (OIDC/LDAP)** | OIDC / LDAP 企业级身份插件、Watch 任务刷新安全 ACL、执行解析器加固 | `444cc87b`, `21029f40`, `03bd4694` | `test_ldap_auth.py` PASS | `v1.3.7` | ⏳ 待开始 |
| **Task Card 7** | **Storage & VikingFS 容错** | `mkdir` 错误主动透传、`mv` 突破 1000 节点深拷贝、废弃向量后端清理 | `0205914d`, `ecab57e1`, `1d02a72b` | `test_mv_copy_node_limit.py` PASS | `v1.3.8` | ⏳ 待开始 |
| **Task Card 8** | **Markdown 与内容写入增强** | `content_write` 处理模式、解析后不拆分 (`no_split`)、CJK Token 预算对齐 | `6f43a404`, `8d1d52fe`, `3087f943` | `test_markdown_split_token_budget.py` PASS | `v1.3.9` | ⏳ 待开始 |

---

## ⚡ 二、 当前活跃与待调度 Studio 原子工单 (Scheduled Active Task Cards)

### 📌 P0: [x] TASK-VL-DEPLOY-01 (v1.4.4): 2080Ti (22GB) 本地 Qwen3-VL 双模型自主拉起、INT8显存治理与全系统对接闭环 ✅
- **类型**：Core Infrastructure ｜ **优先级**：🔴 P0（知识库与多模态检索中枢）
- **目标**：在 Windows 宿主机 2080Ti (22GB) 上完成 Qwen3-VL-Embedding-8B-W8A16 与 Qwen3-VL-Reranker-2B 双模型拉起，进行算子层与 INT8 显存治理，保留 2.8GB+ 动态空间，打通 11432 统一 REST 服务，完成 OpenViking 与 OpenClaw 全系统对接。
- **交付清单**：
  1. `C:\openviking_offline\offline_serve.py`：高吞吐原生多模态双模型服务（`/v1/embeddings` 4096 维 + `/v1/rerank` 相关性评分）；
  2. 修复 `compressed_tensors` 算子解压与 `transformers` 命名空间绑定，实现 100% 真实数学参数还原；
  3. Reranker 2B 引入 `bitsandbytes` INT8 量化，显存从 21.6GB 峰值彻底优化至 18.6GB，保留 2.81GB 动态显存池；
  4. `~/.openviking/ov.conf` 绑定 4096 维 dense embedding 与 rerank 接口；
  5. `~/.openclaw/openclaw.json` 挂载 `local-vl` 供应商；
  6. Wiki 沉淀：`viking://resources/master_memory/retrieval_bvl_r12_architecture.md`。
- **验收结果**：已验收通过 ✅ ｜ **服务端口**：`http://127.0.0.1:11432`

---

### 📌 P0: [ ] TASK-STUDIO-MODELS-MONITOR-01: AI 模型监控面板 (Models) 分类治理、去重防串与高密信达雅重构
- **类型**：UI / Architecture Refactoring ｜ **优先级**：🔴 P0（核心运行态观测白盒雷达）
- **背景病灶**：
  1. **模型分类错位与重复统计 (Misclassification & Duplication)**：`qwen3-vl-emb` 是 4096 维密集向量嵌入模型，却同时在“VLM 视觉模型”下统计了 1,405 次，在“Embedding 向量模型”下显示 0 次；`auto-router`、`command-r-plus` 等纯文本/路由模型被粗暴机械归入 VLM，分类定义混乱；
  2. **供应商机械死板写死 "Openai"**：所有使用 OpenAI 兼容协议的模型，供应商列均机械展示为 `openai`，无法区分实际物理部署源（如 CPA 网关 8317、本地 2080Ti 11432/11433、Mac Studio 13389、本地 CPU 等）；
  3. **历史僵尸模型堆积未归档**：历史弃用模型（如 INT8, W8A16, text-embedding-3-small, 0次调用的 llmlingua-2）缺乏时间窗口切分（24H 活跃 vs 全量历史），面板信噪比严重劣化；
  4. **高密视觉排版不达标**：行高松散、信息密度低，缺少状态微胶囊、P95 响应时延、调用成功率与自解释相对时间戳。
- **重构方案 (第一性原理)**：
  1. **前后端模型四态语义精准重构 (Semantic Categorizer)**：
     - `LLM & VLM 认知/多模态推理模型`：`qwen3.8-flash-next`, `ornith-1.5-35b-a3b-vl` 等；
     - `Embedding 向量表征模型`：`qwen3-vl-emb`（物理收口于此，彻底清除跨类重复项）、`Qwen3-Embedding-8B` 等；
     - `Rerank 语义重排模型`：`qwen3-reranker-0.6b` / `qwen3-vl-rer`；
     - `Prompt Compressor 提示词压缩模型`：`microsoft/llmlingua-2...`。
  2. **真实物理供应商来源映射 (Physical Node Mapping)**：
     - 结合端口与路由特征，将 `openai` 替换为自解释真实物理来源：`CPA 网关 (8317)`、`Local 2080Ti (11432/11433)`、`Mac Studio`、`Local CPU`。
  3. **24H 动态滚动窗口与历史归档抽屉**：
     - 新增 `🕒 24H 活跃` / `全量历史` 切换，历史 0 调用模型默认归档折叠，主面板仅高亮活跃实时模型。
  4. **高密紧凑排版与 NO GREEN EVER 落地**：
     - 表格内边距压缩为 `py-1`，数值统一采用 `font-mono tabular-nums text-xs`，字号下限 `>= 11px`；
     - 增加状态指示微胶囊（`活跃 / 待命 / 归档`）与相对时间自解释展示。
- **验收标准**：
  - [ ] `qwen3-vl-emb` 不再跨类重复出现，分类 100% 准确；
  - [ ] 供应商列真实反映物理节点，消除一刀切 `openai` 假象；
  - [ ] 支持 24H 活跃筛选与历史折叠；
  - [ ] 严格遵守 NO GREEN EVER（冰青 `cyan-500` / 沉静灰 `muted` / 玫瑰红 `rose-500`）；
  - [ ] 中英文双语 i18n 100% 同步覆盖，`pnpm build` PASS。

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

### 📌 P2-2: [ ] Card-Studio-03：企业级 Auth 状态自适应与只读模式 Banner
- **类型**：Feature ｜ **优先级**：P2
- **目标**：对齐上游企业级认证模式，当服务端开启 OIDC/LDAP 时在 Studio 设置页优雅展示认证源状态与权限级别。
- **关联后端**：Task Card 6 (`v1.3.7`)
- **验收标准**：
  - [ ] 认证模式下优雅提示只读/管理员状态，无假控制台报错。

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
