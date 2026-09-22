#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Auxiliary Documentation Governance & Dehydration Script.
Reorganizes completed task cards from REFACTORING_PLAN.md into DELIVERY_ARCHIVE.md,
ensuring 100% zero-loss archiving, bidirectional cross-linking, and attention compaction.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def main():
    plan_path = REPO_ROOT / "REFACTORING_PLAN.md"
    archive_path = REPO_ROOT / "DELIVERY_ARCHIVE.md"

    plan_text = plan_path.read_text(encoding="utf-8")
    archive_text = archive_path.read_text(encoding="utf-8")

    # Locate sections in REFACTORING_PLAN.md
    wave1_idx = plan_text.find("### 🌊 Wave 1:")
    card1_idx = plan_text.find("#### 📌 [P0] [x] Card 1:")
    card18_idx = plan_text.find("#### 📌 [P1] [x] Card 18:")

    assert wave1_idx != -1, "Wave 1 not found"
    assert card1_idx != -1, "Card 1 not found"
    assert card18_idx != -1, "Card 18 not found"

    # Slice Milestone 4 content (Card 18 & Card 19)
    milestone4_content = plan_text[card18_idx:].strip()

    # Slice Milestone 3 Cards 1-17 content
    milestone3_cards_content = plan_text[card1_idx:card18_idx].strip()

    # Slice Milestone 3 Waves 1-5 content
    milestone3_waves_content = plan_text[wave1_idx:card1_idx].strip()

    # Build new Milestone 4 section in DELIVERY_ARCHIVE.md
    ms4_section = f"""## 🏆 Milestone 4 (v1.5.75 ~ v1.5.76) 全量交付总览 (已 100% 验收交付)

> **阶段成果总结**：
> 1. **Stanford DSPy (MIPO) 强类型提示词编译管线 (`v1.5.75`)**：落实 `BLUEPRINT.md` 课题五轮子 #5，实现启发式输入输出强类型 Schema 规约提取、Few-Shot 黄金样本动态自优化排序、Strict JSON 强类型输出格式固化与不可变边界注入，编译耗时 0.87ms，契约状态 PASS 零幻觉；
> 2. **亚毫秒级 LRU 本地二级缓存引擎 (`v1.5.76`)**：落实 `BLUEPRINT.md` 课题四与高并发性能加速规范，基于 `collections.OrderedDict` 与 `threading.RLock` 构建线程安全 LRU 缓存，支持 TTL 淘汰与 `wait=False` 非阻塞防击穿/雪崩协议，10,000 并发压测实测平均延迟 0.0007ms，零绿色座舱监控总盘就绪。

### 📋 Milestone 4 核心任务规格卡片详单

{milestone4_content}
"""

    # Build new Milestone 3 section in DELIVERY_ARCHIVE.md
    ms3_section = f"""## 🏆 Milestone 3 (v1.5.01 ~ v1.5.74) 全量交付总览 (已 100% 验收交付)

> **阶段成果总结**：
> 1. **全套自进化与质量门禁闭环**：落实 LiveGen 在线技能创生脚手架 (`v1.5.71`)、PrivacyMasker 统一端到端隐私脱敏引擎 (`v1.5.70`) 与 SkillOpt 四维质量标尺 (0~100分) 及 Attempt/Judge 门禁 (`v1.5.72`)；
> 2. **五驱多引擎上下文压缩矩阵**：落实 PointFive TokenShift AST 语法树保护与分级代码压缩 (`v1.5.73`)、Context Router 异构提示词自适应语义分段与统一保序重组网关 (`v1.5.74`)、微软 LLMLingua-2 离线 Wiki 脱水 (`v1.5.46`)、阿里 SkillZip 写入即压缩 (`v1.5.35`) 与 Active Notes/History 双轨分仓 (`v1.5.34`)；
> 3. **工程健壮性与抗熵增治理**：SQLite 全链路 30s 锁超时加固 (`v1.5.58`)、FUSE 虚拟只读文件系统与内存 Overlay 屏蔽层 (`v1.5.59`, `v1.5.67`)、Session 巨石解耦 (`v1.5.62`)、双向索引一致性修剪 (`v1.5.63`)、Experience 标签稳定哈希 (`v1.5.68`) 与全库 2,029 项单测 100% 全绿基线 (`v1.5.69`)。

### 📋 一、 近期活跃原子化任务卡片详单 (Cards 1 ~ 17: v1.5.58 ~ v1.5.74)

{milestone3_cards_content}

### 📋 二、 历史演进波次交付详单 (Waves 1 ~ 5: v1.5.01 ~ v1.5.57)

{milestone3_waves_content}
"""

    # Find the insertion point in DELIVERY_ARCHIVE.md (right before Milestone 2)
    ms2_marker = "## 🏆 Milestone 2 (v1.4.4 ~ v1.4.110)"
    ms2_idx = archive_text.find(ms2_marker)
    assert ms2_idx != -1, "Milestone 2 marker not found in DELIVERY_ARCHIVE.md"

    archive_header = archive_text[:ms2_idx].strip()
    archive_ms2_and_below = archive_text[ms2_idx:].strip()

    # Update archive header with complete bidirectional links
    new_archive_header = """# 📚 OpenViking Studio — 历史交付全量归档台账 (DELIVERY_ARCHIVE.md SSOT)

> **唯一归档真相源 (Archive SSOT)**：本文档为 OpenViking Studio 已验收通过的历史版本、Task Cards、波次演进与 Git Tag 履历全量归档。
> **关联研发大蓝图**：[`BLUEPRINT.md`](file:///home/skloxo/aho/openclaw/project/.agents/BLUEPRINT.md) ｜ **唯一任务总看板**：[`REFACTORING_PLAN.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/REFACTORING_PLAN.md) ｜ **通用资产档案库**：[`COMPONENT_AND_WHEEL_INVENTORY.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/docs/architecture/COMPONENT_AND_WHEEL_INVENTORY.md) ｜ **👁️ 人工验收测试指南**：[`docs/HUMAN_ACCEPTANCE_TESTING.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/docs/HUMAN_ACCEPTANCE_TESTING.md)
> **归档原则**：历史所有已验收交付的版本履历（Milestone 1~4 全量 19 张 Task Cards 及前序波次）完整归纳于此，保持 100% 物理真实性与细节零丢失，为后续会话提供纯净轻量的活跃任务看板。

---
"""

    new_archive_text = f"{new_archive_header}\n\n{ms4_section}\n\n---\n\n{ms3_section}\n\n---\n\n{archive_ms2_and_below}\n"
    archive_path.write_text(new_archive_text, encoding="utf-8")
    print(f"✅ Updated DELIVERY_ARCHIVE.md: {len(new_archive_text.splitlines())} lines")

    # Now generate condensed REFACTORING_PLAN.md
    new_plan_content = """# 🗺️ OpenViking 项目主线重构与原子化任务卡片总看板 (Master Task Cards Kanban - SSOT)

> **关联研发大蓝图**：[`BLUEPRINT.md`](file:///home/skloxo/aho/openclaw/project/.agents/BLUEPRINT.md) ｜ **交付全量归档台账**：[`DELIVERY_ARCHIVE.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md) ｜ **通用资产档案库**：[`COMPONENT_AND_WHEEL_INVENTORY.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/docs/architecture/COMPONENT_AND_WHEEL_INVENTORY.md) ｜ **👁️ 人工验收测试指南**：[`docs/HUMAN_ACCEPTANCE_TESTING.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/docs/HUMAN_ACCEPTANCE_TESTING.md)
> **唯一真相源 (SSOT)**：本文档为 OpenViking 当前活跃的重构规划与就绪待调度的任务矩阵看板。历史所有已验收交付的版本履历（Milestone 1~4 全量 19 张 Task Cards 及前序波次）已完整归档至 [`DELIVERY_ARCHIVE.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md)，严禁多头维护。所有版本的 30 秒人工肉眼走查清单集中在 `docs/HUMAN_ACCEPTANCE_TESTING.md`。

---

## 📌 一、 研发基线与近期已交付版本速查索引 (Recent Delivered Releases: v1.5.70 ~ v1.5.76)

> **生产物理事实声明**：
> - **线上正式部署版本**：**`v1.4.106`**（物理访问地址：`vk.tide.red/studio/home`，已实机验证）；
> - **最新生产封板版本**：**`v1.5.76`**（Tag: `v1.5.76`，Commit: `03e1b4728`，已全量推流至远端）；
> - **历史里程碑详单检索**：如需查阅具体版本的修改文件清单、自动化单测回显与架构细节，请点击跳转至 [`DELIVERY_ARCHIVE.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md)。

| 版本 Tag | 任务工单 ID | 模块与重构主题 | 核心治理成果与物理交付物 | 验收状态 |
|:---|:---|:---|:---|:---:|
| **`v1.5.76`** | **Card-Cache-Tier2-LRU-FastHit** | 亚毫秒级 LRU 本地二级缓存引擎、防击穿协议与 10k 并发压测总盘 | 1. LRU 亚毫秒级二级缓存 (`cache_tier2_engine.py`, 195行)，`wait=False` 防击穿协议；<br>2. REST API 端点 (`/api/v1/cache/stats`, `/clear`, `/benchmark`)；<br>3. 监控大盘交互卡片 (`tier2-cache-card.tsx`, 198行)；<br>4. 实测 10,000 次操作平均延迟 0.0007ms，单测 6/6 全绿，生产构建通过。<br>**详见台账**：[`DELIVERY_ARCHIVE.md#card-19`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md) | [x] 已验收通过 ✅ |
| **`v1.5.75`** | **Card-DSPy-MIPO-Prompt-Compiler** | Stanford DSPy (MIPO) 强类型提示词编译、Few-Shot 自优化与试验台 | 1. DSPy 编译引擎 (`dspy_compiler_engine.py`, 223行)，强类型 Schema 规约提取与 Strict JSON 输出；<br>2. 检索大屏 Tab 11 试验台套件 (`dspy-compiler-cockpit.tsx`, 265行)；<br>3. 实机验证编译耗时 0.87ms，契约状态 PASS 零幻觉，单测 5/5 全绿。<br>**详见台账**：[`DELIVERY_ARCHIVE.md#card-18`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md) | [x] 已验收通过 ✅ |
| **`v1.5.74`** | **Card-Context-Router-Pipeline** | 异构多引擎上下文路由网关、自适应语义分段与统一重组管线 | 1. 统一调度 5 驱压缩矩阵 (Native Caching, LLMLingua-2, TokenShift, SkillZip, Active Notes)；<br>2. 5 类提示词片段自适应语义分段与严格保序无损重组；<br>3. 检索大屏 Tab 10 路由网关座舱 (`context-router-cockpit.tsx`, 373行)；单测 7/7 全绿。<br>**详见台账**：[`DELIVERY_ARCHIVE.md#card-17`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md) | [x] 已验收通过 ✅ |
| **`v1.5.73`** | **Card-TokenShift-ASTAware-CodeCompressor** | PointFive TokenShift 代码语法树保护探针与分级无损压缩 | 1. AST 语法感知三级渐进压缩 (L0 大纲 ~70%, L1 骨架 ~50%, L2 紧凑 ~25%)；<br>2. Python / TS / JS / SQL / Shell 多语言 AST 破坏率严格为 0；<br>3. 检索大屏专属 Tab 座舱 (`tokenshift-cockpit.tsx`, 327行)；单测 7/7 全绿。<br>**详见台账**：[`DELIVERY_ARCHIVE.md#card-16`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md) | [x] 已验收通过 ✅ |
| **`v1.5.72`** | **Card-SkillOpt-QualityGate-And-AutoOpt-Engine** | SkillOpt Attempt / Judge 质量门禁引擎与自动优化 Patch 闭环 | 1. 规范/能力/信噪比/触发区分度四维评分标尺 (0~100分) 与 Grade S~D 评级；<br>2. Attempt 执行测试与 Judge Gate 判据输出；<br>3. 技能大盘「🎯 SkillOpt 评测与体检」一级 Tab；单测 7/7 全绿。<br>**详见台账**：[`DELIVERY_ARCHIVE.md#card-15`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md) | [x] 已验收通过 ✅ |
| **`v1.5.71`** | **Card-Skill-LiveGen-Editor-And-Sandbox** | LiveGen 在线技能创生脚手架、规范校验与自然语言沙箱 | 1. Monaco 高亮编辑、YAML 校验与单文件规模阶梯评估；<br>2. 中文滑窗 n-gram 语义触发推演沙箱；<br>3. 技能大盘「✨ LiveGen 在线技能创生」一级 Tab；单测 7/7 全绿。<br>**详见台账**：[`DELIVERY_ARCHIVE.md#card-14`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md) | [x] 已验收通过 ✅ |
| **`v1.5.70`** | **Card-Privacy-Masker-And-PydanticV2** | 统一动态隐私脱敏引擎 (PrivacyMasker) 与 Pydantic V2 告警清退 | 1. 高性能预编译正则脱敏管道 (`privacy_masker.py`, 123行)；<br>2. Pydantic V2 `model_config = ConfigDict(...)` 升级，全库测试 0 告警 0 失败；<br>3. 客户端 LocalClient / Session 动态导出加固；单测 12/12 全绿。<br>**详见台账**：[`DELIVERY_ARCHIVE.md#card-13`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md) | [x] 已验收通过 ✅ |

---

## 📌 二、 活跃原子化任务卡片总看板 (Active Task Cards Kanban)

> **当前工程状态**：  
> 🎉 **所有已规划的 19 张任务卡片（Card 1 至 Card 19）及前序波次已 100% 全部完成验收交付！**  
> 历史全量卡片规格、修改文件清单、测试执行回显与详实履历已完整归拢至 [`DELIVERY_ARCHIVE.md`](file:///home/skloxo/aho/openclaw/project/OpenVikingStudio/DELIVERY_ARCHIVE.md)。  
> 当前活跃任务看板处于就绪待调度状态，随时准备接收后续新阶段（如 Milestone 5 / v2.0+ 企业级自治网络与多租户联邦）的任务卡片拆解。

### 📋 下一阶段就绪任务卡片模板 (Next Milestone Cards Template)

当接收到新的重大需求或重构指令时，严格遵循以下四步规范与标准模板立卡：
1. **第一阶·梳理方案** ➔ 2. **第二阶·CPA/业界模型补齐** ➔ 3. **第三阶·哲学审讯 (第一性原理/奥卡姆/信达雅/单文件≤500行)** ➔ 4. **第四阶·红蓝对抗与客观指标锚定**。

```markdown
#### 📌 [P1] [ ] Card-X: Card-Name (v2.x.y): <一句话任务概括> ⏳
- **类型**：<架构领域> ｜ **优先级**：🔥 P1 ｜ **目标版本**：`v2.x.y` ｜ **当前状态**：[ ] 就绪待调度 ⏳
- **开工前客观数据指标锚定 (Frontend Metric Anchor SSOT)**：
  - **衡量指标**：<显式声明前端客观指标，如检索延迟、Token 压缩率、门禁拦截率>
  - **展示界面与卡片**：<明确指出人类在前端哪个界面、哪个卡片能直观看到改动成效>
- **核心交付目标**：
  1. <目标一：核心算法/服务>
  2. <目标二：REST API / 路由>
  3. <目标三：座舱大屏交互套件，严格遵守 NO GREEN EVER 🚫 与字号 >= 12px>
- **验收条件**：单测 100% 通过、安全扫描 0 泄露、前端构建通过、实机浏览器验证。
```
"""

    plan_path.write_text(new_plan_content, encoding="utf-8")
    print(f"✅ Updated REFACTORING_PLAN.md: {len(new_plan_content.splitlines())} lines")


if __name__ == "__main__":
    main()
