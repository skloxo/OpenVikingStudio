# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
OpenViking Plugin Quad-Model (四位一体) Strongly-Typed DTOs.
SSOT: docs/architecture/ATOMIC_TASK_CARDS_MATRIX.md -> TASK-PLUG-01

First Principles:
1. "Quad-Model Completeness": A production plugin MUST encapsulate Skill (brain),
   Hook (reflex), MCP Tool (executor), and GUI (view window).
2. "Strict Pydantic Rails": Raw dicts are strictly forbidden. All plugin metadata
   and grant configurations must be strongly typed and validated.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    """MCP 原子算子定义 DTO。"""
    name: str = Field(..., description="工具唯一标识符 (例如: openviking_find)")
    description: str = Field(..., description="工具功能与用途自解释说明")
    category: str = Field("default", description="工具所属逻辑子分组 (例如: core, satellite, query, vault)")
    parameters_schema: Optional[Dict[str, Any]] = Field(default=None, description="入参 JSON Schema 摘要")
    is_dangerous: bool = Field(False, description="是否属于高危破坏性操作 (需前置快照保护)")


class HookDefinition(BaseModel):
    """自主神经与切面拦截 Hook 定义 DTO。"""
    hook_id: str = Field(..., description="Hook 唯一标识 (例如: ov_pre_invocation)")
    name: str = Field(..., description="Hook 人类可读名称")
    trigger_event: str = Field(..., description="触发切面事件 (例如: before_prompt_submit, pre_invoke)")
    description: str = Field(..., description="Hook 行为与静默守护逻辑说明")
    enabled: bool = Field(True, description="默认是否激活生效")


class SkillDefinition(BaseModel):
    """专属操作指南与认知导轨 Skill 定义 DTO。"""
    skill_id: str = Field(..., description="技能唯一标识 (例如: openviking-memory-ops)")
    name: str = Field(..., description="技能人类可读名称")
    description: str = Field(..., description="技能定位与认知目标")
    sop_summary: str = Field(..., description="核心 SOP 操作工序序列摘要")
    rules: List[str] = Field(default_factory=list, description="严禁违背的负向反模式与硬性契约")


class GuiSchemaDefinition(BaseModel):
    """人机交互配置与座舱面板定义 DTO。"""
    settings_fields: Dict[str, Any] = Field(default_factory=dict, description="GUI 表单字段配置 Schema (用于 DSH SettingsForm)")
    dashboard_route: Optional[str] = Field(None, description="Web Studio 对应监控大屏路由 (例如: /plugins, /memories)")


class PluginHealthProbe(BaseModel):
    """插件运行态健康探针结果 DTO。"""
    status: Literal["healthy", "degraded", "down", "unknown"] = Field("healthy", description="健康状态枚举")
    latency_ms: float = Field(0.0, description="探针端到端测量时延 (毫秒)")
    message: str = Field("OK", description="探针诊断信息或异常堆栈摘要")
    checked_at: float = Field(default_factory=time.time, description="最后一次探针采样 Unix 时间戳")


class QuadPluginDefinition(BaseModel):
    """四位一体完整插件规格定义 SSOT DTO。"""
    plugin_id: str = Field(..., description="插件唯一全局标识 (例如: openviking-memory, keepass-vault)")
    name: str = Field(..., description="插件显示名称 (例如: OpenViking 记忆体外大脑)")
    version: str = Field("1.0.0", description="语义化版本号 (严格遵循 SemVer X.Y.Z)")
    category: Literal["platform", "user", "custom"] = Field("platform", description="插件类型 (platform=官方内置, user=租户私有)")
    description: str = Field(..., description="插件核心能力与职责自解释概述")
    
    # 🧩 四位一体维度核心对象
    skill: SkillDefinition = Field(..., description="1. 认知层 (Skill 操作手册)")
    hooks: List[HookDefinition] = Field(default_factory=list, description="2. 拦截层 (Hook 神经反射)")
    tools: List[ToolDefinition] = Field(default_factory=list, description="3. 工具层 (MCP 物理算子列表)")
    gui: GuiSchemaDefinition = Field(default_factory=GuiSchemaDefinition, description="4. 交互层 (GUI 设置与驾驶舱)")
    
    # 探针运行态
    health: PluginHealthProbe = Field(default_factory=PluginHealthProbe, description="运行态健康心跳与探针数据")
