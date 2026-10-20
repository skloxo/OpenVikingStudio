# 🗺️ OpenViking 项目主线重构与原子化任务卡片总看板 (Master Task Cards Kanban - SSOT)

> **关联研发大蓝图**：[`BLUEPRINT.md`](file:///home/skloxo/aho/openclaw/project/.agents/BLUEPRINT.md) ｜ **交付全量归档台账**：[`DELIVERY_ARCHIVE.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md) ｜ **通用资产档案库**：[`COMPONENT_AND_WHEEL_INVENTORY.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/docs/architecture/COMPONENT_AND_WHEEL_INVENTORY.md)
> **唯一真相源 (SSOT)**：本文档为 OpenViking 当前活跃的重构规划与就绪待调度的任务矩阵看板。历史所有已验收交付的版本履历已完整归档至 [`DELIVERY_ARCHIVE.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md)。
> **战略外围项目隔离公理**：`Search2API 商业化搜索聚合网关` (`docs/search/SEARCH2API_COMMERCIAL_GATEWAY_SPEC.md`) 确认为独立多账号商业化代理项目，不占用 OpenViking 核心任务大盘卡槽。
> **基线状态**：线上正式部署 **`v1.4.106`** ｜ 当前最新交付 **`v1.7.156`** (代码基线 `v1.7.149`) ｜ 分支状态：`main` 已全量同步远程 `origin/main`。

---

## 📌 一、 全景版本发布与里程碑验收矩阵 (Milestone Evolution Matrix)

| 版本 Tag | 任务工单 ID | 模块与重构主题 | 核心治理成果与物理交付物 | 验收状态 |
| :--- | :--- | :--- | :--- | :---: |
| **`v1.7.153`** | **Card-196** | **生活与研发物理隔离 (Privacy Isolation)** | 家庭高隐私资产物理移入独立目录，斩除研发库临时私有目录，实现研发与生活物理隔离。 | [x] 已验收通过 ✅ |
| **`v1.7.154`** | **Card-197** | **18 核心母包收敛与平权对齐 (Bundles Convergence)** | 3070 与 2080 平权对等，物理铲除 4 大无关大包 (115场景)，母包收敛至纯粹 18 个。 | [x] 已验收通过 ✅ |
| **`v1.7.155`** | **Card-198** | **端侧极简瘦身与三层法典解耦 (3-Tier AGENTS Law)** | 切除端侧重复技能，全局保留 8 宿主核心骨架，确立单文件 ≤500 行硬上限与 100~300 行甜点区。 | [x] 已验收通过 ✅ |
| **`v1.7.156`** | **Card-199** | **Workspace 超级航母重构与双 Junction (Super-Carrier)** | 建立 Workspace 超级航母，提纯 00_Common 六大通识，双 Junction 零中断保活，死链清零。 | [x] 已验收通过 ✅ |
| **`v1.7.149`** | **Card-184** | **RNFV 两阶段存储事务模型与并发写锁彻底解耦 (Resource RNFV Transaction)** | 意图规划与物理执行两阶段彻底解耦，写入锁仅保护同步提交，根除写锁死锁，31/31 测试全绿。 | [x] 已验收通过 ✅ |
| **`v1.7.148`** | **Card-193** | **AGFS 写入事务加固与目录树一致性 (AGFS Transaction)** | 写入锁跨阶段保持，AGFS 异步拷贝接入 run_to_completion，409 精准透传，索引写入标签净化。 | [x] 已验收通过 ✅ |
| **`v1.7.147`** | **Card-190** | **Gateway 2.0 吞吐优化与 Prompt Cache 态势大盘 (Gateway Optimization)** | 多厂商 Prompt Cache 归一化提取，SSE 流式分帧加速，前端座舱呈现 PromptCache 态势大盘。 | [x] 已验收通过 ✅ |
| **`v1.7.146`** | **Card-189** | **多模态混合检索扩展与显式作用域保护 (Multimodal Search)** | 多模态 Query 扩展，显式目标作用域保护，复合稠密+稀疏分离路由，512 项测试回归全绿。 | [x] 已验收通过 ✅ |
| **`v1.7.145`** | **Card-188** | **AGFS 事务加固与解析管线防崩 (Parser Crash Prevention)** | PDFium 互斥锁，Markdown 顶级标题前内容保真，飞书表格管道符转义，脏快照覆写物理阻断。 | [x] 已验收通过 ✅ |
| **`v1.7.144`** | **Card-187** | **Session 高并发读写去重与归档锁解耦 (Session Lock Decoupling)** | 任务归档移出临界区根除死锁，状态机单轨收敛至 SessionCommit，落地 open() 热读去重。 | [x] 已验收通过 ✅ |
| **`v1.7.142`** | **Card-185** | **VikingBot 流式实时中断与动态舵向注入 (Stream Steer & Interruption)** | SSE 流式生成毫秒级释放资源，支持动态修正注意力方向，前端提供一键打断纠偏。 | [x] 已验收通过 ✅ |
| **`v1.7.143`** | **Card-186** | **Map-Shuffle-Reduce 知识多阶段编译管线 (MSR Compiler)** | 海量文档 Map 切片、Shuffle 聚类、Reduce 蒸馏 L0/L1 摘要，支持超大型工程秒级索引。 | [x] 已验收通过 ✅ |
| **`v1.7.136`** | **Card-166** | **技能使用频次遥测、ROI 价值度量与自动排序 (Skill ROI Telemetry)** | SQLite 记录技能调用，加权计算 ROI 价值分，前端排行榜与沉睡预警，全套门禁全绿。 | [x] 已验收通过 ✅ |
| **`v1.7.127`** | **Card-165** | **全双工实时事件总线与技能大盘毫秒级自愈刷新 (Skill Event Bus)** | WebSocket/SSE 双端点，状态微脉冲下发 (PIPELINE_PULSE)，前端 TanStack 毫秒自愈拉新。 | [x] 已验收通过 ✅ |
| **`v1.7.126`** | **Card-164** | **运行态技能动态注脑与 Token 预算自适应抽稀 (Skill JIT Injection)** | 运行时动态注脑，Token 预算自适应抽稀，占位符物理冻结代码块，防线单测变绿。 | [x] 已验收通过 ✅ |
| **`v1.7.125`** | **Card-163** | **超级大包分面过滤、即时检索与防死灰复燃 (Mega-Bundle Faceted Search)** | 前端分面过滤栏，即时检索响应，大包子场景穿透展示与删除防死灰复燃门禁。 | [x] 已验收通过 ✅ |
| **`v1.7.124`** | **Card-162** | **20 领域能力大包纯化结晶与单测 (20 Capability Bundles)** | 纯化收敛 20 核心能力大包，生成标准化结构与单测视网膜守护。 | [x] 已验收通过 ✅ |
| **`v1.7.124`** | **Card-104** | **存量孤儿切片物理大扫除与向量库深度同步 (Ghost Slices Pruning)** | 修复向量过滤字典契约，彻底清退僵尸测试孤儿索引，批量清退 2,500+ 废弃向量切片。 | [x] 已验收通过 ✅ |
| **`待排期`** | **Card-167** | **技能大盘在线交互测试沙箱与意图命中试算器 (Skill Playground & Scaffolding)** | 开发者交互调试终端，Prompt 命中可视化，注脑压缩对比度量，标准 6 章节脚手架生成。 | [ ] 待排期迭代 ⏳ |
| **`待排期`** | **Card-168** | **系统底层与体外大脑五层抗熵增治理中枢 (Anti-Entropy Memory Evolution)** | 前门语义准入去重，失效认知版本演进链 (Superseded DAG)，夜间离线做梦蒸馏 (ov_dream)。 | [ ] 待排期迭代 ⏳ |
| **`待排期`** | **Card-203** | **上游 Storage 写入锁协调提前消费与跨进程恢复整并 (Upstream Storage Lock)** | 吸收 upstream PR #6300 锁泄漏修复、#6281 跨进程恢复、#6298 大小写冲突规避。 | [ ] 待排期迭代 ⏳ |
| **`待排期`** | **Card-204** | **上游 Gateway 缓存遥测增强与 DSH 无工具请求防重复召回整并 (Upstream Gateway)** | 吸收 upstream PR #6295 DSH 侧向请求防重复召回、#6267 缓存告警、#6026 降低 CPU 损耗。 | [ ] 待排期迭代 ⏳ |
| **`待排期`** | **Card-205** | **上游 Session 消息写入与接口去重读取性能优化整并 (Upstream Session Perf)** | 吸收 upstream PR #6270 消息写入与 Session 重复读取优化、#6075 防脏快照 upsert。 | [ ] 待排期迭代 ⏳ |
| **`待排期`** | **Card-206** | **上游 Studio 前端多语言 i18n 补全与 AppleDouble 元数据过滤整并 (Upstream Studio)** | 吸收 upstream PR #6292 全域多语言 i18n 补齐、#6316 AppleDouble 元数据过滤、#6215 Key 透传。 | [ ] 待排期迭代 ⏳ |
| **`v1.7.157`** | **Card-200** | **`openviking-memory` 插件母本自内聚转接驱动重构与自愈清洗 (Antigravity Memory Proxy Stub & SSOT v2.0.16)** | 1. 彻底拔除 setup.py 中外部桌面路径硬编码与 candidate_scripts 扫描，插件目录自带自内聚 server.py 独立转接驱动；<br>2. 统一多机物理契约：2080Ti 本地与 3070 远程代码 100% 相同，唯一变量仅为 OPENVIKING_API；<br>3. 强制自愈清洗幽灵：安装与注册逻辑强制 pop("openviking", None)，消灭历史幽灵条目；<br>4. 版本原子递增：plugin.json 与 setup.py 同步自增至 v2.0.16，全景生态健康测试 100% 满绿通过。<br>*(Commit: `06dc379d0`, Tag: `v1.7.157`)* | [x] 已验收通过 ✅ |
| **`待排期`** | **Card-201** | **`openviking-ops` 插件母本自内聚转接驱动与运维接口标准化 (SSOT v1.0.3)** | 拔除路径依赖，统一环境嗅探与单向部署，版本原子递增。 | [ ] 待排期迭代 ⏳ |
| **`待排期`** | **Card-202** | **`fleet-mesh` 插件母本自内聚转接驱动与多节点拓扑自适应 (SSOT v1.0.2)** | 拔除路径依赖，自适应探测 2080Ti/3070 节点，版本原子递增。 | [ ] 待排期迭代 ⏳ |
| **`待排期`** | **Card-207** | **知识盲区自愈、反思骨架铸造与双轨补全自进化 (Knowledge Deficit Scaffolding)** | 推理缺口捕获，自动生成反思骨架草稿，双轨触发本地/外部知识补全。 | [ ] 待排期迭代 ⏳ |
| **`待排期`** | **Card-208** | **Workspace 分层配置与项目级 Peer 身份持久化 (Workspace Config & SSOT)** | 支持 `.openviking.toml` 项目级配置固化，解决跨设备/子目录迁移导致的项目记忆失效。 | [ ] 待排期迭代 ⏳ |
| **`待排期`** | **Card-158** | **KeePass 本地凭据保险箱端侧体验与安全体检深化 (KeePass Local Vault)** | 本地 `.kdbx` 路径自动寻路、解密测试、弱口令分析与高熵生成。 | [ ] 待排期迭代 ⏳ |
| **`待排期`** | **Card-159** | **Dify 智能体与工作流中枢插件机制演进与 DSL 备份回滚 (Dify Workflow)** | 工作流入参强校验，DSL 导入前本地快照备份与一键安全回滚。 | [ ] 待排期迭代 ⏳ |
| **`待排期`** | **Card-160** | **CPA 跨模型算力协同工兵调度与 429 降级记账闭环 (CPA Multi-Model)** | 专家咨询与工兵扇出分工固化，429 限流自愈与熔断转移，Token 成本审计。 | [ ] 待排期迭代 ⏳ |
| **`待排期`** | **Card-105** | **常驻自净巡检哨兵引擎 (MemoryPuritySentinel Daemon Engine)** | 单例低开销守护线程，串联孤儿清除、艾宾浩斯冷存、冲突脱水、staging TTL。 | [ ] 待排期迭代 ⏳ |
| **`待排期`** | **Card-106** | **入口级实时免疫门禁与血统拦截 (Ingress Anti-Poison Gatekeeper)** | 拦截未经生命周期登记的外部长切片，相似度 >0.85 自动级联降级旧知识并挂载 DAG。 | [ ] 待排期迭代 ⏳ |
| **`待排期`** | **Card-107** | **Web Studio 观测大屏自净态势瓦片与手动干预沙箱 (Cockpit Purity)** | 观测大屏回显 SNR 信噪比、Purity Score、净减熵数，支持一键 Dry-run 自检。 | [ ] 待排期迭代 ⏳ |
| **`待排期`** | **Card-108** | **FastMCP 工具调用执行切面与异步事件总线发射器 (FastMCP Interceptor)** | mcp_endpoint 工具分发入口增加统一环绕拦截切面，异步发射事件至总线。 | [ ] 待排期迭代 ⏳ |
| **`待排期`** | **Card-109** | **UsageAudit 投影层 MCP 规约与脱水脱敏流水线 (Usage Audit Projection)** | projection.py 补齐 mcp.tool_call 转换器，挂载 PrivacyMasker 动态脱敏。 | [ ] 待排期迭代 ⏳ |
| **`待排期`** | **Card-110** | **Web Studio 审计大盘 MCP 工具分类与参数详情抽屉 (Logs MCP Drawer)** | 前端 request-logs 增加 MCP 工具筛选胶囊，增加高密工具调用卡片与参数抽屉。 | [ ] 待排期迭代 ⏳ |

---

## 📌 二、 待攻坚活跃任务卡片深度规划 (Active & Pending Task Cards Details)

### 🚀 第一优先批次：核心主线与上游整并 (P0)

#### 📌 [P0] [ ] Card-167: 技能大盘在线交互测试沙箱与意图命中试算器 (Skill Playground, Intent Hit-Testing & Scaffolding SSOT) ⏳
- **类型**：Web Studio 交互调试 / 意图命中试算 / Token 压缩实时度量 / 标准脚手架生成 ｜ **优先级**：🔥 P0 首选
- **核心契约与方案拆解**：
  1. **意图命中试算端点 (`/api/v1/skills/playground/hit-test`)**：
     - 调用 `SkillIntentMatcher` 与 `SkillPackageRouter`，输入 Prompt 实时可视化计算 Top-1/Top-2 母包亲和度、KNN Margin、子场景路由判定及别名透明投影流向；
     - 自动检测触发词碰撞与覆盖率分析 (`detect_collisions`)；
  2. **动态注脑压缩度量 (`/api/v1/skills/playground/compress-simulate`)**：
     - 接入 `SkillZipEngine.compress_contractual`，在线对比原始全文 vs Six-Tuple 结构化抽稀；
     - 实时回显字符数/Token 节省数、压缩率（%）、耗时（ms）与契约保真度（Fidelity）；
  3. **标准 6 章节脚手架生成器 (`/api/v1/skills/playground/scaffold`)**：
     - 表单化填写名称、触发词、领域与角色，自动生成标准 YAML Frontmatter 与 6 章节 Markdown，一键通过门禁检测并支持导出；
  4. **前端交互工作台 (`src/routes/skills/-components/skill-playground-cockpit.tsx`)**：
     - 顶栏模式切换直达，解耦三大面板 (`skill-hit-tester.tsx`, `skill-compression-bench.tsx`, `skill-scaffold-generator.tsx`)；
     - 严格遵循 **NO GREEN EVER 🚫**，字号硬下限 $\ge 12	ext{px}$ (`text-xs`)，单文件 100~300 行黄金甜点区；
  5. **视网膜单测与门禁**：WSL 原生 Pytest 单测变绿，Vitest 前端单测变绿，打标 Tag `v1.7.150`。

#### 📌 [P0] [ ] Card-203: 上游 Storage 写入锁协调提前消费与跨进程恢复整并 (Upstream Storage Lock Leak & Recovery Alignment) ⏳
- **类型**：底层存储加固 / 并发锁治理 / 跨进程恢复 ｜ **优先级**：🔥 P0
- **核心契约与方案拆解**：
  1. **吸收上游 PR #6300 (c89efb7c3)**：修复写入协调消息提前消费导致的锁泄漏；在消费协调器中确保锁释放与状态 settle 严格原子化；
  2. **吸收上游 PR #6281 (c476a3184)**：整并跨进程崩溃自愈与残留锁清理 (`cross process recovery`)，确保进程意外中止后 PathLock 自动释放；
  3. **吸收上游 PR #6298 (b51cba425)**：切除大小写敏感冲突误报；
  4. **视网膜单测**：编写针对性锁泄漏与跨进程崩溃恢复单元测试，验证高并发 0 锁残留。

#### 📌 [P0] [ ] Card-204: 上游 Gateway 缓存遥测增强与 DSH 无工具请求防重复召回整并 (Upstream Gateway Cache Telemetry & Anti-Duplicate Recall) ⏳
- **类型**：网关吞吐优化 / 记忆召回防抖 / DSH 协议治理 ｜ **优先级**：🔥 P0
- **核心契约与方案拆解**：
  1. **吸收上游 PR #6295 (e855796c8)**：针对 DSH 及无工具侧向请求，拦截并停止重复的记忆召回与无谓创建新 Session，大幅削减 CPU 与 Token 开销；
  2. **吸收上游 PR #6267 (27db44123)**：从所有上游格式解析 Cache Usage，当长对话丢失 Prompt Cache 时主动发出预警；
  3. **吸收上游 PR #6026 (26fa00b91)**：精简请求准备、回复中继与查找过程中的 CPU 消耗；
  4. **视网膜单测**：单测覆盖 DSH 侧向请求拦截、Cache Usage 提取与报警，确保网关 0 冗余调用。

#### 📌 [P0] [ ] Card-168: 系统底层与体外大脑五层抗熵增治理中枢 (Anti-Entropy Memory Evolution, Superseded DAG & Offline Distillation SSOT) ⏳
- **类型**：体外大脑演进 / 知识准入去重 / DAG 版本链 / 离线做梦蒸馏 ｜ **优先级**：🔥 P0 备选
- **核心契约与方案拆解**：
  1. **Layer 1 前门准入查重 (`Ingestion Dedup`)**：余弦相似度 > 0.88 时触发增量合并判别而非盲目重复写入；
  2. **Layer 2 冲突消解与演进链 (`Superseded DAG`)**：新经验推翻旧做法时原子标记 `superseded_by`，检索层物理阻断已失效旧经验；
  3. **Layer 3 时效动力学与差异化半衰期**：永久规范 (1.0)、踩坑经验 (90天)、过程事件 (14天冷归档)；
  4. **Layer 4 夜间离线做梦蒸馏 (`ov_dream`)**：空闲算力驱动，20 条碎片经验蒸馏为 1 条高精纯 Recipe；
  5. **Layer 5 物理快照与后悔药灾备**：治理前强制快照，支持秒级无损回滚。

---

### 🛠️ 第二优先批次：上游性能整并与插件母本自内聚 (P1)

#### 📌 [P1] [ ] Card-205: 上游 Session 消息写入与接口去重读取性能优化整并 (Upstream Session Write IO Optimization & Deduplicated Reading) ⏳
- **吸收内容**：上游 PR #6270 (减少消息写入和 Session 接口重复读取)、PR #6075 (防脏快照 upsert 覆写)、PR #6165 (删除会话时跳过冗余向量清理)。

#### 📌 [P1] [ ] Card-206: 上游 Studio 前端多语言 i18n 补全与 AppleDouble 元数据过滤整并 (Upstream Studio i18n & AppleDouble Metadata Filter) ⏳
- **吸收内容**：上游 PR #6292 (UI 剩余文案全量 i18n 补齐并加入门禁检查)、PR #6316 (代码 Lint 忽略 AppleDouble 元数据)、PR #6215 (Bot 聊天请求透传 Admin Key)。

#### 📌 [P1] [ ] Card-200 ~ Card-202: 插件母本自内聚转接驱动重构与自愈清洗三部曲 ⏳
- **Card-200**: `openviking-memory` 插件母本自内聚转接驱动重构与自愈清洗 (SSOT v2.0.16)
- **Card-201**: `openviking-ops` 插件母本自内聚转接驱动与运维接口标准化 (SSOT v1.0.3)
- **Card-202**: `fleet-mesh` 插件母本自内聚转接驱动与多节点拓扑自适应 (SSOT v1.0.2)
- **统一目标**：彻底拔除 setup.py 中外部桌面路径硬编码，直连母港，清洗历史残留幽灵别名。

#### 📌 [P1] [ ] Card-207: 知识盲区自愈、反思骨架铸造与双轨补全自进化 (Knowledge Deficit Scaffolding) ⏳
- **来源规约**：[`docs/architecture/KNOWLEDGE_DEFICIT_SCAFFOLDING_SPEC.md`](file:///c:/Users/Skl/Desktop/Workspace/coding/OpenVikingStudio/docs/architecture/KNOWLEDGE_DEFICIT_SCAFFOLDING_SPEC.md)
- **核心目标**：当智能体推理捕获知识盲区时，自动反思生成骨架草稿并触发本地/外部知识双轨补全。

#### 📌 [P1] [ ] Card-208: Workspace 分层配置与项目级 Peer 身份持久化 (Workspace Hierarchical Config & SSOT Peer Identity) ⏳
- **来源规约**：[`docs/design/workspace-config-and-peer-source-rfc.md`](file:///c:/Users/Skl/Desktop/Workspace/coding/OpenVikingStudio/docs/design/workspace-config-and-peer-source-rfc.md)
- **核心目标**：支持项目级 `.openviking.toml` 持久化配置，解决跨机器/子目录导致的项目记忆丢失问题。

#### 📌 [P1] [ ] Card-158 ~ Card-160: 生态扩展三部曲 ⏳
- **Card-158**: KeePass 本地凭据保险箱端侧体验与安全体检深化
- **Card-159**: Dify 智能体与工作流中枢插件机制演进与 DSL 备份回滚
- **Card-160**: CPA 跨模型算力协同工兵调度与 429 降级记账闭环

---

### 🛡️ 第三优先批次：观测大屏与常驻自净巡检 (P2)
- **Card-105**: 常驻自净巡检哨兵引擎 (MemoryPuritySentinel Daemon Engine)
- **Card-106**: 入口级实时免疫门禁与血统拦截 (Ingress Anti-Poison Gatekeeper & Lineage Triage)
- **Card-107**: Web Studio 观测大屏自净态势瓦片与手动干预沙箱 (Cockpit Purity Telemetry)
- **Card-108**: FastMCP 工具调用执行切面与异步事件总线发射器 (FastMCP Tool Call Interceptor)
- **Card-109**: UsageAudit 投影层 MCP 规约与脱水脱敏流水线 (Usage Audit MCP Projection)
- **Card-110**: Web Studio 审计大盘 MCP 工具分类与参数详情抽屉 (Request Logs MCP Filter)
