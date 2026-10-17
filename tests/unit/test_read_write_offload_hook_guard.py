"""
tests/unit/test_read_write_offload_hook_guard.py - 腾讯 DECO 级读写两侧 Offload 护栏与 Hook 切面长文本防偷懒/防越权体系单元测试
"""

import pytest
from typing import Any, Dict, List

from openviking.core.hook_aspects import (
    AspectContext,
    AspectDecisionType,
    HookAspectRegistry,
)
from openviking.core.read_write_offload import (
    AntiLazyCodeGuard,
    ReadOffloadManager,
    FileRefHandle,
)
from openviking.core.hitl_gate import (
    DangerousActionPolicy,
    HITLGate,
)
from openviking.core.agent_loop import (
    AgentMessage,
    OnionGuardConfig,
    ToolCallResult,
    TwoTierAgentLoop,
)


def test_anti_lazy_code_guard_blocks_omission_patterns():
    """验证防偷懒省略护栏对各种语言省略占位符的物理拦截"""
    guard = AntiLazyCodeGuard()
    ctx = AspectContext()

    lazy_snippets = [
        "def main():\n    /* ... 省略中间 500 行实现 ... */\n    return True",
        "class Engine:\n    # ... rest of code unchanged ...\n    pass",
        "function run() {\n    // ... existing code ...\n    return 42;\n}",
        "<div>\n    <!-- ... 省略表单项 ... -->\n</div>",
        "def test_foo():\n    ... rest of code\n",
    ]

    for snippet in lazy_snippets:
        args = {"TargetFile": "/app/service.py", "CodeContent": snippet}
        decision = guard.before_tool_call("write_to_file", args, ctx)
        assert decision.decision == AspectDecisionType.BLOCK, f"未能拦截偷懒代码: {snippet}"
        assert "偷懒代码省略占位符" in decision.block_reason
        assert "物理阻断: 防偷懒省略护栏" in decision.override_output

    # 验证在 ReplacementChunks 嵌套结构中也能精准拦截
    chunk_args = {
        "TargetFile": "/app/main.py",
        "ReplacementChunks": [
            {"ReplacementContent": "# ... rest of code unchanged ...\nreturn 0"}
        ],
    }
    decision = guard.before_tool_call("multi_replace_file_content", chunk_args, ctx)
    assert decision.decision == AspectDecisionType.BLOCK


def test_anti_lazy_code_guard_allows_clean_code():
    """验证完整合规代码不会被误杀，顺利放行"""
    guard = AntiLazyCodeGuard()
    ctx = AspectContext()

    clean_code = """
def compute_metrics(values: list[float]) -> dict[str, float]:
    if not values:
        return {"avg": 0.0, "max": 0.0}
    return {
        "avg": sum(values) / len(values),
        "max": max(values),
    }
"""
    decision = guard.before_tool_call(
        "write_to_file",
        {"TargetFile": "/app/metrics.py", "CodeContent": clean_code},
        ctx,
    )
    assert decision.decision == AspectDecisionType.ALLOW


def test_read_offload_manager_under_threshold():
    """验证阈值以内的正常文本不会被 Offload，原样返回"""
    manager = ReadOffloadManager(max_lines=300, max_bytes=12_000)
    ctx = AspectContext()

    short_content = "line 1\nline 2\nline 3"
    result = manager.after_tool_call(
        "view_file",
        {"AbsolutePath": "/app/short.py"},
        short_content,
        ctx,
    )
    assert result == short_content


def test_read_offload_manager_exceeds_threshold():
    """验证超过 300 行超长文件被自动 Offload，下发 FileRefHandle 句柄并支持精确切片"""
    manager = ReadOffloadManager(max_lines=300, max_bytes=12_000)
    ctx = AspectContext()

    # 构造 600 行超长文件
    long_content = "\n".join([f"line_{i:04d}: data payload row {i}" for i in range(1, 601)])
    result = manager.after_tool_call(
        "view_file",
        {"AbsolutePath": "/var/log/app.log"},
        long_content,
        ctx,
    )

    assert isinstance(result, str)
    assert "FileRefHandle" in result
    assert "Total Lines: 600" in result
    assert "[DECO 读护栏提示]" in result
    assert "Head Preview: Lines 1~20" in result

    # 从输出中提取 ref_id 并测试切片读取
    import re
    m = re.search(r"FileRefHandle \((ref_[a-f0-9]+)\)", result)
    assert m is not None, "未找到生成的 ref_id"
    ref_id = m.group(1)

    sliced = manager.slice_cached_content(ref_id, start_line=10, end_line=12)
    assert sliced is not None
    assert "line_0010: data payload row 10" in sliced
    assert "line_0012: data payload row 12" in sliced


def test_hitl_gate_blocks_dangerous_operations():
    """验证高危破坏性工具在未获授权时被物理拦截，携带 Token 后放行"""
    gate = HITLGate()
    ctx = AspectContext(phase="execution")

    # 1. 未授权调用高危工具
    decision = gate.before_tool_call("rm_rf", {"path": "/var/data"}, ctx)
    assert decision.decision == AspectDecisionType.BLOCK
    assert "高危受限工具" in decision.block_reason
    assert "HITL 权限阻断" in decision.override_output

    # 2. 未授权调用包含高危指令的 CLI
    cmd_args = {"CommandLine": "rm -rf / --no-preserve-root"}
    decision = gate.before_tool_call("run_command", cmd_args, ctx)
    assert decision.decision == AspectDecisionType.BLOCK
    assert "高危破坏性指令模式" in decision.block_reason

    # 3. 授权 Token 注入后放行
    gate.grant_approval_token("AUTH_TOKEN_VIP_2026")
    authorized_ctx = AspectContext(auth_tokens=["AUTH_TOKEN_VIP_2026"])
    decision = gate.before_tool_call("rm_rf", {"path": "/tmp/test"}, authorized_ctx)
    assert decision.decision == AspectDecisionType.ALLOW

    # 4. 阶段门禁：planning 阶段即使带 Token 也严禁破坏性操作
    planning_ctx = AspectContext(phase="planning", auth_tokens=["AUTH_TOKEN_VIP_2026"])
    decision = gate.before_tool_call("rm_rf", {"path": "/tmp/test"}, planning_ctx)
    assert decision.decision == AspectDecisionType.BLOCK
    assert "当前处于 'planning' 阶段" in decision.block_reason


def test_agent_loop_hook_aspect_pipeline_integration():
    """验证 TwoTierAgentLoop 与 HookAspectRegistry 全链路协同工作"""
    registry = HookAspectRegistry([
        AntiLazyCodeGuard(),
        HITLGate(),
    ])

    executed_tools: list[str] = []

    def mock_invoker(messages: List[AgentMessage]) -> AgentMessage:
        last = messages[-1]
        if last.role == "user":
            # 模拟模型尝试调用写工具并输出偷懒代码
            return AgentMessage(
                role="assistant",
                content="I will write the file.",
                tool_calls=[{
                    "name": "write_to_file",
                    "id": "call_1",
                    "args": {"CodeContent": "def test():\n    /* 省略若干行 */\n    pass"},
                }],
            )
        else:
            return AgentMessage(role="assistant", content="Finished after tool result.")

    def mock_dispatcher(tool_name: str, args: Dict[str, Any]) -> ToolCallResult:
        executed_tools.append(tool_name)
        return ToolCallResult(call_id="call_1", tool_name=tool_name, output="File written.")

    loop = TwoTierAgentLoop(
        model_invoker=mock_invoker,
        tool_dispatcher=mock_dispatcher,
        hook_registry=registry,
        config=OnionGuardConfig(max_inner_turns=3),
    )

    turn_result = loop.run_turn("Please update my code.")
    # 物理断言：dispatcher 绝不能被执行！
    assert len(executed_tools) == 0, "偷懒代码本应被拦截，但 dispatcher 却被执行了！"
    # 验证 tool 消息记录了阻断回显
    tool_msgs = [m for m in turn_result.history if m.role == "tool"]
    assert len(tool_msgs) == 1
    assert "物理阻断: 防偷懒省略护栏" in tool_msgs[0].content
