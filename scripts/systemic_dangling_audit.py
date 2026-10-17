#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
全系统悬空功能与虚假断层全景审计总线 (Systemic Dangling Feature & Fake Mock Audit Pipeline)
结合 规则静态扫描器 + CPA 工兵多并发模型 (mux-flash, 8~12并发)，
对全量前端 Cockpit/Card 组件与后端 Routers 执行地毯式全面排查。
"""

import os
import sys
import json
import time
import re
import urllib.request
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

DEFAULT_CPA_URL = os.environ.get("CPA_API_URL", "http://127.0.0.1:8317/v1/chat/completions")

def load_cpa_key() -> str:
    key = os.environ.get("CPA_API_KEY", "")
    if key:
        return key
    conf_path = Path.home() / ".openviking" / "ov.conf"
    if conf_path.is_file():
        try:
            cfg = json.loads(conf_path.read_text(encoding="utf-8"))
            return (
                cfg.get("cpa", {}).get("api_key")
                or cfg.get("llm", {}).get("api_key")
                or cfg.get("vlm", {}).get("api_key")
                or cfg.get("server", {}).get("root_api_key", "")
            )
        except Exception:
            pass
    return ""

CPA_KEY = load_cpa_key()

# ----------------------------------------------------------------------
# 1. 静态规则扫描引擎 (Deterministic Static Feature Scanner)
# ----------------------------------------------------------------------

def scan_file_static_clues(file_path: Path) -> List[Dict[str, Any]]:
    """扫描单文件是否存在悬空、硬编码、缺少选择器、假操作等特征。"""
    clues = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return clues

    lines = content.splitlines()

    # 特征 1: 硬编码样例/Mock 常量
    mock_patterns = [
        (r'const\s+DEFAULT_SAMPLE\w*\s*=', 'HARDCODED_SAMPLE', '存在写死的 DEFAULT_SAMPLE 样例常量，可能缺少从全库选择加载功能'),
        (r'const\s+MOCK_\w*\s*=', 'HARDCODED_MOCK', '存在 MOCK_ 前缀的硬编码模拟数据'),
        (r'const\s+SAMPLE_\w*\s*=', 'HARDCODED_SAMPLE', '存在 SAMPLE_ 示例静态数据'),
        (r'const\s+DUMMY_\w*\s*=', 'HARDCODED_MOCK', '存在 DUMMY_ 静态假数据'),
        (r'const\s+INITIAL_\w*\s*=\s*\[\s*\{', 'HARDCODED_INITIAL_ARRAY', '存在写死的初始实体数组而非后端直读'),
    ]

    for line_idx, line in enumerate(lines, 1):
        for pat, cat, desc in mock_patterns:
            if re.search(pat, line):
                clues.append({
                    "line": line_idx,
                    "category": cat,
                    "code_snippet": line.strip()[:120],
                    "description": desc,
                })

    # 特征 2: 交互调优或操作工作台，但完全没有实体选择器
    is_workbench = any(w in file_path.name.lower() for w in ['workbench', 'editor', 'cockpit', 'sandbox'])
    if is_workbench:
        has_select = any(w in content for w in ['<select', '<Select', 'useCombobox', 'CommandInput', 'Popover', 'dropdown', 'Dropdown'])
        has_search_selector = any(w in content for w in ['searchQuery', 'filterQuery', 'selectedItem', 'selectedSkill', 'selectedSession'])
        has_hardcoded_content = 'DEFAULT_SAMPLE' in content or 'DEFAULT_SKILL' in content
        if has_hardcoded_content and not has_select and not has_search_selector:
            clues.append({
                "line": 1,
                "category": "ISOLATED_WORKBENCH",
                "code_snippet": file_path.name,
                "description": "工作台包含硬编码示例，但通篇没有任何实体选择器 (<Select>/<Dropdown>/搜索框)，无法从全量资产中选取",
            })

    # 特征 3: 假按钮 / 假操作 (console.log / alert / 无后端请求)
    fake_action_patterns = [
        (r'onClick\s*=\s*\{\s*\(\)\s*=>\s*console\.log', 'FAKE_BUTTON', '按钮仅执行 console.log，没有真实调用后端 API 或状态流转'),
        (r'onClick\s*=\s*\{\s*\(\)\s*=>\s*alert\(', 'FAKE_BUTTON', '按钮仅弹窗 alert，属于地下伪功能'),
        (r'onClick\s*=\s*\{\s*\(\)\s*=>\s*\{\s*\}\s*\}', 'EMPTY_HANDLER', '按钮点击回调为空函数，功能完全悬空未实现'),
    ]
    for line_idx, line in enumerate(lines, 1):
        for pat, cat, desc in fake_action_patterns:
            if re.search(pat, line):
                clues.append({
                    "line": line_idx,
                    "category": cat,
                    "code_snippet": line.strip()[:120],
                    "description": desc,
                })

    # 特征 4: 路径扫描错位 (后端 Router 或 Service 硬编码历史旧路径)
    if file_path.suffix == '.py':
        if '.openviking/skills' in content and 'viking/default/user/default/skills' not in content:
            clues.append({
                "line": 1,
                "category": "PATH_MISMATCH",
                "code_snippet": "~/.openviking/skills",
                "description": "后端引用了本地旧单层目录 ~/.openviking/skills，未包含 VikingFS 真实生产落地路径，易发生漏检失真",
            })

    return clues

# ----------------------------------------------------------------------
# 2. CPA 工兵模型红队审查 (CPA Adversarial Worker)
# ----------------------------------------------------------------------

CPA_REVIEW_PROMPT = """你是一个严苛的分布式代码与全栈架构红队审查专家。
用户发现系统中存在多处【功能悬空、数据失真、假操作、孤岛工作台】隐患。
静态分析器已经在该代码中探测出若干可疑特征线索。

请深入审读该文件代码，对这些线索做深度研判与挑刺，查明真相：
1. 它是否真的是一个【假功能/悬空功能/孤岛】？
2. 用户在前端界面操作它时，是否会遇到“只能看写死数据/无法选择真实资产/按钮点了没物理落盘”的问题？
3. 真实物理根因是什么？对生产治理有何严重后果？
4. 应该如何彻底改造与打通（给出精准工程方案）？

【输出格式】
必须且仅输出标准的 JSON 格式：
{
  "is_confirmed_dangling": true/false,
  "severity": "CRITICAL" | "HIGH" | "MEDIUM" | "FALSE_POSITIVE",
  "summary": "一句话核心定性",
  "root_cause": "深入物理根因剖析",
  "impact": "用户与业务层面的实际断层后果",
  "remediation": "彻底打通与根治的具体重构方案"
}"""

def review_file_with_cpa(file_path: Path, clues: List[Dict[str, Any]]) -> Dict[str, Any]:
    content = file_path.read_text(encoding="utf-8", errors="ignore")
    lines = content.splitlines()
    snippet = "\n".join(lines[:350])
    
    clues_str = json.dumps(clues, ensure_ascii=False, indent=2)
    user_msg = (
        f"【待审查源码文件】: {file_path}\n"
        f"【静态探测器捕获的存疑线索】:\n{clues_str}\n\n"
        f"【源码前 350 行切片】:\n```\n{snippet}\n```"
    )

    payload = {
        "model": "mux-flash",
        "messages": [
            {"role": "system", "content": CPA_REVIEW_PROMPT},
            {"role": "user", "content": user_msg}
        ],
        "max_tokens": 1500,
        "temperature": 0.1,
    }

    req = urllib.request.Request(
        DEFAULT_CPA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {CPA_KEY}",
            "User-Agent": "OpenViking-CPA-Auditor/1.0",
        },
        method="POST"
    )

    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            # 提取 JSON 对象
            m = re.search(r"\{[\s\S]*\}", raw)
            if m:
                parsed = json.loads(m.group(0))
            else:
                parsed = {"is_confirmed_dangling": True, "severity": "MEDIUM", "summary": raw[:200], "raw": raw}
            return {
                "file": str(file_path),
                "name": file_path.name,
                "elapsed": round(time.perf_counter() - t0, 2),
                "review": parsed,
                "clues": clues,
                "error": None
            }
    except Exception as exc:
        return {
            "file": str(file_path),
            "name": file_path.name,
            "elapsed": round(time.perf_counter() - t0, 2),
            "review": None,
            "clues": clues,
            "error": str(exc)
        }

def main():
    print("🔍 [Phase 1: 全局静态特征地毯式扫描] 正在遍历 src/routes 与 openviking/server ...")
    routes_dir = Path("src/routes")
    routers_dir = Path("openviking/server/routers")
    services_dir = Path("openviking/service")

    all_targets: List[Path] = []
    if routes_dir.exists():
        all_targets.extend(list(routes_dir.glob("**/*.tsx")))
    if routers_dir.exists():
        all_targets.extend(list(routers_dir.glob("*.py")))
    if services_dir.exists():
        all_targets.extend(list(services_dir.glob("*.py")))

    print(f"📊 目标代码文件总数: {len(all_targets)} 个")

    clues_map: Dict[Path, List[Dict[str, Any]]] = {}
    for f in all_targets:
        clues = scan_file_static_clues(f)
        if clues:
            clues_map[f] = clues

    print(f"🚩 静态规则捕获存疑文件: {len(clues_map)} 个！")
    for f, c in clues_map.items():
        print(f"   • {f.name} ({len(c)} 条存疑特征: {[x['category'] for x in c]})")

    print("\n⚡ [Phase 2: 调度 CPA 多并发工兵模型深度红队审讯] (8 并发线程池)...")
    results = []
    t_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_file = {
            executor.submit(review_file_with_cpa, f, clues): f
            for f, clues in clues_map.items()
        }
        for future in as_completed(future_to_file):
            f = future_to_file[future]
            try:
                res = future.result()
                results.append(res)
                rev = res.get("review") or {}
                is_dang = rev.get("is_confirmed_dangling", False)
                sev = rev.get("severity", "UNKNOWN")
                print(f"   [{'🚨 确诊悬空' if is_dang else '✅ 误报排除'}] {f.name} ({sev}) 耗时 {res.get('elapsed')}s")
            except Exception as e:
                print(f"   ❌ {f.name} CPA 审讯出错: {e}")

    total_time = round(time.perf_counter() - t_start, 2)
    print(f"\n🎉 CPA 协同红队审讯完成！总耗时: {total_time}s")

    # 结果归档
    report_json_path = Path("docs/architecture/DANGLING_FEATURE_AUDIT_REPORT.json")
    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    report_json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"📄 原始审计数据落盘: {report_json_path}")

    # 生成 Markdown 简报
    confirmed = [r for r in results if (r.get("review") or {}).get("is_confirmed_dangling")]
    critical = [r for r in confirmed if (r.get("review") or {}).get("severity") == "CRITICAL"]
    high = [r for r in confirmed if (r.get("review") or {}).get("severity") == "HIGH"]
    medium = [r for r in confirmed if (r.get("review") or {}).get("severity") == "MEDIUM"]

    md_lines = [
        "# 🚨 全系统悬空功能与虚假断层红队审计全景白皮书",
        "",
        "> **审计方法论**：静态 AST/正则特征过滤 + CPA 顶级工兵模型 (`mux-flash` 8 并发) 逐行深度审讯。",
        f"> **统计全貌**：扫描目标文件 `{len(all_targets)}` 个，探测出存疑文件 `{len(clues_map)}` 个，**CPA 确诊存在悬空/断层隐患 `{len(confirmed)}` 个**（CRITICAL: {len(critical)}, HIGH: {len(high)}, MEDIUM: {len(medium)}）。",
        "",
        "---",
        "",
        "## 📌 一、 确诊悬空与断层缺陷汇总矩阵",
        "",
        "| 严重度 | 缺陷模块 / 文件 | 核心定性与断层表现 | 物理根因剖析 | 彻底根治方案 |",
        "| :---: | :--- | :--- | :--- | :--- |",
    ]

    for item in sorted(confirmed, key=lambda x: (0 if (x.get("review") or {}).get("severity") == "CRITICAL" else (1 if (x.get("review") or {}).get("severity") == "HIGH" else 2))):
        rev = item.get("review") or {}
        name = item.get("name")
        fpath = item.get("file")
        sev = rev.get("severity", "MEDIUM")
        summary = rev.get("summary", "")
        root_cause = rev.get("root_cause", "")
        remediation = rev.get("remediation", "")
        md_lines.append(f"| **{sev}** | [`{name}`](file://{fpath}) | {summary} | {root_cause} | {remediation} |")

    md_lines.append("")
    md_lines.append("---")
    md_lines.append("## 📌 二、 缺陷详案与代码实证")
    md_lines.append("")

    for idx, item in enumerate(confirmed, 1):
        rev = item.get("review") or {}
        name = item.get("name")
        fpath = item.get("file")
        sev = rev.get("severity", "MEDIUM")
        md_lines.append(f"### {idx}. [{sev}] [`{name}`](file://{fpath})")
        md_lines.append(f"- **核心定性**: {rev.get('summary')}")
        md_lines.append(f"- **断层表现与危害**: {rev.get('impact')}")
        md_lines.append(f"- **物理根因**: {rev.get('root_cause')}")
        md_lines.append(f"- **根治方案**: {rev.get('remediation')}")
        md_lines.append("- **探测线索**:")
        for c in item.get("clues", []):
            md_lines.append(f"  - `L{c.get('line')}` [{c.get('category')}]: `{c.get('code_snippet')}` ({c.get('description')})")
        md_lines.append("")

    report_md_path = Path("docs/architecture/DANGLING_FEATURE_AUDIT_REPORT.md")
    report_md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"📄 Markdown 审计报告落盘: {report_md_path}")

if __name__ == "__main__":
    main()

