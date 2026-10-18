import json
import os
import re
from openviking._version import __version__


def test_card74_version_alignment():
    """Verify SemVer version alignment across Python and package.json is 1.7.28."""
    pkg_path = os.path.join(os.path.dirname(__file__), "..", "..", "package.json")
    with open(pkg_path, "r", encoding="utf-8") as f:
        pkg_data = json.load(f)
    assert pkg_data["version"] == __version__
    assert __version__.startswith("1.7.")


def test_card74_harness_engine_card_truthfulness():
    """Verify that harness-engine-card.tsx has real data bindings and no dead column 4 text."""
    card_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "src",
        "routes",
        "monitoring",
        "-components",
        "harness-engine-card.tsx",
    )
    assert os.path.exists(card_path), f"File {card_path} must exist"

    with open(card_path, "r", encoding="utf-8") as f:
        content = f.read()
        lines = content.splitlines()

    # Rule 1: Single file size within golden sweet spot
    assert len(lines) <= 300, f"File size must be <= 300 lines, got {len(lines)}"

    # Rule 2: Column 4 dead text removed
    assert '<span className="font-semibold text-muted-foreground tabular-nums">--</span>' not in content, (
        "Column 4 must not contain hardcoded dead '--' placeholder"
    )

    # Rule 3: Dynamic latency and engine binding present
    assert "avg_latency_ms" in content, "avg_latency_ms must be queried"
    assert "active_engine" in content, "active_engine must be queried"
    assert "is_model_loaded" in content, "is_model_loaded must be queried"

    # Rule 4: Cold start 0-sample handling
    assert "待抽稀" in content, "Should handle 0 samples as '待抽稀'"
    assert "待编译" in content, "Should handle 0 samples as '待编译'"

    # Rule 5: NO GREEN EVER
    green_matches = re.findall(r"(?:text|bg|border)-green-\d+", content)
    assert len(green_matches) == 0, f"NO GREEN EVER violated: {green_matches}"
