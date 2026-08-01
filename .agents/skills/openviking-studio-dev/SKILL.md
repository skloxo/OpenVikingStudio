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

---

## 一、三层文档权威规范 (3-Tier Document System)

1. **唯一活跃工单看板** ➔ [REFACTORING_PLAN.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/REFACTORING_PLAN.md)
   - 仅保留当前 1-2 个迭代即将执行的原子工单（数据契约明确、量化验收标准清晰）。
   - 禁止在此写入未拆解的远期愿景或大型 Epic。
2. **远期 Epic 路线图** ➔ [ROADMAP.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/ROADMAP.md)
   - 存放 `v1.1.24` (Skill-Loop)、`v1.1.25` (Gate Engine) 等大型愿景，进入开发时再拆解为原子工单下发。
3. **历史交付档案** ➔ [DELIVERY_ARCHIVE.md](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md)
   - 归档所有已验收通过的版本履历 (`v1.1.0` ~ `v1.1.23d`+)。

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
