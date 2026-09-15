"""
tests/unit/test_version_alignment_gate.py - 版本对齐与自动化发布门禁单元测试
"""

import os
import json
import pytest
from scripts.release_step import (
    read_package_json_version,
    read_python_version,
    compute_next_version,
    verify_dist_baked_version,
    PKG_JSON_PATH,
    VERSION_PY_PATH,
)


def test_package_json_and_python_version_parity():
    """验证 package.json 与 openviking/_version.py 版本号严格一致"""
    pkg_ver = read_package_json_version()
    py_ver = read_python_version()

    assert pkg_ver, "package.json 版本号不能为空"
    assert py_ver, "openviking/_version.py 版本号不能为空"
    assert pkg_ver == py_ver, (
        f"双端版本号不一致: package.json={pkg_ver} vs openviking/_version.py={py_ver}"
    )


def test_compute_next_version_semver():
    """验证 semver 递增算法正确性"""
    assert compute_next_version("1.5.04", "patch") == "1.5.5"
    assert compute_next_version("1.5.9", "patch") == "1.5.10"
    assert compute_next_version("1.5.4", "minor") == "1.6.0"
    assert compute_next_version("1.5.4", "major") == "2.0.0"

    with pytest.raises(ValueError):
        compute_next_version("invalid_version", "patch")


def test_dist_baked_version_integrity():
    """验证 dist/assets 静态产物已物理烘焙当前 package.json 版本"""
    current_ver = read_package_json_version()
    assert verify_dist_baked_version(current_ver) is True, (
        f"dist/assets 产物中未检测到当前版本 {current_ver}，请执行 npm run build"
    )

    # 验证虚假未来版本一定报错返回 False
    assert verify_dist_baked_version("999.999.999") is False
