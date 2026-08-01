# OpenViking Studio 任务卡片化超细粒度重构计划 (Single Source of Truth)

> **🎯 唯一真相源 ⭐⭐⭐⭐⭐ — 基于 Git 历史 + 会话 Transcript 双重物理证据**
>
> 本文档每条记录均有**会话 ID + 步骤号 / Git Commit Hash** 作为物理证据支撑，100% 真实可追溯。
>
> **干活必留痕铁律（每次迭代完成后缺一不可）：**
> 1. `git tag -a v1.x.y <hash> -m "release: v1.x.y <概括>"` → 立即 `git push origin v1.x.y`
> 2. 将本文档对应卡片状态改为 `[x] ✅`，补写 Git hash + 修改文件清单
> 3. `git commit -m "docs: update REFACTORING_PLAN.md - mark v1.x.y as delivered"` → `git push`

---

## ✅ 阶段 0：v1.0.x 基础建设（Tag: `V1.0.0`）

**【Git 证据】Tag `V1.0.0` (commit `9898cdd`)，后续 v1.0.8~v1.0.12 commit messages**

| 版本 | Git Commit | 内容 |
|------|-----------|------|
| V1.0.0 | `9898cdd` | 全站重构：Sessions / Resources / Tasks / Retrieval / Home 路由完整建立 |
| v1.0.8 | `0b8cbb2` | 首页 MetricPanels 4px 微圆角，等宽数字，dev mode bypass |
| v1.0.9 | `a36183b` | 首页 TokenTrendPanel 14天面积图 |
| v1.0.10 | `e2cf5e4` | 首页 ContextCommitsHeatmap 365天热力图 |
| v1.0.11 | `d7732eb` | 检索搜索栏 4px 高密重构 |
| v1.0.12 | `75ea5e1` | 检索结果列表 4px 高密卡片 |
| — | `acc44db` | 任务中心一键重排队按钮 |
| — | `8e235be` | 任务耗时与实时秒表列 |
| — | `09c2ccb` | 会话中心渐进式分页加载 |

---

## ✅ 阶段 1：v1.1.0 监控大盘建设（Tag: `v1.1.0`）

**【Git 证据】Tag `v1.1.0` (commit `8278ff2`)，后续 v1.1.2~v1.1.7 commits**

| 版本标记 | Git Commit | 内容 |
|---------|-----------|------|
| v1.1.0 | `8278ff2` | 版本升至 1.1.0，README 更新 |
| v1.1.2 | `12b418a` `0ac5c25` | 监控大盘 QueueStatusCard（工序队列健康状态） |
| v1.1.3 | `96fe309` | VikingDbCard（VikingDB 向量库概览） |
| v1.1.4 | `1d9fbae` | RetrievalStatusCard（检索状态） |
| v1.1.5 | `bf19143` | ModelMonitoringCard（模型使用监控） |
| v1.1.6 | `6ad7e3b` | HttpStatusChart（HTTP 状态码甜甜圈图） |
| v1.1.7 | `4a4842d` | KnowledgeBaseOverview（知识库全景概览） |

---

## ✅ 阶段 2：v1.1.8~v1.1.14（Commit 已标注版本，Tags 已补打）

**【Git 证据】Commit 消息含版本号；Tags `v1.1.8` `v1.1.9` `v1.1.10` `v1.1.11` 已于 2026-07-30 补打推送**
**【会话证据】`eb762217` implementation_plan.md 明确标注"阶段 1：已全量验收完成卡片 (v1.1.8 ~ v1.1.14)"**

#### [x] v1.1.8: AGENT PEER 记忆中枢看护看板高密重构 ✅
- **Git**: `e4537b5` `feat(home): v1.1.8 complete AGENT PEER memory dashboard grid`
- **Tag**: `v1.1.8` (补打于 2026-07-30)
- **内容**: 9 大 Agent 节点全景监控网格，三态命名（活跃/空闲/休眠），60s 焦点感知懒拉取
- **文件**: `src/routes/home/-components/peer-memory-grid.tsx`

#### [x] v1.1.9: 监控大盘 SystemResourceChart 系统物理资源走势图 ✅
- **Git**: `00d4575` `feat(monitoring): v1.1.9 complete SystemResourceChart area chart`
- **Tag**: `v1.1.9` (补打于 2026-07-30)
- **内容**: CPU / RAM 占用率与 VikingDB 向量增长双通道面积走势图
- **文件**: `src/routes/monitoring/-components/system-resource-chart.tsx`

#### [x] v1.1.10: 技能中心 Skills 搜索过滤与 4px 高密卡片 ✅
- **Git**: `7edb47b` `feat(skills): v1.1.10 complete skills client search filtering`
- **Tag**: `v1.1.10` (补打于 2026-07-30)
- **内容**: < 5ms 无抖动搜索过滤，4px 微圆角高密网格卡片
- **文件**: `src/routes/skills/route.tsx`

#### [x] v1.1.11: 技能中心 Skills L0/L1/L2 语义摘要侧滑抽屉 ✅
- **Git**: `e2c16c5` `feat(skills): release v1.1.11 with Occam's razor UI, L0/L1/L2 drawer`
- **Tag**: `v1.1.11` (补打于 2026-07-30)
- **内容**: L0/L1/L2 三级 Tabs 侧滑 Sheet，YAML 解析防空兜底
- **文件**: `src/routes/skills/route.tsx`

#### [x] v1.1.12: 技能中心 Skills 关联资源树与文件依赖结构树视图 ✅
- **会话证据**: `b4e6a358` implementation_plan 标注为 ⏳ → `eb762217` 确认为 "阶段 1 已全量验收完成 (v1.1.8~v1.1.14)"
- **⚠️ 无独立 Git Tag**（断电中断会话期间开发，未打 Tag）
- **内容**: 技能关联资源树依赖可视化

#### [x] v1.1.13: 检索测试台 Retrieval Score 相似度得分滑动阈值筛选器 ✅
- **会话证据**: `b4e6a358` 标注为 ⏳ → `eb762217` 确认完成
- **⚠️ 无独立 Git Tag**
- **内容**: 0.0~1.0 Score 滑块过滤检索结果

#### [x] v1.1.14: 检索测试台 Retrieval 命中文档高亮与代码块预览卡片化 ✅
- **会话证据**: `b4e6a358` 标注为 ⏳ → `eb762217` 确认完成
- **⚠️ 无独立 Git Tag**
- **内容**: 命中关键字高亮，代码块预览卡片

---

## ✅ 阶段 3：v1.1.15~v1.1.18（代码已上线，会话有明确验收记录，无 Tag）

**【会话证据】全部来自会话 `d597f5c3`（2026-07-29 01:28 ~ 2026-07-30 03:27），用户明确验收**
**⚠️ 均无 Git Tag —— 断电中断导致留痕缺失，已列为历史教训**

#### [x] v1.1.15 (A/B/C): 监控中心 16 张深层监控指标 DeepMetricsGrid ✅
- **会话**: `d597f5c3` step 754：用户原文 "**1.1.15全部验收通过**"
- **内容**:
  - 15-A: API 探查 + TypeScript 类型契约 (`-types.ts`)
  - 15-B: 前 8 张核心指标 Tile（HTTP 成功率/向量数/命中率/GPU显存/Top-1准确率/Cosine相似度/EMB延迟/最长延迟）
  - 15-C: 后 8 张高级指标 Tile + Tooltip 释义 + 全量 i18n（队列状态/Peer节点/Token消耗/瘦身率/EMB速率/模型组件等）
- **文件**: `src/routes/monitoring/-components/deep-metrics-grid.tsx`

#### [x] v1.1.16: 监控中心 RTX2080Ti 显存折线图 + EMB 延迟分位柱状图 ✅
- **会话**: `d597f5c3` step 883：用户原文 "**嗯，1.1.16验收通过**"
- **内容**: GPU VRAM 区域折线图；P50/P90/P99 Embedding 延迟分位柱状图
- **文件**: `src/routes/monitoring/-components/gpu-vram-chart.tsx`、`embedding-latency-chart.tsx`

#### [x] v1.1.17: 监控中心 SLA 趋势折线图 + 召回准确率趋势 + Token 构成饼图 ✅
- **会话**: `d597f5c3` step 982：用户原文 "**1.17验收通过**"
- **内容**: 核心 SLA 历史趋势、HTTP 状态占比饼图、Top-1召回率改善曲线、Token构成占比饼图
- **文件**: `src/routes/monitoring/-components/sla-trend-chart.tsx`、`retrieval-accuracy-trend-chart.tsx`、`token-breakdown-pie-chart.tsx`

#### [x] v1.1.18: 关系图谱 /graph 路由 — 1458 节点力导向知识图谱 ✅
- **会话**: `d597f5c3` step 1659：用户原文 "**这个先算验收通过吧，后排加个优化任务，以后有空再做**"
- **内容**: 全新 `/graph` 路由；react-force-graph-2d 力导向图；1458 节点渲染；节点 Inspector 侧滑抽屉；4 大维度切片过滤器；资源/会话穿透跳转
- **文件**: `src/routes/graph/knowledge-graph-canvas.tsx`、`graph-toolbar.tsx`、`node-details-drawer.tsx`
- **📌 后排优化任务**: 白屏 Bug、会话跳转定位、性能优化（1458 节点卡顿）

---

## ✅ 阶段 4：v1.1.19~v1.1.21（正式打 Tag，完整留痕 ✅）

#### [x] v1.1.19: 任务中心 /tasks 双卡片平齐、术语统一、真数据解耦 ✅
- **Git Tag**: `v1.1.19` | **Commits**: `6d6d1b3` `6d98258` `e780a73`
- **会话**: `d597f5c3` 后段 + 当前会话 `3b9ec36b`
- **内容**: 第一性原理物理序（左=任务队列，右=工序队列），消灭假数据与调试按钮，统一"任务"领域语言，NO GREEN EVER 三态配色
- **文件**: `src/routes/tasks/route.tsx`、`src/routes/monitoring/-components/queue-status-card.tsx`

#### [x] v1.1.20: 任务中心 工序队列与流水线步骤数量 1-to-1 物理对齐 ✅
- **Git Tag**: `v1.1.20` | **Commit**: `5b5b0ca`
- **会话**: `3b9ec36b` step 1254（发现 Bug）→ step 1349（验收）
- **验收原文**: step 1349 — "**行吧行吧，那这个补丁算是通过了吧？**" ✅
- **内容**: 发现工序队列统计卡片显示 9 条，但下方 24h 任务列表实际只有 8 条工序，不一致。修复后两侧数量完全 1-to-1 物理对齐。
- **文件**: `src/routes/tasks/route.tsx`、`src/routes/monitoring/-components/queue-status-card.tsx`

#### [x] v1.1.21: 任务中心 祛除"队列"冗余后缀 全盘名称统一 ✅
- **Git Tag**: `v1.1.21` | **Commit**: `a4f0988`
- **验收**: 用户确认通过 ✅（"21、20都算通过了"）
- **内容**: 切除"嵌入向量**队列**"等 5 条冗余"队列"后缀，使卡片名称与流水线步骤名字符级 100% 对齐

#### [x] v1.1.22: 关系图谱 /graph 性能优化与白屏 Bug 修复 ✅
- **Git Tag**: `v1.1.22` | **Commit**: `ed6feca`
- **验收**: 用户确认通过 ✅（"勉强算通过吧"）
- **内容**: 修复 NaN 坐标引起的 camera / Canvas 白屏崩溃；基于 Set 缓存构建 O(1) 连线与邻居查找；`warmupTicks` 从 150/200 降低至 30 消除主线程冻结；`cooldownTime={3000}` 实现稳定后 CPU 自动归零；`GraphErrorBoundary` 防护 WebGL 上下文崩溃；`getRouterBasePath()` 修复动态 BasePath 路由跳转。
- **文件**: `src/routes/graph/-components/knowledge-graph-canvas.tsx`、`src/routes/graph/-components/node-details-drawer.tsx`、`src/routes/graph/route.tsx`

---

## 🟡 阶段 5：后续待执行任务卡片（v1.1.23 起）

> **📌 v1.1.19 迭代期间新增的架构方向**（来自 `3b9ec36b` step 599）：
> 用户明确提出「监控数据应分散到各功能页面」：
> - 监控**任务/队列**指标 → 任务中心（本次已开始执行 ✅）
> - 监控**技能**指标 → 技能中心页
> - 监控**资源**指标 → 资源库页
> - 平台级指标（HTTP/GPU/延迟/SLA）→ 保留首页监控页
> - 远期：首页监控页逐步收敛精简

#### [x] v1.1.23a (原子工单 1): MCP 网关层 Harness 经验统计与 L0 规范打标 ✅ (Deliver Pass)
- **来源**: 遵循最小粒度拆分与高内聚低耦合原则（纯后端 MCP 网关层，代码改动 < 50 行）
- **交付内容**:
  1. 在 `mcp_openviking_server.py` 中新增线程安全的 `HARNESS_METRICS` 内存计数器与 `_record_harness_call()`。
  2. 注册了新的 MCP 工具 `openviking_harness_stats`，向前端透出实时调用频次、模式与节点头统计。
  3. 实测运行通过 `python3 -c "import mcp_openviking_server as s; print(s.openviking_harness_stats())"`。
- **文件**: `/home/skloxo/aho/openclaw/mcp-openviking/mcp_openviking_server.py`
- **Git Commit**: `caafb2c`

#### ⏳ v1.1.23b (原子工单 2): 技能中心 /skills 页调用统计与演进版本展示 (Skills Page UI Only)
- **来源**: 遵循高内聚低耦合原则（纯前端 Skills 视图组件）
- **文件与边界**: 仅修改 `src/routes/skills/route.tsx`
- **目标**: 渲染 85 个技能卡片上的调用次数、最近激活时间、演进版本号 (v1.0)，与后端 100% 解耦

#### ⏳ v1.1.23c (原子工单 3): 检索测试台 /retrieval 页 L0/L1 白盒检索轨迹树 (Retrieval Page UI Only)
- **来源**: 遵循高内聚低耦合原则（纯前端 Retrieval 视图组件）
- **文件与边界**: 仅修改 `src/routes/retrieval/route.tsx`
- **目标**: 可视化绘制 Agent 任务触发时命中的 Viking L0/L1 避坑节点树与余弦相似度（如 0.985）

#### ⏳ v1.1.23d (原子工单 4): 监控页 /monitoring Token 节省率与 SLA 时延对比图 (Monitoring Page UI Only)
- **来源**: 遵循高内聚低耦合原则（纯前端 Monitoring 图表组件）
- **文件与边界**: 仅修改 `src/routes/monitoring/route.tsx`
- **目标**: 在监控页中新增 Harness L0 经验加载前后的 SLA 耗时分布与 Token 节省对比折线图

#### ⏳ v1.1.24: 基于 Reflexion / Voyager / Hermes 范式的 Skill-Loop 闭环自进化引擎 (Grounded Critique & Self-Refine Loop)
- **来源**: NousResearch Hermes-Agent 自进化范式 + Reflexion + Voyager + OpenClaw 精华融合
- **架构规范**: 参见 [HARNESS_EVOLUTION_ARCHITECTURE.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/docs/HARNESS_EVOLUTION_ARCHITECTURE.md)（含多 Agent 拓扑与时序交互图）
- **核心细节与落地设计**:
  1. **反馈捕获 (Grounded Critique)**: 任务物理校验（退出码 Exit Code 0、测试通过）通过后，捕获修正轨迹。
  2. **三段式 Lesson 萃取**: 采用 OpenClaw 的结构化模板 `CONTEXT / REFLECTION / LESSON`，生成高密度避坑摘要。
  3. **防虚假误判原则**: 只有在终端控制台物理校验通过或用户显式纠错时才记录，严禁从沉默中假想推导规则。
  4. **SKILL.md 自动热重写 (Auto Refine)**: 自动追加 `Lesson` 至 `SKILL.md`，并通过 Git Commit 留痕（`chore(harness): evolve skill <name>`）。
  5. **🧹 冗余清理**: 上线后彻底废除并清理 OpenClaw 旧单体技能 `self-improving` (`~/self-improving/`)，全盘收归 1933 向量中枢统一管理。

#### ⏳ v1.1.25: 基于微软 SkillOpt 机制的技能健康度评分与 Gate 验证矩阵 (Skill Health Scoring & Gate Verification Matrix)
- **来源**: NousResearch Hermes-Agent 评估体系 + 微软 SkillOpt 框架 (`skillopt-skill-analyzer`) 精华吸收
- **架构规范**: 参见 [HARNESS_EVOLUTION_ARCHITECTURE.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/docs/HARNESS_EVOLUTION_ARCHITECTURE.md)
- **核心细节与落地设计**:
  1. **Gate 尝试验证 (Attempt / Judge Engine)**: 借鉴 SkillOpt 的 Gate 校验逻辑，在更新 `SKILL.md` 前分别用新旧版本尝试运行 Mock 任务 (Attempt)，由评判器 (Judge) 确认效果提升后才允许通过 Gate 落地。
  2. **健康度综合得分 (0~100分)**: 基于【活跃度、成功率、修正频次、避坑积累量】四维加权计算技能健康得分。
  3. **优胜劣汰与警告降级**: 分数低于 60 分的技能给予警告高亮并提供自动修复建议，高分优秀技能获得 Prompt 最高权重倾斜。
  4. **🧹 架构收归**: 将原本 OpenClaw 5050 端口的 Flask 外挂分析器（`skillopt-skill-analyzer`）核心打分逻辑 100% 重构收归为 OpenViking 1933 的原生 API。

#### ⏳ v1.1.26: 技能创生、克隆与在线沙盒测试器 (Autonomous Skill Creation & Playground)
- **来源**: EvoSkills 自动构建范式
- **架构规范**: 参见 [HARNESS_EVOLUTION_ARCHITECTURE.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/docs/HARNESS_EVOLUTION_ARCHITECTURE.md)
- **核心细节与落地设计**:
  1. **自然语言创生**: 支持通过自然语言描述自动生成符合 YAML Frontmatter + Markdown 规范的全新技能模板。
  2. **在线语法与 YAML 校验**: 在 OpenViking Studio 页面提供带语法高亮的在线 `SKILL.md` 编辑器与结构校验。
  3. **沙盒 Simulate 测试器**: 支持在 Web 页面上一键模拟触发该技能，透视 Agent 的 Payload 与响应，验证成功后再发布至 Viking 向量库。

#### ⏳ v1.1.27: 资源库 /resources 历史版本追踪与一键回滚 (Resource Version History & Rollback)
- **来源**: 对应 OpenViking Dashboard (`/dashboard/resources`) 经典功能对齐
- **目标**:
  1. **资源头部控制**: 资源预览区右上角增加「查看历史版本」主按钮（位于文件 URI 描述旁）。
  2. **历史版本时间轴弹窗 (History Versions Dialog/Modal)**:
     - 弹窗呈现目标 URI（如 `viking://resources/.../.abstract.md`）的 Commit 历史版本链。
     - 时间轴卡片包含：修改摘要 ("更新了产品文档"/"修复错别字")、时间戳 ("2023-10-27 14:30")、操作人 ("by admin")。
  3. **历史内容预览 (View Content)**:
     - 弹窗卡片提供「查看文件内容」按钮，支持查看该历史版本文本与 Diff 差异对比。
  4. **一键恢复/回滚 (One-Click Rollback)**:
     - 卡片右侧提供「回滚至此版本」动作按钮，触发二次确认后发起版本恢复并更新向量与图谱索引。

#### ⏳ v1.1.28: 首页 /home 6 大卡片信达雅视觉精修
- **目标**: 审查首页 6 大数据卡片布局、颜色、字体、圆角是否 100% 合规

#### ⏳ v1.1.29: 检索测试台 /retrieval 命中关键字精确高亮
- **目标**: Score 滑块实时过滤，命中关键字高亮精准

#### ⏳ v1.1.30: 会话中心 /sessions 跨 Agent 共享历史与记忆透视
- **目标**: 查看 Antigravity/OpenClaw/Hermes 各 Agent 对话链及 OpenViking 记忆沉淀节点

#### ⏳ v1.1.31: 设置页面 /settings 1933/1936 反向代理健康诊断与 API Key 管理
- **目标**: 准确呈现代理连通性与 Dev/Production 模式鉴权状态

#### ⏳ v1.1.32: 监控数据重分配 — 技能/资源监控指标归位各功能页
- **背景**: 来自 `3b9ec36b` step 599 架构方向
- **目标**: 将监控页中技能、资源相关指标卡片迁移至各自功能页，监控页仅保留平台级指标

#### ⏳ v1.1.33: 技能中心 /skills 全面管理迭代 — 入口改名 + 指标展示 + 运营能力
- **来源**: `d597f5c3` step 469 — "技能中心这块儿增加一个迭代任务，往后排"
- **目标**:
  1. 侧边栏入口"技能"改名为**"技能中心"**，页面标题同步
  2. 展示 85 个技能的关键指标（调用次数、触发频率、最近激活时间）
  3. 技能分类管理（按 `agent`/`user` scope 分组，支持搜索过滤）
  4. 远期：支持云服务/公网接入，对外开放技能市场
- **文件**: `src/routes/skills/route.tsx`、侧边栏 i18n

#### ⏳ v1.1.34: 任务中心 /tasks 时间范围自定义下拉选择器
- **来源**: `3b9ec36b` step 184 — "在任务中心让用户自己手动去选，他想看几天看几天"
- **目标**:
  1. 顶部下拉默认选「近 24 小时」，可切换「近 7 天」「近 30 天」「全部数据」
  2. 去掉隐晦的归档机制，给用户透明的时间范围控制权
  3. 切换后任务列表与统计卡片数据同步刷新
- **文件**: `src/routes/tasks/route.tsx`

#### ⏳ v1.1.35: 关系图谱 /graph 深度性能二次重构（LOD 分级渲染 & WebGL 视口剪裁）
- **来源**: v1.1.22 验收反馈（"太卡了，还是不行。在最后再加个任务卡片，继续优化迭代吧"）
- **目标**:
  1. 针对 1458 节点与 3,890 条连线引入 LOD (Level of Detail) 视距动态分级渲染
  2. 视口外节点 Viewport Culling 自动剪裁隐去
  3. 优化纯 GPU 顶点着色与 Batching，彻底提升低配 GPU 帧率

#### ⏳ v1.1.36: 360° OpenViking 核心服务可观测性与健康度指标迭代 (Observability & Health Dashboard)
- **来源**: 2026-08-01 1933 冻结事故与用户可观测性排查反馈
- **目标**:
  1. **首页 /home — 存活红绿灯与降级模式指示器 (Health Badge & Mode Indicator)**:
     - 增加 `1933 API (1.5ms)`、`11432 Embedding-8B (在线)`、`11433 Reranker-0.6b (在线)` 实时心跳徽章。
     - 显示运行模式指示器（`HTTP + CLI 双模式` 或 `CLI-Only 降级警报`）。
     - 引入 CPU/内存红线警告 Banner（CPU > 80% 或线程池死锁时高亮预警）。
  2. **监控页 /monitoring — API 时延分位与降级率图表**:
     - 新增 API P95 / P99 响应耗时折线图 (`find` / `read` / `write`)。
     - 新增 Embedding 与 Reranker 本地 LLM 模型推理耗时统计。
     - 监控并展示 MCP CLI 降级发生率统计。
  3. **任务中心 /tasks — 概念引导与空状态预警**:
     - 显式文案说明："任务中心用于呈现离线重索引与长时批处理 Task"。
     - 列表为空时提供友好空状态提示（"当前离线批处理队列空闲，所有 1933 实时 API 正常运行中"），防止误判挂掉。

#### ⏳ v1.1.37: WebDAV 云网盘挂载中心与图形化连接配置 (WebDAV Cloud Drive Management)
- **目标**: 
  1. 提供 WebDAV 挂载向导（支持 Linux davfs2 / Windows 映射网盘 / macOS Cyberduck 提示）
  2. 提供 WebDAV 账户/Token 独立管理与鉴权校验
  3. 提供在线 WebDAV 文件目录流预览

#### ⏳ v1.1.38: 向量库全量/增量备份与一键在线灾备恢复 (Backup & Restore)
- **目标**:
  1. 支持手动/定时创建 `~/.openviking/data` 数据快照
  2. 提供快照历史列表、占用体积展示与 ZIP 导出
  3. 支持选择历史快照发起一键在线恢复

#### ⏳ v1.1.39: 关系图谱 /graph 可视化手动连线与断开编辑器 (Graph Relation Editor)
- **目标**:
  1. 图谱画布支持“连线模式”：鼠标拖拽 Node A -> Node B 弹窗创建关系 (`openviking_link`)
  2. 点击边线（Edge）支持查看关系属性与一键断开 (`openviking_unlink`)
  3. 集成 `openviking_get_relations` 关系全路径透视

#### ⏳ v1.1.40: 资源库 /resources 隐私标记 (Privacy Tags) 与 PII 脱敏开关
- **目标**:
  1. 支持为资源/记忆设置隐私等级（Public / Private / Confidential）
  2. 检索测试台与会话中心集成隐私擦除与脱敏展示开关

#### ⏳ v1.1.41: 设置页 /settings 系统一致性校验 (Consistency Check) 与孤立节点修复
- **目标**:
  1. 调用 `openviking_consistency` 检查 SQLite 元数据与向量索引对齐状态
  2. 提供“一键修复孤立节点” (Orphan Node Repair) 运维按钮

---

## 📊 迭代总览

| 版本段 | Tag 状态 | 验收证据 | 备注 |
|--------|---------|---------|------|
| V1.0.0, v1.1.0 | ✅ 正式 Tag | — | 最早基建 |
| v1.1.8~v1.1.11 | ✅ 补打 Tag (2026-07-30) | commit 消息含版本号 | — |
| v1.1.12~v1.1.14 | ❌ 无 Tag | `eb762217` impl_plan 确认完成 | 断电丢失 |
| v1.1.15~v1.1.18 | ❌ 无 Tag | `d597f5c3` step 754/883/982/1659 明确验收 | 断电丢失 |
| v1.1.19 | ✅ 正式 Tag | `3b9ec36b` step 1112 "验收通过了，封板吧" | ✅ 完整 |
| v1.1.20 | ✅ 正式 Tag | `3b9ec36b` step 1349 "这个补丁算是通过了吧" | ✅ 完整 |
| v1.1.21 | ✅ 正式 Tag | "21、20都算通过了" | ✅ 完整 |
| v1.1.22 | ✅ 正式 Tag | "勉强算通过吧" | ✅ 完整 (commit `ed6feca`) |

