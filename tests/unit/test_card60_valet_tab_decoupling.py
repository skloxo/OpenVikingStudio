"""Unit tests for Card-60: Valet Tab Decoupling & Dedicated Ingestion Observability.

Verifies that Tab 7 (valet) in route.tsx is purely decoupled from Tab 5 (crystallizer)
governance cards, eliminating duplicate background probe polling and restoring
dedicated ingestion observability.
"""

import json
from pathlib import Path
import re
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_valet_tab_decoupling_in_route():
    """Ensure Tab 7 mounts ONLY ValetIngestionCockpit and no crystallizer cards."""
    route_file = REPO_ROOT / "src" / "routes" / "retrieval" / "route.tsx"
    assert route_file.exists(), f"Missing route file at {route_file}"
    content = route_file.read_text(encoding="utf-8")

    # Match Tab 7 block
    valet_tab_match = re.search(
        r"\{\s*/\*\s*Tab 7:[^*]+\*/\s*\}\s*\{activeTab === 'valet'\s*&&([^}]+)\}",
        content,
    )
    assert valet_tab_match is not None, "Tab 7 block not found in route.tsx"
    valet_body = valet_tab_match.group(1).strip()

    # Must contain ValetIngestionCockpit
    assert "<ValetIngestionCockpit />" in valet_body, "ValetIngestionCockpit must be mounted in Tab 7"

    # Must NOT contain crystallizer cards
    forbidden_cards = [
        "MemoryPurityGaugeCard",
        "TemporalDecayDreamCard",
        "MemoryLineageDAGCard",
        "MemoryGovernanceStreamCard",
    ]
    for card in forbidden_cards:
        assert card not in valet_body, f"Forbidden card {card} found in Tab 7 block"

    # Tab 5 (crystallizer) must still retain its cards
    tab5_match = re.search(
        r"\{\s*/\*\s*Tab 5:[^*]+\*/\s*\}\s*\{activeTab === 'crystallizer'\s*&&([^}]+)\}",
        content,
    )
    assert tab5_match is not None, "Tab 5 block not found in route.tsx"
    tab5_body = tab5_match.group(1)
    for card in forbidden_cards:
        assert card in tab5_body, f"Tab 5 must retain card {card}"


def test_valet_cockpit_component_size_and_health():
    """Verify ValetIngestionCockpit file exists and adheres to size limits."""
    cockpit_file = (
        REPO_ROOT
        / "src"
        / "routes"
        / "retrieval"
        / "-components"
        / "valet-ingestion-cockpit.tsx"
    )
    assert cockpit_file.exists(), f"ValetIngestionCockpit missing at {cockpit_file}"
    lines = cockpit_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 500, f"ValetIngestionCockpit has {len(lines)} lines, exceeding 500 limit"
    assert len(lines) >= 100, f"ValetIngestionCockpit has only {len(lines)} lines"


def test_valet_cockpit_registered_in_inventory():
    """Verify ValetIngestionCockpit is registered in COMPONENT_AND_WHEEL_INVENTORY.md."""
    inventory_file = (
        REPO_ROOT / "docs" / "architecture" / "COMPONENT_AND_WHEEL_INVENTORY.md"
    )
    assert inventory_file.exists(), "COMPONENT_AND_WHEEL_INVENTORY.md missing"
    inventory = inventory_file.read_text(encoding="utf-8")
    assert "ValetIngestionCockpit" in inventory, (
        "ValetIngestionCockpit must be registered in COMPONENT_AND_WHEEL_INVENTORY.md"
    )
    assert "v1.7.14" in inventory, "ValetIngestionCockpit must reference delivery version v1.7.14"


def test_version_bump_card60():
    """Verify Card-60 SemVer patch bump to at least 1.7.14 and parity with python version."""
    package_json = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
    pkg_ver = package_json["version"]
    parts = [int(p) for p in pkg_ver.split(".")]
    assert (parts[0], parts[1], parts[2]) >= (1, 7, 14)

    py_version_file = REPO_ROOT / "openviking" / "_version.py"
    py_version_content = py_version_file.read_text(encoding="utf-8")
    assert f'"{pkg_ver}"' in py_version_content
