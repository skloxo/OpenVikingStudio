# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""TDD Test Suite for quant-trading Domain Capability Bundle (Card-103)."""

import pytest
from pathlib import Path
import yaml

BUNDLE_ROOT = Path("/home/skloxo/.openviking/data/viking/default/agent/skills/quant-trading")
MODULES_DIR = BUNDLE_ROOT / "modules"
SCENARIOS_DIR = BUNDLE_ROOT / "scenarios"


def test_quant_trading_bundle_structure():
    assert BUNDLE_ROOT.exists()
    assert (BUNDLE_ROOT / "SKILL.md").exists()
    assert (BUNDLE_ROOT / "ABSORPTION_PROVENANCE.json").exists()
    assert (BUNDLE_ROOT / "PROVENANCE.json").exists()
    assert MODULES_DIR.is_dir()
    assert SCENARIOS_DIR.is_dir()
    
    # Check 5 core modules exist and line count in sweet spot (20~350)
    expected_modules = [
        "01_market_data_sourcing.md",
        "02_fundamental_and_factors.md",
        "03_backtest_and_alpha_zoo.md",
        "04_derivatives_and_hedging.md",
        "05_execution_and_risk_control.md",
    ]
    for mod in expected_modules:
        mod_path = MODULES_DIR / mod
        assert mod_path.exists(), f"Module {mod} missing"
        lines = len(mod_path.read_text(encoding="utf-8").splitlines())
        assert 20 <= lines <= 350, f"Module {mod} line count {lines} out of sweet spot"


def test_quant_trading_scenarios_preservation():
    # Ensure all 100 scenarios remain preserved in scenarios/ (Q1 ceiling)
    scenario_files = list(SCENARIOS_DIR.glob("*.md"))
    assert len(scenario_files) >= 100, f"Expected at least 100 scenarios, found {len(scenario_files)}"
    
    # Critical benchmark scenarios must exist
    critical_scenarios = [
        "tushare.md", "akshare.md", "yfinance.md", "ccxt.md",
        "3-statement-model.md", "pair-trading.md", "options-payoff.md"
    ]
    for cs in critical_scenarios:
        assert (SCENARIOS_DIR / cs).exists(), f"Critical scenario {cs} missing"


def test_quant_trading_skill_frontmatter_and_fsm():
    skill_md = (BUNDLE_ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert skill_md.startswith("---")
    fm = yaml.safe_load(skill_md.split("---", 2)[1])
    
    assert fm["name"] == "quant-trading"
    assert "量化" in fm["triggers"]
    assert "回测" in fm["triggers"]
    assert "夏普率" in fm["triggers"]
    assert "对冲" in fm["triggers"]
    
    # Check L1 Router Table integrity
    for i in range(1, 6):
        assert f"modules/0{i}_" in skill_md
    
    # Total lines of master SKILL.md should be lean (<= 150)
    total_lines = len(skill_md.splitlines())
    assert total_lines <= 150, f"Master SKILL.md too bloated ({total_lines} lines)"


def test_quant_natural_language_intent_routing():
    skill_md = (BUNDLE_ROOT / "SKILL.md").read_text(encoding="utf-8")
    fm = yaml.safe_load(skill_md.split("---", 2)[1])
    triggers = fm.get("triggers", [])
    
    test_queries = [
        ("编写一个针对A股和美股跨市场套利回测策略", ["A股", "美股", "套利", "回测", "量化"]),
        ("检查资产负债表与现金流量表计算Alpha因子", ["三张表", "财务分析", "财报", "多因子", "alpha"]),
        ("使用CCXT连接OKX获取永续合约资金费率", ["CCXT", "ccxt", "okx", "资金费率", "加密货币"]),
        ("设置期权Delta中性对冲与凯利仓位硬性止损", ["期权", "对冲", "仓位管理", "止损", "风控"]),
    ]
    
    for query, expected_keywords in test_queries:
        hit = any(kw.lower() in query.lower() and any(kw.lower() == t.lower() for t in triggers) for kw in expected_keywords)
        assert hit, f"Query '{query}' failed to trigger quant-trading keywords"
