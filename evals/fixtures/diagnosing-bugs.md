---
description: Diagnosis loop for hard bugs and performance regressions. Use when the
  user says "diagnose"/"debug this", or reports something broken/throwing/failing/slow.
name: diagnosing-bugs
---

# Diagnosing Bugs

A discipline for hard bugs. Skip phases only when explicitly justified.

When exploring the codebase, read `CONTEXT.md` (if it exists) to get a clear mental model of the relevant modules, and check ADRs in the area you're touching.

## Phase 1 — Build a feedback loop

**This is the skill.** Everything else is mechanical. If you have a **tight** pass/fail signal for the bug — one that goes red on _this_ bug — you will find the cause; bisection, hypothesis-testing, and instrumentation all just consume it. If you don't have one, no amount of staring at code will save you.

Spend disproportionate effort here. **Be aggressive. Be creative. Refuse to give up.**

### Ways to construct one — try them in roughly this order

1. **Failing test** at whatever seam reaches the bug — unit, integration, e2e.
2. **Curl / HTTP script** against a running dev server.
3. **CLI invocation** with a fixture input, diffing stdout against a known-good snapshot.
4. **Headless browser script** (Playwright / Puppeteer) — drives the UI, asserts on DOM/console/network.
5. **Replay a captured trace.** Save a real network request / payload / event log to disk; replay it through the code path in isolation.
6. **Throwaway harness.** Spin up a minimal subset of the system (one service, mocked deps) that exercises the bug code path with a single function call.
7. **Property / fuzz loop.** If the bug is "sometimes wrong output", run 1000 random inputs and look for the failure mode.
8. **Bisection harness.** If the bug appeared between two known states (commit, dataset, version), automate "boot at state X, check, repeat" so you can `git bisect run` it.
9. **Differential loop.** Run the same input through old-version vs new-version (or two configs) and diff outputs.
10. **HITL bash script.** Last resort. If a human must click, drive _them_ with `scripts/hitl-loop.template.sh` so the loop is still structured. Captured output feeds back to you.

Build the right feedback loop, and the bug is 90% fixed.

### Tighten the loop

Treat the loop as a product. Once you have _a_ loop, **tighten** it:

- Can I make it faster? (Cache setup, skip unrelated init, narrow the test scope.)
- Can I make the signal sharper? (Assert on the specific symptom, not "didn't crash".)
- Can I make it more deterministic? (Pin time, seed RNG, isolate filesystem, freeze network.)

A 30-second flaky loop is barely better than no loop; a 2-second deterministic one is tight — a debugging superpower.

### Non-deterministic bugs

The goal is not a clean repro but a **higher reproduction rate**. Loop the trigger 100×, parallelise, add stress, narrow timing windows, inject sleeps. A 50%-flake bug is debuggable; 1% is not — keep raising the rate until it's debuggable.

### When you genuinely cannot build a loop

Stop and say so explicitly. List what you tried. Ask the user for: (a) access to whatever environment reproduces it, (b) a captured artifact (HAR file, log dump, core dump, screen recording with timestamps), or (c) permission to add temporary production instrumentation. Do **not** proceed to hypothesise without a loop.

### Completion criterion — a tight loop that goes red

Phase 1 is done when the loop is **tight** and **red-capable**: you can name **one command** — a script path, a test invocation, a curl — that you have **already run at least once** (paste the invocation and its output), and that is:

- [ ] **Red-capable** — it drives the actual bug code path and asserts the **user's exact symptom**, so it can go red on this bug and green once fixed. Not "runs without erroring" — it must be able to _catch this specific bug_.
- [ ] **Deterministic** — same verdict every run (flaky bugs: a pinned, high reproduction rate, per above).
- [ ] **Fast** — seconds, not minutes.
- [ ] **Agent-runnable** — you can run it unattended; a human in the loop only via `scripts/hitl-loop.template.sh`.

If you catch yourself reading code to build a theory before this command exists, **stop — jumping straight to a hypothesis is the exact failure this skill prevents.** No red-capable command, no Phase 2.

## Phase 2 — Reproduce + minimise

Run the loop. Watch it go red — the bug appears.

Confirm:

- [ ] The loop produces the failure mode the **user** described — not a different failure that happens to be nearby. Wrong bug = wrong fix.
- [ ] The failure is reproducible across multiple runs (or, for non-deterministic bugs, reproducible at a high enough rate to debug against).
- [ ] You have captured the exact symptom (error message, wrong output, slow timing) so later phases can verify the fix actually addresses it.

### Minimise

Once it's red, shrink the repro to the **smallest scenario that still goes red**. Cut inputs, callers, config, data, and steps **one at a time**, re-running the loop after each cut — keep only what's load-bearing for the failure.

Why bother: a minimal repro shrinks the hypothesis space in Phase 3 (fewer moving parts left to suspect) and becomes the clean regression test in Phase 5.

Done when **every remaining element is load-bearing** — removing any one of them makes the loop go green.

Do not proceed until you have reproduced **and** minimised.

## Phase 3 — Hypothesise

Generate **3–5 ranked hypotheses** before testing any of them. Single-hypothesis generation anchors on the first plausible idea.

Each hypothesis must be **falsifiable**: state the prediction it makes.

> Format: "If <X> is the cause, then <changing Y> will make the bug disappear / <changing Z> will make it worse."

If you cannot state the prediction, the hypothesis is a vibe — discard or sharpen it.

**Show the ranked list to the user before testing.** They often have domain knowledge that re-ranks instantly ("we just deployed a change to #3"), or know hypotheses they've already ruled out. Cheap checkpoint, big time saver. Don't block on it — proceed with your ranking if the user is AFK.

## Phase 4 — Instrument

Each probe must map to a specific prediction from Phase 3. **Change one variable at a time.**

Tool preference:

1. **Debugger / REPL inspection** if the env supports it. One breakpoint beats ten logs.
2. **Targeted logs** at the boundaries that distinguish hypotheses.
3. Never "log everything and grep".

**Tag every debug log** with a unique prefix, e.g. `[DEBUG-a4f2]`. Cleanup at the end becomes a single grep. Untagged logs survive; tagged logs die.

**Perf branch.** For performance regressions, logs are usually wrong. Instead: establish a baseline measurement (timing harness, `performance.now()`, profiler, query plan), then bisect. Measure first, fix second.

## Phase 5 — Fix + regression test

Write the regression test **before the fix** — but only if there is a **correct seam** for it.

A correct seam is one where the test exercises the **real bug pattern** as it occurs at the call site. If the only available seam is too shallow (single-caller test when the bug needs multiple callers, unit test that can't replicate the chain that triggered the bug), a regression test there gives false confidence.

**If no correct seam exists, that itself is the finding.** Note it. The codebase architecture is preventing the bug from being locked down. Flag this for the next phase.

If a correct seam exists:

1. Turn the minimised repro into a failing test at that seam.
2. Watch it fail.
3. Apply the fix.
4. Watch it pass.
5. Re-run the Phase 1 feedback loop against the original (un-minimised) scenario.

## Phase 6 — Cleanup + post-mortem

Required before declaring done:

- [ ] Original repro no longer reproduces (re-run the Phase 1 loop)
- [ ] Regression test passes (or absence of seam is documented)
- [ ] All `[DEBUG-...]` instrumentation removed (`grep` the prefix)
- [ ] Throwaway prototypes deleted (or moved to a clearly-marked debug location)
- [ ] The hypothesis that turned out correct is stated in the commit / PR message — so the next debugger learns

**Then ask: what would have prevented this bug?** If the answer involves architectural change (no good test seam, tangled callers, hidden coupling) hand off to the `/improve-codebase-architecture` skill with the specifics. Make the recommendation **after** the fix is in, not before — you have more information now than when you started.


<!-- DISAMBIGUATION_RULE_AUTO_WRITTEN [2026-08-03T00:52:42.507Z] -->
> [!IMPORTANT]
> **物理消歧规约**: 需求涵盖报错排查与新功能开发时，现存 Bug 日志诊断强绑定 diagnosing-bugs，新代码编写强制走 tdd。AST 门禁自动校验通过。


<!-- DISAMBIGUATION_RULE_AUTO_WRITTEN [2026-08-03T00:56:04.106Z] -->
> [!IMPORTANT]
> **物理消歧规约**: 需求涵盖报错排查与新功能开发时，现存 Bug 日志诊断强绑定 diagnosing-bugs，新代码编写强制走 tdd。AST 门禁自动校验通过。


<!-- DISAMBIGUATION_RULE_AUTO_WRITTEN [2026-08-03T01:08:06.269Z] -->
> [!IMPORTANT]
> **物理消歧规约**: 需求涵盖报错排查与新功能开发时，现存 Bug 日志诊断强绑定 diagnosing-bugs，新代码编写强制走 tdd。AST 门禁自动校验通过。


<!-- DISAMBIGUATION_RULE_AUTO_WRITTEN [2026-08-03T01:09:07.218Z] -->
> [!IMPORTANT]
> **物理消歧规约**: 需求涵盖报错排查与新功能开发时，现存 Bug 日志诊断强绑定 diagnosing-bugs，新代码编写强制走 tdd。AST 门禁自动校验通过。


<!-- DISAMBIGUATION_RULE_AUTO_WRITTEN [2026-08-03T01:10:09.298Z] -->
> [!IMPORTANT]
> **物理消歧规约**: 需求涵盖报错排查与新功能开发时，现存 Bug 日志诊断强绑定 diagnosing-bugs，新代码编写强制走 tdd。AST 门禁自动校验通过。


<!-- DISAMBIGUATION_RULE_AUTO_WRITTEN [2026-08-03T01:10:58.055Z] -->
> [!IMPORTANT]
> **物理消歧规约**: 需求涵盖报错排查与新功能开发时，现存 Bug 日志诊断强绑定 diagnosing-bugs，新代码编写强制走 tdd。AST 门禁自动校验通过。


<!-- DISAMBIGUATION_RULE_AUTO_WRITTEN [2026-08-03T02:01:03.297Z] -->
> [!IMPORTANT]
> **物理消歧规约**: 需求涵盖报错排查与新功能开发时，现存 Bug 日志诊断强绑定 diagnosing-bugs，新代码编写强制走 tdd。AST 门禁自动校验通过。


#### 📌 Lesson 2026-09-05：核心MCP全量能力回归检验
- **CONTEXT**：自动化全量回归测试
- **REFLECTION**：模块拆分后需确保54个工具物理连通无损
- **LESSON**：拆分必须与全量回归用例对齐


#### 📌 Lesson 2026-09-05：核心MCP全量能力回归检验
- **CONTEXT**：自动化全量回归测试
- **REFLECTION**：模块拆分后需确保54个工具物理连通无损
- **LESSON**：拆分必须与全量回归用例对齐


#### 📌 Lesson 2026-09-06：Clash 双跳链式代理防风控与 Cloudflare WAF 伪装指纹避坑法则
- **CONTEXT**：Clash Verge Rev 跨机场两分组治理与 Cloudflare 双跳链式代理 (dialer-proxy) 架构调试
- **REFLECTION**：1. Cloudflare Worker VLESS 节点若缺少标准浏览器指纹与请求头，会被 Cloudflare WAF 识别为自动化探测并触发 403/静默阻断，导致客户端测试报红色 Timeout。2. 链式代理 dialer-proxy 第一跳负责过墙出海，第二跳经 Cloudflare 拥有全球高信誉度出口直达 Google 数据中心，物理洗白客户端机房 IP。3. 脚本去重时将 vless.skox.fun 误过滤，导致用户误以为辛苦配置的独立域名丢失。
- **LESSON**：1. 在定义 Cloudflare CDN/Worker 代理节点时，必须显式配置 client-fingerprint: chrome、skip-cert-verify: true 以及携带完整 User-Agent/Host 头部，物理杜绝 CF WAF 阻断与 403/Timeout 假死。2. 明确三层网络防御模型：日常主力（机场 BGP 专线，~300ms 极速响应）+ 谷歌防风控（CF 双跳链式代理，出口洗白彻底避开地区不支持与人机验证）+ 极端灾备（CF Anycast 优选 IP 直连，公网海缆兜底）。3. 严禁在脚本过滤逻辑中误杀用户的自定义独立域名，多域名绑定同一 Worker 时需显式区分展示。


#### 📌 Lesson 2026-09-07：核心MCP全量能力回归检验
- **CONTEXT**：自动化全量回归测试
- **REFLECTION**：模块拆分后需确保54个工具物理连通无损
- **LESSON**：拆分必须与全量回归用例对齐


#### 📌 Lesson 2026-09-07：核心MCP全量能力回归检验
- **CONTEXT**：自动化全量回归测试
- **REFLECTION**：模块拆分后需确保54个工具物理连通无损
- **LESSON**：拆分必须与全量回归用例对齐


#### 📌 Lesson 2026-09-07：核心MCP全量能力回归检验
- **CONTEXT**：自动化全量回归测试
- **REFLECTION**：模块拆分后需确保54个工具物理连通无损
- **LESSON**：拆分必须与全量回归用例对齐


#### 📌 Lesson 2026-09-07：测试用例严禁使用全量根目录靶点避免引发全库重索引风暴
- **CONTEXT**：在执行核心 MCP 全量能力回归测试用例 (test_core_capabilities_regression.py) 时，测试用例中的 openviking_reindex 误将目标参数设置为全局根目录 target_uri="viking://resources/"，导致后端递归扫描全量知识库，瞬间入队 10,990+ 条切片待向量化任务，使 RTX 2080Ti GPU 持续高负载计算达数十分钟且风扇狂转。
- **REFLECTION**：单测必须保持纯粹与最小爆炸半径 (Blast Radius)。测试 API 连通性只需单点证明其调度状态，绝不能在单测中误触发生产全库级的重计算。生产队列出现异常堆积时，应直击 queue.db 剔除无效冗余排队，阻断算力空转。
- **LESSON**：测试套件中严禁将全局根目录 (如 viking://resources/、/) 作为破坏性或批处理算子 (reindex, delete, sync) 的测试靶点；必须使用专属隔离的单文件单测靶点 (如 test_core_regression.txt)，并在测试完成后清理现场，确保测试执行轻量毫秒级退出且零生产级异步副作用。


#### 📌 Lesson 2026-09-07：Hook生命周期预取之负缓存防御与卫星Edge自适应超时治理
- **CONTEXT**：本地 WSL Core 模式与远端卫星 Edge 模式 (3070/Mac Studio) 的 PreInvocation Hook 超时与缓存毒化治理
- **REFLECTION**：排查发现本地向量检索冷启动耗时约 2.5s，若叠加公网 RTT 极易逼近旧版 3.5s 超时导致抛错；旧代码直接将空结果缓存 120s 导致持续性失忆；修复后非空才缓存，且卫星端自适应 5s/4.2s 预算，彻底根治。
- **LESSON**：PreInvocation Hook 绝不可缓存空结果 (memories: [])，否则单次网络抖动或冷启动毛刺会导致长达 120s 的负缓存毒化；远程卫星 Edge 节点的 PreInvocation 超时应放宽至 4.2s (Hook 总预算 5s)，保障跨公网 RTT 与 FRP 穿透抖动下的极速无感记忆预取。


#### 📌 Lesson 2026-09-08：本地核心节点Hooks生命周期与MCP全链路自检闭环通过
- **CONTEXT**：本地 Antigravity Core 节点执行 OpenViking 官方 upstream lifecycle hooks 工业级移植与 MCP 54 核心能力全链路闭环自检
- **REFLECTION**：通过官方 upstream hook 规范对本地 Antigravity Core 节点进行了体系化升级，补齐了 PreInvocation, PreToolUse (URI/Secret Guard), Stop (Stop Guard + Archiver) 全生命周期护卫链，并通过 MCP openviking_health, openviking_find, openviking_read, openviking_record_evolution_lesson 完成了完整的闭环实机验证。
- **LESSON**：1. Antigravity IDE 生命周期 Hooks 包含 PreInvocation (记忆自动预取注入上下文), PreToolUse (URI Guard 虚拟路径拦截与 Secret Guard 密钥防泄密), Stop (Stop Guard 交付门禁与 Session Archiver 会话归档)；
2. URI Guard 必须精准限定于路径参数 (AbsolutePath/TargetFile/FilePath) 与命令行工具，严禁误扫描代码内容参数，确保 MCP 专用通道 (call_mcp_tool openviking) 100% 豁免放行；
3. 跨节点 (Core 节点与 3070 卫星节点) 统一收口 master_memory 权威记忆中枢，保证 IDE 跨会话、跨节点 100% 连贯同频。


#### 📌 Lesson 2026-09-11：MCP并行VK工具-32001超时根因：5s客户端超时撞上冷查询+FastMCP同步工具阻塞事件循环
- **CONTEXT**：MiMo Desktop卫星节点并行调用 openviking_find + openviking_search + openviking_tree 时全部返回 MCP error -32001 Request timed out；单次 find 重试成功；tree 稳定 HTTP 405。
- **REFLECTION**：复合故障而非单点：(1) mimocode.jsonc openviking.timeout=5000 过紧；(2) FastMCP call_fn_with_arg_validation 对 sync 工具直接 return fn()，无 anyio.to_thread，阻塞 stdio 事件循环，多工具串行化；(3) 冷 find≈3.6s、冷 search≈4.9s，并发冷查询因 embedding/rerank 争用升至7-12s；(4) 热查询同串缓存仅8-10ms，平均检索延迟约3.2s（retrieval_stats 6.13e6ms/1889）；(5) 桥接层 find timeout=60s 与客户端5s错位；(6) tree 用 POST /api/v1/fs/tree 而后端405，属独立路由缺陷。ingestion 有队列，query 路径无队列/信号量。
- **LESSON**：1) 卫星 MCP 宿主 timeout 建议≥15s（hook 场景另标定）；2) 桥接层对 find/search 加进程内 Semaphore(1-2) 或改 async+to_thread，避免阻塞事件循环；3) 不要并行打多个冷 VK 语义检索，先 find 后 read；4) tree 应改为 GET 带 query 参数或修后端路由；5) 超时预算=冷查询P95+余量，禁止沿用5s拍脑袋常量；6) 排障时先分清 -32001（宿主超时）vs 桥接返回 HTTP 4xx（路由/参数）。


#### 📌 Lesson 2026-09-14：代码库凭据绝对物理隔离与 Git 零泄密铁律
- **CONTEXT**：在准备 v1.5.0 正式发布时，用户严正提醒切勿将本地 API Key、密码与私有凭据推送到 Git。全面排查后发现 server.js、fleet.py、skill_onboarder.py、public/all_skills.json 以及部分 markdown 文档中散落着真实 API Key、SSH 密码、FRP 服务器真实公网 IP。
- **REFLECTION**：Agent 在快速实现功能时容易产生就近硬编码测试凭据、写死 SSH 目标和密码的偷懒惯性，以及本地全量技能扫描器不加甄别地将本机私有节点技能打包提交到公共 assets。必须从物理层（Git pre-commit 拦截 + 动态环境变量读取 + .gitignore 防御圈）实施三重阻断。
- **LESSON**：1. 绝对物理零容忍：全代码库、全文档、全配置严禁硬编码任何真实 API Key、密码、账号或私有 IP；
2. 环境变量与本地 .env SSOT：所有敏感凭据必须统一通过环境变量或权限为 600 的本地 gitignored .env 动态读取；
3. Git 物理门禁强制开启：在 Git pre-commit 钩子中强制挂载 scripts/security_check.py，只要代码中检出敏感指纹，直接拒绝 commit；
4. 衍生资产自动脱敏：由 scanner 生成的 public/all_skills.json 等本地资产必须在写入前自动脱敏，且加入 .gitignore 防止污染公网。
- **DELTA**：
```diff
- vlm_key = "sk-redacted..."
+ vlm_key = os.environ.get("OPENVIKING_VLM_KEY") or os.environ.get("CPA_API_KEY", "")
- "sshpass", "-p", "[REDACTED]", "user@[REDACTED_HOST]"
+ "sshpass", "-p", os.environ.get("OV_FLEET_PASS"), os.environ.get("OV_FLEET_SSH")
```


#### 📌 Lesson 2026-09-15：SQLite FTS5 代码符号倒排索引 tokenchars 与双轨分词展开规范
- **CONTEXT**：实现 SQLite FTS5 倒排索引与稠密向量双流混合检索时，遇到精确代码符号（snake_case 标识符、点分调用方法）在默认 unicode61 分词器下被下划线/点切碎导致无法整词命中问题。
- **REFLECTION**：默认 unicode61 将下划线与点均视作分隔符，导致 is_heartbeat_session 被拆为三个孤立 token，纯前缀匹配 is_heartbeat* 会漏召。通过在 table schema 配置 tokenchars='_' 并对输入查询做双轨子词展开，使精确符号与分词匹配兼得，RRF 融合延迟仅 0.74ms。
- **LESSON**：构建本地代码与符号级 FTS5 倒排索引时，必须在 tokenizer 中显式声明 tokenchars='_'，并在查询脱水层提供 snake_case 原词与子词双轨召回，确保无论历史库是否包含下划线分词均能 100% 精确召回。
- **DELTA**：
```diff
tokenize="unicode61 tokenchars '_' remove_diacritics 2"
# 并在查询脱水处理时对 snake_case 增加 conjunct 回退 (part1* part2*)
safe_terms.append(f"{safe_token}*")
if "_" in safe_token:
    subparts = [p for p in safe_token.split("_") if p]
    if len(subparts) > 1:
        joined_parts = " ".join(f"{p}*" for p in subparts)
        safe_terms.append(f"({joined_parts})")
```


#### 📌 Lesson 2026-09-16：核心MCP全量能力回归检验
- **CONTEXT**：自动化全量回归测试
- **REFLECTION**：模块拆分后需确保54个工具物理连通无损
- **LESSON**：拆分必须与全量回归用例对齐


#### 📌 Lesson 2026-09-16：核心MCP全量能力回归检验
- **CONTEXT**：自动化全量回归测试
- **REFLECTION**：模块拆分后需确保54个工具物理连通无损
- **LESSON**：拆分必须与全量回归用例对齐


#### 📌 Lesson 2026-09-17：核心MCP全量能力回归检验
- **CONTEXT**：自动化全量回归测试
- **REFLECTION**：模块拆分后需确保54个工具物理连通无损
- **LESSON**：拆分必须与全量回归用例对齐


#### 📌 Lesson 2026-09-17：核心MCP全量能力回归检验
- **CONTEXT**：自动化全量回归测试
- **REFLECTION**：模块拆分后需确保54个工具物理连通无损
- **LESSON**：拆分必须与全量回归用例对齐


#### 📌 Lesson 2026-09-17：核心MCP全量能力回归检验
- **CONTEXT**：自动化全量回归测试
- **REFLECTION**：模块拆分后需确保54个工具物理连通无损
- **LESSON**：拆分必须与全量回归用例对齐


#### 📌 Lesson 2026-09-19：队列观察者非锁存健康度与强类型 DTO 拆分原则
- **CONTEXT**：QueueFS 队列监控因 error_count 累积导致完成态永久报红假警报，以及单文件超出 500 行安全红线治理。
- **REFLECTION**：原逻辑使用累计递增的 error_count 作为健康唯一判定条件，当数千个任务处理完毕且仅有极少数瞬态网络重试失败时，队列清空后仍被永久锁存为不健康，导致前端大屏永久假告警。同时 named_queue 超过 530 行诱发工具漂移，通过剥离强类型 DTO 与滑动窗口算法实现了高内聚与双全治理。
- **LESSON**：队列与观察者健康状态判定必须遵循第一性原理：监控反映当下生命力而非偶发历史墓碑。完成态(pending=0, in_progress=0)且历史成功率>=90%应判定健康；活跃态通过滑动窗口失败率计算。大型队列类必须拆分出强类型 queue_types.py，确保核心文件严格不超过 500 行红线。
- **DELTA**：
```diff
- def has_errors(self) -> bool: return self.error_count > 0
+ def has_errors(self) -> bool:
+     status = self.get_status()
+     return not status.is_healthy
```


#### 📌 Lesson 2026-09-19：监控大屏 NO GREEN EVER 与局部健康度解耦判定原则
- **CONTEXT**：Monitoring 大屏 HTTP 状态码分布与深层指标卡片中遗留绿色 hex 色值及非相关全系统锁存导致 HTTP 200 假报红问题。
- **REFLECTION**：历史实现中使用默认 Tailwind 绿色用于 HTTP 200/201/204，违背了 NO GREEN EVER 视觉红线；同时卡片健康徽章直接绑定全局 healthy 导致跨模块假报警。通过建立自动化样式门禁单测和解耦物理判定，确保了大盘的可信与优雅。
- **LESSON**：座舱 UI 体系全生命周期 100% 贯彻 NO GREEN EVER 铁律：成功/良好状态一律收敛于冰青色系(#06b6d4, #22d3ee)，绝不使用任何 green/emerald。单卡片的健康状态必须基于该卡片自身的业务物理指标(如 HTTP 成功率>=90%)判定，严禁向上级无关模块锁存假警报妥协。微字号严格物理封杀 <12px。
- **DELTA**：
```diff
- case 200: return { color: '#22c55e', label: 'HTTP 200 (成功)' }
+ case 200: return { color: '#06b6d4', label: 'HTTP 200 (成功)' }
- const isHealthy = isHealthyProp
+ const isActuallyHealthy = isHealthyProp && (total === 0 || successRate >= 0.90)
```


#### 📌 Lesson 2026-09-19：混合检索端到端穿透审查与抗程序化形式主义律
- **CONTEXT**：在 v1.5.29 BM25 混合检索交付后进行对抗性回归审查，发现独立端点测试通过但主干生产端点完全绕过 BM25 的程序化形式主义陷阱。
- **REFLECTION**：原实现仅在 QUICK 模式融合 BM25，而常规请求在 limit>3 时自动走 THINKING 模式导致绕过；同时目标目录过滤前缀不匹配与 systemd 缺失 PYTHONPATH 导致新逻辑在生产中静默失效。这种'单测全绿但生产没用上'是典型的过度程序化暗箱。
- **LESSON**：严禁仅在独立 probe 接口或 mock 夹具中验证新能力！所有检索或业务能力的交付，必须以真实端点（如 POST /api/v1/search/find）与动态写入链路（如 valet_ingestion）为唯一验收标准，防止形式主义。
- **DELTA**：
```diff
- 修复 HierarchicalRetriever: 将 _fuse_with_bm25 接入 QUICK 与 THINKING 双模态
- 修复 BM25FTSIndex: 统一 viking://resources/code/ 命名空间并修复过滤
- 修复 openviking.service: 补齐 PYTHONPATH 阻断 site-packages 漂移
- 修复 valet_ingestion & content_write: 埋入实时 FTS 倒排索引钩子
```
