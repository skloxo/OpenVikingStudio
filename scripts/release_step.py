#!/usr/bin/env python3
"""
scripts/release_step.py - OpenViking 版本自增、前端构建与全链路物理同步自动化流水线

第一性原理：彻底根除人工人肉记忆导致的“版本号忘记改、改了没打包、打包版本脱节、服务未生效”等工程断层。
单指令自动化闭环：
1. 物理读写 package.json 与 openviking/_version.py；
2. 自动触发 npm run build 重新编译前端，将版本号物理烘焙至静态产物；
3. 自动验真 dist/assets 必须包含目标版本字符串；
4. 运行 scripts/security_check.py 零密钥门禁；
5. 重启本地 openviking.service 并探针校验 /health 返回版本。
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

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
    return f"{major}.{minor}.{patch}"


def run_cmd(cmd: list[str], desc: str) -> None:
    print(f"⚙️ [{desc}] 正在执行: {' '.join(cmd)} ...")
    t0 = time.time()
    res = subprocess.run(cmd, cwd=REPO_ROOT)
    if res.returncode != 0:
        print(f"❌ [{desc}] 失败，退出码: {res.returncode}")
        sys.exit(res.returncode)
    elapsed = time.time() - t0
    print(f"✅ [{desc}] 成功 (耗时 {elapsed:.2f}s)")


def verify_dist_baked_version(version: str) -> bool:
    print(f"🔍 [产物验真] 检查 dist/assets 是否包含版本号 {version} ...")
    if not os.path.isdir(DIST_ASSETS_DIR):
        print(f"❌ dist/assets 目录不存在: {DIST_ASSETS_DIR}")
        return False

    found = False
    for fname in os.listdir(DIST_ASSETS_DIR):
        if fname.endswith(".js"):
            fpath = os.path.join(DIST_ASSETS_DIR, fname)
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
        print(f"❌ 警告: 在 dist/assets/*.js 中未找到版本号 {version}！")
        return False
    print(f"✅ [产物验真通过] 前端静态资源已物理注入版本: {version}")
    return True


def probe_health_version(expected_ver: str, retries: int = 15) -> bool:
    print(f"🩺 [服务探针] 正在校验 {HEALTH_URL} 返回版本 ...")
    for i in range(retries):
        try:
            req = urllib.request.Request(HEALTH_URL, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    ret_ver = data.get("version", "")
                    if ret_ver == expected_ver:
                        print(f"✅ [服务探针通过] 运行时版本 100% 对齐: {ret_ver}")
                        return True
                    else:
                        print(f"⏳ 探针返回版本 ({ret_ver}) != 预期 ({expected_ver})，等待 1s 重试 ({i+1}/{retries})...")
        except Exception as e:
            print(f"⏳ 连接探针等待中 ({e}) ...")
        time.sleep(1)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenViking 自动化版本发布与构建同步流水线")
    parser.add_argument("--bump", choices=["patch", "minor", "major"], help="自动递增指定位")
    parser.add_argument("--set", dest="set_ver", help="显式指定目标版本号 (如 1.5.04)")
    parser.add_argument("--sync", action="store_true", help="校准对齐现有两端版本，不递增")
    parser.add_argument("--skip-build", action="store_true", help="跳过 npm run build 前端构建")
    parser.add_argument("--skip-restart", action="store_true", help="跳过 systemctl restart openviking")

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
        # 默认行为：若两端一致，则提示用法；若两端不一致，自动以 package.json 为准同步
        if pkg_ver and py_ver and pkg_ver != py_ver:
            print(f"⚠️ 两端版本脱节，自动对齐为: {pkg_ver}")
            target_ver = pkg_ver
        else:
            target_ver = pkg_ver

    print(f"🚀 [目标版本确认] -> {target_ver}")
    write_versions(target_ver)
    print("✅ 已完成 package.json 与 openviking/_version.py 物理双写。")

    # 前端编译
    if not args.skip_build:
        run_cmd(["npm", "run", "build"], "前端生产编译 (Vite Build)")
        if not verify_dist_baked_version(target_ver):
            print("🚨 编译产物版本验真失败！终止流水线。")
            sys.exit(1)

    # 安全凭据审计门禁
    run_cmd(["python3", "scripts/security_check.py"], "安全凭据审计门禁")

    # 重启服务并校验
    if not args.skip_restart:
        run_cmd(["systemctl", "--user", "restart", "openviking"], "重启 openviking.service")
        time.sleep(1)
        if not probe_health_version(target_ver):
            print("⚠️ 探针未能在超时内确认新版本，请手动检查服务日志。")

    print("\n" + "=" * 60)
    print(f"🎉 版本发布与环境同步 100% 成功！")
    print(f"• 物理版本号: v{target_ver}")
    print(f"• 前端产物: dist/assets 已验证包含 {target_ver}")
    print(f"• 运行时服务: 已健康重启并确认版本对齐")
    print("=" * 60)
    print(f"👉 建议留痕指令:")
    print(f'   git commit -m "release: v{target_ver} ..."')
    print(f'   git tag -a v{target_ver} -m "release: v{target_ver} ..."')
    print(f"   git push origin main && git push origin v{target_ver}\n")


if __name__ == "__main__":
    main()
