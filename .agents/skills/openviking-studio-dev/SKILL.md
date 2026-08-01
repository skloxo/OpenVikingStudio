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

## 四、闭环构建与交付 SOP (Deployment & Verification)

1. **构建与部署同步命令**：
   ```bash
   npm run build && cp -r dist/* /home/skloxo/.local/lib/python3.12/site-packages/openviking/web_studio/dist/
   ```
2. **版本留痕铁律**：
   - 完成迭代后打 Git Tag：`git tag -a v1.1.x <hash> -m "release: v1.1.x <摘要>"`
   - 将交付记录追加至 `DELIVERY_ARCHIVE.md`，并同步更新 `REFACTORING_PLAN.md`。

---

## 六、 技能治理与自动规范装载双重防线 (Skill Governance & Auto-Standardization Pipeline)

1. **第一道防线：Agent 下载/生成技能闭环**
   - 每当 Agent 在 IDE/命令行下载、克隆或生成新技能后，**必须自动触发物理检查**，校验其是否包含标准的 `SKILL.md` 和 YAML Header (`name`, `description`)。
   - 若不合规，Agent 自动推导补充标准 YAML Header 与 SOP 规约，并自动软链接上架到 `~/.openviking/skills/`，向 OpenViking 向量库注册。
2. **第二道防线：Web 控制台白盒曝光与一键规范化**
   - 技能中心 UI 必须同时展示 `已就绪合规技能` 与 `⚠️ 待规范技能`。
   - 对漏网之鱼，UI 提供 `⚡ 一键规范化上架` 交互流程，用户点击确认后自动补全上架，实现技能的最佳实践曝光与 100% 自动触发率。
