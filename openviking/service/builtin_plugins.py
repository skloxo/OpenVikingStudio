# -*- coding: utf-8 -*-
"""内置 Quad 插件元数据与标准定义清单 (Builtin Quad Plugins SSOT)

严格遵循四大标杆标准:
1. Quad Plugin (四位一体: Tools + Hooks + Skill + GUI);
2. 单文件 100~300 行黄金甜点区 (<= 500 行安全红线);
3. 战地核心记忆插件收敛为 34 项战地工具 + 3 项 Hook 物理守卫;
4. 系统运维治理插件 openviking-ops 独立封装 (17 项运维特权工具 + 2 项 Hook 守卫);
5. CPA 算力 (2 项) 与 Fleet 同频 (2 项) 彻底解耦独立。
"""

from typing import List, Dict, Tuple
from openviking.models.plugin import QuadPluginDefinition
from openviking.service.builtin_plugins_core import (
    BATTLEFIELD_34_TOOL_NAMES,
    OPS_17_TOOL_NAMES,
    create_core_and_ops_plugins,
)
from openviking.service.builtin_plugins_eco import create_ecosystem_plugins

__all__ = [
    "BATTLEFIELD_34_TOOL_NAMES",
    "OPS_17_TOOL_NAMES",
    "create_builtin_plugins",
]


def create_builtin_plugins() -> Tuple[List[QuadPluginDefinition], Dict[str, str], Dict[str, str]]:
    """创建并返回所有官方内置 Quad 插件实例、全局别名表及工具反查映射表。"""
    tool_to_plugin_map: Dict[str, str] = {}
    aliases: Dict[str, str] = {}

    core_plugins = create_core_and_ops_plugins(tool_to_plugin_map, aliases)
    eco_plugins = create_ecosystem_plugins(tool_to_plugin_map, aliases)

    all_plugins = core_plugins + eco_plugins
    return all_plugins, aliases, tool_to_plugin_map
