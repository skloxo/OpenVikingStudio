# 🗺️ OpenViking 项目主线重构与原子化任务卡片总看板 (Master Task Cards Kanban - SSOT)

> **关联研发大蓝图**：[`BLUEPRINT.md`](file:///home/skloxo/aho/openclaw/project/.agents/BLUEPRINT.md) ｜ **交付全量归档台账**：[`DELIVERY_ARCHIVE.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md) ｜ **通用资产档案库**：[`COMPONENT_AND_WHEEL_INVENTORY.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/docs/architecture/COMPONENT_AND_WHEEL_INVENTORY.md)
> **唯一真相源 (SSOT)**：本文档为 OpenViking 当前活跃的重构规划与就绪待调度的任务矩阵看板。历史所有已验收交付的版本履历已完整归档至 [`DELIVERY_ARCHIVE.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md)。
> **战略外围项目隔离公理**：`Search2API 商业化搜索聚合网关` (`docs/search/SEARCH2API_COMMERCIAL_GATEWAY_SPEC.md`) 确认为独立多账号商业化代理项目，不占用 OpenViking 核心任务大盘卡槽。
> **基线状态**：线上正式部署 **`v1.4.106`** ｜ 当前最新交付 **`v1.7.174`** (代码基线 **`v1.7.153`**) ｜ 分支状态：`main` 已全量同步远程 `origin/main`。

---

## 📌 一、 全景版本发布与里程碑验收矩阵 (Milestone Evolution Matrix)

| 版本 Tag | 任务工单 ID | 模块与重构主题 | 核心治理成果与物理交付物 | 验收状态 |
| :--- | :--- | :--- | :--- | :---: |
| **`v1.7.180`** | **Card-236** | **双型插件全息架构范式确立、芒格逆向 25 大避坑铁律与体外大脑抗熵增重构 (Dual-Archetype Plugin Architecture, 25 Munger Invariants & Anti-Entropy Refactor)** | 1. **双型插件全息架构范式确立 (Two Plugin Archetypes)**：以真实发布的 `keepass-vault` 与 `openviking-memory` 为标杆，正式划分 **Type A 本地自治解耦型**（纯单机高私密、数据纯本地、计算纯本地、零网络依赖）与 **Type B 云端协同中枢型**（重计算卸载、全集群记忆漫游、动态能力投影），彻底打破单一云端偏见；<br>2. **查理·芒格逆向 25 大避坑铁律扩充更新**：扩充收录死穴 21~25（PowerShell 5.1 BOM 杀手、奥卡姆剔除自检实体、SPA 404 兜底诱骗死锁、DSH `defineTool` Schema 原生契约、驱使大模型静态源码肉眼逆向数数）；<br>3. **体外大脑 (OpenViking) 资产抗熵增重构与清洗**：重构 `recipes/openviking_plugin_crafting_spec.md` 写入双型标准与 7 大逆向防御；净化重构 `recipes/keepass_safe_selfcheck_sop.md` 为极简 1-Step 业务验真契约（`keepass_status` ≤1 step, ≤1s，严禁捏造自检实体）；录入全新踩坑演进经验 `evolution_lessons/20261029_keepass_plugin_crafting_pitfalls_and_anti_entropy.md`；<br>4. **四方技能与母港同频**：升级母本与本地 `antigravity-plugin-crafting/SKILL.md` 至 `v2.1.0`，双端同频并完成 Git Commit 留痕。<br>*(Commit: `77d818e13`, Tag: `v1.7.180`)* | [x] 已验收通过 ✅ |
| **
1.7.177** | **Card-233** | **KeePass Vault 10 工具完全体升维、DSH 座舱 client.js 补齐与 1.3.0 原子发版 (KeePass Vault 10-Tool DSH Cockpit & Atomic Release v1.3.0)** | 1. **DSH 座舱 client.js 补齐 10 工具**：在 packages/plugins/keepass-vault/client.js 的 TOOL_CATEGORIES 中正式纳入 keepass_selfcheck，彻底消除 DSH 端 MCP (9) 显示断层，点亮 10 工具；<br>2. **自动级联升级机制加固**：在 sync_all_plugins.py 与 ump_plugin.py 中补全母港 package.json 与 client.js 的自动版本级联逻辑，杜绝任何硬编码死版本；<br>3. **凡新增工具必 Bump 铁律落地 (v1.3.0)**：原子升级母本版本至 
1.3.0，构建并上线全新不可变包 keepass-vault-1.3.0.tgz (32,241 B) 与 dsh-plugin-keepass-vault-1.3.0.tgz (37,157 B)；<br>4. **DSH 本地与生产四方原子同频**：DSH 本地 package.json 依赖切至 1.3.0 并解压部署，四方审计大盘 100% PASS，生产 API GET /api/v1/plugins 验真返回 1.3.0 与 10 工具全部就绪。<br>*(Tag: 
1.7.177)* | [x] 已验收通过 ✅ |
| **
1.7.176** | **Card-232** | **KeePass Vault 真实沙箱打靶自检工具升级、Standard Schema 规范对齐修复、全系不可变分发与四方同频 (KeePass Vault Selfcheck Sandbox, Standard Schema & Clean SSOT v1.2.8)** | 1. **keepass_selfcheck 真实打靶自检工具落盘**：新增第 10 项原子工具 keepass_selfcheck，真实打靶 status/add/get/edit/rm 全生命周期，验证解密与一致性，执行完毕自动物理自毁清理，零生产数据泄漏，零脏数据残留；<br>2. **DSH Schemastery Standard Schema 规范对齐**：彻底修复 DSH 客户端 TypeError: Cannot read properties of undefined (reading 'validate') 崩溃，替换为官方完备 Schemastery 运行时并注入 ~standard 容错守卫；<br>3. **清理旧版物理残留与消除宿主注册表 DRIFT**：物理删除 keepass-vault 与 hooks 下的 __pycache__ 编译字节码残留；修正 ~/.gemini/config/config.json 宿主注册表由 1.2.6 升级至 1.2.8，消除版本漂移；<br>4. **四方原子同频与不可变分发构建**：母本 plugin.json (1.2.8) ≡ 安装目录 plugin.json (1.2.8) ≡ 宿主注册表 (1.2.8) ≡ 生产不可变包 keepass-vault-1.2.8.tgz (32,217 B) 与 dsh-plugin-keepass-vault-1.2.8.tgz (37,124 B)；生产 API GET /api/v1/plugins 100% 返回 1.2.8 且 10 工具点亮；<br>5. **双端单测与 MCP 真实打靶**：Node.js 单测 	est_dsh_keepass_adapter.mjs 10/10 工具 100% PASS，Python 集成单测 	est_keepass_vault_plugin.py 5/5 满绿，宿主 MCP 真实打靶 keepass_selfcheck 100% 通过。<br>*(Commit: e818dfb9, Tag: 
1.7.176)* | [x] 已验收通过 ✅ |
| **`v1.7.175`** | **Card-231** | **KeePass Vault 9 大原子工具全量升维、DSH 适配层完备实现与四方同频 (KeePass Vault 9-Tool Full Set & DSH Complete Adapter v1.2.6)** | 1. **母本母港 9 算子完全体升维**：扩充 `packages/plugins/keepass-vault/index.js` 为完备 9 大原子工具（Status, Search, Get, Add, Edit, Rm, Tree, Analyze, Export），DSH `output.render` 严守 ContentBlock 数组契约，补齐 `schema.js` 规范定义；<br>2. **四方原子同频级联迭代**：母本 `plugin.json` (1.2.6) ≡ `package.json` (1.2.6) ≡ `client.js` (1.2.6) ≡ `README.md` (1.2.6) ≡ 宿主部署端 `~/.gemini/config/plugins/keepass-vault` ≡ 宿主注册表 `~/.gemini/config/config.json`；<br>3. **不可变分发构建落盘**：打包流水线生成不可变分发包 `keepass-vault-1.2.6.tgz` (20,776 B) 与 `dsh-plugin-keepass-vault-1.2.6.tgz` (25,616 B) 部署至 `public/` 与 `dist/`，增量同频 WSL2 原生服务；<br>4. **探针与物理真实自检**：WSL2 原生服务平滑重启，本地 `http://127.0.0.1:1933/api/v1/plugins` 与公网 `https://vk.tide.red/api/v1/plugins` 100% 验真返回 1.2.6，`setup.py --inspect` 实测 323 条凭据正常解锁；<br>5. **双端单测与 MCP 实测打靶**：Node.js 单测 `test_dsh_keepass_adapter.mjs` 9/9 工具契约 100% PASS，Python 集成单测 `test_keepass_vault_plugin.py` 5/5 满绿，宿主 MCP 真实打靶 `keepass_status` 与 `keepass_search` 零阻断。<br>*(Commit: `873a63c02`, Tag: `v1.7.175`)* | [x] 已验收通过 ✅ |
| **`v1.7.174`** | **Card-230** | **DSH 智能体表现层 output.render 气泡渲染契约修复与原子递增发布 (DSH Bubble Output Render Contract & Atomic Release v1.2.5)** | 1. **DSH 框架底层 `userRender` 契约精准修复**：深入 DSH `resources/app.asar` 逆向分析 `defineTool` 与 `assertRenderedContent` 源码，彻底查明 `userRender is not a function` 根因。重构 `packages/plugins/keepass-vault/index.js`，严格为所有工具注入 `output: { schema: { type: 'string' }, render: (args, value) => [{ type: 'text', text: String(value) }] }`，100% 符合 DSH ContentBlock 数组契约；<br>2. **规范化调用展示卡片 (presentCall)**：为 `keepass_search`、`keepass_get`、`keepass_status` 注入标准 `presentCall` 元数据，生成 DSH 原生规范的执行卡片；<br>3. **双轨兼容与参数规范化防御**：实现 `toStandardJsonSchema` 自动转译参数，动态侦测 `@deepseek-ai/dsh-tools`，有无环境均可优雅运行；<br>4. **单元测试与安全门禁视网膜守护**：新增 Node.js 独立单元测试 `tests/unit/test_dsh_keepass_adapter.mjs`，拔除 `test_keepass_vault_plugin.py` 中写死的死版本号，实现 100% 动态 SSOT 校验；修复 `antigravity-plugin-crafting/SKILL.md` 偶发 IP/密码泄漏隐患，`security_check.py` 5391 个文件 0 缺陷通过；<br>5. **四方原子版本递增与不可变分发**：插件内核 `plugin.json` (1.2.5) ≡ `package.json` (1.2.5) ≡ `client.js` (1.2.5) ≡ `README.md` (1.2.5) ≡ 宿主注册表 ≡ 生产不可变包 `dsh-plugin-keepass-vault-1.2.5.tgz` (23,824 字节) ≡ `keepass-vault-1.2.5.tgz` (19,063 字节)，WSL 原生服务平滑重载，外部 HTTPS 探针 100% HTTP 200。 | [x] 已验收通过 ✅ |
| **`v1.7.173`** | **Card-229** | **插件生态三大原型升维、本地离线高安全物理隔离与教条主义债务清算 (Plugin Archetypes SSOT, Air-Gapped Local-Offline Guard & Dogmatic Debt Clearance v1.2.4)** | 1. **插件生态三大原生原型 (Archetypes SSOT)**：在 `plugin.json`、`plugin_scanner.py`、`models/plugin.py`、前端 TS DTO 正式引入 `archetype: local-offline | server-backed | hybrid-gateway`；<br>2. **Web Studio 抽屉与接入指引形态自适应**：对 `local-offline` 插件物理隐藏“服务中枢地址”输入框与本地/云端切换按钮，替换为冰青色“Air-Gapped 纯本地离线高安全”勋章，杜绝凭据外泄误解；<br>3. **全链路硬编码与幽灵代码大清洗**：斩除 `client.js` 中向 19339 端口的幽灵 fetch；拔除 `setup.py`、`client.js`、`README.md` 中的 `C:/Users/Skl` 路径，改用 `Path.home()` 动态推导；将认主提示词中的假常数 `314 项` 纠偏为自适应动态条目汇报；将工具分类由八股“长程记忆”纠偏为“凭据检索与分组遍历”；<br>4. **Server Key 收敛与 64 字符防溢出加固**：将 `mcp_config.json` 私有 Server Key 由冗余的 `"keepass-vault"` 统一改为 `"core"`，杜绝双重 Server 冗余注册与命名膨胀；<br>5. **不可变分发与四方同频**：原子发布 `keepass-vault` 与 `dsh-plugin-keepass-vault` v1.2.4 (22,493 Bytes)，生产分发包与 API HTTP 200，全套单测 100% 满绿通过。 | [x] 已验收通过 ✅ |
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
| **`v1.7.172`** | **Card-203** | **`keepass-vault` 本地高安全凭据保险箱完全体重构与标杆化落地 (Credential SSOT v1.2.1)** | 1. 统一母港 packages/plugins/keepass-vault 四位一体落盘；<br>2. FastMCP 9 大算子与 stdin 安全管道传递主密码；<br>3. 写前物理防抖快照 Hook (40ms 冷启动)；<br>4. 查库第一公理潜意识与 setup.py 双轨自举；<br>5. 不可变打包与 sync_all_plugins 100% 对齐，5/5 专项单测全绿。<br>*(Commit: `85a063282`, Tag: `v1.7.172`)* | [x] 已验收通过 ✅ |

| **`待排期`** | **Card-207** | **知识盲区自愈、反思骨架铸造与双轨补全自进化 (Knowledge Deficit Scaffolding)** | 推理缺口捕获，自动生成反思骨架草稿，双轨触发本地/外部知识补全。 | [ ] 待排期迭代 ⏳ |
| **`待排期`** | **Card-208** | **Workspace 分层配置与项目级 Peer 身份持久化 (Workspace Config & SSOT)** | 支持 `.openviking.toml` 项目级配置固化，解决跨设备/子目录迁移导致的项目记忆失效。 | [ ] 待排期迭代 ⏳ |
| **`v1.7.172`** | **Card-158** | **KeePass 本地凭据保险箱端侧体验与安全体检深化 (KeePass Local Vault)** | 由 Card-203 统一吸收完成四位一体与母港重构。 | [x] 已吸收通过 ✅ |
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

## 📌 二、 待攻坚活跃任务卡片与 Tududi 咬合看板 (Active Cards & Tududi SSOT)

> 💡 **历史已完成卡片已全量冷归档**：历史交付卡片详见 [docs/archive/REFACTORING_PLAN_ARCHIVE_202611.md](file:///c:/Users/Skl/Desktop/Workspace/coding/OpenVikingStudio/docs/archive/REFACTORING_PLAN_ARCHIVE_202611.md)。
> 📋 **全域任务调度与工单统一收口**：所有待办状态已 100% 托管至 Tududi P01 OpenViking (VK) 项目。


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
     - 严格遵循 **NO GREEN EVER 🚫**，字号硬下限 $\ge 12\text{px}$ (`text-xs`)，单文件 100~300 行黄金甜点区；
  5. **视网膜单测与门禁**：WSL 原生 Pytest 单测变绿，Vitest 前端单测变绿。

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

#### 📌 [P1] [ ] Card-213: 上游外部客户端插件生态协议对齐与时间衰减整并 (Upstream External Plugins Ecosystem & Recall Decay) ⏳
- **吸收内容与物理契约**：
  1. **召回配置时间衰减窗口 (PR #6390 / 3edc0b7f7)**：在 recall 配置中支持传入事件时间衰减半衰期 (`time-decay window`)；
  2. **增量重放 claim 刷新 (PR #5689 / f8d36722a)**：刷新 pending replay claim 时间戳，防止租约超时误判；
  3. **Codex PreCompact 身份保持 (PR #5660 / 7355b926e)**：Codex 插件压缩阶段保留规范化 PreCompact 会话身份；
  4. **Pi 与 LangChain 生态同步 (PR #6381 / 401c1f7ef & PR #6342 / 6ec6116b7)**：Pi 插件分支发散捕获，LangChain Store 读取与命名空间发现；
  5. **Claude-Code 测试上下文预算 (PR #6353 / 0902110a0)**：控制测试 fixture 严格处于上下文预算以内。
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