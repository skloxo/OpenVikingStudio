# 📦 OpenViking 插件中心演进教训档案 (Evolution Lessons Archive)

> **定位**：本文件收录插件中心演化过程中沉淀的 16 条历史避坑教训，主控 SKILL.md 保持精简导航。


#### 📌 Lesson 2026-10-11：零信任单轨鉴权铁律、空间+用户双轴防串号契约与体外大脑绝对私有封闭堡垒法则
- **CONTEXT**：在 3070 远程节点接入 DSH 客户端的实战闭环验收中，排查出三项致命架构隐患：1）“本地内网免密、公网远程要密”的双轨割裂，引发本地跑得通、远端必 401 暴雷；2）企图通过“访客模式 (Guest Mode)”搞免密只读，直接威胁体外大脑私有数据主权与机密安全；3）多租户下必须空间（Tenant）+ 用户（Agent）双轴强绑定（256-bit CSPRNG 高熵 Token + 笛卡尔积命名空间沙箱），杜绝同名用户跨空间串号；4）DSH 异构客户端必须基于 stdio proxy 挂载 MCP 桥梁，并通过 pre-step 瀑布流拦截穿透系统快照精准提取提问。
- **REFLECTION**：安全没有特权，也没有双轨。本地免密是软件工程中典型的“环境特例主义大泥潭”。全系统无论本地还是公网，一律强制零信任单轨 Bearer 鉴权；体外大脑是绝对私有的外挂大脑，0 访客、0 免密、物理拒止；多租户严格双轴绑定沙箱化。从根源切除了环境特例与越权隐患。


#### 📌 Lesson 2026-10-07：插件与Agent两级中心第一性原理：服务端本体解耦、客户端单桥梁动态投影与制作运维SOP闭环
- **CONTEXT**：在梳理插件中心与 Agent 中心整体方案时，彻底击穿“插件安装必须拷贝代码到客户端”的思想钢印，明确插件本体 100% 运行于服务端，客户端仅维护单一通用透传桥梁，通过 FastMCP 网关根据 Agent 授权白名单实现“动态能力投影”；同时梳理澄清了插件制作 SOP（服务端算子+注册表登记，客户端零代码）与运维 SOP（服务端探针+严格SemVer桥梁打包）。
- **REFLECTION**：脱离了客户端打包的思维束缚后，插件生态的扩展与运维复杂度从 O(N*M) 骤降为 O(N+1)。服务端模块高内聚，客户端极简无状态，这才是真正的信达雅与奥卡姆剃刀。
- **LESSON**：1. 插件制作极简化：新插件 100% 仅在服务端实现并通过注册表暴露，客户端无需重复开发或打包；
2. 权限装配动态化：Agent 中心维护插件与具体工具白名单，网关握手时动态投影，秒级生效且绝对安全；
3. 通用桥梁标准化：客户端按需安装独立轻量领域插件包，基于 User Key 鉴权并 1:1 投影所属能力。
- **DELTA**：
```diff
+ 更新 openviking-plugin-ops/SKILL.md 至 v2.3.0
+ 明确插件制作 SOP (纯服务端编写FastMCP算子 + 注册表登记，客户端零开发)
+ 明确插件运维 SOP (服务端探针 + 通用桥梁不可变发布 + 严格SemVer)
+ 蓝图与 REFACTORING_PLAN 任务看板全面同步对齐
```

#### 📌 Lesson 2026-10-07：插件四位一体(Skill+Hook+MCP+GUI)深度咬合、认知导轨与防“左右互搏”铁律
- **CONTEXT**：在明确插件三大标杆（Wiki Memory、KeePass Vault、Network Search）后，进一步穿透插件内部机理：光有 MCP 会导致 Agent 盲目乱调与幻觉；光有 Hook 会因 Agent 不知其存在而造成重复查询或冲突；缺少 Skill 则是死工具无 SOP；缺少 GUI 则是人机黑盒。
- **REFLECTION**：真正生产级的插件必须四位一体：Skill (脑/认知手册) + Hook (自主神经/条件反射) + MCP (四肢/原子算子) + GUI (五官/交互视窗)。三者在运行时必须物理咬合：Skill 在开篇必须显式向 Agent 交代 Hook 的静默行为（如“系统已自动预取，严禁开局盲目重复调 find”），并严格约束 MCP 调用工序序列与 403 优雅降级策略。
- **LESSON**：1. 建立四位一体绝对契约：后续开发新插件或维护旧插件，四层缺一不可，严禁单发裸 MCP 工具；
2. 认知手册同步下发：插件授权给 Agent 时，配套 Skill 同步注入认知，杜绝认知断层；
3. 彻底根除“左右互搏”：在 Skill 中白纸黑字写明底层 Hook 的自动化拦截逻辑，达成机智协同。
- **DELTA**：
```diff
+ 升级 openviking-plugin-ops/SKILL.md 至 v2.4.0
+ 确立三大标杆插件四位一体对照全息表 (Memory: 47 MCP + 3 Hook + 专属Skill + GUI)
+ 确立防冲突三大铁律 (交代底牌律、精密工序律、优雅降级律)
+ 升级新插件制作 SOP 为四位一体全流程
```



#### 📌 Lesson 2026-10-07：插件四位一体深度咬合与两级中心顶层架构规约
- **CONTEXT**：
- **REFLECTION**：脱离了客户端打包的思维束缚后，插件生态的扩展与运维复杂度从 O(N*M) 骤降为 O(N+1)。服务端模块高内聚，客户端极简无状态，这才是真正的信达雅与奥卡姆剃刀。真正生产级的插件必须四位一体深度咬合。
- **LESSON**：插件四位一体(Skill+Hook+MCP+GUI)深度咬合体系与防冲突铁律：\n1. 插件四维分工：Skill 是操作手册(认知脑)，Hook 是自动拦截预取(自主神经)，MCP 是原子算子(执行手脚)，GUI 是配置面板(人机视窗)；\n2. 彻底根除“左右互搏”：坚决杜绝只暴露裸 MCP 导致 Agent 盲调与幻觉，也坚决杜绝 Hook 静默执行而 Agent 认知空缺导致的重复调用。Skill 开篇必须明示底层 Hook 的自动化拦截逻辑；\n3. 新插件开发铁律：新插件立项必须四层齐备，100% 服务端实现，客户端仅需单一不可变轻量桥梁。
- **DELTA**：
```diff
+ 升级 openviking-plugin-ops 至 v2.4.0\n+ 确立三大插件四位一体架构\n+ 蓝图与看板全面同步对齐
```


#### 📌 Lesson 2026-10-07：DSH客户端UserKey与AgentID认证鉴权与RPC通信全链路契约
- **CONTEXT**：
- **REFLECTION**：将身份认证与权限授权在协议层彻底解耦，兼顾了安全性与动态灵活性。DSH 客户端通过 volatile-update 与不可变桥梁实现了秒级热更新，无需重启客户端，符合现代云原生体外大脑的最高体验标准。
- **LESSON**：以 DSH 为例的异构客户端认证鉴权与 RPC 桥梁时序契约：\n1. 双轨分离：User Key 负责身份验真 (Authentication ➔ 401 门禁)，Agent ID 负责权限范围与工具白名单动态投影 (Authorization ➔ 403 门禁)；\n2. 凭据解析：客户端按 GUI SettingsForm (role secret) ➔ .credentials.yaml ➔ 环境变量 三级链解析；\n3. 安全传输：Agent ID 与 User ID 走 URL Query 参数，User Key 严格走 Authorization Bearer 报头，绝不污染 URL 日志；\n4. 热生效机制：计算 mcpUrl#key 物理签名，监听 volatile-update，修改配置 50ms 内 dispose 旧连接并重新挂载，零重启生效。
- **DELTA**：
```diff
+ 升级 openviking-plugin-ops 至 v2.5.0\n+ 增补 DSH 客户端 User Key 与 Agent ID 认证鉴权时序契约\n+ 明确三级凭据探测、URL/Header双轨分离与 volatile-update 热重载机制
```


#### 📌 Lesson 2026-10-07：插件生态与两级中心重构20张原子任务卡片矩阵细化拆解规约
- **CONTEXT**：
- **REFLECTION**：用户关于'够原子化吗'的拷问极其切中要害。过去的粗粒度卡片极易导致前后端交叉大杂烩和注意力衰减。将 4 个粗工单拆解为 20 张清晰解耦的原子卡片，做到了真正的第一性原理、信达雅与小步快跑。
- **LESSON**：插件中心与两级中心重构原子化拆解工程方法论：\n1. 粗工单(Card-121~124)仅作为发布版本里程碑(Milestone Tags)，绝不可直接作为单次编码交付单元；\n2. 严格拆解为 6 大专项、20 张 Tracer Bullet 原子任务卡片(TASK-PLUG/AGNT/GATE/ASST/UI-01~05)；\n3. 每张卡片明确单一接缝(Seam)、强类型契约、单文件<=200行甜点区、独立测试门禁与客观衡量指标，彻底消灭大卡片盲目堆砌代码的顽疾。
- **DELTA**：
```diff
+ 落地 docs/architecture/ATOMIC_TASK_CARDS_MATRIX.md (20 张原子任务卡片)\n+ 将 Card-121~124 细化映射至 6 大专项战役与 20 张原子卡片\n+ 严格落实单卡单 Seam、单文件 100~200 行甜点区与 TDD 视网膜门禁
```


#### 📌 Lesson 2026-10-10：三层模型大一统与空间管理看板人机平权SSOT
- **CONTEXT**：消除手握 Root Key 却看不到空间管理的认知割裂。
- **REFLECTION**：User 是空间内的唯一操作实体，User 完全等同于 Agent，消除把智能体特殊化的过度工程。
- **LESSON**：三层模型大一统 (Root-Account-User)、空间管理实体看板现形与人机平权合并经验。

#### 📌 Lesson 2026-10-11：插件接入验收单一变量隔离原则、切除生硬黑话与透明代理自愈铁律
- **CONTEXT**：在 3070 远程节点进行 DSH 插件全能力实战验收时，发现因 Prompt 动词（“查一下”）诱发模型调用官方欠费的内置 `web_search`；守卫暴力 deny 抛红字报错后，小模型由于多轮纠偏格式错乱，反常喷出 Claude 风格的文本 XML 标签 `<invoke>`；同时模型调用 DSH 自带未实现的 `list_mcp_resources` 产生 `server is disconnected` 伪断联；导轨中过多的生硬黑话（“算子”、“管理类接口”）也造成了认知过载与粉色大象效应。
- **REFLECTION**：芒格逆向审讯第一性原理：“倒过来想，总是倒过来想”。1) 体检非生产：初验必须分阶段、控制单一变量（单测记忆、单测搜索、单测凭据），严禁首测即混用内外两脑；2) 切除生硬黑话与否定词：Transformer 注意力天生容易被否定词毒化或产生过度约束恐惧，导轨必须全部采用纯大白话正向引导；3) 透明代理优于暴力报错：客户端内置不可卸载坏工具，守卫严禁直接 deny 抛红字吓坏模型，必须在底层静默透明桥接至自研多云后端，消除报错与 XML 幻觉。
- **LESSON**：1. 确立新 Agent 接入六阶标准化验收矩阵（探针 ➔ 纯净记忆 ➔ 纯净搜索 ➔ 纯净凭据 ➔ 原生轨迹审讯 ➔ 内外双脑复合化合）；
2. 导轨大白话律：切除一切“算子”、“管理接口”生硬行话，正向引导模型优先消费预取记忆；
3. 透明代理自愈律：底层静默接管官方失效工具，将 `web_search` 桥接自研后端，将 `list_mcp_resources` 抹平为合法空响应，彻底根除红字与 `<invoke>` 文本逃逸。
- **DELTA**：
```diff
+ 升级 openviking-plugin-ops 至 v2.9.0
+ 重构 references/AGENT_PLUGIN_ONBOARDING_TEST_SOP.md 为六阶全息验收矩阵
+ 插件 index.js 导轨大白话化，切除黑话与否定词毒化
+ 确立单一变量隔离体检与生产双脑跨域化合两步法
```

#### 📌 Lesson 2026-10-11：全栈四大恶性反模式根治与高密健壮性演进 (Four Major Anti-Patterns & Robustness SSOT)
- **CONTEXT**：在 DSH 客户端与 Web Studio 端到端联调验收中，连续遭遇四大致命暗病：
  1. **SPA 通配路由劫持**：在 `app.py` 中过早注册 `/{filename:path}` 导致访问 `/studio/settings` 报 `File not found` 404；
  2. **DSH 消息协议非法 Source Kind 崩溃**：向会话推送 `source.kind: 'plugin'` 触发 DSH 底层断言 `format v4 message requires a producer-owned source kind` 导致会话中断；
  3. **人类发言气泡篡改与无脑全局触发**：无意图过滤导致发 `1+1` 也强行检索记忆，且将记忆拼入 `lastUserMsg.content` 导致人类聊天气泡被污染塞满几千字机器文本；
  4. **时序倒置与小模型伪工具调用**：`systemPrompt.context` 装配早于 `agent/pre-step` 导致模型没拿到记忆，子进程未继承 `process.env` 导致工具缺失，小模型被迫喷出 Claude 风格 `<invoke>` 标签。
- **REFLECTION**：
  1. **路由注册顺序即物理契约**：FastAPI 先到先得，精确与前缀路由必须绝对优先于全局通配兜底；
  2. **协议类型绝对合法性**：DSH 消息只认 producer-owned source kind（`runtime-context`, `user`, `system-prompt`），绝不可发明私有未知类型；
  3. **人类气泡绝对神圣不可侵犯**：用户的发言实体绝不允许追加机器内容，人机视网膜必须彻底解耦（通过隐藏 `runtime-context` 传递给模型，界面 100% 隐藏）；
  4. **意图精准触发律**：常规闲聊与简单算术严禁触发体外大脑检索，杜绝上下文污染与 Token 浪费；
  5. **Windows 环境变量继承律**：跨进程派生子进程必须完整继承 `...process.env`（PATH, SYSTEMROOT），杜绝子进程静默崩溃。
- **LESSON**：
  1. **SPA 路由优先铁律**：`/studio` 与 `/studio/{path:path}` 必须在 `/{filename:path}` 之前注册，通配路由严格收敛为只匹配 `.tgz` 产物；
  2. **隐藏环境快照律**：记忆注入统一收口为 `source.kind: 'runtime-context'`，界面对人类无感，后台对模型全开；
  3. **意图门禁律 (`isMemoryIntent`)**：严禁 `length >= 2` 全局无脑触发，必须包含领域关键词才预取；
  4. **跨进程环境继承律**：子进程 `childEnv` 必须展开 `...process.env`，确保 Windows stdio 代理 100% 稳如磐石。
- **DELTA**：
  - 升级 `openviking-plugin-ops` 至 **`v3.1.0`**；
  - 修复 `app.py` 路由注册顺序，公网 `/studio/settings` 恢复 200 OK；
  - 重构插件 `index.js` 为 **`v2.0.7`**，实现隐藏 `runtime-context` 注入与 `isMemoryIntent` 门禁；
  - 3070 节点完成 `2.0.7` 覆盖部署与实机验收。


#### 📌 Lesson 2026-10-11：全栈四大恶性反模式根治与高密健壮性演进 (SPA通配劫持/非法SourceKind/气泡污染/伪工具调用)
- **CONTEXT**：在 3070 远端节点与 Web Studio 客户端接入联调中，连续遭遇四大阻断性恶性反模式：1) FastAPI 根通配路由劫持 SPA 导致 /studio/settings 报 404 File not found；2) DSH 拦截器塞入非法 source.kind: 'plugin' 导致 format v4 校验断言崩溃；3) pre-step 将记忆拼入用户消息实体导致人类聊天气泡被大段机器文本污染且发 1+1 也无脑触发；4) Prompt 组装时序倒置且子进程未继承 Windows PATH 导致模型伪输出 <invoke> 标签报错。
- **REFLECTION**：1. 路由注册顺序即物理契约：FastAPI 是先到先得匹配，精确路由与 SPA fallback 必须绝对优于全局通配；
2. 强类型协议零私有发明：DSH 只认 producer-owned kind（runtime-context 等），严禁发明未知类型；
3. 人类气泡绝对神圣不可侵犯：机器上下文必须通过隐藏 runtime-context 传递给模型，界面对人类 100% 隐藏，人机视网膜彻底解耦；
4. 意图精准门禁：严禁全局无脑检索，简单算术或打招呼物理阻断；
5. 跨进程环境继承：Windows 子进程必须展开 ...process.env，杜绝静默 crash。
- **LESSON**：1. SPA 路由优先铁律：/studio 与 /studio/{path:path} 必须在 /{filename:path} 之前注册，通配路由严格收敛只匹配 .tgz 安装包；
2. 隐藏环境快照律：记忆注入统一收口为 source.kind: 'runtime-context'，界面对人类无感，后台对模型全开；
3. 意图门禁律 (isMemoryIntent)：包含专有领域关键词才预取，常规算术零网络开销；
4. 跨进程环境继承律：子进程 childEnv 必须包含 ...process.env，保障 stdio MCP 代理稳定启动。
- **DELTA**：
```diff
+ 修复 app.py 路由顺序，/studio/settings 恢复 200 OK
+ 升级 dsh-plugin-openviking 至 2.0.7，实现隐藏 runtime-context 注入与 isMemoryIntent
+ 升级 openviking-plugin-ops 至 v3.1.0
```


#### 📌 Lesson 2026-10-11：DSH 客户端 invoke 文本泄漏两大根因：MCP 代理重复 /mcp 404 与会话归档检索淹没
- **CONTEXT**：
- **REFLECTION**：
- **LESSON**：


#### 📌 Lesson 2026-10-11：DSH 客户端租户错位致 read 404 引发 22 轮死循环与 865K Token 异常消耗根治
- **CONTEXT**：
- **REFLECTION**：
- **LESSON**：


#### 📌 Lesson 2026-10-14：多智能体一核多壳插件架构与双轨身份正交隔离公理
- **CONTEXT**：反重力IDE工作区从project切到coding，并正式立项落地反重力官方标准插件 (v2.0.11) 以及厘清反重力双身份体系
- **REFLECTION**：1. 过去试图将 DSH 的 npm 包套给反重力 IDE 导致架构水土不服；反重力 IDE 天生支持声明式标准 Plugin；2. 混用 Antigravity@2080Ti 导致桌面版与 IDE 版私有命名空间无法区分，拆分 AntigravityIDE 彻底解决归属冲突；3. 客户端 Hook 缺乏云端状态感知易导致用户中心开关形同虚设，必须内置快照缓存实现闭环管控。
- **LESSON**：1. 跨平台多智能体插件遵循「一核多壳」铁律：记忆中枢与协议唯一，宿主包装因地制宜，反重力IDE使用原生 plugin.json 目录标准，拒绝冗余外部运行时；2. 客户端实体必须严格按「软件形态@节点」命名隔离，桌面客户端与开发IDE分立两套账号以防私有记忆串号；3. 客户端 Hook 必须具备云端动态感知与短路降级，严格尊重用户中心的开关管控。
- **DELTA**：
```diff
+ integrations/antigravity/openviking-memory/ (官方标准插件目录)
+ Antigravity@2080Ti (Windows 桌面专属) vs AntigravityIDE@2080Ti (WSL2 开发座舱专属)
+ hooks/ov_pre_invocation.py 增加云端能力缓存与短路感知
```


#### 📌 Lesson 2026-10-19：OpenViking 客户端插件 Windows Hook 绝对路径与有效凭据双闭环铁律
- **CONTEXT**：Windows 客户端下 Antigravity 宿主无法自动感知 OpenViking 体外大脑技能中心与核心记忆，导致 Agent 出现开局失忆、无法自动召回专属插件技能的现象。
- **REFLECTION**：1. Antigravity 触发 Hook 时子进程的工作目录是用户当前打开的工作区根目录（如 C:/Users/Skl/Desktop/coding），若写相对路径 hooks/xxx.py，操作系统寻址必然抛出 [Errno 2] No such file or directory，被宿主静默丢弃导致每轮提问注脑失败；2. 插件 config.json 曾残留失效 Token，导致请求 /api/v1/search/find 时触发 HTTP 401 Unauthorized 静默降级；3. 双重物理阻断导致 Agent 彻底丢失对体外大脑技能中心与记忆库的自动感知通道。
- **LESSON**：所有官方 Antigravity 客户端插件的 hooks.json 配置，必须强制声明绝对 Python 路径与绝对脚本路径（结合 -E -s -S 极速隔离参数），绝不可写相对路径；同时插件 config.json 的凭据必须与后端主控密钥强一致，确保 PreInvocation 预取反射链路 100% 物理连通。
- **DELTA**：
```diff
- "command": "python3 hooks/ov_pre_invocation.py"
+ "command": "C:/Python311/python.exe -E -s -S C:/Users/Skl/.gemini/config/plugins/openviking-memory/hooks/ov_pre_invocation.py"
- "api_key": "ZGVmYXVsdA..."
+ "api_key": "vk-sk-***"
```

#### 📌 Lesson 2026-10-19：技能入库严禁手工文件拷贝强制走官方自动化准入流水线铁律
- **CONTEXT**：在更新 OpenViking 技能中心时，Agent 企图用 Linux cp 命令手动拷贝技能目录到底座 SSOT 路径下。用户严正指出：系统内生有自动化准入流程，只有通过自动化流程才能正常入库。
- **REFLECTION**：底层数据事实（skill_ingestion_inbox.db 记录着 63 COMMITTED, 1098 REJECTED, 25 ERROR）证明系统内生存在严密的 PENDING ➔ VALIDATING ➔ STAGED ➔ COMMITTED 状态机。手工拷贝绕过了这一体系，造成无 receipt_id、无母包结晶、无向量索引的严重后果。
- **LESSON**：所有新技能与技能升级一律严禁手搓 cp。必须依托 skill_syncer 自动侦测或调用 /api/v1/skills/ingestion/submit，经 SkillIngestionValidator 安全与格式门禁校验通过并进入 COMMITTED 状态后，方属合法入库。
- **DELTA**：
+ 升级 openviking-plugin-ops 至 v3.2.0
+ 确立 Card-95 & Card-165 技能自动化准入演进流水线规约 (Section 10)
+ AGENTS.md 全局追加第十二条铁律

---
