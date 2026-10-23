#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/assemble_dsh_adapter.py
OpenViking 智能体适配器通用装配流水线 (Universal DSH Adapter Assembler)

基于【完整插件 = 插件内核 (Core Kernel) + 智能体适配器 (Agent Adapter)】最高范式：
1. 插件内核 (Core Kernel): 物理 AST 抽取 MCP 工具、生命周期 Hooks、Skills 认知导轨与规约；
2. 智能体适配器 (Agent Adapter): 针对 DSH 宿主环境，从 universal_dsh_client.js 模板全自动装配；
3. 零前端维护成本：任何插件内核 1 秒装配全功能表现层，三插槽冗余注册、实时探针、高对比度 UI。
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

TEMPLATE_PATH = ROOT_DIR / "packages" / "templates" / "universal_dsh_client.js"

logger = logging.getLogger("dsh_adapter_assembler")

# 插件内核与 DSH 官方桥接器权威映射表 (SSOT)
KERNEL_TO_DSH_MAP: Dict[str, str] = {
    "openviking-memory": "dsh-plugin-openviking-memory",
    "openviking-ops": "dsh-plugin-openviking-ops",
    "fleet-mesh": "dsh-plugin-openviking-fleet",
    "keepass-vault": "dsh-plugin-keepass-vault",
    "dify": "dsh-plugin-dify",
    "cpa-squad": "dsh-plugin-cpa",
    "network-search": "dsh-plugin-search-gateway",
    "agent-circuit-breaker": "agent-circuit-breaker",
}

DSH_TO_KERNEL_MAP: Dict[str, str] = {v: k for k, v in KERNEL_TO_DSH_MAP.items()}
DSH_TO_KERNEL_MAP["dsh-plugin-openviking"] = "openviking-memory"


def categorize_tool(tool_name: str, raw_cat: str = "") -> str:
    """根据算子名称与原始分类自动归入高内聚领域分类标签。"""
    nl = tool_name.lower()
    cl = (raw_cat or "").lower()
    if any(k in nl or k in cl for k in ("memory", "find", "search", "read", "remember", "store", "write", "tree", "grep", "glob")):
        return "核心长程记忆与检索 (Memory & Context)"
    if any(k in nl or k in cl for k in ("ops", "resource", "backup", "restore", "init", "dlq", "purge", "reindex", "audit", "server_doctor")):
        return "系统运维治理与快照 (Ops & Snapshots)"
    if any(k in nl or k in cl for k in ("keepass", "vault", "secret", "clip", "cred", "show")):
        return "本地高安全凭据保险库 (Credentials & Security)"
    if any(k in nl or k in cl for k in ("fleet", "mesh", "node", "satellite", "sync")):
        return "卫星集群网络与节点同频 (Fleet & Mesh)"
    if any(k in nl or k in cl for k in ("cpa", "squad", "token", "quota")):
        return "模型聚合路由与多租户分摊 (CPA Squad)"
    if any(k in nl or k in cl for k in ("dify", "workflow")):
        return "Dify 工作流与编排引擎 (Dify Engine)"
    if any(k in nl or k in cl for k in ("breaker", "circuit", "guard", "fault")):
        return "熔断风控与护栏中枢 (Circuit Breaker)"
    if any(k in nl or k in cl for k in ("web", "url", "scrape", "crawl", "tavily", "searxng")):
        return "全网检索与智能抓取 (Network Search)"
    return "原子扩展工具箱 (FastMCP Tools)"


def resolve_canonical_names(kernel_dir: Path) -> Tuple[str, str]:
    """计算规范的 DSH Package ID 和 Short Name。"""
    folder_name = kernel_dir.name
    pj = kernel_dir / "plugin.json"
    raw_name = folder_name
    if pj.is_file():
        try:
            raw_name = json.loads(pj.read_text(encoding="utf-8")).get("name", folder_name)
        except Exception:
            pass

    if raw_name in KERNEL_TO_DSH_MAP:
        dsh_id = KERNEL_TO_DSH_MAP[raw_name]
        short_name = raw_name
    elif raw_name in DSH_TO_KERNEL_MAP:
        dsh_id = raw_name
        short_name = DSH_TO_KERNEL_MAP[raw_name]
    elif raw_name.startswith("dsh-plugin-"):
        dsh_id = raw_name
        short_name = raw_name.replace("dsh-plugin-", "")
    else:
        dsh_id = f"dsh-plugin-{raw_name}"
        short_name = raw_name

    return dsh_id, short_name


def assemble_dsh_adapter(
    kernel_dir: Path,
    template_path: Optional[Path] = None,
) -> Tuple[str, Dict[str, Any]]:
    """从插件内核目录装配 DSH client.js 解释器代码与元数据。"""
    tpl_file = template_path or TEMPLATE_PATH
    if not tpl_file.is_file():
        raise FileNotFoundError(f"通用 DSH 客户端模板不存在: {tpl_file}")

    from openviking.service.plugin_scanner import scan_single_plugin_dir, resolve_builtin_tools

    dsh_pkg_name, short_name = resolve_canonical_names(kernel_dir)

    # 1. 解析插件内核基本描述
    pj_file = kernel_dir / "plugin.json"
    manifest: Dict[str, Any] = {}
    if pj_file.is_file():
        try:
            manifest = json.loads(pj_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    pkg_file = kernel_dir / "package.json"
    if pkg_file.is_file() and not manifest:
        try:
            manifest = json.loads(pkg_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    display_name = manifest.get("displayName") or manifest.get("name") or short_name
    version = manifest.get("version", "1.0.0")
    description = manifest.get("description", f"OpenViking {display_name} 领域插件。")
    suggested_prompts = manifest.get("suggestedPrompts", [])

    # 2. 物理 AST 抽取真实算子、技能与钩子
    q = scan_single_plugin_dir(kernel_dir)
    tools = q.tools if q and q.tools else resolve_builtin_tools(short_name)
    skills = q.skills if q else []
    hooks = q.hooks if q else []

    # 3. 结构化分类与 JSON 序列化
    cat_map: Dict[str, List[str]] = {}
    for t in tools:
        c_label = categorize_tool(t.name, getattr(t, "category", ""))
        cat_map.setdefault(c_label, []).append(t.name)
    tool_categories_data = [{"cat": k, "tools": v} for k, v in cat_map.items()]

    skills_data = [{"name": s.name, "desc": s.description} for s in skills]
    hooks_data = [{"name": h.name, "desc": h.description, "event": h.trigger_event} for h in hooks]
    rules = q.rules if q and q.rules else []
    rules_data = [{"name": r.name, "desc": r.description, "content": getattr(r, "content", "")} for r in rules]

    # 4. 提取真实 README 内容 (唯一真相源)
    readme_content = ""
    if q and q.readme_content:
        readme_content = q.readme_content
    elif (kernel_dir / "README.md").is_file():
        try:
            readme_content = (kernel_dir / "README.md").read_text(encoding="utf-8")
        except Exception:
            pass
    if not readme_content:
        readme_content = f"# {display_name}\n\n{description}"

    # 5. 读取模板并完成 100% 参数化动态置换
    tpl_text = tpl_file.read_text(encoding="utf-8")
    assembled_code = (
        tpl_text
        .replace("__PLUGIN_ID__", dsh_pkg_name)
        .replace("__SHORT_NAME__", short_name)
        .replace("__PLUGIN_NAME__", display_name)
        .replace("__PLUGIN_VERSION__", version)
        .replace("__TOOL_CATEGORIES_JSON__", json.dumps(tool_categories_data, ensure_ascii=False))
        .replace("__SKILLS_JSON__", json.dumps(skills_data, ensure_ascii=False))
        .replace("__HOOKS_JSON__", json.dumps(hooks_data, ensure_ascii=False))
        .replace("__RULES_JSON__", json.dumps(rules_data, ensure_ascii=False))
        .replace("__README_CONTENT_JSON__", json.dumps(readme_content, ensure_ascii=False))
    )

    meta = {
        "dsh_pkg_name": dsh_pkg_name,
        "short_name": short_name,
        "display_name": display_name,
        "version": version,
        "tools_count": len(tools),
        "skills_count": len(skills),
        "hooks_count": len(hooks),
        "rules_count": len(rules),
    }
    return assembled_code, meta


def assemble_and_write(kernel_dir: Path, target_dir: Path) -> Dict[str, Any]:
    """装配适配器并物理落盘 client.js 与修正 package.json。"""
    target_dir.mkdir(parents=True, exist_ok=True)
    assembled_code, meta = assemble_dsh_adapter(kernel_dir)
    short_name = meta["short_name"]
    dsh_pkg_name = meta["dsh_pkg_name"]

    client_path = target_dir / "client.js"
    client_path.write_text(assembled_code, encoding="utf-8")

    # DSH 官方插件必须声明 dsh.bundle 及其 cordis.patch.yml，否则 DSH 会拦截报错“这个包没有声明组合包，不能作为插件管理”
    patch_file = target_dir / "cordis.patch.yml"
    patch_content = f"# dsh bundle patch: inserts this plugin into profile layer stack\n- insert:\n    - id: {short_name}\n      name: {dsh_pkg_name}\n"
    patch_file.write_text(patch_content, encoding="utf-8")

    pkg_json_file = target_dir / "package.json"
    if pkg_json_file.is_file():
        try:
            pkg_data = json.loads(pkg_json_file.read_text(encoding="utf-8"))
            pkg_data["exports"] = {".": "./index.js", "./client": "./client.js"}
            files_list = pkg_data.get("files", [])
            for f in ("client.js", "cordis.patch.yml"):
                if f not in files_list:
                    files_list.append(f)
            pkg_data["files"] = files_list
            pkg_data["dsh"] = {
                "bundle": {
                    "patch": "./cordis.patch.yml"
                },
                "client": {
                    "platform": "web",
                    "immediately": True,
                    "inject": [
                        "@deepseek-ai/dsh-client-ui-plugin-manager",
                        "@deepseek-ai/dsh-client-ui-conversation"
                    ]
                }
            }
            pkg_json_file.write_text(json.dumps(pkg_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        except Exception as e:
            logger.warning("更新 %s 异常: %s", pkg_json_file, e)

    return meta


def assemble_all() -> List[Dict[str, Any]]:
    """扫描全工作区全系插件内核，全自动批量装配 DSH 智能体适配器。"""
    results = []
    # 1. packages/plugins/ 母港
    homeland = ROOT_DIR / "packages" / "plugins" / "openviking-memory"
    if homeland.is_dir():
        dsh_target = ROOT_DIR / "integrations" / "deepseek-harness" / "dsh-plugin-openviking-memory"
        m1 = assemble_and_write(homeland, homeland)
        m2 = assemble_and_write(homeland, dsh_target)
        results.append(m1)

    # 2. integrations/antigravity/ 插件内核
    ag_dir = ROOT_DIR / "integrations" / "antigravity"
    dsh_dir = ROOT_DIR / "integrations" / "deepseek-harness"
    if ag_dir.is_dir():
        for k_dir in sorted(ag_dir.iterdir()):
            if not k_dir.is_dir() or k_dir.name == "openviking-memory":
                continue
            dsh_name = KERNEL_TO_DSH_MAP.get(k_dir.name, f"dsh-plugin-{k_dir.name}")
            target_p = dsh_dir / dsh_name
            if target_p.is_dir():
                res = assemble_and_write(k_dir, target_p)
                results.append(res)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenViking 智能体适配器装配流水线")
    parser.add_argument("kernel", nargs="?", help="插件内核路径或名称")
    parser.add_argument("--out", "-o", help="输出目标目录")
    parser.add_argument("--all", "-a", action="store_true", help="全量扫描并装配全系插件")
    args = parser.parse_args()

    if args.all or not args.kernel:
        print("🚀 [DSH Adapter Assembler] 正在全量装配全系插件智能体适配器...")
        items = assemble_all()
        print(f"\n✅ 装配完成！共装配 {len(items)} 个插件 DSH 适配器：")
        print(f"  {'包名':<32} {'版本':<10} {'Tools':<8} {'Skills':<8} {'Hooks':<8}")
        print("  " + "-" * 70)
        for it in items:
            print(f"  {it['dsh_pkg_name']:<32} v{it['version']:<9} {it['tools_count']:<8} {it['skills_count']:<8} {it['hooks_count']:<8}")
    else:
        k_path = Path(args.kernel)
        if not k_path.is_dir():
            k_path = ROOT_DIR / "integrations" / "antigravity" / args.kernel
        if not k_path.is_dir():
            k_path = ROOT_DIR / "packages" / "plugins" / args.kernel

        out_path = Path(args.out) if args.out else k_path
        meta = assemble_and_write(k_path, out_path)
        print(f"✅ 成功为 {meta['dsh_pkg_name']} (v{meta['version']}) 装配 DSH 适配器 -> {out_path / 'client.js'}")


if __name__ == "__main__":
    main()
