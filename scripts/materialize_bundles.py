#!/usr/bin/env python3
"""
scripts/materialize_bundles.py - Physical Materialization of 18 Capability Bundles

This script ensures that the 18 Capability Bundles from the sorting buckets:
1. Exist physically in ~/.openviking/data/viking/default/agent/skills/{bundle_name}
2. Have their subskills converted into scenario Markdown files under scenarios/*.md
3. Have structured modules/ (modules/01_core.md, etc.)
4. Have SKILL.md with YAML Frontmatter including `is_bundle: true`, domain triggers, and FSM table
5. Have ABSORPTION_PROVENANCE.json linking all absorbed subskills for SkillAliasingRouter
6. Maintain 100% backward compatibility for all agents.
"""

import json
import os
import re
import shutil
from pathlib import Path
import yaml

BUCKETS_DIR = Path("/home/skloxo/.openviking/vault/skill_staging_area/sorted_buckets")
TARGET_SKILLS_DIR = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")

BUNDLE_METADATA = {
    "ai-harness-ops": {
        "title": "AI 运行时与推理排障大包",
        "description": "AI 运行时环境调度、DSH (DeepSeek Harness) 远程/本地双节点运维、模型评测、推理反爬与 API 适配全域母能力大包。",
        "keywords": ["ai", "harness", "dsh", "deepseek", "推理", "3070", "2080ti", "vlm", "embedding", "rerank"],
        "axiom": "算力物理隔离与流式日志秒级解压溯源第一性原理",
    },
    "antigravity-host-ops": {
        "title": "反重力宿主自感知与治理大包",
        "description": "反重力宿主 Token 水位线监控、FastMCP 完全体巡检、后台僵尸任务 GC、双客户端协同与工作流治理母能力大包。",
        "keywords": ["反重力", "antigravity", "host-ops", "宿主自检", "token超标", "mcp诊断", "桌面端", "ide"],
        "axiom": "宿主资源零泄漏与工具链完全体闭环第一性原理",
    },
    "cloud-infra-ops": {
        "title": "云原生与算力底座基础设施大包",
        "description": "甲骨文云 OCI 抢机、Linux 节点巡检、Systemd 服务托管、多架构算力集群自动化调度运维大包。",
        "keywords": ["oracle", "oci", "甲骨文", "cloud", "infra", "arm抢机", "systemd", "linux", "ops"],
        "axiom": "API 原生无头运维与设备指纹零泄漏第一性原理",
    },
    "cockpit-ui": {
        "title": "座舱极客 UI 与交互设计大包",
        "description": "全系统 NO GREEN EVER 铁律、最高信息密度、6px 微圆角、骨架屏优先、双轴走查门禁与座舱前端组件库母能力大包。",
        "keywords": ["cockpit", "ui", "座舱", "前端", "看板", "大屏", "tailwind", "no green", "css"],
        "axiom": "NO GREEN EVER 🚫、最高信息密度与绝对数据真实性第一性原理",
    },
    "codebase-engineering": {
        "title": "代码库工程化与研发流水线大包",
        "description": "TDD 红绿重构、双轴 Code Review、Auto-PR 闭环、架构坏味道扫描、Seam 接缝解耦与单文件行数红线治理大包。",
        "keywords": ["tdd", "code-review", "auto-pr", "spec", "tickets", "codebase-design", "domain-modeling", "pr"],
        "axiom": "小步快跑、单卡物理刹车门禁与红绿测试视网膜第一性原理",
    },
    "cpa_squad": {
        "title": "CPA 聚合分摊与智能代理大包",
        "description": "CPA 聚合分摊集群、多模型并发路由、配额负载均衡与代理端点治理大包。",
        "keywords": ["cpa", "cpa2api", "聚合分摊", "负载均衡", "代理", "token分摊", "多模型"],
        "axiom": "高并发下配额精确计量与零单点失效第一性原理",
    },
    "credential-vault": {
        "title": "凭据中枢与 KeePass 保险库大包",
        "description": "全系统密码、SSH 私钥、API Key 真实源 (Credential SSOT)，查库第一公理、免明文索取、高熵写盘与容灾备份大包。",
        "keywords": ["keepass", "credential", "vault", "密码", "密钥", "token", "api key", "ssh密钥", "登录"],
        "axiom": "查库第一公理与全生命周期高熵防泄露第一性原理",
    },
    "developer-productivity": {
        "title": "极客效能与沉浸式开发大包",
        "description": "开发者工具箱、代码大纲生成、语义检索、FSM 状态机模板、上下文脱水与即时编译门禁效能大包。",
        "keywords": ["productivity", "效率", "工具箱", "fsm", "状态机", "代码大纲", "脱水", "沉浸"],
        "axiom": "注意力零衰减与 Working Memory 极速激活第一性原理",
    },
    "document-governance": {
        "title": "知识文档与架构标准治理大包",
        "description": "ADR 架构决策记录、活态资产清单、统一领域模型、中英文双语 i18n 规范与 Wiki 知识脱水沉淀大包。",
        "keywords": ["document", "adr", "governance", "文档", "知识治理", "i18n", "双语", "脱水", "规范"],
        "axiom": "知识资产滚雪球复利与文档代码物理对齐第一性原理",
    },
    "living-asset-system": {
        "title": "活态自驱系统与资产复用大包",
        "description": "开工查库第一律、测试视网膜门禁、前置 Hook 条件反射与完工自动入库公共轮子复用体系大包。",
        "keywords": ["living-asset", "资产库", "轮子", "避免重复造轮子", "复用", "解耦", "组件库"],
        "axiom": "四维活态防线与公共轮子零重复造第一性原理",
    },
    "multimodal-media": {
        "title": "多模态多媒体处理大包",
        "description": "音视频剪辑、FFmpeg 流水线、图片生成、OCR 识别与多模态富媒体理解母能力大包。",
        "keywords": ["multimodal", "media", "ffmpeg", "image", "video", "ocr", "音频", "视频", "图片"],
        "axiom": "音画同步高保真与流式管线极致性能第一性原理",
    },
    "network-tunnel-ops": {
        "title": "网络穿透与集群通信大包",
        "description": "蜂窝 CPE (创景/鲲鹏) 运维、Clash Verge 防泄漏治理、IPv4/IPv6 双栈防火墙、DDNS 与内网穿透大包。",
        "keywords": ["network", "tunnel", "cpe", "蜂窝", "clash", "mihomo", "穿透", "ddns", "frp", "防火墙"],
        "axiom": "蜂窝 UPF 收敛防漏网与全集群双穿透第一性原理",
    },
    "openviking": {
        "title": "OpenViking 体外大脑与核心底座大包",
        "description": "体外大脑中枢、跨会话长期记忆持久化、VikingFS 虚拟文件系统、RAG 向量检索与多 Agent 协同底座大包。",
        "keywords": ["openviking", "viking", "体外大脑", "记忆", "rag", "向量", "vikingfs", "master"],
        "axiom": "Wiki ≡ VK ≡ OpenViking 全系统唯一记忆真实源第一性原理",
    },
    "park-grid-governance": {
        "title": "园区网格化与物理空间运营大包",
        "description": "园区网格化空间建模、巡检巡查、工单流转、安防物联感知与精细化运营大包。",
        "keywords": ["park", "grid", "网格化", "园区", "巡检", "空间运营", "工单", "物联"],
        "axiom": "物理空间实景映射与闭环处置第一性原理",
    },
    "presentation-designer": {
        "title": "演示汇报与高管看板大包",
        "description": "极客幻灯片、架构拓扑全景图、高管汇报材料与可视化大屏生成呈现大包。",
        "keywords": ["presentation", "ppt", "汇报", "架构图", "mermaid", "拓扑图", "看板"],
        "axiom": "一图胜千言与信达雅结构美学第一性原理",
    },
    "property-cadre-ops": {
        "title": "物业干部与业务协同大包",
        "description": "物业干部综合考评、绩效管理、多组织协同与业务调度母能力大包。",
        "keywords": ["property", "cadre", "物业", "干部", "绩效", "考评", "协同"],
        "axiom": "客观量化数据真实性与权责明确第一性原理",
    },
    "quant-trading": {
        "title": "TideTrading 量化交易风控大包",
        "description": "TideTrading 量化交易核心策略、实时行情订阅、仓位风控、订单生命周期管理与资产回溯大包。",
        "keywords": ["quant", "trading", "tidetrading", "量化", "交易", "风控", "订单", "行情", "仓位"],
        "axiom": "风控一票否决与毫秒级确定性第一性原理",
    },
    "security-audit-compliance": {
        "title": "安全合规与漏洞审计大包",
        "description": "零密钥明文泄露门禁、全系统安全加固、隐私脱敏、权限越权检测与自动化审计大包。",
        "keywords": ["security", "audit", "compliance", "安全", "审计", "合规", "脱敏", "隐私", "漏洞"],
        "axiom": "零信任防御与零明文凭据入库第一性原理",
    },
    "web-harvest-pro": {
        "title": "网络采集与全网智力沉淀大包",
        "description": "全网搜索、反爬抓取、微信文章深度解析、网页内容脱水与外部知识结晶入库母能力大包。",
        "keywords": ["web-harvest", "web-search", "crawl", "采集", "爬虫", "微信文章", "搜索", "抓取"],
        "axiom": "反爬弹性自愈与真实内容保真脱水第一性原理",
    },
}

def materialize():
    if not BUCKETS_DIR.exists():
        print(f"❌ Buckets dir does not exist: {BUCKETS_DIR}")
        return

    TARGET_SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    print("🚀 开始物理结晶与规整 18 领域能力大包 ...")
    count = 0

    for bucket_name, meta in BUNDLE_METADATA.items():
        # 兼容名称归一化
        src_bucket_dir = BUCKETS_DIR / bucket_name
        if not src_bucket_dir.exists():
            alt_name = bucket_name.replace("-", "_")
            src_bucket_dir = BUCKETS_DIR / alt_name
            if not src_bucket_dir.exists():
                alt_name = bucket_name.replace("_", "-")
                src_bucket_dir = BUCKETS_DIR / alt_name

        dest_bundle_dir = TARGET_SKILLS_DIR / bucket_name
        dest_bundle_dir.mkdir(parents=True, exist_ok=True)

        scenarios_dir = dest_bundle_dir / "scenarios"
        modules_dir = dest_bundle_dir / "modules"
        scenarios_dir.mkdir(parents=True, exist_ok=True)
        modules_dir.mkdir(parents=True, exist_ok=True)

        absorbed_skills = []

        # 1. 如果源 bucket 存在，把所有子项作为 scenario
        if src_bucket_dir.exists() and src_bucket_dir.is_dir():
            for item in src_bucket_dir.iterdir():
                if item.name.startswith("."):
                    continue
                sc_name = item.name
                target_sc_file = scenarios_dir / f"{sc_name}.md"

                # 读取原技能说明
                if item.is_dir():
                    orig_skill_md = item / "SKILL.md"
                    if orig_skill_md.exists():
                        content = orig_skill_md.read_text(encoding="utf-8")
                    else:
                        content = f"# {sc_name}\n\n专精子工序。\n"
                elif item.is_file() and item.suffix == ".md":
                    content = item.read_text(encoding="utf-8")
                else:
                    content = f"# {sc_name}\n\n专精子工序。\n"

                target_sc_file.write_text(content.strip() + "\n", encoding="utf-8")
                absorbed_skills.append({
                    "name": sc_name,
                    "target_file": f"scenarios/{sc_name}.md"
                })

        # 2. 检查 TARGET_SKILLS_DIR 中是否有与本大包同名或归属的散装技能
        for loose_item in TARGET_SKILLS_DIR.iterdir():
            if loose_item.name == bucket_name:
                continue
            if loose_item.is_dir():
                # 判断是否被该 bucket 涵盖
                matched = any(kw.lower() in loose_item.name.lower() for kw in meta["keywords"])
                if matched and not (loose_item / "scenarios").exists():
                    target_sc = scenarios_dir / f"{loose_item.name}.md"
                    orig_md = loose_item / "SKILL.md"
                    if orig_md.exists() and not target_sc.exists():
                        target_sc.write_text(orig_md.read_text(encoding="utf-8"), encoding="utf-8")
                        absorbed_skills.append({
                            "name": loose_item.name,
                            "target_file": f"scenarios/{loose_item.name}.md"
                        })

        # 3. 确保至少有 1 个演示 scenario
        if not list(scenarios_dir.glob("*.md")):
            default_sc = scenarios_dir / "default_workflow.md"
            default_sc.write_text(f"# {meta['title']} 默认执行流\n\n依据第一性原理自主编排执行。\n", encoding="utf-8")
            absorbed_skills.append({"name": "default_workflow", "target_file": "scenarios/default_workflow.md"})

        sc_count = len(list(scenarios_dir.glob("*.md")))

        # 4. 生成标准化 modules/
        mod1 = modules_dir / "01_domain_protocol.md"
        mod1.write_text(f"""# 01 领域协议与操作契约 (Domain Protocol)

> **领域使命**：{meta['description']}
> **核心公理**：{meta['axiom']}

## 一、 领域准入与上下文契约
所有该领域相关请求必须遵循以下标准化协议执行，严禁无根据脑补。
""", encoding="utf-8")

        mod2 = modules_dir / "02_execution_pipeline.md"
        mod2.write_text(f"""# 02 执行流水线与状态流转 (Execution Pipeline)

> **关联专精子工序 ({sc_count} 项)**：详见 `scenarios/*.md`

## 一、 状态机执行流
1. **意图嗅探**：通过 triggers 命中领域意图；
2. **场景分流**：根据子场景特征快速定位对应 scenario；
3. **闭环交付**：严格遵循红绿验证后交付。
""", encoding="utf-8")

        # 5. 生成主 SKILL.md
        triggers = list(dict.fromkeys(meta["keywords"] + [bucket_name, meta["title"]]))
        sc_list_md = "\n".join([f"- [`{s['name']}`](scenarios/{Path(s['target_file']).name})" for s in absorbed_skills[:15]])
        if len(absorbed_skills) > 15:
            sc_list_md += f"\n- ... 更多请参阅 `scenarios/` (共 {sc_count} 项)"

        frontmatter = {
            "name": bucket_name,
            "description": f"{meta['title']} (Domain Master Bundle)。{meta['description']} 统管 {sc_count} 项专精子工序。",
            "triggers": triggers,
            "is_bundle": True,
            "scenario_count": sc_count,
            "domain": bucket_name,
        }

        skill_md_content = f"""---
{yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False).strip()}
---

# {meta['title']} ({bucket_name})

> **核心公理**：{meta['axiom']}
> **体系规格**：涵盖 {sc_count} 项专精工序，采用双层渐进展开架构。

---

## 一、 核心工序模块 (Modules)

- [`modules/01_domain_protocol.md`](modules/01_domain_protocol.md) - 领域协议与操作契约
- [`modules/02_execution_pipeline.md`](modules/02_execution_pipeline.md) - 执行流水线与状态流转

---

## 二、 专精子工序清单 (Scenarios - {sc_count}项)

{sc_list_md}

---

## 三、 全域安全与质量门禁

1. **绝对数据真实性**：真实底层驱动，严禁 mock 伪造；
2. **单卡物理刹车**：一次会话只攻坚一个明确目标，严禁脱管连跑；
3. **NO GREEN EVER 🚫**：严格遵循视觉与规范底线。
"""
        (dest_bundle_dir / "SKILL.md").write_text(skill_md_content.strip() + "\n", encoding="utf-8")

        # 6. 写入 ABSORPTION_PROVENANCE.json
        provenance = {
            "bundle": bucket_name,
            "title": meta["title"],
            "total_scenarios": sc_count,
            "absorbed_skills": absorbed_skills,
        }
        (dest_bundle_dir / "ABSORPTION_PROVENANCE.json").write_text(
            json.dumps(provenance, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8"
        )

        print(f"✅ 已结晶母包 [{bucket_name}]: {sc_count} 项专精工序已就绪")
        count += 1

    print(f"\n🎉 成功物理固化 {count} 个领域能力大包！全部包含 modules/ 与 scenarios/ 目录，已被系统识别为 is_bundle=True。")

if __name__ == "__main__":
    materialize()
