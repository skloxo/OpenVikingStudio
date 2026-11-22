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
import re
import shutil
import sys
import tarfile
from pathlib import Path

# 引入智能体适配器装配流水线
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
from assemble_dsh_adapter import assemble_dsh_adapter, DSH_TO_KERNEL_MAP

ROOT_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = ROOT_DIR / "public"
DIST_DIR = ROOT_DIR / "dist"

PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
DIST_DIR.mkdir(parents=True, exist_ok=True)

RETIRED_PACKAGE_PREFIXES = (
    "dsh-plugin-nubia-operator",
    "nubia-mobile-operator",
    "nubia-operator",
)
_TARBALL_VERSION_RE = re.compile(r"^(.+)-(\d+(?:\.\d+)+.*?)\.tgz$")
_NUMERIC_PREFIX_RE = re.compile(r"^(\d+(?:\.\d+)+)(.*)$")


def _parse_tarball_version(filename: str) -> tuple[str, tuple[int, ...], str] | None:
    """Parse `<base>-<semver>.tgz` into `(base, numeric_parts, raw_version)`."""
    matched = _TARBALL_VERSION_RE.match(filename)
    if not matched:
        return None
    base, raw_ver = matched.group(1), matched.group(2)
    num_match = _NUMERIC_PREFIX_RE.match(raw_ver)
    if not num_match:
        return None
    numeric_parts = tuple(int(part) for part in num_match.group(1).split("."))
    return base, numeric_parts, raw_ver


def _tarball_sort_key(parsed: tuple[str, tuple[int, ...], str]) -> tuple[tuple[int, ...], int, str]:
    """Order numeric versions cleanly and prefer final releases over prereleases."""
    _, numeric_parts, raw_ver = parsed
    is_release = 1 if re.fullmatch(r"\d+(?:\.\d+)+", raw_ver) else 0
    return numeric_parts, is_release, raw_ver


def prune_stale_tarballs(
    target_dir: Path,
    keep_exact: set[str],
    managed_bases: set[str],
) -> list[str]:
    """Remove unversioned shadows, retired plugins, and superseded .tgz archives."""
    if not target_dir.is_dir():
        return []

    pruned: list[str] = []
    unmanaged: dict[str, list[tuple[tuple[str, tuple[int, ...], str], Path]]] = {}

    for tgz in sorted(target_dir.glob("*.tgz")):
        if not (tgz.is_file() or tgz.is_symlink()):
            continue
        parsed = _parse_tarball_version(tgz.name)
        if parsed is None:
            tgz.unlink()
            pruned.append(tgz.name)
            continue

        base = parsed[0]
        if base in RETIRED_PACKAGE_PREFIXES:
            tgz.unlink()
            pruned.append(tgz.name)
        elif base in managed_bases:
            if tgz.name not in keep_exact:
                tgz.unlink()
                pruned.append(tgz.name)
        else:
            unmanaged.setdefault(base, []).append((parsed, tgz))

    for entries in unmanaged.values():
        if len(entries) <= 1:
            continue
        _, keep_path = max(entries, key=lambda item: (_tarball_sort_key(item[0]), item[1].name))
        for _, tgz in entries:
            if tgz != keep_path:
                tgz.unlink()
                pruned.append(tgz.name)

    return pruned

TAR_EXCLUDES = {
    "__pycache__",
    ".git",
    "node_modules",
    ".pytest_cache",
    ".caps_cache.json",
    ".coverage",
    "config.json",
    "mcp_config.json",
    ".ov_Hook.log",
}


def filter_tar_info(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo | None:
    parts = Path(tarinfo.name).parts
    for p in parts:
        if p in TAR_EXCLUDES or p.endswith(".pyc") or p.endswith(".tgz"):
            return None
    # 强制固定归档时间戳，确保打包字节级确定性 (Deterministic Tarball)
    tarinfo.mtime = 1700000000
    tarinfo.uid = 0
    tarinfo.gid = 0
    tarinfo.uname = "openviking"
    tarinfo.gname = "openviking"
    return tarinfo


def pack_directory(src_dir: Path, target_base_name: str, version: str, is_npm: bool = False) -> tuple[int, Path]:
    """将插件目录打包为标准 .tgz，并同步至 public/ 与 dist/"""
    versioned_name = f"{target_base_name}-{version}.tgz"
    pub_v_path = PUBLIC_DIR / versioned_name

    # 严格守卫单一不可变发布包公理：已发布的包禁止无脑原地覆盖，防止客户端 lockfile 校验和崩溃
    if pub_v_path.is_file() and not os.environ.get("FORCE_REPACK"):
        shutil.copy2(pub_v_path, DIST_DIR / versioned_name)
        return pub_v_path.stat().st_size, pub_v_path

    with tarfile.open(pub_v_path, "w:gz") as tar:
        for item in src_dir.iterdir():
            if item.name in TAR_EXCLUDES or item.suffix == ".tgz" or item.name == "client.js":
                continue
            arc = f"package/{item.name}" if is_npm else item.name
            tar.add(item, arcname=arc, filter=filter_tar_info)

    shutil.copy2(pub_v_path, DIST_DIR / versioned_name)
    size = pub_v_path.stat().st_size
    return size, pub_v_path


def pack_dsh_with_injected_client(
    src_dir: Path,
    target_base_name: str,
    version: str,
    template_path: Path,
    readme_path: Path,
    kernel_dir: Path | None = None,
) -> tuple[int, Path]:
    """打包 DSH 插件包，并在打包时自动注入通用的 client.js 解释器，源码 0 行前端"""
    import io
    versioned_name = f"{target_base_name}-{version}.tgz"
    pub_v_path = PUBLIC_DIR / versioned_name

    # 严格守卫单一不可变发布包公理：已发布的包禁止无脑原地覆盖，防止客户端 lockfile 校验和崩溃
    if pub_v_path.is_file() and not os.environ.get("FORCE_REPACK"):
        shutil.copy2(pub_v_path, DIST_DIR / versioned_name)
        return pub_v_path.stat().st_size, pub_v_path

    # 若插件目录下已存在专精定制的 client.js，优先使用母港原生适配器；否则使用通用模板动态组装
    custom_client = src_dir / "client.js"
    if custom_client.is_file():
        injected_client_js = custom_client.read_text(encoding="utf-8")
    else:
        # 优先使用通用装配流水线动态提取内核能力并组装适配器代码
        k_dir = kernel_dir or src_dir
        try:
            injected_client_js, meta = assemble_dsh_adapter(k_dir, template_path)
        except Exception:
            # 兼容退化
            readme_text = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else "# " + target_base_name
            safe_readme = readme_text.replace("`", "\\`").replace("${", "\\${")
            tpl_text = template_path.read_text(encoding="utf-8")
            injected_client_js = (
                tpl_text
                .replace("__PLUGIN_ID__", target_base_name)
                .replace("__PLUGIN_VERSION__", version)
                .replace("__PLUGIN_NAME__", target_base_name)
                .replace("__SHORT_NAME__", target_base_name.replace("dsh-plugin-", ""))
                .replace("__TOOL_CATEGORIES_JSON__", "[]")
                .replace("__SKILLS_JSON__", "[]")
                .replace("__HOOKS_JSON__", "[]")
                .replace("__RULES_JSON__", "[]")
                .replace("__README_CONTENT_JSON__", json.dumps(safe_readme, ensure_ascii=False))
            )

    with tarfile.open(pub_v_path, "w:gz") as tar:
        # 确保存在 cordis.patch.yml 满足 DSH 插件管理器的安装门禁
        patch_file = src_dir / "cordis.patch.yml"
        if not patch_file.is_file():
            short_n = target_base_name.replace("dsh-plugin-", "")
            patch_content = f"# dsh bundle patch: inserts this plugin into profile layer stack\n- insert:\n    - id: {short_n}\n      name: {target_base_name}\n"
            patch_file.write_text(patch_content, encoding="utf-8")

        for item in src_dir.iterdir():
            if item.name in TAR_EXCLUDES or item.suffix == ".tgz" or item.name == "client.js":
                continue

            if item.name == "package.json":
                try:
                    pkg_dict = json.loads(item.read_text(encoding="utf-8"))
                except Exception as e:
                    raise RuntimeError(f"🚨 [致命阻断] 插件 {src_dir.name}/package.json 非法或存在损坏编码，严禁打包: {e}") from e

                pkg_dict["exports"] = {".": "./index.js", "./client": "./client.js"}
                files_list = pkg_dict.get("files", [])
                for f in ("client.js", "cordis.patch.yml"):
                    if f not in files_list:
                        files_list.append(f)
                pkg_dict["files"] = files_list
                pkg_dict["dsh"] = {
                    "bundle": {
                        "patch": "./cordis.patch.yml"
                    },
                    "client": {
                        "platform": "web",
                        "immediately": True,
                        "inject": [
                            "@deepseek-ai/dsh-client-ui-plugin-manager",
                            "@deepseek-ai/dsh-client-ui-conversation"
                        ]
                    }
                }
                pkg_bytes = json.dumps(pkg_dict, indent=2, ensure_ascii=False).encode("utf-8")
                ti = tarfile.TarInfo(name="package/package.json")
                ti.size = len(pkg_bytes)
                ti.mtime = int(item.stat().st_mtime)
                tar.addfile(ti, io.BytesIO(pkg_bytes))
                continue

            arc = f"package/{item.name}"
            tar.add(item, arcname=arc, filter=filter_tar_info)

        # 动态将通用 client.js 注入至压缩包内
        client_bytes = injected_client_js.encode("utf-8")
        ti_client = tarfile.TarInfo(name="package/client.js")
        ti_client.size = len(client_bytes)
        ti_client.mtime = int(template_path.stat().st_mtime)
        tar.addfile(ti_client, io.BytesIO(client_bytes))

    shutil.copy2(pub_v_path, DIST_DIR / versioned_name)
    size = pub_v_path.stat().st_size
    return size, pub_v_path


def main():
    print("📦 [全系插件 SSOT 打包流水线] 正在扫描并打包全系插件...")
    results = []
    processed_plugins = set()

    template_path = ROOT_DIR / "packages" / "templates" / "universal_dsh_client.js"

    # 1. 优先扫描 packages/plugins/ 统一母港 (单一母港，双向自动分发打包)
    homeland_dir = ROOT_DIR / "packages" / "plugins"
    if homeland_dir.is_dir():
        for p_dir in homeland_dir.iterdir():
            if not p_dir.is_dir():
                continue
            pj = p_dir / "plugin.json"
            if not pj.is_file():
                continue
            try:
                data = json.loads(pj.read_text(encoding="utf-8"))
                base_name = data.get("name", p_dir.name)
                version = data.get("version", "1.0.0")
                readme_path = p_dir / "README.md"

                # 1.1 打包反重力原生插件包 (直接打包母本)
                size_ag, _ = pack_directory(p_dir, base_name, version, is_npm=False)
                results.append((base_name, version, size_ag, "Antigravity"))

                # 1.2 打包 DSH 独立桥插件包 (自动注入通用 client.js 解释器)
                dsh_pkg_name = f"dsh-plugin-{base_name}" if not base_name.startswith("dsh-plugin-") else base_name
                size_dsh, _ = pack_dsh_with_injected_client(
                    p_dir, dsh_pkg_name, version, template_path, readme_path
                )
                results.append((dsh_pkg_name, version, size_dsh, "DSH (Auto-Injected)"))
                processed_plugins.add(base_name)
                processed_plugins.add(dsh_pkg_name)
            except Exception as e:
                print(f"  ⚠️ 打包统一母港插件 {p_dir.name} 失败: {e}")

    # 2. 扫描尚未迁移的 DeepSeek Harness 独立插件 (兼容老目录)
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
                    if name in processed_plugins:
                        continue
                    version = data.get("version", "1.0.0")

                    # 解析对应内核目录并自动装配 DSH 表现层适配器
                    kernel_name = DSH_TO_KERNEL_MAP.get(name, name.replace("dsh-plugin-", ""))
                    kernel_dir = ROOT_DIR / "integrations" / "antigravity" / kernel_name
                    if not kernel_dir.is_dir():
                        kernel_dir = ROOT_DIR / "packages" / "plugins" / kernel_name

                    readme_path = p_dir / "README.md"
                    size, _ = pack_dsh_with_injected_client(
                        p_dir, name, version, template_path, readme_path,
                        kernel_dir=kernel_dir if kernel_dir.is_dir() else None
                    )
                    results.append((name, version, size, "DSH (Auto-Injected)"))
                    processed_plugins.add(name)
                except Exception as e:
                    print(f"  ⚠️ 打包 DSH 插件 {p_dir.name} 失败: {e}")

    # 3. 扫描尚未迁移的 Antigravity 插件 (兼容老目录)
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
                    if name in processed_plugins:
                        continue
                    version = data.get("version", "1.0.0")
                    size, _ = pack_directory(p_dir, name, version, is_npm=False)
                    results.append((name, version, size, "Antigravity (Legacy)"))
                except Exception as e:
                    print(f"  ⚠️ 打包反重力插件 {p_dir.name} 失败: {e}")

    print("\n📊 打包产物清单 (已落盘至 public/ 和 dist/):")
    print(f"  {'插件生态':<24} {'包名':<32} {'版本':<10} {'体积 (Bytes)':<12}")
    print("  " + "-" * 82)
    for name, ver, size, eco in results:
        print(f"  {eco:<24} {name:<32} v{ver:<9} {size:<12}")

    if results:
        keep_exact = {f"{name}-{ver}.tgz" for name, ver, _, _ in results}
        managed_bases = {name for name, _, _, _ in results}
        pruned_public = prune_stale_tarballs(PUBLIC_DIR, keep_exact, managed_bases)
        pruned_dist = prune_stale_tarballs(DIST_DIR, keep_exact, managed_bases)
        if pruned_public or pruned_dist:
            print(
                f"\n🧹 已清理历史冗余与退役压缩包: "
                f"public/ -{len(pruned_public)} 份, dist/ -{len(pruned_dist)} 份"
            )

    wsl_svc = Path("/home/skloxo/services/openviking")
    if wsl_svc.is_dir() and wsl_svc != ROOT_DIR:
        print("\n🔄 正在自动同频至生产服务分发目录 (/home/skloxo/services/openviking)...")
        (wsl_svc / "dist").mkdir(parents=True, exist_ok=True)
        (wsl_svc / "public").mkdir(parents=True, exist_ok=True)
        for tgz in DIST_DIR.glob("*.tgz"):
            shutil.copy2(tgz, wsl_svc / "dist" / tgz.name)
        for tgz in PUBLIC_DIR.glob("*.tgz"):
            shutil.copy2(tgz, wsl_svc / "public" / tgz.name)
        if results:
            pruned_svc_public = prune_stale_tarballs(
                wsl_svc / "public", keep_exact, managed_bases
            )
            pruned_svc_dist = prune_stale_tarballs(
                wsl_svc / "dist", keep_exact, managed_bases
            )
            if pruned_svc_public or pruned_svc_dist:
                print(
                    f"  🧹 已清理生产分发目录历史压缩包: "
                    f"public/ -{len(pruned_svc_public)} 份, dist/ -{len(pruned_svc_dist)} 份"
                )
        print("  ✔ 生产服务静态分发目录同频完毕！")

    print("\n✅ 全系插件打包完成，随时可用于生产分发！")


if __name__ == "__main__":
    main()
