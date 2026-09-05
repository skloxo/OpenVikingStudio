# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
tools: OpenViking MCP 业务工具分域实现包
按照语义内聚原则划分为：
- memory: 记忆存储、两阶段重排检索与智能聚合读取
- code: 代码语义搜索、大纲提纯、符号展开与全局正则行检索
- filesystem: VikingFS 目录树、移动、差异比较与重命名
- skills: 知识中枢技能审计、规范修复、自动收录与演进 Lesson 存盘
- sessions: 多智能体会话、图谱关联拓扑构建
- system: 系统健康、环境自检、服务管控与灾备快照
- observability: 运行态遥测指标与令牌统计
- shims: 卫星模式向后兼容优雅垫片
"""

from .memory import register_memory_tools
from .code import register_code_tools
from .filesystem import register_filesystem_tools
from .skills import register_skills_tools
from .sessions import register_sessions_tools
from .system import register_system_tools
from .observability import register_observability_tools
from .shims import register_shims

__all__ = [
    "register_memory_tools",
    "register_code_tools",
    "register_filesystem_tools",
    "register_skills_tools",
    "register_sessions_tools",
    "register_system_tools",
    "register_observability_tools",
    "register_shims",
]
