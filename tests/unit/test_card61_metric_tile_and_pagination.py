"""Unit tests for Card-61: Shared MetricTile & UniversalPagination Wheel Harvesting.

Verifies that MetricTile and UniversalPagination:
1. Exist in src/components/common/
2. Strictly adhere to single file size <= 500 lines (golden sweet spot)
3. 100% adhere to NO GREEN EVER (no emerald/green classes)
4. 100% adhere to minimum font size >= 12px (no text-[8..11px])
5. Are exported in src/components/common/index.ts
6. Are registered in COMPONENT_AND_WHEEL_INVENTORY.md
7. Align with SemVer patch 1.7.15
"""

import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_metric_tile_wheel_contracts():
    """Verify MetricTile component existence, size and design system contracts."""
    tile_file = REPO_ROOT / "src" / "components" / "common" / "metric-tile.tsx"
    assert tile_file.exists(), f"MetricTile missing at {tile_file}"
    content = tile_file.read_text(encoding="utf-8")
    lines = content.splitlines()

    assert 50 <= len(lines) <= 500, f"MetricTile lines={len(lines)}, outside 50~500 range"
    # Strict NO GREEN EVER
    assert "text-green" not in content and "bg-green" not in content
    assert "text-emerald" not in content and "bg-emerald" not in content
    # Strict minimum font size >= 12px
    for forbidden in ["text-[8px]", "text-[9px]", "text-[10px]", "text-[11px]"]:
        assert forbidden not in content, f"MetricTile violates font size limit: {forbidden}"
    # tabular-nums and font-mono for digits
    assert "tabular-nums" in content
    assert "font-mono" in content


def test_universal_pagination_wheel_contracts():
    """Verify UniversalPagination component existence, size and design system contracts."""
    page_file = (
        REPO_ROOT / "src" / "components" / "common" / "universal-pagination.tsx"
    )
    assert page_file.exists(), f"UniversalPagination missing at {page_file}"
    content = page_file.read_text(encoding="utf-8")
    lines = content.splitlines()

    assert 50 <= len(lines) <= 500, f"UniversalPagination lines={len(lines)}, outside 50~500 range"
    # Strict NO GREEN EVER
    assert "text-green" not in content and "bg-green" not in content
    assert "text-emerald" not in content and "bg-emerald" not in content
    # Strict minimum font size >= 12px
    for forbidden in ["text-[8px]", "text-[9px]", "text-[10px]", "text-[11px]"]:
        assert forbidden not in content, f"UniversalPagination violates font size limit: {forbidden}"
    # i18n support
    assert "useTranslation" in content


def test_common_index_exports():
    """Verify common index exports MetricTile and UniversalPagination."""
    index_file = REPO_ROOT / "src" / "components" / "common" / "index.ts"
    assert index_file.exists(), f"index.ts missing at {index_file}"
    content = index_file.read_text(encoding="utf-8")
    assert "MetricTile" in content
    assert "UniversalPagination" in content
    assert "CopyButton" in content


def test_inventory_and_version_card61():
    """Verify inventory registration and SemVer bump to 1.7.15."""
    inventory_file = (
        REPO_ROOT / "docs" / "architecture" / "COMPONENT_AND_WHEEL_INVENTORY.md"
    )
    inventory = inventory_file.read_text(encoding="utf-8")
    assert "MetricTile" in inventory
    assert "UniversalPagination" in inventory
    assert "v1.7.15" in inventory

    package_json = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
    pkg_ver = package_json["version"]
    parts = [int(p) for p in pkg_ver.split(".")]
    assert (parts[0], parts[1], parts[2]) >= (1, 7, 15)

    py_version = (REPO_ROOT / "openviking" / "_version.py").read_text(encoding="utf-8")
    assert f'"{pkg_ver}"' in py_version
