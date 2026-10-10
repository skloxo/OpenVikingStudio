# ADR & 架构蓝图：FastMCP 总线端点解耦与模块化重构白皮书 (MCP Endpoint Decoupling Blueprint)

> **文档标识**：`ADR-ARCH-2026-10-08-MCP-DECOUPLE`  
> **所属主题**：底层核心通信网关重构与插件中心拓扑同构  
> **关联任务卡片**：[`REFACTORING_PLAN.md` -> Card-131](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/REFACTORING_PLAN.md)  
> **关联代码真相源**：[`openviking/server/mcp_endpoint.py`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/openviking/server/mcp_endpoint.py) ｜ [`openviking/service/plugin_registry.py`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/openviking/service/plugin_registry.py)

---

## 1. 架构决策背景与核心矛盾 (Context & Core Contradictions)

### 1.1 历史成因与上游基线
经 Git 物理溯源核验（Commit `ccad9c5e0`，PR #1738，2026-04-28）：
- `openviking/server/mcp_endpoint.py` 最初由火山引擎 OpenViking 官方核心维护者引入，用于取代 Node.js MCP 进程，通过 Python FastMCP 在 `/mcp` 暴露 9 项原生工具。
- 上游主干分支（`upstream/main`）当前该文件已有 **2,042 行**，包含 15 项最底层的 VikingFS 核心工具（`find`, `search`, `read`, `write`, `edit`, `ls`, `tree`, `remember`, `forget`, `grep`, `glob`, `add_resource`, `list_watches`, `cancel_watch`, `health`）。
- **上游本身的架构设计即为“大单体 (Monolith)”**，将所有 MCP 工具与 ASGI 网关逻辑堆叠在单一文件中。

### 1.2 Fork 分支的演进膨胀
在我们的 Fork 分支演进历程中（从 Card-58、Card-66 微软 SkillOpt、Card-75 Harness 探针到 Card-128 鉴权属主校验），为了向全集群智能体提供工业级自治能力，我们在该文件底部直接平铺追加了 **32 项扩展 MCP 工具**，导致文件规模急剧膨胀至 **3,088 行**（剥离 `search_mcp_tools.py` 后仍有 **2,819 行**）。

### 1.3 核心工程痛点 (The Non-Negotiable Problems)
1. **注意力崩塌与认知过载 (Lost in the Middle)**：
   单文件超过 1,500 行触发 LLM 注意力 U 型严重衰减；超过 800 行超出单次 `view_file` 视野上限；超过 2,800 行导致任何 Agent 在进行微小修改时极易产生行号漂移、上下文截断与打补丁套叠，严重违反项目 **“单文件 100~300 行黄金甜点区，硬上限 $\le 500$ 行”** 的物理铁律。
2. **单一职责原则失效 (Single Responsibility Principle)**：
   `mcp_endpoint.py` 本应是纯粹的 **通信网关与协议装配器**（生命周期、ContextVars、鉴权中间件），却硬编码了 DSPy 编译、正则隐私脱敏、技能打分、AIFP 工单流等大段业务逻辑。
3. **与插件中心 (Plugin Center) 拓扑撕裂**：
   前端座舱与 `plugin_registry.py` 已经将系统划分为四大支柱插件体系；但后端服务端却仍以远古大单体形式存在，前后端逻辑架构严重不一致。

---

## 2. 芒格逆向对抗审讯：倒推五大系统死因 (Adversarial Inversion Analysis)

在推进任何底层重构前，必须用芒格逆向思维审问：“如果这次重构搞砸了，我们是怎么死掉的？”

| 倒推系统死因 | 致命风险机理 | 防御与阻断策略 (Occam's Safeguards) |
| :--- | :--- | :--- |
| **死因一：上游合并地狱 (Upstream Merge Hell)** | 盲目重构上游原生的 15 项核心工具代码，导致未来 `git merge upstream/main` 时出现数百处不可调和的代码冲突。 | **【动静分离第一公理】**：坚决不碰上游原生的 15 项 VikingFS 核心工具（L512~L1779）；只剥离我们在 Fork 中追加的 31 项生态扩展工具。 |
| **死因二：请求上下文断流 (ContextVar Detachment)** | FastMCP 依赖 `_get_ctx()` 从 ContextVars 提取 `RequestContext`（租户/用户/Agent 身份）。若抽离模块未透传或在不同线程运行，将导致权限击穿或全部抛出 401。 | **【上下文纯函数桥接】**：所有抽离的注册函数接受统一 `mcp` 实例与 `_READ_ONLY_TOOL_ANNOTATIONS`，完全复用原生装饰器与上下文链路，零异步上下文篡改。 |
| **死因三：循环导入死锁 (Circular Dependency Lock)** | `mcp_endpoint.py` 依赖 service 层的工具，若 service 层反向引用 `mcp_endpoint.py` 中的内部辅助函数（如 `_mcp_failure`），导致服务启动时 Python 报错 `ImportError` 崩溃。 | **【单向依赖与辅助下沉】**：将 `_mcp_failure`、`_portable_schema` 等公共工具函数沉淀在 `openviking/service/mcp_common.py`，保持单向无环拓扑 (DAG)。 |
| **死因四：动态 ACL 与中间件穿透失效 (Tool ACL Bypass)** | Card-121 与 Card-128 落地了 Tool ACL 门禁（`_IdentityASGIMiddleware` 拦截 `tools/call`），若工具注册名称、装饰器元数据被意外修改，将破坏全集群权限控制。 | **【物理指纹视网膜门禁】**：重构前后通过 AST 严格比对 61 项 MCP 工具的名称、参数签名与注解，单测 `test_mcp_tool_acl_enforcement.py` 必须 100% 绿灯。 |
| **死因五：过度设计与碎片化反噬 (Over-Fragmentation)** | 将 31 项工具拆成 20 个几行的小文件，造成文件爆炸与认知负担转移。 | **【领域接缝适度原则】**：仅划分为 3 个高度内聚的领域模块，每个模块严格控制在 250~350 行，保持架构清爽。 |

---

## 3. 目标架构与接缝划分 (Target Clean Architecture)

重构完成后，`mcp_endpoint.py` 将彻底收缩为 **微内核总线装配器 (Micro-Kernel Assembler)**，代码行数从 2,819 行骤降至 **400~500 行**：

```
openviking/server/mcp_endpoint.py (微内核网关装配器, <= 500 行)
   │
   ├── [保留] FastMCP 实例创建、Lifespan、ASGI 中间件、ContextVars 透传
   ├── [保留] 15 项上游原生 VikingFS 核心工具 (find, search, read, write, edit, ls...)
   ├── [保留] zg_search (AST 结构检索)
   │
   ├── [挂载] register_search_mcp_tools(mcp)
   │          └── openviking/service/search_mcp_tools.py (12 项工具, 已就绪)
   │
   ├── [挂载] register_governance_mcp_tools(mcp)
   │          └── openviking/service/governance_mcp_tools.py (10 项工单/协同工具, 待实施)
   │
   ├── [挂载] register_skill_evolution_mcp_tools(mcp)
   │          └── openviking/service/skill_evolution_mcp_tools.py (8 项演化流水线工具, 待实施)
   │
   └── [挂载] register_code_privacy_mcp_tools(mcp)
              └── openviking/service/code_privacy_mcp_tools.py (13 项代码/隐私/探针工具, 待实施)
```

---

## 4. 详细工具迁移与物理归属对照表 (Migration Mapping SSOT)

| 抽离模块 (Service Layer) | 工具清单 (共 31 项 Fork 扩展工具) | 业务职责与领域接缝 | 单文件预估行数 |
| :--- | :--- | :--- | :---: |
| **`openviking/service/governance_mcp_tools.py`** | 1. `openviking_file_task_card`<br>2. `openviking_list_pending_cards`<br>3. `openviking_resolve_task_card`<br>4. `openviking_task_cards_summary`<br>5. `openviking_dlq_status`<br>6. `openviking_retry_dead_letter`<br>7. `openviking_valet_handover`<br>8. `openviking_valet_ticket_status`<br>9. `openviking_agent_sensors`<br>10. `openviking_active_notes_get`<br>11. `openviking_active_notes_update` | **AIFP 智能体自治工单中枢与状态协同**：跨集群异常建卡、死信队列自愈、便签同步、中继转接。 | ~320 行 |
| **`openviking/service/skill_evolution_mcp_tools.py`** | 1. `openviking_skill_validate`<br>2. `openviking_skill_intent_match`<br>3. `openviking_skill_publish`<br>4. `openviking_skill_judge`<br>5. `openviking_skill_remediate`<br>6. `openviking_skill_weight_tune`<br>7. `openviking_skill_evolution_pipeline`<br>8. `openviking_skill_zip` | **技能全生命周期自治演化管线**：意图匹配、动态打分、自动修复降级、微软 SkillOpt 仿真。 | ~290 行 |
| **`openviking/service/code_privacy_mcp_tools.py`** | 1. `openviking_code_impact`<br>2. `openviking_generate_contract_test`<br>3. `openviking_harness_probe`<br>4. `openviking_dspy_compile`<br>5. `openviking_tokenshift_compress`<br>6. `openviking_context_route`<br>7. `openviking_history_search`<br>8. `openviking_privacy_mask`<br>9. `openviking_privacy_quarantine`<br>10. `openviking_privacy_audit`<br>11. `openviking_memory_purity_report`<br>12. `openviking_vector_sync_metrics` | **代码感知、隐私安全隔离与上下文工程**：AST 爆炸半径分析、TDD 契约生成、正则脱敏隔离、Prompt 编译。 | ~330 行 |

---

## 5. 三阶段零风险受控实施路线图 (Three-Phase Staged Migration SOP)

为确保“牵涉面极广的底层重构”绝对稳健、物理零风险，必须分阶段严格按门禁推进：

### Phase 0: 静态契约冻结与测试桩准备 (Preparation)
- 编写 FastMCP 61 工具真身静态指纹比对脚本 `scripts/verify_mcp_signature.py`；
- 冻结当前所有工具的参数名、返回类型、Docstring、Annotations 注解。

### Phase 1: 逐模块解耦迁移与并行测试 (Incremental Extraction)
- **Step 1.1**：创建 `openviking/service/governance_mcp_tools.py`，切除 `mcp_endpoint.py` 对应代码，挂载 `register_governance_mcp_tools(mcp)`，运行单测验真；
- **Step 1.2**：创建 `openviking/service/skill_evolution_mcp_tools.py`，切除对应代码，挂载并验真；
- **Step 1.3**：创建 `openviking/service/code_privacy_mcp_tools.py`，切除对应代码，挂载并验真。

### Phase 2: 全链路回归与物理门禁验证 (End-to-End Retina Gate)
- 执行 FastMCP 物理探针，断言 61 项工具 100% 存在且签名 1:1 无漂移；
- 执行 `pytest -o addopts="" tests/` 全量后端测试全绿；
- 执行 `test_mcp_tool_acl_enforcement.py` 验证 Tool ACL 拦截依然强生效；
- 执行 `python3 scripts/security_check.py` 验证 0 凭据泄露；
- 执行 `npm run build` 验证前端座舱无破坏。

### Phase 3: 灾备预案与 Git Tag 留痕 (Disaster Recovery & Commit)
- 重构前先建 Git 分支或物理打标；重构若有任何未预期行为，支持一条命令 `git checkout` 秒级回滚；
- 验收通过后，按标准发版 SOP 打 Git Tag，同步更新 `REFACTORING_PLAN.md`。

---

## 6. 总结与研讨决策点 (Decisions for Tomorrow's Review)

明日深入研讨时需重点敲定的 3 个技术细节：
1. **辅助函数复用**：`_mcp_failure` 等助手函数是否抽离至统一的 `openviking/service/mcp_common.py`，还是各模块按需导入？
2. **渐进式实施次序**：明日是一次性分 3 个 commit 推进，还是按工单分步实施？
3. **上游代码隔离策略**：确认是否完全锁定 L512~L1779 上游官方代码，实现零破坏。
