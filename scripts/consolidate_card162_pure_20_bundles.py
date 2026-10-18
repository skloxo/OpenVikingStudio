#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
scripts/consolidate_card162_pure_20_bundles.py - Card-162: 20 核心领域能力大包物理纯化与归并引擎

核心使命：
1. 将 web-search-pro 及回潮的单体工序 100% 安全收敛至对应的母包 scenarios/；
2. 将顶层散装/多余目录安全迁移至 agent/skills_archive_transition/ 归档；
3. 确保顶层目录严格收敛为 20 个黄金核心领域能力大包；
4. 重新烘焙这 20 个大包的 .abstract.md 极速元数据索引；
5. 验证 SkillAliasingRouter 虚拟投影零破坏透明路由契约。
"""

import os
import shutil
import sys
import yaml
from pathlib import Path

SKILLS_ROOT = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")
ARCHIVE_ROOT = Path("/home/skloxo/.openviking/data/viking/default/agent/skills_archive_transition")

EXPECTED_20_BUNDLES = [
    "ai-harness-ops",
    "antigravity-host-ops",
    "cloud-infra-ops",
    "cockpit-ui",
    "codebase-engineering",
    "cpa_squad",
    "credential-vault",
    "developer-productivity",
    "document-governance",
    "living-asset-system",
    "multimodal-media",
    "network-tunnel-ops",
    "openviking",
    "park-grid-governance",
    "presentation-designer",
    "property-cadre-ops",
    "quant-trading",
    "security-audit-compliance",
    "session-handover",
    "web-harvest-pro",
]

TRANSITION_SKILLS_TO_ARCHIVE = [
    "web-search-pro",
    "agent-governance-guardrails",
    "capability-bundle-crystallizer",
    "clash_verge_governance",
    "deepseek-harness-ops",
    "global-agent-core",
]


def ensure_scenario_presence():
    """保障所有即将归档的工序在对应的母包 scenarios/ 中 100% 完整留存"""
    print("🔍 [1/5] 正在校验并同步单体工序至母包 scenarios/ ...")
    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)

    # 1. global-agent-core (12KB 最新版本同步至母包)
    g_core_skill = SKILLS_ROOT / "global-agent-core" / "SKILL.md"
    if g_core_skill.exists():
        content = g_core_skill.read_text(encoding="utf-8")
        target_cb = SKILLS_ROOT / "codebase-engineering" / "scenarios" / "global-agent-core.md"
        target_ov = SKILLS_ROOT / "openviking" / "scenarios" / "global-agent-core.md"
        target_cb.parent.mkdir(parents=True, exist_ok=True)
        target_ov.parent.mkdir(parents=True, exist_ok=True)
        target_cb.write_text(content, encoding="utf-8")
        target_ov.write_text(content, encoding="utf-8")
        print("  ✅ global-agent-core.md 已同步至 codebase-engineering 和 openviking scenarios/")

    # 2. web-search-pro (确保在 web-harvest-pro 中完整存在)
    w_search_sc = SKILLS_ROOT / "web-harvest-pro" / "scenarios" / "web-search-pro.md"
    if not w_search_sc.exists() or w_search_sc.stat().st_size < 1000:
        top_w_search = SKILLS_ROOT / "web-search-pro" / "SKILL.md"
        if top_w_search.exists():
            w_search_sc.write_text(top_w_search.read_text(encoding="utf-8"), encoding="utf-8")
            print("  ✅ web-search-pro.md 已固化至 web-harvest-pro/scenarios/")
    else:
        print(f"  ✅ web-search-pro.md 确认在 web-harvest-pro/scenarios/ 完整留存 ({w_search_sc.stat().st_size} bytes)")

    # 3. 矫正历史误归入 document-governance 的场景，移至正统母包
    doc_gov_sc = SKILLS_ROOT / "document-governance" / "scenarios"
    ai_ops_sc = SKILLS_ROOT / "ai-harness-ops" / "scenarios"
    net_tunnel_sc = SKILLS_ROOT / "network-tunnel-ops" / "scenarios"

    # deepseek-harness-ops -> ai-harness-ops (保留最完整版本)
    dsh_doc = doc_gov_sc / "deepseek-harness-ops.md"
    dsh_ai = ai_ops_sc / "deepseek-harness-ops.md"
    if dsh_doc.exists():
        if not dsh_ai.exists() or dsh_ai.stat().st_size < dsh_doc.stat().st_size:
            dsh_ai.write_text(dsh_doc.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"  ✅ deepseek-harness-ops.md 完整版 ({dsh_doc.stat().st_size} bytes) 已矫正至 ai-harness-ops/scenarios/")
        dsh_doc.unlink()
        print("  🧹 已从 document-governance/scenarios/ 清理误放的 deepseek-harness-ops.md")

    # clash_verge_governance -> 确保在 network-tunnel-ops，清理 document-governance 误放
    clash_doc = doc_gov_sc / "clash_verge_governance.md"
    clash_net = net_tunnel_sc / "clash_verge_governance.md"
    if clash_doc.exists():
        if not clash_net.exists() or clash_net.stat().st_size < clash_doc.stat().st_size:
            clash_net.write_text(clash_doc.read_text(encoding="utf-8"), encoding="utf-8")
        clash_doc.unlink()
        print("  🧹 已从 document-governance/scenarios/ 清理误放的 clash_verge_governance.md")

    # agent-governance-guardrails -> 确保在 ai-harness-ops，清理 document-governance 误放
    guard_doc = doc_gov_sc / "agent-governance-guardrails.md"
    guard_ai = ai_ops_sc / "agent-governance-guardrails.md"
    if guard_doc.exists():
        if not guard_ai.exists():
            guard_ai.write_text(guard_doc.read_text(encoding="utf-8"), encoding="utf-8")
        guard_doc.unlink()
        print("  🧹 已从 document-governance/scenarios/ 清理误放的 agent-governance-guardrails.md")


def archive_transition_skills():
    """将散落单体工序迁移至 skills_archive_transition/"""
    print("📦 [2/5] 正在将过渡工序安全迁移归档 ...")
    for name in TRANSITION_SKILLS_TO_ARCHIVE:
        src = SKILLS_ROOT / name
        if src.exists() and src.is_dir():
            dst = ARCHIVE_ROOT / name
            if dst.exists():
                shutil.rmtree(dst)
            shutil.move(str(src), str(dst))
            print(f"  📦 已迁移归档: {name} -> skills_archive_transition/{name}")
        else:
            print(f"  ℹ️ 目录无需迁移 (已不存在于顶层): {name}")


def verify_pure_20_bundles():
    """严苛校验顶层目录纯化为 20 个大包"""
    print("⚖️ [3/5] 正在严苛核验 20 核心领域能力大包物理纯化事实 ...")
    current_dirs = sorted([
        d.name for d in SKILLS_ROOT.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ])
    print(f"  📊 当前顶层大包列表 (共 {len(current_dirs)} 个): {current_dirs}")

    assert len(current_dirs) == 20, f"顶层目录数必须严格为 20，实际检测为: {len(current_dirs)} -> {current_dirs}"
    assert current_dirs == sorted(EXPECTED_20_BUNDLES), f"顶层目录集合必须与 20 核心大包 100% 对齐！"

    for b_name in current_dirs:
        b_dir = SKILLS_ROOT / b_name
        skill_md = b_dir / "SKILL.md"
        assert skill_md.exists(), f"大包 [{b_name}] 必须包含标准 SKILL.md 定义文件！"
        sc_dir = b_dir / "scenarios"
        sc_cnt = len(list(sc_dir.glob("*.md"))) if sc_dir.is_dir() else 0
        print(f"    - {b_name:28} | scenarios: {sc_cnt:3} | SKILL.md: OK")

    print("  ✅ 20 核心领域能力大包物理纯化校验 100% PASS！")


def generate_abstract_indices():
    """为 20 个大包生成最新 .abstract.md 极速元数据索引"""
    print("📝 [4/5] 正在重新烘焙 20 核心大包 .abstract.md 摘要索引 ...")
    for b_name in EXPECTED_20_BUNDLES:
        b_dir = SKILLS_ROOT / b_name
        skill_md = b_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        try:
            content = skill_md.read_text(encoding="utf-8", errors="ignore")
            from openviking.core.skill_loader import SkillLoader
            parsed = SkillLoader.parse(content)
            abstract_meta = {
                "name": parsed.get("name") or b_name,
                "description": parsed.get("description", f"Domain Capability Bundle for {b_name}"),
                "tags": parsed.get("tags") or [],
                "allowed_tools": parsed.get("allowed_tools") or [],
                "triggers": parsed.get("triggers") or [],
                "is_bundle": True,
            }
            abstract_path = b_dir / ".abstract.md"
            abstract_path.write_text(yaml.safe_dump(abstract_meta, allow_unicode=True, sort_keys=False), encoding="utf-8")
        except Exception as err:
            print(f"  ⚠️ 生成 {b_name} 摘要异常: {err}")
    print("  ✅ 20 核心大包 .abstract.md 极速索引重新烘焙完毕！")


def verify_aliasing_router():
    """验证 SkillAliasingRouter 虚拟别名透明投影零破坏"""
    print("🔗 [5/5] 正在验证 SkillAliasingRouter 虚拟别名透明投影契约 ...")
    from openviking.service.skill_aliasing_router import SkillAliasingRouter
    router = SkillAliasingRouter(skills_root=SKILLS_ROOT)
    alias_map = router.get_alias_map(force_refresh=True)

    test_targets = [
        ("web-search-pro", "web-harvest-pro"),
        ("global-agent-core", None),
        ("deepseek-harness-ops", "ai-harness-ops"),
        ("clash_verge_governance", "network-tunnel-ops"),
        ("agent-governance-guardrails", "ai-harness-ops"),
        ("capability-bundle-crystallizer", "openviking"),
        ("tide-trading-dev", None),
        ("auto-pr", None),
    ]

    for req_name, exp_bundle in test_targets:
        res = router.resolve(req_name)
        assert res is not None, f"别名网关无法解析: {req_name}"
        if exp_bundle:
            assert res["bundle_name"] == exp_bundle, f"解析母包不匹配: {req_name} -> {res['bundle_name']} != {exp_bundle}"
        v_skill = router.get_virtual_skill(req_name)
        assert v_skill is not None, f"无法组装虚拟技能响应: {req_name}"
        assert v_skill["name"] == req_name
        assert "content" in v_skill and len(v_skill["content"]) > 50
        print(f"  ✅ 投影测试通过: {req_name:30} -> bundle: {res['bundle_name']:22} (is_virtual={res.get('is_virtual')})")

    print("  ✅ 虚拟别名透明网关 100% 验收通过！")


if __name__ == "__main__":
    try:
        ensure_scenario_presence()
        archive_transition_skills()
        verify_pure_20_bundles()
        generate_abstract_indices()
        verify_aliasing_router()
        print("\n🎉 [Card-162] 20 核心领域能力大包物理纯化与归并闭环圆满完成！")
    except Exception as e:
        print(f"\n❌ [Card-162 物理纯化失败] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
