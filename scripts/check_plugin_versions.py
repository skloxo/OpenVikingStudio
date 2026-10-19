#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from pathlib import Path

repo_plugins = Path("integrations/antigravity")
installed_plugins = Path.home() / ".gemini" / "config" / "plugins"
cfg_path = Path.home() / ".gemini" / "config" / "config.json"

with open(cfg_path, "r", encoding="utf-8") as f:
    cfg = json.load(f)
cfg_plugins = cfg.get("plugins", {})

print("| 插件名称 | 母本 plugin.json | 母本 setup.py | 已安装 plugin.json | 宿主 config.json | 状态 |")
print("| :--- | :--- | :--- | :--- | :--- | :--- |")

for p_dir in sorted(repo_plugins.iterdir()):
    if not p_dir.is_dir():
        continue
    p_name = p_dir.name
    pj = p_dir / "plugin.json"
    repo_ver = "N/A"
    if pj.exists():
        with open(pj, "r", encoding="utf-8") as f:
            repo_ver = json.load(f).get("version", "N/A")

    setup_py = p_dir / "setup.py"
    setup_ver = "N/A"
    if setup_py.exists():
        for line in setup_py.read_text(encoding="utf-8", errors="ignore").splitlines():
            line_str = line.strip()
            if "VERSION =" in line_str or "PLUGIN_VERSION =" in line_str or "version=" in line_str:
                setup_ver = line_str
                break

    inst_pj = installed_plugins / p_name / "plugin.json"
    inst_ver = "N/A"
    if inst_pj.exists():
        with open(inst_pj, "r", encoding="utf-8") as f:
            inst_ver = json.load(f).get("version", "N/A")

    cfg_ver = "N/A"
    if p_name in cfg_plugins:
        p_info = cfg_plugins[p_name]
        if isinstance(p_info, dict):
            cfg_ver = p_info.get("installedFrom", {}).get("version", p_info.get("version", "N/A"))

    ok = (repo_ver == inst_ver == cfg_ver) and repo_ver != "N/A"
    status = "PASS" if ok else "DRIFT"
    print(f"| {p_name} | {repo_ver} | {setup_ver} | {inst_ver} | {cfg_ver} | {status} |")
