# 📦 OpenVikingStudio 历史已完成卡片冷归档 (Cards Archive 2026-10 ~ 2026-11)

> **说明**：本文件归档已全量交付并打标 Git Tag 的历史迭代卡片（Card-200 ~ Card-223 等）。活跃看板仅保留最近版本与当前待攻坚卡片。


| **
| **
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
#### 📌 [P0] [x] Card-204: 上游 Gateway 缓存遥测增强与 DSH 无工具请求防重复召回整并 (Upstream Gateway Cache Telemetry & Anti-Duplicate Recall) ✅
- **类型**：网关吞吐优化 / 记忆召回防抖 / DSH 协议治理 ｜ **优先级**：🔥 P0 ｜ **交付版本**：`v1.7.151`
- **核心治理成果与物理交付物**：
  1. **吸收上游 PR #6295 (e855796c8)**：针对 DSH 会话标题生成与已发工具会话的单轮侧向请求，自动识别并拦截 `auxiliary`，阻断 0 价值记忆召回与幽灵 Session 污染；剥离 3 类诊断与运行上下文噪音；统一工具参数紧凑化 JSON 解析；
  2. **吸收上游 PR #6026 (26fa00b91)**：落地回复增量哈希 (`reply_chain`) 根除 140k 上下文全文重复哈希的 CPU 损耗，落地 `SSEDecoder` 批量分帧与就地字符串拼接 (`safe_append_delta`)；
  3. **吸收上游 PR #6267 (27db44123) 闭环**：在 `proxy.py` 成功与异常路径打通 `_report_telemetry`，物理接入 `_GATEWAY_EVENT_BUFFER`，精准驱动长对话连续 3 次 Miss 告警；
  4. **视网膜单测**：编写专项测试 `tests/gateway/test_card204_gateway_telemetry_and_anti_duplicate_recall.py` (9/9 全绿)，全量 61/61 项网关单测 3.98s 满绿通过，安全扫描 0 泄露，打标 Tag `v1.7.151`。

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
  6. **不可变分发与流水线对齐**：构建落盘 `keepass-vault-1.2.1.tgz` 与 `dsh-plugin-keepass-vault-1.2.1.tgz`，`sync_all_plugins.py --verify-only` 实现 3 大生产标杆 100% PASS，专属单测 `test_keepass_vault_plugin.py` 5/5 满绿通过 (0.07s)。<br>*(Commit: `85a063282`, Tag: `v1.7.172`)*

- **Card-110**: Web Studio 审计大盘 MCP 工具分类与参数详情抽屉 (Request Logs MCP Filter)