#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
OpenVikingStudio/scripts/sync_to_wsl.py - 范式 A 极速源码同步与无感热生效引擎

第一性原理：
1. 物理战场解耦：Windows 宿主负责编辑与 Git 留痕，WSL2 原生 Linux 目录负责编译与运行时执行。
2. 彻底消灭 9P 瓶颈：严禁跨 /mnt/c/... 执行高频 IO 与 vite build，必须增量同步至 Linux ext4 原生目录。
3. 秒级高频热生效：仅增量同步活跃源码树，排除 node_modules/.git/dist 等重资产目录，同步耗时 ≤ 1s。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DEFAULT_WSL_SERVICE_DIR = os.environ.get(
    "OPENVIKING_SERVICE_DIR", "/home/skloxo/services/openviking"
)
HEALTH_URL = "http://127.0.0.1:1933/health"

# 范式 A 增量同步排除规则 (保护 WSL 原生 node_modules、.venv 与运行态缓存)
SYNC_EXCLUDES = [
    "node_modules",
    ".git",
    ".venv",
    "dist",
    "assets",
    "__pycache__",
    ".pytest_cache",
    ".tanstack",
    "evals",
    "benchmark",
    "*.db",
    "*.log",
    "scratch",
    "*.egg-info",
    ".coverage",
]


def is_running_on_windows() -> bool:
    """判断当前脚本是否运行在 Windows 宿主 Python 环境"""
    return sys.platform == "win32" or os.name == "nt"


def is_9p_mount(path: str) -> bool:
    """判断路径是否位于 WSL2 的 9P 挂载虚拟网络文件系统 (/mnt/c/...)"""
    abs_p = os.path.abspath(path).replace("\\", "/")
    return abs_p.startswith("/mnt/")


def to_wsl_path(win_path: str) -> str:
    """将 Windows 路径转为 WSL2 Linux 绝对路径 (如 C:\\a\\b -> /mnt/c/a/b)"""
    p = str(win_path).replace("\\", "/")
    if len(p) >= 2 and p[1] == ":" and p[0].isalpha():
        drive = p[0].lower()
        rest = p[2:].lstrip("/")
        return f"/mnt/{drive}/{rest}"
    if p.startswith("/"):
        return p
    abs_p = os.path.abspath(win_path).replace("\\", "/")
    if len(abs_p) >= 2 and abs_p[1] == ":" and abs_p[0].isalpha():
        drive = abs_p[0].lower()
        rest = abs_p[2:].lstrip("/")
        return f"/mnt/{drive}/{rest}"
    return abs_p


def get_repo_root() -> str:
    """获取当前 OpenVikingStudio 代码库根目录"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build_rsync_command(src: str, dst: str, delete: bool = False) -> list[str]:
    """构造增量 rsync 命令"""
    src_dir = src.rstrip("/\\") + "/"
    dst_dir = dst.rstrip("/\\") + "/"
    cmd = ["rsync", "-av"]
    if delete:
        cmd.append("--delete")
    for exc in SYNC_EXCLUDES:
        cmd.append(f"--exclude={exc}")
    cmd.extend([src_dir, dst_dir])
    return cmd


def sync_source(src_dir: str, dst_dir: str, delete: bool = False, verbose: bool = True) -> bool:
    """执行从宿主工作区向 WSL 原生目录的增量同步"""
    if verbose:
        print(f"⚡ [范式 A 同步] 正在增量同步源码: {src_dir} -> {dst_dir} ...")
    t0 = time.time()
    cmd = build_rsync_command(src_dir, dst_dir, delete=delete)
    res = subprocess.run(cmd, capture_output=not verbose, text=True)
    if res.returncode != 0:
        err = res.stderr if res.stderr else "未知错误"
        print(f"❌ [范式 A 同步失败] 退出码 {res.returncode}: {err}")
        return False
    elapsed = time.time() - t0
    if verbose:
        print(f"✅ [范式 A 同步完成] 耗时 {elapsed:.2f}s (秒级增量到达)")
    return True


def sync_dist_back(native_dir: str, host_dir: str, verbose: bool = True) -> bool:
    """将原生构建的 dist/ 产物增量回传至宿主工作区，保障 Git 留痕与版本追踪"""
    native_dist = os.path.join(native_dir, "dist").rstrip("/\\") + "/"
    host_dist = os.path.join(host_dir, "dist").rstrip("/\\") + "/"
    if not os.path.isdir(native_dist):
        print(f"❌ [产物回传失败] 原生 dist 目录不存在: {native_dist}")
        return False
    if verbose:
        print(f"📦 [产物回传] 正在将 dist/ 增量回传: {native_dist} -> {host_dist} ...")
    t0 = time.time()
    cmd = ["rsync", "-a", "--delete", native_dist, host_dist]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"❌ [产物回传失败] 退出码 {res.returncode}: {res.stderr}")
        return False
    elapsed = time.time() - t0
    if verbose:
        print(f"✅ [产物回传成功] 耗时 {elapsed:.2f}s")
    return True


def run_native_build(native_dir: str) -> bool:
    """在 WSL2 原生 Linux 目录下执行 vite build 生产编译 (15~20秒级)"""
    print(f"🔨 [原生极速编译] 正在进入 WSL2 原生目录执行 npm run build: {native_dir} ...")
    t0 = time.time()
    res = subprocess.run(["npm", "run", "build"], cwd=native_dir)
    elapsed = time.time() - t0
    if res.returncode != 0:
        print(f"❌ [原生编译失败] 退出码: {res.returncode}")
        return False
    print(f"✅ [原生编译成功] 耗时: {elapsed:.2f}s (极速构建达成)")
    return True


def run_native_test(native_dir: str, test_target: str = "") -> bool:
    """在 WSL2 原生 Linux 目录下执行 pytest 单测验证"""
    target = test_target if test_target else "tests/unit/test_seam_decision_gate_b5.py"
    print(f"🧪 [原生单测验证] 正在执行 python3 -m pytest {target} ...")
    cmd = ["python3", "-m", "pytest", "-o", "addopts=", target, "-q"]
    t0 = time.time()
    res = subprocess.run(cmd, cwd=native_dir)
    elapsed = time.time() - t0
    if res.returncode != 0:
        print(f"❌ [单测验证失败] 退出码: {res.returncode}")
        return False
    print(f"✅ [单测验证通过] 耗时: {elapsed:.2f}s")
    return True


def probe_health(retries: int = 30) -> tuple[bool, str]:
    """探针验真 /health 返回版本与健康状态"""
    print(f"🩺 [服务探针] 正在校验 {HEALTH_URL} ...")
    for i in range(retries):
        try:
            req = urllib.request.Request(HEALTH_URL, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    raw = resp.read().decode("utf-8").strip()
                    print(f"✅ [服务探针通过] HTTP 200 -> {raw}")
                    return True, raw
        except Exception:
            pass
        time.sleep(0.5)
    print("❌ [服务探针超时] 无法连接到 OpenViking 服务")
    return False, ""


def restart_native_service() -> bool:
    """重启 WSL2 原生 openviking.service 并探针验活"""
    print("🔄 [服务重启] 正在重启 systemctl --user restart openviking ...")
    res = subprocess.run(["systemctl", "--user", "restart", "openviking"])
    if res.returncode != 0:
        print(f"❌ [服务重启失败] 退出码: {res.returncode}")
        return False
    time.sleep(1.0)
    ok, _ = probe_health()
    return ok


def delegate_to_wsl(args: list[str]) -> int:
    """在 Windows 宿主环境下，无缝委托当前脚本至 WSL2 执行"""
    repo_root = get_repo_root()
    wsl_script = to_wsl_path(os.path.abspath(__file__))
    wsl_cmd = ["wsl", "-e", "python3", wsl_script] + args
    print(f"🔀 [宿主委托] 正在无缝委托 WSL2 原生环境执行: {' '.join(wsl_cmd)}")
    res = subprocess.run(wsl_cmd)
    return res.returncode


def main() -> None:
    if is_running_on_windows():
        sys.exit(delegate_to_wsl(sys.argv[1:]))

    parser = argparse.ArgumentParser(
        description="OpenViking 范式 A 极速增量同步与 WSL 原生构建引擎"
    )
    parser.add_argument(
        "--target-dir",
        default=DEFAULT_WSL_SERVICE_DIR,
        help=f"WSL2 原生运行目录 (默认: {DEFAULT_WSL_SERVICE_DIR})",
    )
    parser.add_argument(
        "-b", "--build",
        action="store_true",
        help="同步后在 WSL 原生目录触发 npm run build 并将 dist/ 增量回传",
    )
    parser.add_argument(
        "-r", "--restart",
        action="store_true",
        help="同步后重启 WSL2 原生 openviking.service 并验活",
    )
    parser.add_argument(
        "--hot",
        action="store_true",
        help="前端零停机热生效 (编译前端并就地生效，不重启后端服务，0个502)",
    )
    parser.add_argument(
        "-t", "--test",
        nargs="?",
        const="tests/unit/test_seam_decision_gate_b5.py",
        help="在 WSL 原生目录执行指定 pytest 测试用例",
    )
    parser.add_argument(
        "-s", "--status",
        action="store_true",
        help="仅检查当前运行时服务健康状态与探针响应",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="rsync 带 --delete 参数 (慎用，仅在深度同步时启用)",
    )

    args = parser.parse_args()

    if args.status:
        ok, payload = probe_health(retries=5)
        sys.exit(0 if ok else 1)

    repo_root = get_repo_root()
    target_dir = os.path.abspath(args.target_dir)

    print("=" * 60)
    print("🚀 [OpenViking 范式 A 极速同步管线]")
    print(f"• 宿主源码根目录: {repo_root} (9P={is_9p_mount(repo_root)})")
    print(f"• WSL2 原生目录: {target_dir}")
    print("=" * 60)

    # 1. 增量同步源码至 WSL 原生服务目录
    if not sync_source(repo_root, target_dir, delete=args.delete):
        sys.exit(1)

    # 2. 原生快速构建
    if args.build or args.hot:
        if not run_native_build(target_dir):
            sys.exit(1)
        # 将 dist/ 回传至宿主工作区
        if is_9p_mount(repo_root):
            sync_dist_back(target_dir, repo_root)

    # 3. 原生单测验证
    if args.test:
        if not run_native_test(target_dir, args.test):
            sys.exit(1)

    # 4. 服务热生效 / 重启
    if args.hot:
        print("⚡ [前端零停机热部署] 动静解耦完成：新前端产物直接在服务目录就地生效！")
    elif args.restart:
        if not restart_native_service():
            sys.exit(1)

    print("\n🎉 [范式 A 执行完毕] 一切就绪！")


if __name__ == "__main__":
    main()
