#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenViking & Antigravity 全系 7 大插件一键同步与版本对齐总控流水线 (SSOT 自动化引擎)
对齐四大真相源 (SSOT)：
1. 母本 plugin.json (唯一输入真相源)
2. 母本文档与向导 (README.md 徽章/文案 + setup.py 自动级联更新)
3. 部署端 plugin.json (~/.gemini/config/plugins/<name>)
4. 宿主注册表 config.json (~/.gemini/config/config.json)
5. 分发构建包 (public/ 与 dist/ 下不可变 .tgz)
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# SECTION: Windows UTF-8 Stdio Safeguard
if sys.platform == "win32":
    try:
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGINS_SRC_DIR = REPO_ROOT / "integrations" / "antigravity"
INSTALLED_DIR = Path.home() / ".gemini" / "config" / "plugins"
CFG_FILE = Path.home() / ".gemini" / "config" / "config.json"
PYTHON_EXE = sys.executable

PRODUCTION_PLUGINS = [
    "agent-circuit-breaker",
    "openviking-memory",
    "keepass-vault",
]

EXPERIMENTAL_WIP_PLUGINS = [
    "openviking-ops",
    "fleet-mesh",
    "cpa-squad",
    "dify",
    "network-search",
]


ALL_PLUGINS = PRODUCTION_PLUGINS + EXPERIMENTAL_WIP_PLUGINS


def resolve_plugin_dir(plugin_name: str) -> Path:
    """优先解析 packages/plugins 统一母港，兜底 integrations/antigravity"""
    homeland = REPO_ROOT / "packages" / "plugins" / plugin_name
    if homeland.is_dir():
        return homeland
    return PLUGINS_SRC_DIR / plugin_name


def cascade_version_to_docs(plugin_name: str, version: str):
    """自动将 plugin.json 中的版本号级联至 README.md 与 setup.py，彻底消灭手动核对"""
    clean_ver = version.lstrip("v")
    p_dir = resolve_plugin_dir(plugin_name)
    readme = p_dir / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        # 1. 替换 shields.io 徽章 version-X.Y.Z-cyan.svg
        new_text = re.sub(r"badge/version-[\d\.]+-cyan\.svg", f"badge/version-{clean_ver}-cyan.svg", text)
        # 2. 替换 > **版本**：`vX.Y.Z` 或 > **版本**：vX.Y.Z
        new_text = re.sub(r"(> \*\*版本\*\*：`?v?)[\d\.]+(`?)", rf"\g<1>{clean_ver}\g<2>", new_text)
        # 3. 替换 ## 🌟 核心特性 (vX.Y.Z)
        new_text = re.sub(r"(## 🌟 核心特性 \(v)[\d\.]+(\))", rf"\g<1>{clean_ver}\g<2>", new_text)
        if new_text != text:
            readme.write_text(new_text, encoding="utf-8")
            print(f"  📝 [自动级联] {plugin_name} README.md 文档版本同步 -> v{clean_ver}")

    setup_file = p_dir / "setup.py"
    if setup_file.exists():
        stext = setup_file.read_text(encoding="utf-8")
        new_stext = re.sub(r"\(v[\d\.]+ -", f"(v{clean_ver} -", stext)
        new_stext = re.sub(r"自举安装向导 \(v[\d\.]+\)", f"自举安装向导 (v{clean_ver})", new_stext)
        if new_stext != stext:
            setup_file.write_text(new_stext, encoding="utf-8")
            print(f"  📝 [自动级联] {plugin_name} setup.py 说明版本同步 -> v{clean_ver}")

    client_file = p_dir / "client.js"
    if client_file.exists():
        ctext = client_file.read_text(encoding="utf-8")
        new_ctext = re.sub(r"const CLIENT_VERSION = '[\d\.]+';", f"const CLIENT_VERSION = '{clean_ver}';", ctext)
        new_ctext = re.sub(r"\(client\.js v[\d\.]+\)", f"(client.js v{clean_ver})", new_ctext)
        if new_ctext != ctext:
            client_file.write_text(new_ctext, encoding="utf-8")
            print(f"  📝 [自动级联] {plugin_name} client.js 版本同步 -> v{clean_ver}")


def bump_version(plugin_name: str, new_version: str) -> bool:
    """单一真相源一键 Bump：修改 plugin.json 并联动级联 DSH package.json"""
    clean_ver = new_version.lstrip("v")
    p_dir = resolve_plugin_dir(plugin_name)
    pj = p_dir / "plugin.json"
    if not pj.exists():
        print(f"❌ 插件不存在: {plugin_name}")
        return False
    data = json.loads(pj.read_text(encoding="utf-8"))
    old_ver = data.get("version", "N/A")
    data["version"] = clean_ver
    pj.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"✨ 成功升级 {plugin_name} 版本: v{old_ver} -> v{clean_ver}")

    # 若母港存在 package.json，同步更新
    pkg_file = p_dir / "package.json"
    if pkg_file.exists():
        pkg_data = json.loads(pkg_file.read_text(encoding="utf-8"))
        pkg_data["version"] = clean_ver
        pkg_file.write_text(json.dumps(pkg_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"  ✨ 母港 package.json 版本同步 -> v{clean_ver}")

    # 级联更新文档
    cascade_version_to_docs(plugin_name, clean_ver)

    # 若存在同源 DSH 插件，同步更新 package.json
    dsh_names = [f"dsh-plugin-{plugin_name}", "dsh-plugin-openviking"] if plugin_name == "openviking-memory" else [f"dsh-plugin-{plugin_name}"]
    for dsh_n in dsh_names:
        dsh_pkg = REPO_ROOT / "integrations" / "deepseek-harness" / dsh_n / "package.json"
        if dsh_pkg.exists():
            pkg_data = json.loads(dsh_pkg.read_text(encoding="utf-8"))
            pkg_data["version"] = clean_ver
            dsh_pkg.write_text(json.dumps(pkg_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"  ✨ [DSH 联动] 同步升级 DSH 插件 {dsh_n} 版本 -> v{clean_ver}")
    return True


def sync_plugin(plugin_name: str) -> bool:
    src_dir = resolve_plugin_dir(plugin_name)
    setup_file = src_dir / "setup.py"
    pj = src_dir / "plugin.json"
    if not setup_file.exists():
        print(f"❌ {plugin_name}: 缺少 setup.py 安装向导！")
        return False

    version = "1.0.0"
    if pj.exists():
        try:
            version = json.loads(pj.read_text(encoding="utf-8")).get("version", "1.0.0")
        except Exception:
            pass

    # 1. 自动级联更新文档与注释
    cascade_version_to_docs(plugin_name, version)

    print(f"\n🔄 正在自举安装/更新: {plugin_name} (v{version})...")
    try:
        if plugin_name == "agent-circuit-breaker":
            cmd = [PYTHON_EXE, str(setup_file), "install"]
        else:
            cmd = [PYTHON_EXE, str(setup_file), "--install"]
        
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        res = subprocess.run(cmd, cwd=str(src_dir), capture_output=True, encoding="utf-8", errors="replace", env=env, timeout=15)
        if res.returncode == 0:
            print(f"  ✔ {plugin_name} 自举部署成功 (Exit 0)")
            return True
        else:
            print(f"  ❌ {plugin_name} 部署失败 (Exit {res.returncode}):\n{res.stderr or res.stdout}")
            return False
    except Exception as e:
        print(f"  ❌ {plugin_name} 执行异常: {e}")
        return False


def verify_alignment(include_experimental: bool = False) -> bool:
    print("\n" + "=" * 80)
    print("📊 [已发布生产插件单一真相源 (SSOT) 对齐审计大盘]")
    print("=" * 80)
    print(f"{'插件名称':<25} | {'母本版本':<10} | {'安装目录版本':<12} | {'宿主注册版本':<12} | 状态")
    print("-" * 80)

    if not CFG_FILE.exists():
        print("❌ 宿主 config.json 不存在！")
        return False

    with open(CFG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg_plugins = cfg.get("plugins", {})

    all_pass = True
    check_list = ALL_PLUGINS if include_experimental else PRODUCTION_PLUGINS

    for p_name in check_list:
        is_wip = p_name in EXPERIMENTAL_WIP_PLUGINS
        tag = " (WIP)" if is_wip else ""
        src_pj = resolve_plugin_dir(p_name) / "plugin.json"
        src_ver = "N/A"
        if src_pj.exists():
            with open(src_pj, "r", encoding="utf-8") as f:
                src_ver = json.load(f).get("version", "N/A")

        inst_pj = INSTALLED_DIR / p_name / "plugin.json"
        inst_ver = "N/A"
        if inst_pj.exists():
            with open(inst_pj, "r", encoding="utf-8") as f:
                inst_ver = json.load(f).get("version", "N/A")

        cfg_ver = "N/A"
        if p_name in cfg_plugins:
            p_info = cfg_plugins[p_name]
            if isinstance(p_info, dict):
                cfg_ver = p_info.get("installedFrom", {}).get("version", p_info.get("version", "N/A"))

        matched = (src_ver == inst_ver == cfg_ver) and src_ver != "N/A"
        if not matched:
            all_pass = False

        status = "✅ PASS" if matched else "❌ DRIFT"
        print(f"{(p_name + tag):<25} | {src_ver:<10} | {inst_ver:<12} | {cfg_ver:<12} | {status}")

    print("=" * 80)
    if all_pass:
        print(f"🎉 核心生产插件单一真相源 (SSOT) 100% 对齐，0 漂移，纯净可信！")
    else:
        print("⚠️ 存在版本漂移，请检查上述标记为 DRIFT 的插件！")
    return all_pass


def main():
    parser = argparse.ArgumentParser(description="OpenViking 全系插件单一真相源 (SSOT) 自动级联同步流水线")
    parser.add_argument("--bump", nargs=2, metavar=("PLUGIN", "VERSION"), help="一键提升指定插件版本 (如: --bump openviking-memory 2.0.18)")
    parser.add_argument("--plugin", type=str, help="仅同步指定单个插件")
    parser.add_argument("--include-experimental", action="store_true", help="显式包含未开发完成的 WIP/试验性插件 (默认仅部署正式生产插件)")
    parser.add_argument("--verify-only", action="store_true", help="仅执行四方对齐审计大盘校验")
    parser.add_argument("--skip-pack", action="store_true", help="跳过 .tgz 分发包构建")
    args = parser.parse_args()

    if args.verify_only:
        ok = verify_alignment(include_experimental=args.include_experimental)
        sys.exit(0 if ok else 1)

    if args.bump:
        p_name, n_ver = args.bump
        if not bump_version(p_name, n_ver):
            sys.exit(1)

    if args.plugin:
        target_plugins = [args.plugin]
    elif args.include_experimental:
        print("⚠️ 警告：正在包含未完成开发的 WIP 试验插件！")
        target_plugins = PRODUCTION_PLUGINS + EXPERIMENTAL_WIP_PLUGINS
    else:
        target_plugins = PRODUCTION_PLUGINS

    print(f"🚀 启动插件自动级联同步流水线 (共 {len(target_plugins)} 个正式插件: {', '.join(target_plugins)})...")

    success_count = 0
    for p in target_plugins:
        if sync_plugin(p):
            success_count += 1

    print(f"\n📦 同步阶段完成: {success_count}/{len(target_plugins)} 个插件已同步")

    if not args.skip_pack:
        pack_script = REPO_ROOT / "scripts" / "pack_all_plugins.py"
        if pack_script.exists():
            print("\n📦 [打包流水线] 正在自动触发 pack_all_plugins.py 生成不可变分发包...")
            subprocess.run([PYTHON_EXE, str(pack_script)], check=True)

    ok = verify_alignment(include_experimental=args.include_experimental)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

