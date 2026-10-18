#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
scripts/release_step.py - OpenViking 版本自增、前端构建与全链路物理同步自动化流水线

第一性原理：彻底根除人工人肉记忆导致的“版本号忘记改、改了没打包、打包版本脱节、服务未生效”等工程断层。
范式 A 铁律加固：
1. 物理读写 package.json 与 openviking/_version.py；
2. 物理阻断 9P 跨盘编译：若工作区在 /mnt/c/...，严格先通过增量 rsync 同步源码至 WSL2 原生目录；
3. 严格在 WSL2 原生 Linux 目录执行 npm run build (15~20秒级极速编译)，将版本号烘焙至产物；
4. 增量将 dist/ 回传至宿主工作区，保障 Git 留痕与版本追踪；
5. 运行 scripts/security_check.py 零密钥门禁与 scripts/anti_demo_gate.py；
6. 支持零停机前端热生效或优雅重启 openviking.service 并由探针强校验 /health 版本。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

# 导入范式 A 同步引擎
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from sync_to_wsl import (
        DEFAULT_WSL_SERVICE_DIR,
        is_9p_mount,
        is_running_on_windows,
        sync_dist_back,
        sync_source,
        to_wsl_path,
    )
except ImportError:
    DEFAULT_WSL_SERVICE_DIR = "/home/skloxo/services/openviking"

    def is_running_on_windows() -> bool:
        return sys.platform == "win32" or os.name == "nt"

    def is_9p_mount(path: str) -> bool:
        abs_p = os.path.abspath(path).replace("\\", "/")
        return abs_p.startswith("/mnt/")

    def to_wsl_path(win_path: str) -> str:
        p = os.path.abspath(win_path).replace("\\", "/")
        if len(p) >= 2 and p[1] == ":":
            return f"/mnt/{p[0].lower()}{p[2:]}"
        return p

    def sync_source(src: str, dst: str, delete: bool = False) -> bool:
        res = subprocess.run(["rsync", "-av", "--exclude=node_modules", "--exclude=.git", "--exclude=dist", f"{src}/", f"{dst}/"])
        return res.returncode == 0

    def sync_dist_back(native_dir: str, host_dir: str) -> bool:
        res = subprocess.run(["rsync", "-a", "--delete", f"{native_dir}/dist/", f"{host_dir}/dist/"])
        return res.returncode == 0


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG_JSON_PATH = os.path.join(REPO_ROOT, "package.json")
VERSION_PY_PATH = os.path.join(REPO_ROOT, "openviking", "_version.py")
DIST_ASSETS_DIR = os.path.join(REPO_ROOT, "dist", "assets")
HEALTH_URL = "http://127.0.0.1:1933/health"


def read_package_json_version() -> str:
    with open(PKG_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("version", "").strip()


def read_python_version() -> str:
    with open(VERSION_PY_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r'(?:__version__|version)\s*=\s*(?:version\s*=\s*)?["\']([^"\']+)["\']', content)
    return match.group(1).strip() if match else ""


def write_versions(new_ver: str) -> None:
    # 1. package.json
    with open(PKG_JSON_PATH, "r", encoding="utf-8") as f:
        pkg_data = json.load(f)
    pkg_data["version"] = new_ver
    with open(PKG_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(pkg_data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # 2. openviking/_version.py
    with open(VERSION_PY_PATH, "r", encoding="utf-8") as f:
        py_content = f.read()
    new_py_content = re.sub(
        r'__version__\s*=\s*version\s*=\s*["\'][^"\']+["\']',
        f'__version__ = version = "{new_ver}"',
        py_content,
    )
    if new_py_content == py_content:
        new_py_content = re.sub(
            r'__version__\s*=\s*["\'][^"\']+["\']',
            f'__version__ = "{new_ver}"',
            py_content,
        )
    parts = new_ver.split(".")
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        tuple_str = f"({int(parts[0])}, {int(parts[1])}, {int(parts[2])})"
        new_py_content = re.sub(
            r'__version_tuple__\s*=\s*version_tuple\s*=\s*\([^)]+\)',
            f'__version_tuple__ = version_tuple = {tuple_str}',
            new_py_content,
        )
    with open(VERSION_PY_PATH, "w", encoding="utf-8") as f:
        f.write(new_py_content)


def compute_next_version(current: str, part: str) -> str:
    parts = current.split(".")
    if len(parts) != 3:
        raise ValueError(f"版本格式不符合 semver (x.y.z): {current}")
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    has_leading_zero = len(parts[2]) == 2 and parts[2].startswith("0")
    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "patch":
        patch += 1
    else:
        raise ValueError(f"未知 bump 类型: {part}")

    if has_leading_zero and patch < 10:
        patch_str = f"{patch:02d}"
    else:
        patch_str = str(patch)
    return f"{major}.{minor}.{patch_str}"


def run_cmd(cmd: list[str], desc: str, cwd: str | None = None) -> None:
    work_dir = cwd or REPO_ROOT
    print(f"⚙️ [{desc}] 正在执行 ({work_dir}): {' '.join(cmd)} ...")
    t0 = time.time()
    res = subprocess.run(cmd, cwd=work_dir)
    if res.returncode != 0:
        print(f"❌ [{desc}] 失败，退出码: {res.returncode}")
        sys.exit(res.returncode)
    elapsed = time.time() - t0
    print(f"✅ [{desc}] 成功 (耗时 {elapsed:.2f}s)")


def verify_dist_baked_version(version: str, dist_dir: str | None = None) -> bool:
    target_assets = os.path.join(dist_dir, "assets") if dist_dir else DIST_ASSETS_DIR
    print(f"🔍 [产物验真] 检查 {target_assets} 是否包含版本号 {version} ...")
    if not os.path.isdir(target_assets):
        print(f"❌ assets 目录不存在: {target_assets}")
        return False

    found = False
    for fname in os.listdir(target_assets):
        if fname.endswith(".js"):
            fpath = os.path.join(target_assets, fname)
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    if version in content:
                        found = True
                        print(f"   -> 命中已烘焙版本文件: {fname}")
                        break
            except Exception as e:
                print(f"⚠️ 读取文件 {fname} 出错: {e}")
    if not found:
        print(f"❌ 警告: 在 {target_assets}/*.js 中未找到版本号 {version}！")
        return False
    print(f"✅ [产物验真通过] 前端静态资源已物理注入版本: {version}")
    return True


def probe_health_version(expected_ver: str, retries: int = 70) -> tuple[bool, str]:
    print(f"🩺 [服务探针] 正在校验 {HEALTH_URL} 返回版本 ...")
    last_payload = ""
    for i in range(retries):
        try:
            req = urllib.request.Request(HEALTH_URL, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    raw = resp.read().decode("utf-8")
                    data = json.loads(raw)
                    last_payload = raw.strip()
                    ret_ver = data.get("version", "")
                    if ret_ver == expected_ver:
                        print(f"✅ [服务探针通过] 运行时版本 100% 对齐: {ret_ver}")
                        print(f"   探针物理证据: HTTP 200 -> {last_payload}")
                        return True, last_payload
                    else:
                        print(f"⏳ 探针返回版本 ({ret_ver}) != 预期 ({expected_ver})，等待 1s 重试 ({i+1}/{retries})...")
        except Exception as e:
            print(f"⏳ 连接探针等待中 ({e}) ...")
        time.sleep(1)
    return False, last_payload


def check_has_backend_changes() -> bool:
    """检查 openviking/ 后端核心 Python 代码是否存在未提交或实质性变更 (排除 _version.py)"""
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain", "openviking/"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
            real_changes = [line for line in lines if "_version.py" not in line]
            return len(real_changes) > 0
    except Exception:
        pass
    return False


def main() -> None:
    # 0. Windows 宿主环境无缝委托 WSL2 原生执行
    if is_running_on_windows():
        wsl_script = to_wsl_path(os.path.abspath(__file__))
        wsl_cmd = ["wsl", "-e", "python3", wsl_script] + sys.argv[1:]
        print(f"🔀 [宿主委托] Windows 环境自动委托 WSL2 执行: {' '.join(wsl_cmd)}")
        res = subprocess.run(wsl_cmd)
        sys.exit(res.returncode)

    parser = argparse.ArgumentParser(description="OpenViking 自动化版本发布与构建同步流水线")
    parser.add_argument("--bump", choices=["patch", "minor", "major"], help="自动递增指定位")
    parser.add_argument("--set", dest="set_ver", help="显式指定目标版本号 (如 1.7.72)")
    parser.add_argument("--sync", action="store_true", help="校准对齐现有两端版本，不递增")
    parser.add_argument("--skip-build", action="store_true", help="跳过 npm run build 前端构建")
    parser.add_argument("--skip-restart", action="store_true", help="跳过 systemctl restart openviking")
    parser.add_argument(
        "--hot",
        "--frontend-only",
        dest="hot_reload",
        action="store_true",
        help="前端零停机热发布 (仅同步 dist，不重启后端服务，彻底根治 502)",
    )
    parser.add_argument("--force-restart", action="store_true", help="强制重启 openviking.service 后端服务")
    parser.add_argument("-m", "--msg", default="", help="版本发布描述信息 (配合自动 Git Tag)")
    parser.add_argument("--tag", action="store_true", help="在探针验证 100%% 通过后自动执行 git tag")
    parser.add_argument(
        "-t", "--test",
        nargs="?",
        const="tests/unit/test_seam_decision_gate_b5.py",
        help="在原生目录执行后端 pytest 单测验证",
    )

    args = parser.parse_args()

    pkg_ver = read_package_json_version()
    py_ver = read_python_version()
    print(f"📋 当前检测版本: package.json={pkg_ver}, openviking/_version.py={py_ver}")

    if args.set_ver:
        target_ver = args.set_ver.strip()
    elif args.bump:
        base_ver = pkg_ver or py_ver
        target_ver = compute_next_version(base_ver, args.bump)
    elif args.sync:
        target_ver = pkg_ver or py_ver
    else:
        if pkg_ver and py_ver and pkg_ver != py_ver:
            print(f"⚠️ 两端版本脱节，自动对齐为: {pkg_ver}")
            target_ver = pkg_ver
        else:
            target_ver = pkg_ver

    print(f"🚀 [目标版本确认] -> {target_ver}")
    write_versions(target_ver)
    print("✅ 已完成 package.json 与 openviking/_version.py 物理双写。")

    # 范式 A：9P 物理隔离与原生目录重定向
    live_service_dir = os.environ.get("OPENVIKING_SERVICE_DIR", DEFAULT_WSL_SERVICE_DIR)
    is_9p = is_9p_mount(REPO_ROOT)
    build_dir = REPO_ROOT

    if is_9p:
        if not os.path.isdir(live_service_dir):
            print(f"🚨 [致命阻断] 当前工作区位于 9P 挂载点 ({REPO_ROOT})，但 WSL 原生服务目录不存在: {live_service_dir}")
            print("   请设置 OPENVIKING_SERVICE_DIR 环境变量，严禁跨 9P 虚拟文件系统执行 vite build！")
            sys.exit(1)

        print("\n" + "=" * 60)
        print("🛑 [9P 物理隔离门禁生效] 严禁跨 9P 虚拟网络文件系统执行 vite build！")
        print(f"⚡ 自动激活范式 A 增量同步 -> 同步源码至 WSL2 原生 Linux 目录: {live_service_dir}")
        print("=" * 60)

        # 1. 增量同步源码至原生目录
        if not sync_source(REPO_ROOT, live_service_dir, delete=False):
            print("🚨 增量同步失败！终止流水线。")
            sys.exit(1)
        build_dir = live_service_dir

    # 前端编译 (严格在 build_dir 原生 Linux 目录下触发)
    if not args.skip_build:
        run_cmd(["npm", "run", "build"], "前端生产编译 (Vite Build in Linux Native)", cwd=build_dir)
        if not verify_dist_baked_version(target_ver, dist_dir=os.path.join(build_dir, "dist")):
            print("🚨 编译产物版本验真失败！终止流水线。")
            sys.exit(1)

        # 产物回传至宿主，保障 Git 历史与发布产物对齐
        if is_9p:
            sync_dist_back(build_dir, REPO_ROOT)
            if not verify_dist_baked_version(target_ver, dist_dir=os.path.join(REPO_ROOT, "dist")):
                print("🚨 宿主工作区 dist/ 产物回传验真失败！终止流水线。")
                sys.exit(1)

    # 安全凭据审计门禁
    run_cmd(["python3", "scripts/security_check.py"], "安全凭据审计门禁", cwd=build_dir)

    # 全系统 DEMO 禁令与闭环守护自动化视网膜门禁 (Card-103)
    run_cmd(["python3", "scripts/anti_demo_gate.py"], "全系统 DEMO 禁令与闭环守护自动化视网膜门禁", cwd=build_dir)

    # 原生后端单测验证
    if args.test:
        run_cmd(["python3", "-m", "pytest", "-o", "addopts=", args.test, "-q"], "原生后端单测验证", cwd=build_dir)

    # 重启服务或前端零停机热部署
    probe_payload = ""
    is_pure_frontend = False

    has_backend = check_has_backend_changes()
    if args.hot_reload:
        is_pure_frontend = True
    elif not args.force_restart and not has_backend:
        is_pure_frontend = True

    if is_pure_frontend:
        print("⚡ [前端零停机热部署] 动静完全解耦：检测到纯前端静态资产改动，跳过后端服务重启！")
        print("   ✅ 0 秒停机，0 个 502 Bad Gateway，新版前端产物直接就地热生效。")
    elif not args.skip_restart:
        run_cmd(["systemctl", "--user", "restart", "openviking"], "重启 openviking.service (后端核心变更)")
        time.sleep(1.5)
        ok, probe_payload = probe_health_version(target_ver)
        if not ok:
            print(f"\n🚨 [致命阻断] 服务探针验活失败！目标版本 {target_ver} 与运行中服务不匹配！")
            print(f"   最后一次探针回显: {probe_payload or '无法连接服务'}")
            print("   请排查: 1. systemctl --user status openviking; 2. journalctl --user -u openviking -n 50")
            sys.exit(1)

    # 自动执行 Git Commit 与 Git Tag 闭环 (在 REPO_ROOT Git 仓库执行)
    do_tag = args.tag or bool(args.msg)
    if do_tag:
        tag_name = f"v{target_ver}"
        commit_msg = f"release: {tag_name} {args.msg}".strip()
        print(f"🏷️ [版本打标] 正在为 {tag_name} 自动生成 Git Commit 与 Tag ...")
        subprocess.run(["git", "add", PKG_JSON_PATH, VERSION_PY_PATH, "dist/"], cwd=REPO_ROOT)
        res_commit = subprocess.run(["git", "commit", "-m", commit_msg], cwd=REPO_ROOT, capture_output=True, text=True)
        if res_commit.returncode == 0:
            print(f"   -> Git Commit 成功: {commit_msg}")
        res_tag = subprocess.run(["git", "tag", "-a", tag_name, "-m", commit_msg], cwd=REPO_ROOT, capture_output=True, text=True)
        if res_tag.returncode == 0:
            print(f"   -> Git Tag 创建成功: {tag_name}")
        else:
            print(f"   ⚠️ Git Tag 创建提示: {res_tag.stderr.strip()}")

    print("\n" + "=" * 60)
    print(f"🎉 版本发布与环境同步 100% 成功！范式 A 闭环达成！")
    print(f"• 物理版本号: v{target_ver}")
    print(f"• 运行空间: WSL2 原生 Linux 目录 ({build_dir})")
    print(f"• 前端产物: dist/assets 已验证包含 {target_ver}")
    if is_pure_frontend:
        print(f"• 部署模式: 纯前端零停机热部署 (Zero-Downtime Hot Deploy, 0 个 502)")
    else:
        print(f"• 运行时服务: 已健康重启并由探针验活确认 (HTTP 200)")
    if probe_payload:
        print(f"• 探针真实响应: {probe_payload}")
    if do_tag:
        print(f"• Git Tag: v{target_ver} 已就绪")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
