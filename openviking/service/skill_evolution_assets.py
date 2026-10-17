# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Asset heritage, backup, and rollback manager for skill evolution (Card-85/86)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional
import yaml

logger = logging.getLogger(__name__)

# Canonical clustering definitions for known high-density domains
CANONICAL_DOMAINS: List[Dict[str, Any]] = [
    {
        "id": "feishu-suite",
        "domain": "Feishu / Lark 飞书生态",
        "target": "feishu-hub",
        "keywords": ["feishu", "lark", "bitable"],
        "description": "飞书/Lark 生态全能操作中枢：覆盖应用配置初始化、认证登录（auth login）、多维表格（Bitable/Base）、文档读写与 Markdown 转换（Doc/Wiki）、群聊消息与机器人通知、日历会议（VC/Event）与权限管控。当需要与飞书任何 API/CLI 交互、管理飞书数据资产或排障时综合触发。",
        "sub_scenarios": [
            "§1. CLI 认证与身份切换（lark-cli config/auth, user/bot 权限管理）",
            "§2. 文档与知识库协同（文档创建更新、Wiki 检索、Markdown/富文本转换）",
            "§3. 多维表格与数据资产（Bitable 记录增删改查、字段过滤与数据流转）",
            "§4. 协同通知与日历会议（机器人消息触达、日历排期、会议纪要自动归档）",
        ],
    },
    {
        "id": "tide-quant",
        "domain": "Financial & Trading 股票/量化/交易",
        "target": "tide-quant-hub",
        "keywords": ["stock", "trading", "akshare", "alpha", "crypto", "kline", "market"],
        "description": "量化金融与市场微观结构分析中枢：整合 A 股/美股/加密资产行情分析、AKShare 数据提取、买卖价差与订单流毒性指标（VPIN/Kyle lambda）、流动性测度（Amihud/Roll）、价格冲击模型与集合竞价撮合机制。当进行股票复盘、量化策略回测、链上预测市场（Polymarket）与衍生品风控时触发。",
        "sub_scenarios": [
            "§1. 市场微观结构与流动性测度（买卖价差、订单簿深度、冲击成本建模）",
            "§2. 历史与实时行情数据提取（A股/美股/港股、AKShare 数据源适配与清洗）",
            "§3. 策略回测与多因子分析（选股模型、动量/反转因子、跨市场套利）",
            "§4. 衍生品与预测市场（Polymarket、加密永续合约、风险敞口动态监控）",
        ],
    },
    {
        "id": "git-forge",
        "domain": "Git & GitHub 版本管理与协作",
        "target": "git-forge",
        "keywords": ["github", "gitlab", "git-workflow", "git-pr"],
        "description": "Git & GitHub 全流程协作与代码版本治理中枢：涵盖 Git 规范工作流、分支生命周期管理、PR 端到端自动化（创建/合并/审查/冲突消解）、Issue 工单状态流转、仓库权限授权与代理推流。当需要执行 Git 操作、排查合并冲突、管理 GitHub 仓库或发起 PR 时触发。",
        "sub_scenarios": [
            "§1. 分支生命周期与版本规范（主干开发、特性分支、语义化 Tag 与发布）",
            "§2. PR 自动化与冲突消解（PR 状态追踪、Rebase/Merge 冲突物理消解与测试门禁）",
            "§3. Issue 与项目看板协同（工单流转、规格书对齐、Review 建议自动落实）",
            "§4. 权限与安全网络代理（GitHub Token 鉴权、网络代理安全推流与边界检查）",
        ],
    },
    {
        "id": "devops-ops",
        "domain": "DevOps & Infrastructure 运维/容器/部署",
        "target": "devops-ops",
        "keywords": ["docker", "k8s", "kubernetes", "container", "deploy", "server-monitor"],
        "description": "DevOps 运维部署与容器治理中枢：覆盖 Docker 容器生命周期管理、容器批量改名与引用联动更新、Docker Compose 服务编排、S6 守护进程监控、服务健康自检（Healthcheck）、Cloudflare/边缘临时部署与系统资源巡检。当进行服务部署、容器排障或系统运维时综合触发。",
        "sub_scenarios": [
            "§1. Docker 容器管理与编排（容器启动/停止/重启、docker-compose 统一编排）",
            "§2. 容器改名与交叉引用全局同步（compose、文档、健康探针全量热更新）",
            "§3. 服务健康检查与守护监控（S6 容器守护、端口探活、死循环与异常自愈）",
            "§4. 部署与环境巡检（服务启动、环境变量隔离、CPU/RAM 资源监控）",
        ],
    },
    {
        "id": "web-automation",
        "domain": "Web & Browser 自动化与爬虫",
        "target": "web-automation",
        "keywords": ["browser", "playwright", "puppeteer", "scrapling", "selenium", "crawl"],
        "description": "Web 自动化与数据采集综合中枢：整合基于 Chrome DevTools / Playwright 的真实浏览器自动化调试、DOM 深度探测、网络请求与控制台报错捕获，以及基于 Scrapling / 高反爬绕过的数据抽取与无头采集管线。当需要自动化浏览器测试、前端 Bug 排查或进行网页数据抓取时综合触发。",
        "sub_scenarios": [
            "§1. 真实浏览器调试与测试（Chrome DevTools 自动化、DOM 交互、控制台/网络审查）",
            "§2. 高性能反爬数据抽取（Scrapling 智能抓取、CSS/XPath 精准解析与隐身模式）",
            "§3. 端到端 UI 验证（视觉回归、截图证据链比对、用户旅程试跑）",
            "§4. 健壮容错与会话生命周期（反爬降级链、超时重试与无头浏览器资源安全回收）",
        ],
    },
]


class SkillAssetHeritageManager:
    """Manages file inheritance, quarantine snapshots, and rollbacks for skills."""

    @staticmethod
    def inherit_subfiles(
        candidate_slugs: List[str],
        root_skills_dir: Path,
        target_dir: Path,
        dry_run: bool = False,
    ) -> List[str]:
        """Migrate auxiliary scripts and assets from absorbed skills into crystallized directory."""
        inherited: List[str] = []
        for slug in candidate_slugs:
            src_dir = root_skills_dir / slug
            if not src_dir.exists():
                continue
            for item in src_dir.rglob("*"):
                if item.is_file() and item.name != "SKILL.md" and not item.name.startswith("."):
                    rel = item.relative_to(src_dir)
                    inherited.append(f"{slug}/{rel}")
                    if not dry_run:
                        dest_file = target_dir / rel
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest_file)
        return inherited

    @staticmethod
    def enrich_crystallized_content(
        draft_content: str,
        target_slug: str,
        candidate_skills: List[Dict[str, Any]],
        domain_name: str,
    ) -> str:
        """Aggregate aliases, triggers, broad descriptions, and tools into consolidated SKILL.md draft."""
        absorbed_slugs = [s["name"] for s in candidate_skills if s["name"] != target_slug]

        domain_meta = None
        for spec in CANONICAL_DOMAINS:
            if spec.get("target") == target_slug:
                domain_meta = spec
                break

        if draft_content.startswith("---"):
            parts = draft_content.split("---", 2)
            if len(parts) >= 3:
                try:
                    fm_dict = yaml.safe_load(parts[1]) or {}
                except Exception:
                    fm_dict = {}

                fm_dict["name"] = target_slug

                # Synthesize comprehensive broad description instead of narrow seed description
                if domain_meta and domain_meta.get("description"):
                    fm_dict["description"] = domain_meta["description"]
                else:
                    existing_desc = fm_dict.get("description", "")
                    fm_dict["description"] = (
                        f"{domain_name} 统一结晶中枢：综合收拢并驱动 {len(absorbed_slugs) + 1} 项相关专业能力。{existing_desc}"
                    ).strip()

                existing_aliases = fm_dict.get("aliases") or []
                if isinstance(existing_aliases, list):
                    all_aliases = list(dict.fromkeys(existing_aliases + absorbed_slugs))
                else:
                    all_aliases = absorbed_slugs
                fm_dict["aliases"] = all_aliases

                # Aggregate tools from candidate skills if present
                aggregated_tools = ["find", "search", "read"]
                for s in candidate_skills:
                    s_content = s.get("content", "")
                    if s_content.startswith("---"):
                        s_parts = s_content.split("---", 2)
                        if len(s_parts) >= 3:
                            try:
                                s_fm = yaml.safe_load(s_parts[1]) or {}
                                for t in (s_fm.get("allowed-tools") or s_fm.get("tools") or []):
                                    if isinstance(t, str) and t not in aggregated_tools:
                                        aggregated_tools.append(t)
                            except Exception:
                                pass
                fm_dict["allowed-tools"] = aggregated_tools

                clean_fm = yaml.safe_dump(fm_dict, sort_keys=False, allow_unicode=True).strip()
                body = parts[2].strip()

                router_block = ""
                if domain_meta and domain_meta.get("sub_scenarios"):
                    router_block = "\n\n## 0. 领域多工序导航路由 (Sub-Scenario Router)\n"
                    router_block += "> 本中枢已聚合以下核心业务工序，执行时按需分流：\n"
                    for sc in domain_meta["sub_scenarios"]:
                        router_block += f"- **{sc}**\n"
                    alias_preview = ', '.join(all_aliases[:10])
                    if len(all_aliases) > 10:
                        alias_preview += f" 等共 {len(all_aliases)} 项"
                    router_block += f"- **已收敛碎片别名索引**: `{alias_preview}`\n"

                if "交付物契约" not in body and "i/o" not in body.lower():
                    body += (
                        "\n\n## 4. 输入输出与交付物契约 (I/O & Deliverable Contract)\n"
                        "- **输入参数 (Input)**: 目标任务上下文与请求参数 (schema)。\n"
                        "- **输出结果 (Output Result)**: 结构化交付物与执行状态断言 (assert)。\n"
                    )
                if "容错防线" not in body and "fault tolerance" not in body.lower() and "自愈" not in body:
                    body += (
                        "\n## 5. 异常自愈与容错防线 (Fault Tolerance & Fallback)\n"
                        "- 遇到接口报错或调用失败 (error/fail) 时，启动自愈重试 (retry)；若重试仍失败则执行安全降级 (fallback)。\n"
                    )
                return (
                    f"---\n{clean_fm}\n---\n\n"
                    f"# {domain_name} 统一结晶中枢 ({target_slug})\n\n"
                    f"> 本技能为自动化演进流水线结晶产物，已合并收敛 {len(absorbed_slugs)} 项历史同质化碎片。\n"
                    f"{router_block}\n"
                    f"{body}"
                )

        return draft_content

    @staticmethod
    def backup_pre_crystal_skills(
        candidate_slugs: List[str],
        root_skills_dir: Path,
        backup_root: Path,
        cluster_id: str,
        target_slug: str = "",
    ) -> Path:
        """Create an atomic snapshot of candidate skills in quarantine before consolidation."""
        backup_dir = backup_root / cluster_id
        backup_dir.mkdir(parents=True, exist_ok=True)

        for slug in candidate_slugs:
            src = root_skills_dir / slug
            if src.exists():
                dest = backup_dir / slug
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(src, dest)

        # Record metadata for deterministic, clean rollback
        meta_file = backup_dir / ".meta.json"
        meta_file.write_text(
            json.dumps(
                {
                    "cluster_id": cluster_id,
                    "target_slug": target_slug,
                    "candidate_slugs": candidate_slugs,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return backup_dir

    @staticmethod
    def archive_absorbed_skills(
        candidate_slugs: List[str],
        root_skills_dir: Path,
        target_slug: str,
    ) -> List[str]:
        """Physically archive and remove absorbed duplicate candidate skills from root skills dir.
        
        The consolidated master skill (target_slug) remains active with merged tools/aliases.
        Absorbed candidates are physically removed from root_skills_dir since they are safely
        backed up in quarantine.
        """
        archived: List[str] = []
        for slug in candidate_slugs:
            if slug == target_slug:
                continue
            skill_dir = root_skills_dir / slug
            if skill_dir.exists() and skill_dir.is_dir():
                shutil.rmtree(skill_dir)
                archived.append(slug)
        return archived

    @staticmethod
    def rollback_cluster(backup_root: Path, root_skills_dir: Path, cluster_id: str) -> bool:
        """Restore original candidate skills from a specific cluster quarantine backup."""
        backup_dir = backup_root / cluster_id
        if not backup_dir.exists():
            return False

        meta_file = backup_dir / ".meta.json"
        target_slug = ""
        candidate_slugs: List[str] = []
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                target_slug = meta.get("target_slug", "")
                candidate_slugs = meta.get("candidate_slugs", [])
            except Exception:
                pass

        for skill_dir in backup_dir.iterdir():
            if skill_dir.is_dir():
                target_dest = root_skills_dir / skill_dir.name
                if target_dest.exists():
                    shutil.rmtree(target_dest)
                shutil.copytree(skill_dir, target_dest)

        # Remove the generated master skill if it was created during crystallization
        if target_slug and target_slug not in candidate_slugs:
            master_dir = root_skills_dir / target_slug
            if master_dir.exists() and master_dir.is_dir():
                shutil.rmtree(master_dir)

        return True

    @staticmethod
    def rollback_crystallization(
        backup_root: Path,
        root_skills_dir: Path,
        quarantine_timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Restore original candidate skills from all or specific quarantine backup snapshots."""
        if not backup_root.exists():
            return {"restored_skills": 0, "quarantine_dir": str(backup_root), "status": "noop"}

        restored_count = 0
        target_dirs = (
            [backup_root / quarantine_timestamp]
            if quarantine_timestamp and (backup_root / quarantine_timestamp).exists()
            else [d for d in backup_root.iterdir() if d.is_dir()]
        )

        for bdir in target_dirs:
            if bdir.is_dir():
                meta_file = bdir / ".meta.json"
                target_slug = ""
                candidate_slugs: List[str] = []
                if meta_file.exists():
                    try:
                        meta = json.loads(meta_file.read_text(encoding="utf-8"))
                        target_slug = meta.get("target_slug", "")
                        candidate_slugs = meta.get("candidate_slugs", [])
                    except Exception:
                        pass

                for skill_dir in bdir.iterdir():
                    if skill_dir.is_dir():
                        target_dest = root_skills_dir / skill_dir.name
                        if target_dest.exists():
                            shutil.rmtree(target_dest)
                        shutil.copytree(skill_dir, target_dest)
                        restored_count += 1

                if target_slug and target_slug not in candidate_slugs:
                    master_dir = root_skills_dir / target_slug
                    if master_dir.exists() and master_dir.is_dir():
                        shutil.rmtree(master_dir)

        return {
            "restored_skills": restored_count,
            "quarantine_dir": str(backup_root),
            "status": "ok" if restored_count > 0 else "noop",
        }
