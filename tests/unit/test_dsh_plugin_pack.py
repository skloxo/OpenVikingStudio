"""
tests/unit/test_dsh_plugin_pack.py

DSH 官方标杆客户端插件 (dsh-plugin-openviking) 打包与分发流水线测试视网膜。
验证工程铁律：
1. 源码完整性与自包含单文件 schema.js 约束
2. 前端 DSH_PLUGIN_VERSION 契约对齐
3. 不可变 Tarball 结构与别名软链接哈希一致性
4. DshPluginPacker 运行态自检
"""

import hashlib
import json
from pathlib import Path
import sys
import tarfile
import pytest

# 确保脚本模块可导入
PROJECT_ROOT = Path(__file__).resolve().parents[2].parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from pack_dsh_plugin import DshPluginPacker


@pytest.fixture
def packer():
    return DshPluginPacker(project_root=PROJECT_ROOT)


def test_source_integrity(packer):
    """测试插件源码目录与内联 Schema 约束。"""
    meta = packer.verify_source_integrity()
    assert meta["name"] == "dsh-plugin-openviking"
    assert meta["version"] != ""
    assert meta["schema_size"] >= 30 * 1024  # >= 30KB 确保内联 cosmokit/schemastery


def test_frontend_version_contract_alignment(packer):
    """测试前端常数与插件版本单一真实源对齐。"""
    meta = packer.verify_source_integrity()
    fe_version = packer.get_frontend_version()
    assert fe_version is not None
    assert fe_version == meta["version"], (
        f"前端常量 DSH_PLUGIN_VERSION ({fe_version}) 与 package.json 版本 ({meta['version']}) 不一致！"
    )


def test_public_tarball_structure_and_hashes(packer):
    """测试 Web Studio 静态分发目录下的 Tarball 完整性与 SHA256 一致性。"""
    meta = packer.verify_source_integrity()
    version = meta["version"]
    versioned_tar = packer.public_dir / f"dsh-plugin-openviking-{version}.tgz"
    alias_tar = packer.public_dir / "dsh-plugin-openviking.tgz"

    assert versioned_tar.exists(), f"未找到版本化静态产物: {versioned_tar}"
    assert alias_tar.exists(), f"未找到兼容别名静态产物: {alias_tar}"

    # 验证 Tarball 内部文件结构
    with tarfile.open(versioned_tar, "r:gz") as tar:
        names = set(tar.getnames())
        expected = {
            "package/package.json",
            "package/index.js",
            "package/schema.js",
            "package/cordis.patch.yml",
        }
        for item in expected:
            assert item in names, f"Tarball 缺少关键内含文件: {item}"

    # 验证版本包与别名包哈希一致
    h_ver = hashlib.sha256(versioned_tar.read_bytes()).hexdigest()
    h_alias = hashlib.sha256(alias_tar.read_bytes()).hexdigest()
    assert h_ver == h_alias, "版本包与别名包内容哈希不一致！"


def test_packer_dry_run_contract(packer):
    """测试流水线 dry-run 模式返回契约结构。"""
    res = packer.run(allow_dirty=True, dry_run=True)
    assert res["status"] == "dry-run"
    assert res["package_name"] == "dsh-plugin-openviking"
    assert res["version"] == res["frontend_version"]
    assert "public_dir" in res
