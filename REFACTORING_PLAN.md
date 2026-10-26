# 🗺️ OpenViking 项目主线重构与原子化任务卡片总看板 (Master Task Cards Kanban - SSOT)

> **关联研发大蓝图**：[`BLUEPRINT.md`](file:///home/skloxo/aho/openclaw/project/.agents/BLUEPRINT.md) ｜ **交付全量归档台账**：[`DELIVERY_ARCHIVE.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md) ｜ **通用资产档案库**：[`COMPONENT_AND_WHEEL_INVENTORY.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/docs/architecture/COMPONENT_AND_WHEEL_INVENTORY.md)
> **唯一真相源 (SSOT)**：本文档为 OpenViking 当前活跃的重构规划与就绪待调度的任务矩阵看板。历史所有已验收交付的版本履历已完整归档至 [`DELIVERY_ARCHIVE.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md)。
> **战略外围项目隔离公理**：`Search2API 商业化搜索聚合网关` (`docs/search/SEARCH2API_COMMERCIAL_GATEWAY_SPEC.md`) 确认为独立多账号商业化代理项目，不占用 OpenViking 核心任务大盘卡槽。
> **基线状态**：线上正式部署 **`v1.4.106`** ｜ 当前最新交付 **`v1.7.171`** (代码基线 **`v1.7.153`**) ｜ 分支状态：`main` 已全量同步远程 `origin/main`。

---

## 📌 一、 全景版本发布与里程碑验收矩阵 (Milestone Evolution Matrix)

| 版本 Tag | 任务工单 ID | 模块与重构主题 | 核心治理成果与物理交付物 | 验收状态 |
| :--- | :--- | :--- | :--- | :---: |
| **`v1.7.171`** | **Card-228** | **全域插件开箱即用去硬编码、54项工具越界泄漏封堵与三段式 UserKey 跨端自愈 (Plugin Zero-Hardcode, 36-Tool Strict Isolation & UserKey Header Omission SSOT v2.0.40)** | 1. **彻底封堵 54 项工具越界下发漏洞**：删除服务端 `client_caps.py` 未传 `plugin_id` 时将 3 个插件 (36+16+2=54) 混杂下发的分支，默认严格收敛为 `openviking-memory` (36 项工具)，绝不向非 Admin 用户泄漏 `ops`/`fleet` 工具 Schema；`ov_pre_invocation.py` 显式声明 `?plugin_id=openviking-memory`；废除 `mcp_endpoint.py` 按用户名猜测插件的脆弱逻辑；<br>2. **彻底拔除写死/锁死逻辑，回归用户完全自主配置**：斩除 `server.py` 硬编码 `"antigravity@2080ti"` 与 `setup.py` 硬编码私网域名及跨源码仓嗅探；物理清除源码库残留的 `config.json`/`mcp_config.json` 并在 `pack_all_plugins.py` 强制过滤，保障分发包 100% 纯净无状态；<br>3. **跨端 JS 代理库三段式 UserKey 免 Header 冲突与防串号**：在 `examples/memory-plugin-shared/lib` (`credentials.mjs` / `mcp-proxy-config.mjs` / `mcp-proxy-core.mjs`) 实现环境变量与配置文件凭据源严格隔离，三段式签名 UserKey 自动省略冗余 `X-OpenViking-User`/`X-OpenViking-Account` Header 交由服务端直接验签，根治 `X-OpenViking-User: default` 引发的 HTTP 403 与 144 次重启死循环，并同步至全仓 13 处副本；<br>4. **DSH 配置面板与主进程闭环**：打通 `universal_dsh_client.js` 与 `index.js` 本地环回桥 (`127.0.0.1:19339/ov-dsh-config`) 与 `~/.dsh/openviking-plugins-config.json` 持久化，任意用户填写任意接口地址与 UserKey 即可开箱即用，11/11 Python 单测与 12/12 Node 单测全绿，线上 HTTP 200 与 E2E MCP 36 项工具握手验证通过。 | [x] 已验收通过 ✅ |
| **`v1.7.170`** | **Card-227** | **DSH 冗余组件行物理蒸发、单一独立插件公理与极简座舱直达闭环 (DSH Component Row Evaporation & Single Plugin SSOT v2.0.37)** | 1. **单一独立插件公理 (Single Independent Plugin SSOT)**：确立插件解耦公理——每个插件单一职责、独立开发、独立调试、故障物理隔离，杜绝复合多合一黑盒架构；<br>2. **DSH 原生冗余组件行物理蒸发**：针对 DSH 底层自动渲染的 `<section data-plugin-rows>`（包含的组件 共 1 个 · 1 运行中），在通用适配器模板注入局部 CSS `div[data-plugin-detail] [data-plugin-rows] { display: none !important; }`，彻底抹除冗余噪点；<br>3. **彻底废黜 plugins.row.config 插槽与次级面板**：物理删除 `UniversalDshRowPanel`，移除 `plugins.row.config` 注册，阻断 DSH 渲染次级导航箭头 `>` 与重复套娃页面，实现 DSH 详情页一屏直达 6-Tab 全功能座舱；<br>4. **四方原子版本递增与不可变分发**：全系 7 大插件重新装配，`openviking-memory` 递增至 `v2.0.37`，打包不可变分发包并同频生产目录，4/4 WSL 自动化单测满绿，生产分发包 HTTP 200 验证通过。 | [x] 已验收通过 ✅ |
| **`v1.7.169`** | **Card-226** | **DSH 插件嵌套镜像消除、客户端轻量化透明代理与服务端原子发布闭环 (DSH Anti-Nesting, Light Bridge Stub & Atomic Publishing v2.0.36)** | 1. **DSH 顶层与行级视图解耦**：彻底根除插件详情页与组件行点击重复渲染完整座舱的镜像嵌套缺陷，`plugins.bundle.config` 绑定完整 6 Tab 主座舱，`plugins.row.config` 绑定轻量级桥接运行时存根卡片 (`UniversalDshRowPanel`)；<br>2. **第一性原理与架构纯化**：践行客户端作为极轻透明存根 (Ultralight Proxy Stub)、服务端作为重型引擎 (Server Engine) 架构，热更版本与工具数动态直连，零手写假卡片，全量保真真实 README；<br>3. **全系 7 大插件一键装配流水线**：修复 `assemble_dsh_adapter.py` 变量作用域并全量重新装配，自动注入 `cordis.patch.yml` 满足 DSH 组合包安装硬契约；<br>4. **四方原子版本递增与不可变分发**：`openviking-memory` 升级至 `v2.0.36`，生成分发包并同频生产服务目录；4/4 WSL 自动化单测满绿，生产分发包 HTTP 200 验证通过。 | [x] 已验收通过 ✅ |
| **`v1.7.168`** | **Card-225** | **智能体插件生态自举健壮性加固、UTF-8 字节防腐与规则冗余清退 (Plugin Bootstrapping Robustness, UTF-8 Encoding Guard & Rules Deduplication)** | 1. **DSH package.json 字节修复**：根除 `\xe4\xbd?` 非法多字节破损，`pack_all_plugins.py` 增加严格 UTF-8 校验门禁，杜绝静默吞异常；<br>2. **DSH 运行态自愈落地**：重新打包分发包并热更至 DSH 运行态 node_modules，Node.js 原生 JSON.parse 与 exports 校验 100% 通过；<br>3. **规则单一真相源清退**：全域物理铲除 `memory-ssot.md` 影子副本，仅保留单一 `rules/AGENTS.md`，彻底消灭反重力规则双倍冗余注入；<br>4. **凭据解包自愈闭环**：验证三段式 Key 逆向解包与大小写归一化兜底，彻底消除 `"authorized"` 身份降级断层；安全门禁与 Anti-Demo 100% 满绿。 | [x] 已验收通过 ✅ |
| **`v1.7.168`** | **Card-224** | **智能体插件生态解耦与单一母港统一治理 (Agent Plugins Decoupling, Universal DSH Client Injection & Homeland SSOT - ADR-003)** | 1. **统一物理母港大合并 (Card-PLUG-01)**：彻底铲除反重力与 DSH 双轨维护目录，建立 `packages/plugins/openviking-memory/` 单一真相源，版本对齐 `v2.0.30`，消除冗余；<br>2. **打包期自动注入通用解释器 (Card-PLUG-02)**：确立 `universal_dsh_client.js`，源码保持 0 行前端，打包期自动向 DSH 包注入通用 `client.js`，恢复 5 大 Tab、README 渲染与动态健康探测；<br>3. **服务端扫描感知引擎升级 (Card-PLUG-03)**：`plugin_scanner.py` 优先扫描母港，结构化提取 `integration.channels`，`/api/v1/plugins` 接口透传单一真相；<br>4. **VK Web Studio 抽屉通用解耦 (Card-PLUG-04)**：提供【服务地址】与【User Key】自由输入框，彻底消灭黑盒智能猜测；代码块与命令单向动态插值；严守 NO GREEN EVER 🚫、字号 $\ge 12\text{px}$ 规范；前后端单测 100% 变绿；<br>5. **全链路实机部署验真 (Card-PLUG-05)**：3070 节点部署落地，WSL2 生产环境集中编译构建，四方版本原子同频。 | [x] 已验收通过 ✅ |
| **`v1.7.167`** | **Card-223** | **插件动态感知扫描引擎代理桥回填与后台 MCP 工具计数自愈 (Plugin Scanner Proxy Bridge Tools SSOT)** | 1. 彻底根治 Web Studio 插件中心显示“MCP 0”缺陷：重构 `plugin_scanner.py` 动态感知引擎，增加纯透明代理桥 (Proxy Bridge) 权威算子回填链路；<br>2. 针对纯透明代理桥（如 `openviking-memory` 35 项、`fleet-mesh` 2 项等）无本地 `@mcp.tool` 物理函数的情况，动态回填单一真相源标准工具清单；<br>3. 集成单测 `test_plugin_dynamic_scanner.py` 4/4 满绿通过，全集群 7 大插件 78 项真实算子全部点亮回显就绪。<br>*(Commit: `ad526e252`, Tag: `v1.7.167`)* | [x] 已验收通过 ✅ |
| **`v1.7.166`** | **Card-222** | **反重力 Stdio 桥 Notification 幽灵帧阻断与工具命名双向映射加固 (Notification Silence & Tool Mapping v2.0.27)** | 1. 根治反重力启动报错 `calling "tools/list": invalid request`：封杀向客户端回复无 id 的 Notification 响应，彻底消灭幽灵 `id: null` 乱序报文；<br>2. 落地双向工具名标准化映射：`find` ➔ `openviking_find` 等 10 项核心工具标准化对齐，`tools/call` 逆向无损映射回底层原生 API；<br>3. 安装目录 `openviking-memory/server.py` 同频自举部署，全链路 4 阶生命周期测试 100% 满绿通过。<br>*(Commit: `3037fa6de`, Tag: `v1.7.166`)* | [x] 已验收通过 ✅ |
| **`v1.7.165`** | **Card-221** | **全域插件热更版本双轨显著感知体系、废黜死常数与三端同频对齐 (Omni-Platform Plugin Hot-Reload Version Observability v2.0.27)** | 1. 反重力端：`server.py` 在 `initialize` 握手中显著注入 `v2.0.27 [Kernel: v1.7.164 | 35 Tools Online | Synced]`，IDE 插件面板一眼洞悉；<br>2. DSH 端：`client.js` 拔除历史写死 `2.0.24`，顶部 Header 与连通报告显著并排呈现 `端侧: v2.0.27`、`内核: v1.7.164` 与 `35项工具热更同频` 冰青徽章；<br>3. 服务端：`client_caps.py` 彻底斩除写死常数，动态直连母本 `plugin.json`，返回双轨版本与热更状态；<br>4. Web Studio：详情抽屉 Header 显著并排呈现包版本、服务内核版本与实时热更同频指示；<br>5. WSL 原生单测 `4/4 PASS`，服务平滑重载验证通过。 | [x] 已验收通过 ✅ |
| **`v1.7.164`** | **Card-220** | **反重力插件服务端原生驱动纯透明 MCP 代理架构、战地工具完全体与全系规约沉淀 (Antigravity Pure MCP Proxy Architecture v2.0.27)** | 1. 彻底废黜反重力端本地手写适配器模式，`server.py` 重构为 Stdio ➔ Streamable-HTTP (`/mcp`) 纯透明代理桥（代码量由 425 行锐减至 180 行）；<br>2. 工具集由 26 项跃升为服务端单一真实源 (SSOT) 驱动的 35 项战地工具完全体，两端完全同频且零 404/405；<br>3. 物理注入鉴权上下文三元组 (`Authorization`, `X-OpenViking-User`, `X-OpenViking-Account`) 与优雅 JSON-RPC 错误降级；<br>4. 沉淀全系架构规约 `docs/guides/ANTIGRAVITY_PURE_MCP_PROXY_SPEC.md`，确立未来全系插件开发法典；<br>5. 发布 `v2.0.27` 全系插件并生成不可变分发包，线上对齐通过。 | [x] 已验收通过 ✅ |
| **`v1.7.163`** | **Card-219** | **服务端原生 MCP 模块 OpenVikingService.find 缺失根治、单一真相源脱敏引擎归拢与芒格逆向对抗加固 (Server MCP find & Masking)** | 1. 在 `OpenVikingService` 增加顶层 `find` 异步快捷委托方法，彻底消除 `AttributeError`；<br>2. 纠偏 `mcp_endpoint.py` 内部 `openviking_code_search` 与 `openviking_smart_read` 的直接调用为 `service.search.find`；<br>3. 彻底归拢脱敏引擎至 `openviking/privacy/privacy_masker.py` 单一真相源，`openviking/service/privacy_masker.py` 改为直接门面引用；<br>4. 敏感正则精细化加固（API Key 兼容 16 字符短 Key，密码支持键值与负向预查排除语法关键字，严防破坏 `if password is None:`）；<br>5. 编写针对性单测 `4/4 passed in 0.09s` 满绿，WSL2 生产环境平滑重载实测通过。 | [x] 已验收通过 ✅ |
| **`v1.7.162`** | **Card-218** | **反重力端契约对齐瘦身、幽灵工具物理下线与沙盒管道阻塞根除 (Antigravity Contract Parity & Pruning v2.0.26)** | 1. 修正 `server.py` 中 4 大核心工具传参 Bug（`smart_read` 剔除 extra 字段、`link/unlink` 纠正为 `from_uri/to_uris`、`auto_onboard_skills` 补齐正文上传）；<br>2. 物理下线 10 项 404/405 幽灵工具，全量保留 26 项真实绿灯工具；<br>3. 修复 `ov_sandbox_guard.py` 的阻塞式 `sys.stdin.read()` 为流式安全 `sys.stdin.readline()`；<br>4. 发布全系插件 `v2.0.26`，生成不可变分发包并完成部署，26/26 战地工具物理打靶 100% 全绿。 | [x] 已验收通过 ✅ |
| **`v1.7.161`** | **Card-217** | **DSH 插件端点解析降级、宿主路径自适应与全系插件版本单点真相 (Plugin Ecosystem Parity v2.0.25)** | 1. 修复 DSH 插件 `index.js` 中 `getEndpoint()` 缺失凭据 fallback 导致 MCP 工具未挂载的 P0 致命缺陷，打通 `resolveOpenVikingCredentials` 多级降级；<br>2. 消除硬编码路径 `'C:\\Users\\Skl'`，改用 `os.homedir()` 确保跨机便携；<br>3. 废黜 `config.mjs` 硬编码版本，动态直连 `package.json`；清理 `client.js` 冗余插槽注册；<br>4. 发布插件 `v2.0.25`，生成不可变分发包并完成线上部署 (HTTP 200 验证)。 | [x] 已验收通过 ✅ |
| **`v1.7.160`** | **Card-216** | **插件详情抽屉与反重力原生孪生体验像素级对齐 (Antigravity Digital Twin Parity)** | 1. 彻底拔除 README 中冗余源码挂载章节，并入专门“接入指引”Tab，README 回归纯粹架构单一真相源；<br>2. 像素级对齐反重力原生 Tab 切换架构 (概览、技能、MCP、钩子、规则、接入指引 6 大 Tab 解耦)；<br>3. 动态渲染 suggestedPrompts 卡片与 rules 规约文件；<br>4. 全系 7 大插件通用互通，集中构建部署验收通过。 | [x] 已验收通过 ✅ |
| **`v1.7.150`** | **Card-203** | **上游 Storage 写入锁协调提前消费与跨进程恢复整并 (Upstream Storage Lock)** | 吸收 upstream PR #6300 锁泄漏修复、#6281 跨进程自愈、#6298 大小写冲突规避，6/6 专项单测全绿。 | [x] 已验收通过 ✅ |
| **`v1.7.153`** | **Card-196** | **生活与研发物理隔离 (Privacy Isolation)** | 家庭高隐私资产物理移入独立目录，斩除研发库临时私有目录，实现研发与生活物理隔离。 | [x] 已验收通过 ✅ |
| **`v1.7.154`** | **Card-197** | **18 核心母包收敛与平权对齐 (Bundles Convergence)** | 3070 与 2080 平权对等，物理铲除 4 大无关大包 (115场景)，母包收敛至纯粹 18 个。 | [x] 已验收通过 ✅ |
| **`v1.7.155`** | **Card-198** | **端侧极简瘦身与三层法典解耦 (3-Tier AGENTS Law)** | 切除端侧重复技能，全局保留 8 宿主核心骨架，确立单文件 ≤500 行硬上限与 100~300 行甜点区。 | [x] 已验收通过 ✅ |
| **`v1.7.159`** | **Card-199** | **Workspace 超级航母重构与双 Junction (Super-Carrier)** | 建立 Workspace 超级航母，提纯 00_Common 六大通识，双 Junction 零中断保活，死链清零。 | [x] 已验收通过 ✅ |
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
| **`v1.7.151`** | **Card-204** | **上游 Gateway 缓存遥测增强与 DSH 无工具请求防重复召回整并 (Upstream Gateway)** | 吸收 PR #6295 DSH 辅助防召回、#6026 回复增量哈希与 SSE 批量分帧、#6267 缓存告警闭环，61/61 测试全绿。 | [x] 已验收通过 ✅ |
| **`v1.7.152`** | **Card-205** | **上游 Session 消息写入与接口去重读取性能优化整并 (Upstream Session Perf)** | 吸收 upstream PR #6270 消息写入与 Session 重复读取优化、#6075 防脏快照 upsert、#6165 rm(no_vector) 极速旁路，6/6 专项测试全绿。 | [x] 已验收通过 ✅ |
| **`v1.7.153`** | **Card-206** | **上游 Studio 前端多语言 i18n 补全与 AppleDouble 元数据过滤整并 (Upstream Studio)** | 吸收 upstream PR #6292 全域多语言 i18n 补齐、#6316 AppleDouble 元数据过滤、#6215 Key 透传，45/45 测试全绿。 | [x] 已验收通过 ✅ |
| **`v1.7.154`** | **Card-209** | **上游 Storage 存储引擎、Session 瞬态自愈与向量批次控制整并 (Upstream Storage & Session)** | 吸收 upstream PR #6398 瞬态内存读取重试、#6395 多写元数据隐藏、#6259 向量批次上界 (1024)、#6325 O(1) 账号探测，6/6 专项测试全绿。 | [x] 已验收通过 ✅ |
| **`v1.7.155`** | **Card-210** | **上游网关、服务端鉴权与 Windows 编译沙箱指令转译整并 (Upstream Auth & Windows Transpile)** | 吸收 upstream PR #6396 受信任用户组 Header、#6254 OIDC 斜杠容错、#6306 Gateway 字段容错、#6372 Windows POSIX 指令转译、#6376 编译绝对路径，7/7 专项测试全绿。 | [x] 已验收通过 ✅ |
| **`v1.7.159`** | **Card-211** | **上游模型体系、经验归因保真与 CLI 网络原生根因透传整并 (Upstream Models & Native CLI)** | 吸收 upstream PR #6365 经验显式读取归因、#6383 Gemini Embedding 2、#6348 Seed 2.1 Lite VLM、#6361 原生 CA 信任、#6312 报错根因透传、#6053 别名文档，16/16 专项单测全绿。 | [x] 已验收通过 ✅ |
| **`v1.7.160`** | **Card-212** | **上游 Web Studio 连接架构重构与受信任身份目录解耦整并 (Upstream Studio Identity Directory)** | 吸收 upstream PR #6308 解耦独立组件 setup-identity-directory，防冲刷保护，物理斩杀死代码 current-user-menu，对齐中英文 i18n，8/8 专项单测与 29/29 前端单测全绿。 | [x] 已验收通过 ✅ |
| **`待排期`** | **Card-213** | **上游外部客户端插件生态协议对齐与时间衰减整并 (Upstream External Plugins Ecosystem)** | 吸收 upstream PR #6390 召回时间衰减、#5689 claim 时间戳刷新、#5660 Codex PreCompact 身份、#6381 Pi 分支捕获、#6342 LangChain Store。 | [ ] 待排期迭代 ⏳ |
| **`v1.7.157`** | **Card-200** | **`openviking-memory` 插件母本自内聚转接驱动重构与自愈清洗 (Antigravity Memory Proxy Stub & SSOT v2.0.16)** | 1. 彻底拔除 setup.py 中外部桌面路径硬编码与 candidate_scripts 扫描，插件目录自带自内聚 server.py 独立转接驱动；<br>2. 统一多机物理契约：2080Ti 本地与 3070 远程代码 100% 相同，唯一变量仅为 OPENVIKING_API；<br>3. 强制自愈清洗幽灵：安装与注册逻辑强制 pop("openviking", None)，消灭历史幽灵条目；<br>4. 版本原子递增：plugin.json 与 setup.py 同步自增至 v2.0.16，全景生态健康测试 100% 满绿通过。<br>*(Commit: `06dc379d0`, Tag: `v1.7.157`)* | [x] 已验收通过 ✅ |
| **`v1.7.158`** | **Card-201** | **插件与插件中心解耦、动态感知引擎与双端 README 一源互通 (Decoupled Plugin Perception & SSOT README)** | 1. 插件独立解耦托管于 integrations/antigravity，插件中心动态扫描自动感知；<br>2. 真实 AST 静态解析 server.py 工具，彻底斩除虚构假工具与版本断层；<br>3. 抽屉直连渲染原生 README.md，与 Antigravity 详情页 100% 互通共享单一真相源；<br>4. 自动化视网膜门禁全绿，前端生产集中编译生效。 | [x] 已验收通过 ✅ |
| **`待排期`** | **Card-202** | **`fleet-mesh` 插件母本自内聚转接驱动与多节点拓扑自适应 (SSOT v1.0.2)** | 拔除路径依赖，自适应探测 2080Ti/3070 节点，版本原子递增。 | [ ] 待排期迭代 ⏳ |
| **`v1.7.161`** | **Card-203** | **`keepass-vault` 本地高安全凭据保险箱完全体重构与标杆化落地 (Credential SSOT v1.2.1)** | 1. 统一母港 packages/plugins/keepass-vault 四位一体落盘；<br>2. FastMCP 9 大算子与 stdin 安全管道传递主密码；<br>3. 写前物理防抖快照 Hook (40ms 冷启动)；<br>4. 查库第一公理潜意识与 setup.py 双轨自举；<br>5. 不可变打包与 sync_all_plugins 100% 对齐，5/5 专项单测全绿。 | [x] 已验收通过 ✅ |

| **`待排期`** | **Card-207** | **知识盲区自愈、反思骨架铸造与双轨补全自进化 (Knowledge Deficit Scaffolding)** | 推理缺口捕获，自动生成反思骨架草稿，双轨触发本地/外部知识补全。 | [ ] 待排期迭代 ⏳ |
| **`待排期`** | **Card-208** | **Workspace 分层配置与项目级 Peer 身份持久化 (Workspace Config & SSOT)** | 支持 `.openviking.toml` 项目级配置固化，解决跨设备/子目录迁移导致的项目记忆失效。 | [ ] 待排期迭代 ⏳ |
| **`v1.7.161`** | **Card-158** | **KeePass 本地凭据保险箱端侧体验与安全体检深化 (KeePass Local Vault)** | 由 Card-203 统一吸收完成四位一体与母港重构。 | [x] 已吸收通过 ✅ |
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

#### 📌 [P0] [x] Card-216: 插件详情抽屉与反重力原生孪生体验像素级对齐 (Antigravity Digital Twin Parity v1.7.160) ✅
- **类型**：Web Studio 插件详情抽屉 / 单一真相源 (SSOT) 对齐 / 交互体验精纯化 ｜ **优先级**：🔥 P0 ｜ **交付版本**：`v1.7.160`
- **核心治理成果与物理交付物**：
  1. **单一真相源 (SSOT) 彻底落地**：Web Studio 抽屉与反重力（Google Antigravity IDE/Desktop）插件详情页 100% 物理复用同一套 `README.md` 与 `plugin.json`，两端数据完全对齐，彻底斩除“做两套文档”的代码与认知负债；
  2. **README 核心提纯与切除打断**：精简提纯 `openviking-memory` 与 `openviking-ops` 的 `README.md`，拔除冗长手写算子列表与终端安装命令，专注文档自身定位；
  3. **建议交互提示词 (suggestedPrompts) 构件**：新增 `plugin-prompts-section.tsx`，动态直连 `plugin.suggested_prompts`，支持一键点击复制与毫秒级反馈，1:1 对齐反重力原生交互体验；
  4. **解耦可折叠技术附录**：将极速开箱命令 (`PluginQuickstartSection`)、MCP 原子算子全景、配套认知导轨、Hook 守卫与运行时配置统一整编为底部可折叠附录，默认折叠，按需展开；
  5. **全系 7 大插件通用互通**：覆盖 `openviking-memory`, `openviking-ops`, `agent-circuit-breaker`, `keepass-vault`, `fleet-mesh`, `dify`, `cpa-squad`，经浏览器实操全面打靶验收通过；
  6. **强类型抽离与命令数据驱动**：在 `plugin-types.ts` 中单独定义 `DshPluginBridgeInfo`、`DshPackageMapping` 与 `QuickstartCommandItem`，消除组件内匿名弱类型与冗余模板代码，单文件严格保持 177 行黄金甜点区。

#### 📌 [P0] [x] Card-203: 上游 Storage 写入锁协调提前消费与跨进程恢复整并 (Upstream Storage Lock Leak & Recovery Alignment) ✅
- **类型**：底层存储加固 / 并发锁治理 / 跨进程恢复 ｜ **优先级**：🔥 P0 ｜ **交付版本**：`v1.7.150`
- **核心治理成果与物理交付物**：
  1. **吸收上游 PR #6300 (c89efb7c3)**：修复写入协调消息提前消费导致的锁泄漏；`_finish_write_lock` 先交接写入锁再发布提交完成标记，统一单文件与批量写入清理接入 `run_to_completion`，消除调度间隙锁泄漏；
  2. **吸收上游 PR #6281 (c476a3184)**：整并跨进程崩溃自愈与残留锁清理 (`cross process recovery`)，确保进程意外中止后 PathLock 自动释放；
  3. **吸收上游 PR #6298 (b51cba425)**：切除 `LocalParseOutputStore` 中大小写敏感冲突误报，允许不同大小写文件名在本地工件中共存；
  4. **视网膜单测**：编写针对性单元测试 `tests/storage/test_card203_storage_lock_leak_and_recovery.py`，6/6 专项单测全绿 (0.78s)，回归测试 `test_content_write_processing_mode.py` 7/7 全绿，安全扫描 0 泄露，打标 Tag `v1.7.150`。

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
     - 严格遵循 **NO GREEN EVER 🚫**，字号硬下限 $\ge 12\text{px}$ (`text-xs`)，单文件 100~300 行黄金甜点区；
  5. **视网膜单测与门禁**：WSL 原生 Pytest 单测变绿，Vitest 前端单测变绿。

#### 📌 [P0] [x] Card-204: 上游 Gateway 缓存遥测增强与 DSH 无工具请求防重复召回整并 (Upstream Gateway Cache Telemetry & Anti-Duplicate Recall) ✅
- **类型**：网关吞吐优化 / 记忆召回防抖 / DSH 协议治理 ｜ **优先级**：🔥 P0 ｜ **交付版本**：`v1.7.151`
- **核心治理成果与物理交付物**：
  1. **吸收上游 PR #6295 (e855796c8)**：针对 DSH 会话标题生成与已发工具会话的单轮侧向请求，自动识别并拦截 `auxiliary`，阻断 0 价值记忆召回与幽灵 Session 污染；剥离 3 类诊断与运行上下文噪音；统一工具参数紧凑化 JSON 解析；
  2. **吸收上游 PR #6026 (26fa00b91)**：落地回复增量哈希 (`reply_chain`) 根除 140k 上下文全文重复哈希的 CPU 损耗，落地 `SSEDecoder` 批量分帧与就地字符串拼接 (`safe_append_delta`)；
  3. **吸收上游 PR #6267 (27db44123) 闭环**：在 `proxy.py` 成功与异常路径打通 `_report_telemetry`，物理接入 `_GATEWAY_EVENT_BUFFER`，精准驱动长对话连续 3 次 Miss 告警；
  4. **视网膜单测**：编写专项测试 `tests/gateway/test_card204_gateway_telemetry_and_anti_duplicate_recall.py` (9/9 全绿)，全量 61/61 项网关单测 3.98s 满绿通过，安全扫描 0 泄露，打标 Tag `v1.7.151`。

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

#### 📌 [P1] [x] Card-205: 上游 Session 消息写入与接口去重读取性能优化整并 (Upstream Session Write IO Optimization & Deduplicated Reading v1.7.152) ✅
- **吸收内容与物理交付物**：
  1. **极速删除旁路 (PR #6165)**：`VikingFS.rm` 增加 `no_vector: bool = False` 极速旁路，删除会话目录与临时文件时短路目录遍历与向量库清理；`SessionService.delete` 废黜 `self.get()` 全量反序列化，采用 `self.session(ctx, session_id).exists()` 轻量探测；
  2. **热读去重与元数据直出 (PR #6270)**：`record_used` 路由统一切换为 `service.sessions.open()` 热读去重，杜绝重复反序列化；
  3. **防脏快照覆写加固 (PR #6075)**：`MemoryUpdater.apply_operations` 新鲜读取失败时严禁回退到陈旧快照执行覆写，阻断脏数据落盘；
  4. **视网膜单测与门禁**：编写专项测试 `tests/service/test_card205_session_io_and_delete_perf.py` (6/6 全绿)，全量 Session 测试回归全绿，安全扫描 0 泄露，打标 Tag `v1.7.152`。

#### 📌 [P1] [x] Card-206: 上游 Studio 前端多语言 i18n 补全与 AppleDouble 元数据过滤整并 (Upstream Studio i18n & AppleDouble Metadata Filter v1.7.153) ✅
- **吸收内容与物理交付物**：
  1. **AppleDouble 过滤与 i18n ESLint 规则插件 (PR #6316 & #6292)**：在 `eslint.config.js` 增加 `'**/._*'` 屏蔽 macOS 影子元数据；落地 `script/eslint-i18n.mjs`（`no-literal-message` 与 `explicit-locale`），并配合 `script/eslint-i18n.test.ts` (38/38 通过)；
  2. **Bot 凭据鉴权优先级对齐 (PR #6215)**：`src/lib/sessions/bot-chat-api.ts` 修正 `buildFetchHeaders()` 优先级为 `conn.apiKey || conn.adminApiKey`，并补充 `src/lib/sessions/bot-chat-api.test.ts` (2/2 通过)；
  3. **studio 命名空间与格式化基础设施 (PR #6292)**：建立 `src/i18n/format.ts` (`formatNumber`, `formatDateTime`)、`src/i18n/editor-phrases.ts`，落地 `src/i18n/locales/zh-CN/studio.ts` 与 `en/studio.ts` (70+ 条目)，并在 `index.ts` 监听同步 `document.documentElement.lang`；
  4. **业务组件多语言净化**：`clipboard.ts`、`errors.ts`、`code-editor.tsx`、`task-detail-sheet.tsx`、`image-viewer.tsx`、`markdown-renderer.tsx` 消除裸写硬编码；
  5. **视网膜门禁全绿**：`i18n.test.ts` (5/5 通过) 严格校验双语 Key 100% 对齐与插值占位符一致性，前端与后端单测 45/45 全绿，打标 Tag `v1.7.153`。

#### 📌 [P1] [x] Card-209: 上游 Storage 存储引擎、Session 瞬态自愈与向量批次控制整并 (Upstream Storage, Transient Memory & Vector Replay v1.7.154) ✅
- **吸收内容与物理交付物**：
  1. **瞬态读取重试 (PR #6398 / c0e35a54c)**：`openviking/session/memory/memory_updater.py` 封装 `read_fresh_memory(uri)` 并接入 `retry_async(max_retries=1, base_delay=0.1)` 瞬态重试；`MemoryReadError.retryable` 覆盖网络/AGFS/IO瞬态；`session.py` 提取重试判定改为 `not isinstance(error, MemoryUpdateError) and is_retryable_api_error(error)` 杜绝昂贵重提取；
  2. **多写元数据隐藏 (PR #6395 / c133b9467)**：`crates/ragfs/src/core/internal_names.rs` 与 `mountable.rs` 在挂载层精准隐藏 `.redirect.json` 与 `.sync_log.json`，补充 `is_multiwrite_internal_path` 与单元测试；
  3. **向量重放批次上界 (PR #6259 / aa49650a2)**：`openviking/storage/vectordb/collection/local_collection.py` 引入 `_RECOVERY_BATCH_SIZE = 1024`，在 `PersistCollection._recover_index` 中以 1024 为批次上限流式回放增量记录，消除海量 DeltaRecord 的内存积压；
  4. **账号轻量存在性端点 (PR #6325 / 102ff5925)**：`openviking/server/routers/admin.py` 补齐 `GET /api/v1/admin/accounts/{account_id}` 与 `GET /api/v1/admin/accounts/{account_id}/users/{user_id}` 零凭据点读探测端点，SDK (Python/Go/TS) 对应方法对齐；
  5. **视网膜单测与门禁**：编写专属单元测试 `tests/service/test_card209_storage_session_and_vector_replay.py`，6/6 专项单测全绿 (1.29s)，Session 提交与向量恢复回归测试套件全绿，安全扫描 0 泄露，打标 Tag `v1.7.154`。

#### 📌 [P1] [x] Card-210: 上游网关、服务端鉴权与 Windows 编译沙箱指令转译整并 (Upstream Gateway, Trusted Auth & Windows POSIX Transpile v1.7.155) ✅
- **吸收内容与物理交付物**：
  1. **网关类型容错 (PR #6306 / d9db19ab6)**：`openviking_gateway/protocols.py` 引入 `string_type` 防御提取函数，对客户端历史消息中嵌套的非字符串 `type`（如 JSON Schema 字典）进行优雅容错，彻底消除 `unhashable type` 异常与静默记忆丢失；
  2. **受信任用户组 Header (PR #6396 / ce42a166b)**：`openviking/server/auth/plugins/trusted.py` 支持 `X-OpenViking-Groups` header 解析与去重，在 `_build_request_context` 中优先注入 `RequestContext.group_ids`，打通企业级外部网关用户组穿透；
  3. **OIDC 斜杠容错 (PR #6254 / 03b9aecfe)**：`oidc_config.py` 保留精确的 issuer 配置，`plugins/oidc.py` 在 Discovery URL 构造时精准 strip 尾部斜杠，解决 Authentik/Auth0 等主流 IdP 握手兼容性；
  4. **Windows POSIX 转译 (PR #6372 / feb051c70)**：`bot/vikingbot/sandbox/backends/direct.py` 内置轻量级 POSIX 转译器，原生支持 `mkdir -p`、`mkdir -m 700`、`chmod 600` 与环境变量剥离，配套 `test_direct_windows_posix.py` (5/5 满绿)；
  5. **编译工作区绝对路径 (PR #6376 / #6387 / 6545bb2a4)**：`bot/vikingbot/compile/sandbox.py` 在 `CompileSandboxManager` 初始化时强制解析为绝对物理路径，根除相对路径启动导致的 `ENOENT` 异常；
  6. **视网膜单测与门禁**：编写专属单元测试 `tests/service/test_card210_gateway_auth_and_posix_transpile.py`，7/7 专项单测全绿 (0.19s)，安全扫描 0 泄露，打标 Tag `v1.7.155`。

#### 📌 [P1] [x] Card-211: 上游模型体系、经验归因保真与 CLI 网络原生根因透传整并 (Upstream Models, Evolution Attribution & Native CLI v1.7.159) ✅
- **吸收内容与物理契约**：
  1. **经验读取归因保真 (PR #6365 / a07c02cd2)**：`openviking/session/memory/experience_lineage.py` 严格过滤带 Query/Fragment 脏 URI 并正确 resolve 相对与波浪号别名，支持插件命名空间工具提取；
  2. **Gemini Embedding 2 适配 (PR #6383 / b5a389245)**：`openviking/models/embedder/gemini_embedders.py` 支持官方稳定 `gemini-embedding-2` 模型、3072 MRL 向量与文本任务指令前缀格式；
  3. **默认 VLM 升级 (PR #6348 / 1455cb128)**：`openviking-server init` 向导与配置样例默认多模态模型升级为火山引擎 `doubao-seed-2.1-lite`、按量版 `doubao-seed-2-1-lite-260915` 与 BytePlus `seed-2-0-lite-260428`；
  4. **CLI 系统原生 CA 信任与报错透传 (PR #6361 / 5d1027468 & PR #6312 / a9cb3b4d4)**：`crates/ov_cli` 原生信任系统 CA 证书，网络失败通过 `with_sources` 显式透传底层物理根因与证书链详情；
  5. **LocalFS 别名行为规约 (PR #6053 / e6e5f7d2f)**：规约并固化大小写不敏感别名与 ACL 权限边界文档；
  6. **视网膜单测与门禁**：编写专属单元测试 `tests/service/test_card211_models_and_cli_attribution.py`，16/16 专项与 Lineage 单测全绿 (0.16s)，114/114 setup wizard 单测全绿，打标 Tag `v1.7.159`。

#### 📌 [P1] [x] Card-212: 上游 Web Studio 连接架构重构与受信任身份目录解耦整并 (Upstream Studio Connection & Identity Directory) ✅
- **吸收内容与物理契约**：
  1. **连接切换架构重构 (PR #6308 / 0a2578e7e)**：解耦独立组件 `setup-identity-directory.tsx` (245行，黄金甜点区)，提供基于 Admin Key 的多租户与用户直观探测点选；
  2. **身份同步防冲刷保护**：在 `app-connection-utils.ts` 中拦截 control-key 占位符对已有数据用户的冲刷，保持受信任数据身份稳定性；
  3. **废黜旧版 Header 切换器与死代码物理清理**：彻底删除孤儿组件 `current-user-menu.tsx` 及其单测，更新 `COMPONENT_AND_WHEEL_INVENTORY.md` 活态资产档案库与门禁；
  4. **中英文双语 i18n 100% 同步**：在 `zh-CN/settings.ts` 与 `en/settings.ts` 中补齐身份目录全部多语言键值；
  5. **铁律与防线约束**：严格遵守 **NO GREEN EVER 🚫** 冰青湛蓝语义色、字号硬下限严格对齐 `text-xs (12px)`、单文件 ≤500 行硬上限；
  6. **视网膜单测与集中构建**：编写专属单元测试 `tests/service/test_card212_studio_connection_and_identity.py` (8/8 PASS)，29/29 前端单测满绿，生产构建集中封板，打标 Tag `v1.7.160`。*(Commit: 待提交, Tag: `v1.7.160`)*

#### 📌 [P1] [ ] Card-213: 上游外部客户端插件生态协议对齐与时间衰减整并 (Upstream External Plugins Ecosystem & Recall Decay) ⏳
- **吸收内容与物理契约**：
  1. **召回配置时间衰减窗口 (PR #6390 / 3edc0b7f7)**：在 recall 配置中支持传入事件时间衰减半衰期 (`time-decay window`)；
  2. **增量重放 claim 刷新 (PR #5689 / f8d36722a)**：刷新 pending replay claim 时间戳，防止租约超时误判；
  3. **Codex PreCompact 身份保持 (PR #5660 / 7355b926e)**：Codex 插件压缩阶段保留规范化 PreCompact 会话身份；
  4. **Pi 与 LangChain 生态同步 (PR #6381 / 401c1f7ef & PR #6342 / 6ec6116b7)**：Pi 插件分支发散捕获，LangChain Store 读取与命名空间发现；
  5. **Claude-Code 测试上下文预算 (PR #6353 / 0902110a0)**：控制测试 fixture 严格处于上下文预算以内。
#### 📌 [P0] [x] Card-218: 反重力端契约对齐瘦身、幽灵工具物理下线与沙盒管道阻塞根除 (Antigravity Contract Parity & Pruning v2.0.26) ✅
- **治理成果与物理交付物**：
  1. **修正 4 大核心工具传参契约**：`openviking_smart_read` 剔除 extra 字段禁止字段，`openviking_link` 纠正为 `from_uri`/`to_uris` 列表，`openviking_unlink` 纠正为 `from_uri`/`to_uri`，`openviking_auto_onboard_skills` 支持读取本地正文；
  2. **物理下线 10 项 404/405 幽灵工具**：斩除服务端未挂载路由的 10 项死工具，保留真实可调用的 26 项核心工具；
  3. **沙盒守卫流式安全改造**：`ov_sandbox_guard.py` 废黜阻塞式 `sys.stdin.read()`，改用非阻塞 `sys.stdin.readline()`；
  4. **全链路打靶与分发**：发布全系插件 `v2.0.26`，`test_26_tools.py` 物理打靶 26/26 项工具 100% 全绿，生成不可变分发包并部署上线 (HTTP 200)。<br>*(Commit: `f2befa274`, Tag: `v1.7.162`)*

#### 📌 [P0] [x] Card-223: 插件动态感知扫描引擎代理桥回填与后台 MCP 工具计数自愈 (Plugin Scanner Proxy Bridge Tools SSOT v1.7.167) ✅
- **治理成果与物理交付物**：
  1. **代理桥权威算子回填引擎**：在 `openviking/service/plugin_scanner.py` 中引入 `resolve_builtin_tools(plugin_id)`，针对纯透明代理桥（如 `openviking-memory`）无本地 `@mcp.tool` 函数的物理特性，自动从单一真相源回填 35 项核心战地工具定义与 `openviking_*` 标准化命名，彻底根治 Web Studio 插件中心显示“MCP 0”缺陷；
  2. **生态与多插件通用覆盖**：支持 `fleet-mesh`、`dify`、`cpa-squad` 等无本地独立 `server.py` 插件的权威工具定义回填；
  3. **集成单测与系统门禁满绿**：更新 `tests/integration/test_plugin_dynamic_scanner.py`，WSL 原生 Pytest 单测 `4/4 passed in 2.64s` 100% 满绿通过；
  4. **全链路平滑生效**：WSL 原生服务平滑重载，线上与本地 `/api/v1/plugins` 探针一手实测通过，7 个插件 78 项真实算子全部点亮就绪。<br>*(Commit: `ad526e252`, Tag: `v1.7.167`)*

#### 📌 [P0] [x] Card-222: 反重力 Stdio 桥 Notification 幽灵帧阻断与工具命名双向映射加固 (Notification Silence & Tool Mapping v2.0.27) ✅
- **治理成果与物理交付物**：
  1. **Notification 门禁与协议合规**：遵循 JSON-RPC 2.0 规范，对无 `id` 的通知对象（如 `notifications/initialized`）静默发送给 `/mcp`，绝对禁止向 `sys.stdout` 输出任何响应帧，彻底根治反重力 IDE 客户端在 `tools/list` 读到 `id: null` 导致的 `invalid request` 致命启动崩溃；
  2. **双向工具名规范化映射**：引入 `SERVER_TO_CLIENT_TOOLS` 与 `CLIENT_TO_SERVER_TOOLS`，在 `tools/list` 时将 `find`, `search`, `read`, `list`, `tree`, `remember`, `write`, `grep`, `glob`, `health` 规范化为 `openviking_*`，在 `tools/call` 时自动逆向映射回服务端底层名称，实现端到端 100% 契约无缝衔接；
  3. **生命周期打靶全绿**：编写 `scratch/simulate_ide_flow.py`，完整模拟 IDE 发起 `initialize` ➔ `notifications/initialized` ➔ `tools/list` ➔ `tools/call`，全流程 4 阶段测试 100% 满绿通过；
  4. **全自动级联部署**：同步刷新 `C:\Users\Skl\.gemini\config\plugins\openviking-memory\server.py` 与不可变分发包。<br>*(Commit: `3037fa6de`, Tag: `v1.7.166`)*

#### 📌 [P0] [x] Card-221: 全域插件热更版本双轨显著感知体系、废黜死常数与三端同频对齐 (Omni-Platform Hot-Reload Observability v2.0.27) ✅
- **治理成果与物理交付物**：
  1. **反重力端 initialize 握手增强**：`server.py` 拦截并装饰 `initialize` 返回的 `serverInfo`，显著输出 `v2.0.27 [Kernel: v1.7.164 | 35 Tools Online | Synced]`，IDE 界面直观感知热更状态；
  2. **DSH 抽屉双轨版本徽章**：`client.js` 彻底切除写死 `2.0.24` 常量，以母本动态版本为唯一真相源，Header 与连通测试报告卡片显著呈现【端侧适配器版本】、【云端内核版本】与【35 项战地工具热更同频】冰青胶囊；
  3. **服务端路由单一真相源治理**：`client_caps.py` 与 `client_caps_constants.py` 引入 `get_plugin_manifest_version`，物理斩除 `2.0.16` / `1.0.1` 等静态死常数，返回 `kernel_version`、`plugin_version` 与 `hot_reload_synced: True`；单文件行数优化至 455 行安全红线以内；
  4. **Web Studio 抽屉对齐**：`plugin-detail-drawer.tsx` Header 并排挂载 `包: v{plugin.version}`、`内核: v{versionDetails.version}` 与 `● {tools.length} 工具热更同频` 徽章；
  5. **门禁与测试**：WSL 原生 Pytest 单测 `4/4 passed in 0.08s` 满绿，全系插件重新打包落盘，WSL 原生服务平滑重载校验通过。<br>*(Commit: `24f73849a`, Tag: `v1.7.165`)*

#### 📌 [P0] [x] Card-220: 反重力插件服务端原生驱动纯透明 MCP 代理架构、战地工具完全体与全系规约沉淀 (Pure MCP Proxy Architecture v2.0.27) ✅
- **治理成果与物理交付物**：
  1. **纯透明代理桥架构落地**：彻底废黜反重力端本地手写适配器与冗余 REST 组装，重构 `integrations/antigravity/openviking-memory/server.py` 为纯透明 Stdio-to-Streamable-HTTP 代理桥（代码量从 425 行锐减至 180 行，瘦身 58%）；
  2. **战地工具 35 项完全体打通**：工具定义与分发 100% 移交服务端单一真实源 (SSOT)，工具数量从 26 项跃升至 35 项，彻底抹平与 DSH 端的协议割裂且零 404/405；
  3. **上下文三元组与防爆守卫**：代理层统一物理注入 `Authorization`, `X-OpenViking-User`, `X-OpenViking-Account`，网络离线时返回标准 JSON-RPC -32603 错误，绝不导致宿主崩溃；
  4. **标准工程规约沉淀**：结晶落盘 `docs/guides/ANTIGRAVITY_PURE_MCP_PROXY_SPEC.md`，确立未来全系插件开发标准与统一范本；
  5. **版本双写与不可变包分发**：四方原子同步至 `v2.0.27`，生成不可变分发包 `openviking-memory-2.0.27.tgz` 与 `dsh-plugin-openviking-memory-2.0.27.tgz`，探针实测 PASS。<br>*(Commit: `ccd0ec06c`, Tag: `v1.7.164`)*

#### 📌 [P0] [x] Card-219: 服务端原生 MCP 模块 OpenVikingService.find 缺失根治与 privacy_mask 真实脱敏加固 (Server MCP find & Masking) ✅
- **治理成果与物理交付物**：
  1. **服务端 find 入口双重兜底**：`OpenVikingService` 增加顶层 `find` 异步快捷委托，彻底消除 `AttributeError: 'OpenVikingService' object has no attribute 'find'`；同时纠偏 `mcp_endpoint.py` 内部两个直接调用点为 `service.search.find`；
  2. **脱敏引擎统一归拢 (SSOT)**：彻底归拢脱敏引擎至 `openviking/privacy/privacy_masker.py` 单一真相源，`openviking/service/privacy_masker.py` 转化为统一门面，消灭双份实现与功能裂解；
  3. **高精度敏感模式与芒格逆向守卫**：API Key 兼容 16 字符测试短 Key（`sk-1234567890abcdef`），密码支持配置键值与自然语言语境，并使用负向预查排除语法关键字，严密防御误杀 Python 代码（如 `if password is None:`）与前端 CSS 类名；
  4. **门禁与测试**：针对性单测 `tests/unit/test_mcp_find_and_privacy_mask.py` 4/4 满绿通过（0.09s），WSL2 生产环境热生效平滑重载实测通过。<br>*(Commit: `55f681488`, Tag: `v1.7.163`)*

#### 📌 [P1] [x] Card-200: `openviking-memory` 插件母本自内聚转接驱动重构、自愈清洗与四维逆向加固 (SSOT v2.0.16) ✅
- **治理成果与物理交付物**：
  1. **守卫信号透传与显性降级 (Card-205A)**：`ov_sandbox_guard.py` 放行 `SystemExit` 与 `KeyboardInterrupt`，异常时显式输出 `stderr` 告警并附带 `SANDBOX_DEGRADED` 元数据，消除静默缴械；
  2. **超时结构化反幻觉拦截 (Card-205B)**：`server.py` 在 15s 短超时与 120s 兜底超时触发时，恒定返回结构化 `TIMEOUT_TRUNCATED` 标头，阻断因超时致幻造轮子；
  3. **拓扑身份显式三级链 (Card-205C)**：`setup.py` 固化 `CLI --peer` ➔ 环境变量 ➔ 配置文件 ➔ 兜底猜词链路，杜绝多节点记忆分裂脑；
  4. **幽灵静态副本审计与 UTF-8 守护 (Card-205D)**：`setup.py` 探查静态实体目录阻断热更失效，Hook 命令行注入 `-X utf8 -E -s -S` 彻底根除 Windows 代码页异常；
  5. **门禁与测试**：端侧 `setup.py --inspect` 毫秒级自检通过，WSL 核心单测套件 `12/12 passed in 2.77s` 全绿。

#### 📌 [P1] [x] Card-201: `openviking-ops` 系统运维特权插件三位一体架构与三大客户端适配 (SSOT v1.0.4) ✅
- **核心成果与物理交付物**：
  1. **Card-201A (反重力自内聚 Proxy Stub 与母本净化)**：
     - 重构 `integrations/antigravity/openviking-ops/server.py`：纯净 FastMCP 自内聚转接驱动（254行），直连 `OPENVIKING_API`，精准提供 16 项特权运维算子 (SSOT)；
     - 彻底拔除母本 `setup.py` 中历史旧桌面路径倒挂与 `candidate_scripts` 外部依赖；
     - 物理清洗 `skills/` 误拷技能目录，全新构建 `openviking-ops/SKILL.md` 运维专家认知层；
     - 编写 `tests/integration/test_openviking_ops_plugin.py` 沙盒自举与 16 项工具 AST 断言，`5/5 passed in 0.74s` 全绿。
  2. **Card-201B (DSH 适配、零信任单轨鉴权与规范沉淀)**：
     - 彻底铲除 `client_caps.py` 本地 127.0.0.1 免密后门，无凭据严密阻断 HTTP 401；
     - 前端 `client.js` 强制增加 API Key 非空硬校验，杜绝虚假连通测试；
     - 结晶落盘 `docs/guides/DSH_PLUGIN_DEVELOPMENT_SPEC.md` 确立 DSH 插件工程标准与 Cordis 微内核架构开发规范。
  3. **Card-201C (全系插件自动化打包与分发闭环)**：
     - 运行 `scripts/pack_all_plugins.py`，全系 DSH 与 Antigravity 插件（包括 `openviking-ops-1.0.4.tgz`）不可变构建落盘至 `public/` 与 `dist/`。

#### 📌 [P0] [x] Card-203: `keepass-vault` 本地高安全凭据保险箱完全体重构与标杆化落地 (Credential SSOT v1.2.1) ✅
- **治理成果与物理交付物**：
  1. **母港建立与构件四位一体闭环**：在 `packages/plugins/keepass-vault` 建立完整架构（`plugin.json`, `mcp_config.json`, `hooks.json`, `server.py`, `setup.py`, `README.md`, `assets/`, `rules/`, `skills/`, `hooks/`）；
  2. **FastMCP 9 大算子与安全 stdin 通信**：`server.py` 严格基于 `keepassxc-cli.exe` 驱动，主密码仅通过标准输入管道传输，彻底杜绝命令行参数泄漏；
  3. **写前物理防抖快照 Hook (Disaster Recovery First)**：落地 `hooks/vault_guard.py`（纯标准库 `-X utf8 -E -s -S` 隔离，40ms 冷启动），写入前自动生成 `*.bak` 时间戳备份，实测成功生成备份；
  4. **查库第一公理潜意识固化**：落地 `rules/AGENTS.md` 与 `skills/keepass-vault/SKILL.md`，严禁索要明文密码，新增凭据强制高熵；
  5. **自举向导与双轨注册**：`setup.py` 自动写入宿主 `~/.gemini/config/config.json` 与 `mcp_config.json`，自检探针实测 `can_unlock: True (322 条凭据)`；
  6. **不可变分发与流水线对齐**：构建落盘 `keepass-vault-1.2.1.tgz` 与 `dsh-plugin-keepass-vault-1.2.1.tgz`，`sync_all_plugins.py --verify-only` 实现 3 大生产标杆 100% PASS，专属单测 `test_keepass_vault_plugin.py` 5/5 满绿通过 (0.07s)。

#### 📌 [P1] [ ] Card-202: `fleet-mesh` 插件母本自内聚转接驱动与多节点拓扑自适应 (SSOT v1.0.2) ⏳
- **核心目标**：彻底拔除 setup.py 中外部桌面路径硬编码，直连母港，清洗历史残留幽灵别名。

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
