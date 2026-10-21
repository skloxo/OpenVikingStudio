#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/pack_all_plugins.py
全系插件单一真相源 (SSOT) 自动打包构建流水线。
自动从各插件母本 package.json / plugin.json 提取最新版本号，
生成不可变 .tgz 分发包与通用别名包至 public/ 和 dist/。
"""

import json
import os
import shutil
import sys
import tarfile
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = ROOT_DIR / "public"
DIST_DIR = ROOT_DIR / "dist"

PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
DIST_DIR.mkdir(parents=True, exist_ok=True)

TAR_EXCLUDES = {
    "__pycache__",
    ".git",
    "node_modules",
    ".pytest_cache",
    ".caps_cache.json",
    ".coverage",
}


def filter_tar_info(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo | None:
    parts = Path(tarinfo.name).parts
    for p in parts:
        if p in TAR_EXCLUDES or p.endswith(".pyc") or p.endswith(".tgz"):
            return None
    return tarinfo


def pack_directory(src_dir: Path, target_base_name: str, version: str, is_npm: bool = False) -> tuple[int, Path]:
    """将插件目录打包为标准 .tgz，并同步至 public/ 与 dist/"""
    versioned_name = f"{target_base_name}-{version}.tgz"
    # 单一不可变真身：仅分发带版本号的实体包，严禁生成无版本号影子别名包
    pub_v_path = PUBLIC_DIR / versioned_name

    with tarfile.open(pub_v_path, "w:gz") as tar:
        for item in src_dir.iterdir():
            if item.name in TAR_EXCLUDES or item.suffix == ".tgz":
                continue
            arc = f"package/{item.name}" if is_npm else item.name
            tar.add(item, arcname=arc, filter=filter_tar_info)

    # 同步至 dist/ 生产分发目录
    shutil.copy2(pub_v_path, DIST_DIR / versioned_name)

    size = pub_v_path.stat().st_size
    return size, pub_v_path


def main():
    print("📦 [全系插件 SSOT 打包流水线] 正在扫描并打包全系插件...")
    results = []

    # 1. 扫描 DeepSeek Harness 独立插件
    dsh_dir = ROOT_DIR / "integrations" / "deepseek-harness"
    if dsh_dir.is_dir():
        for p_dir in dsh_dir.iterdir():
            if not p_dir.is_dir():
                continue
            pkg_json = p_dir / "package.json"
            if pkg_json.is_file():
                try:
                    data = json.loads(pkg_json.read_text(encoding="utf-8"))
                    name = data.get("name", p_dir.name)
                    version = data.get("version", "1.0.0")
                    size, path = pack_directory(p_dir, name, version, is_npm=True)
                    results.append((name, version, size, "DSH"))
                except Exception as e:
                    print(f"  ⚠️ 打包 DSH 插件 {p_dir.name} 失败: {e}")

    # 2. 扫描 Antigravity 插件
    ag_dir = ROOT_DIR / "integrations" / "antigravity"
    if ag_dir.is_dir():
        for p_dir in ag_dir.iterdir():
            if not p_dir.is_dir():
                continue
            pj = p_dir / "plugin.json"
            if pj.is_file():
                try:
                    data = json.loads(pj.read_text(encoding="utf-8"))
                    name = data.get("name", p_dir.name)
                    version = data.get("version", "1.0.0")
                    size, path = pack_directory(p_dir, name, version, is_npm=False)
                    results.append((name, version, size, "Antigravity"))
                except Exception as e:
                    print(f"  ⚠️ 打包反重力插件 {p_dir.name} 失败: {e}")

    print("\n📊 打包产物清单 (已落盘至 public/ 和 dist/):")
    print(f"  {'插件生态':<12} {'包名':<32} {'版本':<10} {'体积 (Bytes)':<12}")
    print("  " + "-" * 70)
    for name, ver, size, eco in results:
        print(f"  {eco:<12} {name:<32} v{ver:<9} {size:<12}")
    print("\n✅ 全系插件打包完成，随时可用于生产分发！")


if __name__ == "__main__":
    main()
