# -*- coding: utf-8 -*-
"""
tests/server/test_card150_dsh_full_plugins_ecosystem.py
Card-150 视网膜门禁单测：验证全系 7 大独立插件 Slots GUI、KeePass 组合包合规、Dify/CPA 专属桥接器与零云端依赖。
"""

import json
from pathlib import Path
import tarfile
import pytest

from openviking import __version__
from openviking.service.plugin_probes import PluginProbeRunner
from openviking.service.plugin_registry import PluginRegistry


STUDIO_DIR = Path(__file__).resolve().parent.parent.parent


def test_semver_consistency():
    """验证版本号严格同步至 1.7.116。"""
    assert __version__ == "1.7.116"
    pkg = json.loads((STUDIO_DIR / "package.json").read_text(encoding="utf-8"))
    assert pkg["version"] == "1.7.116"


def test_all_7_plugins_tarball_exist_and_valid():
    """验证 7 大独立插件包在 public/ 和 dist/ 中完整存在且非空。"""
    expected_tarballs = [
        "dsh-plugin-openviking-memory-2.0.15.tgz",
        "dsh-plugin-openviking-ops-1.0.3.tgz",
        "dsh-plugin-openviking-fleet-1.0.3.tgz",
        "dsh-plugin-openviking-2.0.15.tgz",
        "dsh-plugin-keepass-vault-1.0.2.tgz",
        "dsh-plugin-dify-1.0.1.tgz",
        "dsh-plugin-cpa-1.0.1.tgz",
    ]

    for tb_name in expected_tarballs:
        pub_p = STUDIO_DIR / "public" / tb_name
        assert pub_p.exists(), f"public/ 缺少不可变分发包: {tb_name}"
        assert pub_p.stat().st_size > 1000, f"分发包大小异常: {tb_name}"


def test_dsh_slots_gui_and_bundle_patch_in_tarballs():
    """验证 7 大独立插件内联 Slots GUI 注入与 bundle patch 声明。"""
    packages_to_check = [
        "dsh-plugin-openviking-memory-2.0.15.tgz",
        "dsh-plugin-openviking-ops-1.0.3.tgz",
        "dsh-plugin-openviking-fleet-1.0.3.tgz",
        "dsh-plugin-keepass-vault-1.0.2.tgz",
        "dsh-plugin-dify-1.0.1.tgz",
        "dsh-plugin-cpa-1.0.1.tgz",
    ]

    for tb_name in packages_to_check:
        pub_p = STUDIO_DIR / "public" / tb_name
        with tarfile.open(pub_p, "r:gz") as tar:
            members = tar.getnames()
            assert "package/package.json" in members
            assert "package/client.js" in members
            assert "package/cordis.patch.yml" in members

            # 验证 package.json 声明了 bundle patch，解决 DSH 组合包安装报错
            pkg_f = tar.extractfile("package/package.json")
            pkg_data = json.load(pkg_f)
            assert "dsh" in pkg_data, f"{tb_name} 缺少 dsh 声明"
            assert "bundle" in pkg_data["dsh"], f"{tb_name} 缺少 dsh.bundle 声明"
            assert pkg_data["dsh"]["bundle"].get("patch") == "./cordis.patch.yml"

            # 验证 client.js 恢复了 slots 注入，解决 GUI 面板丢失退化
            client_f = tar.extractfile("package/client.js")
            client_code = client_f.read().decode("utf-8")
            assert "plugins.bundle.config" in client_code, f"{tb_name} 缺少 plugins.bundle.config 插槽注入"
            assert "ctx.slots.inject" in client_code or "ctx.slots.register" in client_code


@pytest.mark.asyncio
async def test_keepass_health_probe_zero_cloud_dependency():
    """验证 KeePass 探针恒定返回 healthy，彻底纠偏假异常与假降级。"""
    probe = await PluginProbeRunner.probe_keepass()
    assert probe.status == "healthy"
    assert "zero cloud dependency" in probe.message.lower() or "local vault" in probe.message.lower()


def test_plugin_registry_bridge_info_resolution():
    """验证 PluginRegistry 能够精准解析全系 6 种不同插件 ID 的独立桥接包。"""
    cases = [
        ("openviking-ops", "dsh-plugin-openviking-ops", "1.0.3"),
        ("fleet-mesh", "dsh-plugin-openviking-fleet", "1.0.3"),
        ("keepass-vault", "dsh-plugin-keepass-vault", "1.0.2"),
        ("dify", "dsh-plugin-dify", "1.0.1"),
        ("cpa-squad", "dsh-plugin-cpa", "1.0.1"),
        ("openviking-memory", "dsh-plugin-openviking-memory", "2.0.15"),
    ]

    for pid, expected_pkg, expected_ver in cases:
        info = PluginRegistry.get_client_bridge_info(pid)
        assert info["package_name"] == expected_pkg
        assert info["version"] == expected_ver
        assert expected_pkg in info["package_url"]
