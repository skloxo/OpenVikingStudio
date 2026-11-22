"""Unit and repository hygiene tests for scripts.pack_all_plugins.prune_stale_tarballs."""

import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pack_all_plugins import (
    RETIRED_PACKAGE_PREFIXES,
    _parse_tarball_version,
    prune_stale_tarballs,
)


def test_parse_tarball_version_handles_versioned_and_shadow_names() -> None:
    assert _parse_tarball_version("dsh-plugin-openviking-2.0.43.tgz") == (
        "dsh-plugin-openviking",
        (2, 0, 43),
        "2.0.43",
    )
    assert _parse_tarball_version("agent-circuit-breaker-1.3.3.tgz") == (
        "agent-circuit-breaker",
        (1, 3, 3),
        "1.3.3",
    )
    assert _parse_tarball_version("tududi.tgz") is None
    assert _parse_tarball_version("dsh-plugin-nubia-operator.tgz") is None


def test_prune_stale_tarballs_removes_superseded_retired_and_shadows(tmp_path: Path) -> None:
    filenames = [
        "dsh-plugin-openviking-2.0.9.tgz",
        "dsh-plugin-openviking-2.0.43.tgz",
        "dsh-plugin-nubia-operator-1.2.41.tgz",
        "dsh-plugin-nubia-operator-1.2.59.tgz",
        "nubia-mobile-operator-1.2.59.tgz",
        "nubia-operator-1.0.0.tgz",
        "tududi.tgz",
        "tududi-1.1.8.tgz",
        "tududi-1.1.9.tgz",
        "dsh-plugin-mop-1.2.9.tgz",
        "dsh-plugin-mop-1.2.61.tgz",
    ]
    for name in filenames:
        (tmp_path / name).write_bytes(b"tgz")

    pruned = prune_stale_tarballs(
        tmp_path,
        keep_exact={"dsh-plugin-openviking-2.0.43.tgz", "tududi-1.1.9.tgz"},
        managed_bases={"dsh-plugin-openviking", "tududi"},
    )

    remaining = {p.name for p in tmp_path.glob("*.tgz")}
    assert remaining == {
        "dsh-plugin-openviking-2.0.43.tgz",
        "tududi-1.1.9.tgz",
        "dsh-plugin-mop-1.2.61.tgz",
    }
    assert set(pruned) == {
        "dsh-plugin-openviking-2.0.9.tgz",
        "dsh-plugin-nubia-operator-1.2.41.tgz",
        "dsh-plugin-nubia-operator-1.2.59.tgz",
        "nubia-mobile-operator-1.2.59.tgz",
        "nubia-operator-1.0.0.tgz",
        "tududi.tgz",
        "tududi-1.1.8.tgz",
        "dsh-plugin-mop-1.2.9.tgz",
    }


def test_prune_stale_tarballs_prefers_release_over_prerelease(tmp_path: Path) -> None:
    (tmp_path / "ext-tool-1.0.0-rc.1.tgz").write_bytes(b"rc")
    (tmp_path / "ext-tool-1.0.0.tgz").write_bytes(b"rel")

    pruned = prune_stale_tarballs(tmp_path, keep_exact=set(), managed_bases=set())

    assert pruned == ["ext-tool-1.0.0-rc.1.tgz"]
    assert [p.name for p in tmp_path.glob("*.tgz")] == ["ext-tool-1.0.0.tgz"]


def test_prune_stale_tarballs_missing_dir_returns_empty(tmp_path: Path) -> None:
    assert prune_stale_tarballs(tmp_path / "nonexistent", set(), set()) == []


def test_repo_public_tarballs_have_single_latest_version_and_no_retired() -> None:
    public_dir = REPO_ROOT / "public"
    assert public_dir.is_dir()

    tgzs = sorted(public_dir.glob("*.tgz"))
    assert len(tgzs) > 0

    base_counts: Counter[str] = Counter()
    for tgz in tgzs:
        parsed = _parse_tarball_version(tgz.name)
        assert parsed is not None, f"Unversioned shadow tarball found in public/: {tgz.name}"
        base = parsed[0]
        assert base not in RETIRED_PACKAGE_PREFIXES, f"Retired tarball found in public/: {tgz.name}"
        base_counts[base] += 1

    duplicates = {base: count for base, count in base_counts.items() if count != 1}
    assert not duplicates, f"Duplicate/superseded tarballs remain in public/: {duplicates}"
