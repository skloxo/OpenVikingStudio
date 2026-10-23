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


class RuleDefinition(BaseModel):
    """插件内置规约法则与约束定义 DTO。"""
    name: str = Field(..., description="规则名称或文件名 (例如: memory-ssot.md)")
    description: Optional[str] = Field(None, description="规则自解释概述")
    content: str = Field("", description="规则 Markdown 正文或约束法则")


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


class IntegrationChannelDefinition(BaseModel):
    """多渠道接入指引渠道定义 DTO。"""
    id: str = Field(..., description="渠道唯一标识 (antigravity | dsh | universal-mcp)")
    name: str = Field(..., description="渠道显示名称 (Google 反重力 | DeepSeek Harness | 通用 MCP 智能体)")
    install_cmd: str = Field("", description="安装或引入命令行模板")
    agent_prompt: str = Field("", description="智能体一键认主提示词模板")
    config_snippet: str = Field("", description="配置代码片段模板 (JSON 或 YAML)")
    docs_markdown: str = Field("", description="渠道专属接入详细说明 Markdown")


class IntegrationDefinition(BaseModel):
    """插件全渠道接入指引装配 DTO。"""
    channels: List[IntegrationChannelDefinition] = Field(default_factory=list, description="支持的智能体接入渠道列表")


class QuadPluginDefinition(BaseModel):
    """四位一体完整插件规格定义 SSOT DTO。"""
    plugin_id: str = Field(..., description="插件唯一全局标识 (例如: openviking-memory, keepass-vault)")
    name: str = Field(..., description="插件显示名称 (例如: OpenViking 记忆体外大脑)")
    version: str = Field("1.0.0", description="语义化版本号 (严格遵循 SemVer X.Y.Z)")
    category: Literal["platform", "user", "custom"] = Field("platform", description="插件类型 (platform=官方内置, user=租户私有)")
    description: str = Field(..., description="插件核心能力与职责自解释概述")
    
    # 📝 原生 Markdown 介绍文档正文 (反重力 IDE 与 VK 插件中心互通共享单一真相源)
    readme_content: Optional[str] = Field(None, description="插件原生 Markdown 说明文档正文")
    author: Optional[str] = Field(None, description="作者或维护组织名称")
    homepage: Optional[str] = Field(None, description="项目主页或仓库地址")
    license: Optional[str] = Field(None, description="开源许可证 (例如: AGPL-3.0)")
    tags: List[str] = Field(default_factory=list, description="分类标签与搜索关键字")
    suggested_prompts: List[str] = Field(default_factory=list, description="建议提示词列表")

    # 🧩 四位一体维度核心对象
    skill: SkillDefinition = Field(..., description="1. 认知层 (Skill 操作手册，兼容主导轨)")
    skills: List[SkillDefinition] = Field(default_factory=list, description="1. 认知层 (Skill 专属认知导轨全量列表)")
    rules: List[RuleDefinition] = Field(default_factory=list, description="内置规约法则与安全红线列表")
    hooks: List[HookDefinition] = Field(default_factory=list, description="2. 拦截层 (Hook 神经反射)")
    tools: List[ToolDefinition] = Field(default_factory=list, description="3. 工具层 (MCP 物理算子列表)")
    gui: GuiSchemaDefinition = Field(default_factory=GuiSchemaDefinition, description="4. 交互层 (GUI 设置与驾驶舱)")
    integration: Optional[IntegrationDefinition] = Field(default=None, description="5. 接入层 (多渠道智能体接入指引元数据)")
    
    # 探针运行态
    health: PluginHealthProbe = Field(default_factory=PluginHealthProbe, description="运行态健康心跳与探针数据")

