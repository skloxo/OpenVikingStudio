#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/bump_plugin.py
全系插件单一真相源 (SSOT) 原子级联版本递增与自举同频工具。
彻底杜绝“改了代码忘记改版本”、“DSH与Antigravity不同频”、“服务端后台与端侧断层”。
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent

PLUGIN_MAPPING = {
    "openviking-memory": {
        "ag_dir": "packages/plugins/openviking-memory",
        "dsh_dir": "integrations/deepseek-harness/dsh-plugin-openviking-memory",
    },
    "openviking-ops": {
        "ag_dir": "integrations/antigravity/openviking-ops",
        "dsh_dir": "integrations/deepseek-harness/dsh-plugin-openviking-ops",
    },
    "fleet-mesh": {
        "ag_dir": "integrations/antigravity/fleet-mesh",
        "dsh_dir": "integrations/deepseek-harness/dsh-plugin-openviking-fleet",
    },
    "keepass-vault": {
        "ag_dir": "packages/plugins/keepass-vault",
        "dsh_dir": "integrations/deepseek-harness/dsh-plugin-keepass-vault",
    },
    "dify": {
        "ag_dir": "integrations/antigravity/dify",
        "dsh_dir": "integrations/deepseek-harness/dsh-plugin-dify",
    },
    "cpa-squad": {
        "ag_dir": "integrations/antigravity/cpa-squad",
        "dsh_dir": "integrations/deepseek-harness/dsh-plugin-cpa",
    },
    "agent-circuit-breaker": {
        "ag_dir": "integrations/antigravity/agent-circuit-breaker",
        "dsh_dir": "",
    },
}


def increment_version(current: str, bump_type: str) -> str:
    parts = current.strip().split(".")
    while len(parts) < 3:
        parts.append("0")
    try:
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return current

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    else:  # patch
        return f"{major}.{minor}.{patch + 1}"


def bump_plugin(plugin_name: str, target_version: str = "", bump_type: str = "patch"):
    pid = plugin_name.strip().lower()
    meta = PLUGIN_MAPPING.get(pid)
    if not meta:
        for k in PLUGIN_MAPPING:
            if pid in k or k in pid:
                meta = PLUGIN_MAPPING[k]
                pid = k
                break
    if not meta:
        print(f"❌ 未知插件: {plugin_name}，支持的插件列表: {list(PLUGIN_MAPPING.keys())}")
        sys.exit(1)

    ag_path = ROOT_DIR / meta["ag_dir"] if meta["ag_dir"] else None
    dsh_path = ROOT_DIR / meta["dsh_dir"] if meta["dsh_dir"] else None

    # 1. 确定新版本号
    current_ver = "1.0.0"
    if ag_path and (ag_path / "plugin.json").exists():
        try:
            current_ver = json.loads((ag_path / "plugin.json").read_text(encoding="utf-8")).get("version", current_ver)
        except Exception:
            pass
    elif dsh_path and (dsh_path / "package.json").exists():
        try:
            current_ver = json.loads((dsh_path / "package.json").read_text(encoding="utf-8")).get("version", current_ver)
        except Exception:
            pass

    if target_version and re.match(r"^\d+\.\d+\.\d+", target_version):
        new_ver = target_version
    else:
        new_ver = increment_version(current_ver, bump_type or "patch")

    print(f"🔄 正在原子递增插件 [{pid}] 版本: v{current_ver} ➔ v{new_ver}")

    # 2. 更新 Antigravity plugin.json
    if ag_path and (ag_path / "plugin.json").exists():
        pjson_file = ag_path / "plugin.json"
        data = json.loads(pjson_file.read_text(encoding="utf-8"))
        data["version"] = new_ver
        disp = data.get("displayName", "")
        # 规范化 displayName: 替换或附加 (vX.Y.Z)
        clean_disp = re.sub(r"\s*\(v\d+\.\d+\.\d+\)", "", disp).strip()
        data["displayName"] = f"{clean_disp} (v{new_ver})"
        desc = data.get("description", "")
        clean_desc = re.sub(r"^\[版本:\s*v\d+\.\d+\.\d+[^\]]*\]\s*", "", desc).strip()
        data["description"] = f"[版本: v{new_ver}] {clean_desc}"
        pjson_file.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  ✔ Antigravity plugin.json 同步完成 (v{new_ver})")

    # 2.1 更新 packages/plugins/{pid}/ 统一母港
    homeland_path = ROOT_DIR / "packages" / "plugins" / pid
    if homeland_path.is_dir():
        if (homeland_path / "plugin.json").exists():
            hp_file = homeland_path / "plugin.json"
            h_data = json.loads(hp_file.read_text(encoding="utf-8"))
            h_data["version"] = new_ver
            hp_file.write_text(json.dumps(h_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"  ✔ Homeland plugin.json 同步完成 (v{new_ver})")
        if (homeland_path / "package.json").exists():
            hpk_file = homeland_path / "package.json"
            hpk_data = json.loads(hpk_file.read_text(encoding="utf-8"))
            hpk_data["version"] = new_ver
            hpk_file.write_text(json.dumps(hpk_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"  ✔ Homeland package.json 同步完成 (v{new_ver})")

    if ag_path and (ag_path / "package.json").exists():
        ag_pkg = ag_path / "package.json"
        ag_data = json.loads(ag_pkg.read_text(encoding="utf-8"))
        ag_data["version"] = new_ver
        ag_pkg.write_text(json.dumps(ag_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  ✔ Antigravity package.json 同步完成 (v{new_ver})")

    # 3. 更新 DSH package.json
    if dsh_path and (dsh_path / "package.json").exists():
        pkg_file = dsh_path / "package.json"
        data = json.loads(pkg_file.read_text(encoding="utf-8"))
        data["version"] = new_ver
        pkg_file.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  ✔ DSH package.json 同步完成 (v{new_ver})")

    # 4. 更新 builtin_plugins_core.py fallback
    core_file = ROOT_DIR / "openviking" / "service" / "builtin_plugins_core.py"
    if core_file.exists():
        content = core_file.read_text(encoding="utf-8")
        if pid == "openviking-memory":
            content = re.sub(
                r'resolve_package_version\("dsh-plugin-openviking-memory",\s*"[^"]+"\)',
                f'resolve_package_version("dsh-plugin-openviking-memory", "{new_ver}")',
                content
            )
        elif pid == "openviking-ops":
            content = re.sub(
                r'resolve_package_version\("dsh-plugin-openviking-ops",\s*"[^"]+"\)',
                f'resolve_package_version("dsh-plugin-openviking-ops", "{new_ver}")',
                content
            )
        core_file.write_text(content, encoding="utf-8")
        print(f"  ✔ 服务端 builtin_plugins_core.py fallback 对齐完成")

    # 5. 重新自举安装至宿主
    if ag_path and (ag_path / "setup.py").exists():
        print(f"  🚀 正在执行端侧 setup.py 自动部署...")
        subprocess.run([sys.executable, str(ag_path / "setup.py"), "--install"], check=False)

    # 6. 重新打包全系分发包
    pack_script = ROOT_DIR / "scripts" / "pack_all_plugins.py"
    if pack_script.exists():
        print(f"  📦 正在执行自动化全系打包流水线...")
        subprocess.run([sys.executable, str(pack_script)], check=False)

    print(f"\n✅ 插件 [{pid}] 已实现四方原子级联同频发版：v{new_ver}！\n")


def main():
    parser = argparse.ArgumentParser(description="OpenViking 插件版本原子级联升级与治理工具")
    parser.add_argument("plugin", help="插件名称 (如 openviking-ops, openviking-memory)")
    parser.add_argument("type", nargs="?", default="patch", choices=["patch", "minor", "major"], help="升级类型 (默认 patch)")
    parser.add_argument("--set", dest="target_version", default="", help="直接指定确切版本号 (如 1.0.5)")
    args = parser.parse_args()

    bump_plugin(args.plugin, target_version=args.target_version, bump_type=args.type)


if __name__ == "__main__":
    main()
