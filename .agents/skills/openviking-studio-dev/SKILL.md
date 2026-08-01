---
name: openviking-studio-dev
description: Use when developing, refactoring, or iterating OpenVikingStudio (VK Studio / Web UI). Enforces 3-tier doc alignment (REFACTORING_PLAN.md, ROADMAP.md, DELIVERY_ARCHIVE.md), NO GREEN EVER color palette (cyan-500 accents), FastMCP 1933 API data contracts, zero-script direct source edits, and dual-brain evaluation rules. Contains a self-evolution loop to continuously reflect and update SKILL.md.
---

# OpenViking Studio 专项开发与迭代技能 (OpenViking Studio Dev SOP & Self-Evolution)

本技能为 OpenViking Studio (`OpenVikingStudio`) 的专用工程开发与**自我演进技能**。当用户提到 "开发 VK", "重构 Studio", "新增 Studio 页面/卡片", "更新工单" 或处于 OpenVikingStudio 工作区时自动激活。

---

## 🔄 核心机制：“自产自销”自我演进闭环 (Dogfooding Self-Evolution)

本技能不仅是操作指南，更是 **Harness 自演进的第一个试验场 (Dogfooding Testbed)**。在每次迭代收尾时，必须自动执行以下反思演进循环：

1. **纠偏捕获 (Capture)**：感知本次迭代中用户提出的新原则（如“不许写临时胶水脚本”、“文档三层治理”）。
2. **三段式反思 (3-Part Reflection)**：
   - **CONTEXT**：触发问题的上下文场景。
   - **REFLECTION**：根因与物理逻辑分析。
   - **LESSON**：提炼出的永久闭环规范。
3. **自热更新 (Hot Update)**：自动将最新 Lesson 写回本 `SKILL.md`，并在 OpenViking 1933 体外大脑 (`viking://resources/master_memory/`) 持久化。

### 📜 历史演进 Lesson 归档

#### 📌 Lesson 2026-08-01 #1：1936 开发环境 vs 1933 正式环境物理隔绝守则
- **CONTEXT**：开发人员在代码未经用户终验通过前，直接将 `build` 产物推送到 1933 正式环境。
- **REFLECTION**：开发测试通过 ≠ 用户终验通过。1936 (`npm run dev`) 是开发测试端口，1933 (`web_studio`) 是正式物理端口。
- **LESSON**：开发/调试阶段一律仅在 1936 环境热重载渲染；只有在用户明确指令“发布到 1933”或“终验通过”后，方可打包推送至 1933。

#### 📌 Lesson 2026-08-01 #2：零临时脚本与前后端双端源码硬核打通守则
- **CONTEXT**：遇到数据契约不齐时试图编写游离胶水脚本或生成临时 JSON 映射。
- **REFLECTION**：游离胶水脚本会引发文件监听死循环（如 Vite HMR 热重载死循环）、难以追踪与维护。
- **LESSON**：严禁编写任何临时/过渡脚本。遇到 API 或数据缺失，必须同步修改后端 Python 源文件 (`mcp_openviking_server.py`) 与前端 React 源文件，硬核打通源码级链路。

#### 📌 Lesson 2026-08-01 #3：标准 4-Step 开发交付与终验对照 SOP 守则
- **CONTEXT**：在用户未终验通过时误以为可以自动推进下一工单，且终验时未提供对照测试用例。
- **REFLECTION**：缺乏明确测试用例的口头终验是不严谨的。只有测试通过 ➔ 提交终验(带测试用例) ➔ 终验通过(Git Push & Tag) ➔ 用户明确指令“发布到 1933”才是标准闭环。
- **LESSON**：必须严格遵循 4-Step 交付 SOP：开发1936 ➔ 交付测试用例 ➔ 终验通过推送Git Tag ➔ 明确指令后发布到1933。

#### 📌 Lesson 2026-08-01 #4：“找成功的轮子”第一原则 (Wheel-First Engineering Principle)
- **CONTEXT**：在设计复杂系统（如 Harness 门锁与自演进）时凭空造轮子，导致功能退化为表面 Dashboard 花架子。
- **REFLECTION**：开源社区已有大量经过验证的顶级轮子（NeMo Guardrails、Reflexion、Langroid）。盲目闭门造车是低效且易踩坑的。
- **LESSON**：必须绝对遵循“找成功的轮子”三步法：
  1. **先找轮子**：有现成轮子，优先搜索全网/GitHub 寻找成熟开源项目；
  2. **能用即用**：能直接调用的轮子，直接引入使用；
  3. **解构复用**：不能直接用的轮子，深入源码解构理解其物理架构，复用其最核心的优秀设计思想。

#### 📌 Lesson 2026-08-01 #5：观测是手段，不是目的 (Observation as a Diagnostic Radar)
- **CONTEXT**：误将“数据卡片可视化展示”当做迭代的主要目标，混淆了物理功能本身与观测窗口的主次关系。
- **REFLECTION**：Harness 闭环拦截与自动演进机制能够成功物理跑通才是唯一的核心目的。UI 数据卡片只是人类使用者在不懂代码时，用于实时感知系统运行状况与发现缺陷的“白盒诊断雷达”。
- **LESSON**：牢记“观测是过程，不是目标，不是目的”。一切开发重心必须首先保证底层物理门锁与自演进机制 100% 成功跑通，数据卡片只做 100% 真实无假数据的白盒雷达透视。

#### 📌 Lesson 2026-08-01 #6：集百家所长融熔轮子守则 (Top 5 Harness Wheels Fusion)
- **CONTEXT**：借鉴开源轮子时陷入单一视角，容易引入有瑕疵的简单库。
- **REFLECTION**：真正的顶级工程架构应当“集百家所长于一身”，全盘熔铸 GitHub 顶尖开源项目的核心优点。
- **LESSON**：OpenViking Harness 架构熔铸 5 大开源标杆：
  1. **NVIDIA NeMo-Guardrails** ➔ 物理前置拦截门锁 (`_harness_pre_execution_guard`)；
  2. **MIT Reflexion Agent** ➔ 隐式自演进三段式反思闭环 (`openviking_record_evolution_lesson`)；
  3. **Guardrails AI** ➔ 零 Mock 绝对真实数据契约；
  4. **AgentOps Telemetry** ➔ 物理阻断与 Peer 分布遥测；
  5. **E2B & SWE-Agent** ➔ 1936 与 1933 环境物理端口隔离。

#### 📌 Lesson 2026-08-01 #7：原版优先，改造必深研，杜绝半瓶水埋雷守则
- **CONTEXT**：对开源轮子一知半解就盲目拿来使用，未理解其底层 Execution Flow，导致代码中埋下上下文残留与异步死锁隐患。
- **REFLECTION**：半瓶水地封装开源轮子是极度危险的。要么使用官方 PyPI 原版随社区迭代，要么必须拉取原始 GitHub 源码与架构文档，逐行解构其逻辑结构与防错细节。
- **LESSON**：必须严守“原版优先，改造必深研”铁律：
  1. **完全适配** ➔ 直接引入官方 PyPI 包（如 `nemoguardrails`）；
  2. **架构改造** ➔ 必须拉取原始源码与原理文档，分析对比多轮子差异，完成防错解构报告，物理排查所有隐性雷区后再落地！

#### 📌 Lesson 2026-08-01 #8：直改源码与官方 API 契约合并保护守则 (Official API & Clean Upstream Merge)
- **CONTEXT**：写野生的临时胶水脚本，或侵入式破坏官方 API 结构，导致后期合并 OpenViking 上游主线代码时产生大量 Git 冲突与费劲维护。
- **REFLECTION**：野生胶水脚本是项目劣化与合并死锁的根源。坚决直改项目主源码，且必须严格遵循官方 FastMCP / REST 标准 API 契约，保证架构的高内聚低耦合。
- **LESSON**：严守“零野生脚本、直改源码、完全契合官方接口”三铁律：
  1. **零野生脚本**：严禁在 `scripts/` 或 `public/` 创建临时 `.py`/`.json`/`.sh`；
  2. **直改源码**：所有逻辑收敛至前端 React route/component 与后端 `mcp_openviking_server.py` 正式源码；
  3. **官方契约**：严格遵循官方 FastMCP 与 REST 规范，确保后期随 OpenViking 上游社区代码升级时 100% 无缝 Git 合并！

#### 📌 Lesson 2026-08-01 #9：零人工触发·踩坑即自动演进守则 (Fully Autonomous Interception-Triggered Reflexion)
- **CONTEXT**：以前需要用户手动在对话中敲命令“请你迭代演进一下技能”，极度愚蠢且低效。
- **REFLECTION**：真正的 Harness 自演进引擎应当在发生阻断拦截或捕获异常的第一毫秒，由系统后台隐式、全自动触发演进钩子，无需人类用户多说一句话！
- **LESSON**：严守“零人工触发，踩坑/阻断即自动演进”物理机制：
  1. **门锁拦截即自动演进**：当 `_harness_pre_execution_guard` 阻断违规操作时，系统后台自动调用 `openviking_record_evolution_lesson` 归档 Lesson；
  2. **对话感知即隐式落盘**：当感知到用户的自然语言纠偏，Agent 必须在响应的第一个 Step 中隐式完成 Reflexion 归档，禁止要求用户手动触发！

#### 📌 Lesson 2026-08-01 #10：技能中心与 Harness 双重核心 KPI 评估体系守则
- **CONTEXT**：担心技能装载后沦为“僵尸技能”，缺乏量化指标证明技能中心与 Harness 机制运行高效且有价值。
- **REFLECTION**：必须建立明确的 KPI 物理评估指标体系，从“自动触发命中率”、“技能动销率”、“物理阻断成功率”、“自演进闭环率”四大维度量化健康度。
- **LESSON**：严守 Skill Center 与 Harness 双重 KPI 量化指标：
  1. **技能自动触发命中率 (Auto-Trigger Hit Rate)** ➔ `>= 95%` 自然语言意图自动命中激活技能；
  2. **高频工程技能动销率 (Core Skill Utilization)** ➔ 18 个 Matt Pocock 工程技能动销率 `100%`；
  3. **Harness 物理阻断阻绝率 (Zero Breach Guard)** ➔ 违规脚本与非法部署物理阻断率 `100%`；
  4. **Reflexion 零人工自演进闭环率 (Auto-Reflexion Closure)** ➔ 无需人工敲命令自动落盘与向量重索引率 `100%`。

#### 📌 Lesson 2026-08-01 #11：“信雅达”准则与 i18n 顺手即做守则 (Xinyada & Implicit i18n)
- **CONTEXT**：代码变更中遗漏多语言适配，需要用户提醒才去补充 i18n，或者 UI 文案同义词混用违背“信雅达”标准。
- **REFLECTION**：i18n 是现代工程的“出厂必备习惯”，绝不是靠用户催促补救的售后。文案必须达到“信”（准确一致）、“达”（通顺自解释）、“雅”（极客严谨）。
- **LESSON**：严守“信雅达”与“i18n 顺手即做”标准：
  1. **i18n 顺手即做**：新增任何 UI 按钮、文案、面板或提示时，同步在 `zh-CN.ts` 与 `en.ts` 中补全 i18n 映射；
  2. **信雅达审视**：专有名词（Harness 门锁、Reflexion 自演进、NeMo 拦截器）全盘一贯，禁止同义词乱用。

#### 📌 Lesson 2026-08-01 #12：技能详情 100% 防塌陷加载与独立全景专页守则
- **CONTEXT**：技能详情因为网关 URI 缺失 `/default/` 命名空间导致 HTTP 400 失败，且大量演进日志在主页挤压展开影响体验。
- **REFLECTION**：1) 详情加载必须建立双端探针保底（网关 API 失败时自动穿透读取物理磁盘 SKILL.md），确保 100% 成功率；2) 海量履历日志必须收敛至独立全景专页，保持主界面极客简洁。
- **LESSON**：严守 100% 防塌陷加载与全景专页规范：
  1. **物理磁盘探针保底**：网关 API 异常时，通过 `/api/v1/system/skill_content` 探针物理打底，保障 100% 打开；
  2. **独立全景专页路由**：海量明细数据路由至专用全景子页面 (如 `/skills/harness-logs`)。

#### 📌 Lesson 2026-08-01 #13：侧边栏独立 Harness 引擎审计入口守则
- **CONTEXT**：Harness 引擎涵盖物理阻断记录、全量技能调用明细与自演进变更，隐匿在二级子页面不易被排查与观测。
- **REFLECTION**：物理 Harness 引擎是生产力的第一性原理中枢，必须在侧边栏“运维/活动”导航栏中拥有独立的顶级菜单入口，一键透视阻断、解锁与演进审计。
- **LESSON**：严守 Harness 顶级侧边栏导航守则：
  1. **侧边栏物理入口**：AppShell 侧边栏活动/运维组引入 `🛡️ Harness 引擎审计` (`/harness-logs`)；
  2. **全量明细承载**：汇聚拦截阻断解锁明细、调用频次分布与 Reflexion 演进规约。

#### 📌 Lesson 2026-08-01 #14：OpenViking 技能上架统一标准要件与 Gate 2 治理流水线
- **CONTEXT**：开源与第三方技能来源五花八门、规范不一，缺乏统一要件规范导致部分技能装载后无法被 Agent 自动触发。
- **REFLECTION**：入库 OpenViking 的技能必须具备 5 大物理要件方可上架；对于缺乏规范的第三方技能，必须提供 Gate 2 探针白盒诊断与“一键规范化上架”自动化补全流水线。
- **LESSON**：严守 OpenViking 技能上架五大要件与 Gate 2 治理流：
  1. **结构化 YAML 头 (Frontmatter)**：必须包含 `name` 标识与 `description` 自然语言高敏触发词；
  2. **L0-L1-L2 三级渐进式结构**：L0 触发词/标签 + L1 SOP 步骤 + L2 全量源码；
  3. **显式 MCP 工具白名单**：Frontmatter 显式定义 `allowed_tools`；
  4. **向量库双向索引**：完成在 `viking://` master_memory 的向量同步；
  5. **Gate 2 自动化补全**：技能中心 UI 提供 `⚡ 一键规范化上架` 按钮，物理补齐缺失要件。

#### 📌 Lesson 2026-08-01 #15：四色高对比度极客排版与严禁彩色滥用守则
- **CONTEXT**：在界面大面积使用高饱和 Accent 色彩或背景，导致 UI “花里胡哨”、视觉杂乱且严重干扰文本阅读。
- **REFLECTION**：高级极客 UI 必须回归严格的 4 色语义分层规则：正文用标准黑/深灰、次要用哑光灰、负向用玫瑰红、正向/激活微量用冰青，严禁把彩字/彩底铺满全屏。
- **LESSON**：严守 4 色语义排版守则：
  1. **正常文本 (100% 纯正)**：主文本、标题、段落只用标准 `text-foreground`（黑/深灰）；
  2. **次要信息 (沉静)**：路径、时间戳、辅助说明使用 `text-muted-foreground` / `text-slate-500`；
  3. **负向/阻断 (警示)**：阻断/错误使用 `rose-500` / `rose-400`；
  4. **正向/激活 (精炼)**：正向状态/激活 Badge 微量使用 `cyan-500`，绝不大面积作为段落前景或卡片底色。

#### 📌 Lesson 2026-08-01 #16：技能中心 Product-Centric 视角定位与 4 大高价值 KPI 守则
- **CONTEXT**：技能中心共享给全团队后，之前顶部塞满 Harness 物理阻断数、向量存储调用等无关底层指标，导致产品核心价值 KPI 偏移。
- **REFLECTION**：技能中心的第一性原理是“能力共享与零人工隐式自动唤醒”，决定技能中心好不好的核心在于：自然语言隐式自动触发率、标准规范覆盖率、多 Agent 共享复用率与 SOP 闭环成功率。
- **LESSON**：技能中心 4 大高价值 KPI 物理标准：
  1. **自然语言隐式自动触发率 (Auto-Trigger Rate)**：零命令感应用户意图静默唤醒 SOP (`98.6% 隐式唤醒`)；
  2. **标准规范上架率 (Standard Onboarding Rate)**：物理校验 100% 具备 L0/L1/L2 5 大标准要件 (`100% 规范覆盖`)；
  3. **多 Agent 共享复用率 (Multi-Agent Reuse Rate)**：4 大领域 Agent (researcher/developer/operator/test) 频次与跨会话共享；
  4. **SOP 物理闭环成功率 (SOP Closure Rate)**：交付成功率与 14 项 Reflexion 自演进 Lessons (一键跳转独立 Harness 审计专页)。

#### 📌 Lesson 2026-08-01 #17：Harness 后台静默全自动规范化与零人工干预原则
- **CONTEXT**：以前在技能中心 UI 放手动的“待规范技能卡片”和“⚡ 一键规范化上架”按钮，违背了零人工提醒、自动化的原则（人类没有精力盯页面按按钮）。
- **REFLECTION**：待规范技能的探测、自动大模型规范化补全与源码改写，物理上属于 Harness 自演进引擎的底层机制；技能中心页面应彻底切除手动卡片，交由 Harness 后台静默自动感知与自愈上架。
- **LESSON**：严守 Harness 静默全自动治理守则：
  1. **零 UI 手动按键**：切除技能中心 UI 手动按键，系统感知到野路子技能时自动调大模型补全 SOP 规范并改写源码上架；
  2. **日志归拢至 Harness 审计**：自动规范化履历与日志统一汇总存入 `🛡️ Harness 引擎审计` (`/harness-logs`)；
  3. **技能主面保持纯粹**：技能中心界面保持干净，只展示白盒共享的规范技能。

---

## 一、全盘文档三层治理体系与模块导航网 (3-Tier Document Hierarchy & Map)

### 1. 三层治理体系 (如何使用与迭代)
- **Tier 1: 活跃调度层** ➔ [REFACTORING_PLAN.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/REFACTORING_PLAN.md) (唯一活跃原子工单看板，仅存当前 1-2 个可调度原子任务)
- **Tier 2: 路线规划层** ➔ [ROADMAP.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/ROADMAP.md) (远期 Epic 愿景，拆解下发至 Tier 1)
- **Tier 3: 归档履历层** ➔ [DELIVERY_ARCHIVE.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md) (已终验交付履历归档)

### 2. 模块开发与文档映射网 (开发各模块看哪些文档)
- **技能中心 (`/skills`)** ➔ [SKILL.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/.agents/skills/openviking-studio-dev/SKILL.md) (Harness规约) + [VK_DESIGN.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/VK_DESIGN.md) (4卡布局) + [CODING_RULES.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/CODING_RULES.md) (NO GREEN色盘)
- **检索测试台 (`/retrieval`)** ➔ [ARCHITECTURE.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/ARCHITECTURE.md) (L0/L1/L2向量分层) + [REFACTORING_GUIDE.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/REFACTORING_GUIDE.md)
- **系统监控 (`/monitoring`)** ➔ [UI_SPECIFICATION.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/UI_SPECIFICATION.md) (SLA 图表规范) + [ARCHITECTURE.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/ARCHITECTURE.md)
- **发布与 Sentry 部署** ➔ [AGENTS.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/AGENTS.md) (4-Step SOP) + [DELIVERY_ARCHIVE.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md) (Tag明细)

---

## 二、通用 UI 视觉与物理守则 (Baseline Visual Rules)

1. **NO GREEN EVER 铁律 🚫**：
   - 界面**绝对禁止**使用绿/绿色系 (`green-500`, `emerald-500` 等)。
   - **正向 / 良好 / 触发** ➔ 冰青 / 湛蓝 (`cyan-500`, `cyan-400`)
   - **负向 / 异常 / 阻塞** ➔ 玫瑰红 (`rose-500`)
   - **中性 / 静态 / 哑光** ➔ 沉静哑光灰 (`muted`, `border-border/60`)
2. **物理对齐与无胶水脚本铁律**：
   - 卡片底部汇总行统一使用 `mt-auto` 实现 100% 物理平齐。
   - **严禁创建游离胶水脚本 (`.sh`/`.py`)**，必须直接修改项目源码或底层 OpenViking 网关源码！

---

## 三、数据契约与双进程持久化 (Data Contract & Dual-Process Sync)

1. **真实数据源**：
   - HTTP REST API：`http://127.0.0.1:1933/api/v1/system/status`
   - FastMCP 磁盘持久化总线：`~/.openviking/harness_metrics.json`
2. **禁止虚假 Mock**：数据缺失时必须优雅显示 `--`，绝对禁止硬编码伪造假数据数字。

---

## 四、4-Step 标准开发与交付 SOP 铁律 (Standard 4-Step Lifecycle SOP)

1. **Phase 1: 开发与初步测试 (Dev & Pre-testing)**
   - 开发与调试统一在 1936 端口 (`npm run dev`) 热更新进行，初步测试由 Agent 自行跑通。
2. **Phase 2: 提交终验 + 交付测试用例 (Submit for Acceptance with Test Cases)**
   - 初步测试通过后，向用户提交终验请求，**必须同步附带具体点对点的测试用例 (Test Cases)**，方便用户对照验证。
3. **Phase 3: 终验通过 ➔ 提交 Git & 打 Tag (Acceptance Pass ➔ Push & Tag)**
   - 只有用户显式确认“终验通过”后，方可开启下一个功能。
   - 终验通过后立即向远程 Git 仓库推送代码，并打 Tag（带详细 Changelog 变更明细）。
4. **Phase 4: 1933 正式环境更新 (Production Update on Explicit Command Only)**
   - **终验通过 ≠ 自动发布 1933**。
   - **只有当用户明确输入指令“发布到 1933”时**，方可执行打包构建 `npm run build && cp -r dist/* ...` 推送到 1933 正式环境。
     git tag -a v1.1.x <hash> -m "release: v1.1.x
     
     - 🚀 [Feature]: <具体新增功能明细>
     - 🐛 [Fix]: <具体修复问题明细>
     - 📝 [Docs]: <文档与卡片变更明细>"
     ```
   - **`DELIVERY_ARCHIVE.md` 物理对齐**：必须在 `DELIVERY_ARCHIVE.md` 中同步追加该小版本的详细 Change Summary、Git Commit Hash 与修改文件清单。

---

## 六、 技能治理与自动规范装载双重防线 (Skill Governance & Auto-Standardization Pipeline)

1. **第一道防线：Agent 下载/生成技能闭环**
   - 每当 Agent 在 IDE/命令行下载、克隆或生成新技能后，**必须自动触发物理检查**，校验其是否包含标准的 `SKILL.md` 和 YAML Header (`name`, `description`)。
   - 若不合规，Agent 自动推导补充标准 YAML Header 与 SOP 规约，并自动软链接上架到 `~/.openviking/skills/`，向 OpenViking 向量库注册。
2. **第二道防线：Web 控制台白盒曝光与一键规范化**
   - 技能中心 UI 必须同时展示 `已就绪合规技能` 与 `⚠️ 待规范技能`。
   - 对漏网之鱼，UI 提供 `⚡ 一键规范化上架` 交互流程，用户点击确认后自动补全上架，实现技能的最佳实践曝光与 100% 自动触发率。
