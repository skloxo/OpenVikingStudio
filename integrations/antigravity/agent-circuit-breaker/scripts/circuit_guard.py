import sys
import os
import json
import tempfile
from pathlib import Path

# --- Thresholds & Elastic Budget ---
MAX_CONSECUTIVE_FAILURES = 3         # 连续非只读报错达到 3 次触发 force_ask
BASE_HEALTHY_STEP_LIMIT = 36        # 健康全绿灯状态下的单轮步数上限 (足够支撑一次完整的 TDD/重构/跑测试/提交全流程)
BASE_UNHEALTHY_STEP_LIMIT = 15      # 异常/有报错状态下的警戒步数上限 (防止死循环盲目打补丁)
LEASE_EXTENSION_STEPS = 15          # 用户点击放行后，自动追加授予的增量步数租约 (彻底消灭连环夺命弹)
MAX_SAME_FILE_TOUCHES = 3            # 同文件连续写操作达到 3 次且伴随报错触发震荡审核

# --- Read-Only Whitelist & Verbs ---
EXACT_READ_ONLY_TOOLS = {
    "view_file", "search_web", "read_url_content", "list_resources",
    "read_resource", "grep_search", "list_dir", "ask_question",
    "schedule", "manage_task"
}

READ_ONLY_PREFIXES = (
    "view", "read", "search", "list", "get", "check", "grep",
    "find", "inspect", "query", "fetch", "status", "show", "dump",
    "tree", "ls", "diff", "outline", "health", "ping", "metrics",
    "observer", "system_status", "fleet_check"
)

# --- Finalization & Record Files (Exempt from step limit when healthy) ---
FINALIZATION_FILE_KEYWORDS = (
    "refactoring_plan.md", "readme.md", "changelog.md",
    "notes.md", "todo.md", "blueprint.md", "agents.md"
)


def emit_json(payload: dict):
    """通过纯二进制缓冲流直写单行 UTF-8 JSON，完全绕过 Windows 控制台转义与 CP936 污染"""
    try:
        data = json.dumps(payload, ensure_ascii=False)
        sys.stdout.buffer.write(data.encode("utf-8") + b"\n")
        sys.stdout.buffer.flush()
    except BaseException:
        sys.stdout.buffer.write(b'{"decision":"allow"}\n')
        sys.stdout.buffer.flush()


def read_stdin_json() -> dict:
    """安全读取单行输入 JSON，严禁使用 read() 避免与父进程管道死锁"""
    try:
        if sys.stdin.isatty():
            return {}
        line = sys.stdin.readline()
        if not line or not line.strip():
            return {}
        return json.loads(line.strip())
    except BaseException:
        return {}


def is_read_only_tool(tool_name: str, args: dict = None) -> bool:
    """判断工具是否属于无破坏性的只读/探针/交互/查询工具 (支持 MCP 代理穿透识别)"""
    tl = (tool_name or "").lower()

    # 1. 若为 MCP 桥接代理调用 (call_mcp_tool)，提取内部真实工具名
    if tl == "call_mcp_tool" and isinstance(args, dict):
        inner_tool = str(args.get("ToolName") or "").lower()
        if inner_tool:
            tl = inner_tool

    # 2. 若为 eager MCP 工具格式 mcp_<server>_<tool>，提取真实工具名
    if tl.startswith("mcp_"):
        parts = tl.split("_", 2)
        if len(parts) >= 3:
            tl = parts[2]

    # 3. 原生全名匹配
    if tl in EXACT_READ_ONLY_TOOLS:
        return True

    # 4. 剥离服务生态前缀以抽取动词
    verb = tl
    for prefix in ("openviking_", "keepass_", "dify_", "gemini_"):
        if verb.startswith(prefix):
            verb = verb[len(prefix):]
            break

    # 5. 只读词族前缀匹配
    return any(verb.startswith(p) for p in READ_ONLY_PREFIXES)


def get_state_dir() -> Path:
    base = Path(tempfile.gettempdir()) / "antigravity_circuit_breaker"
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_state_file(conv_id: str) -> Path:
    safe_id = "".join(c for c in str(conv_id) if c.isalnum() or c in ("-", "_")) or "default"
    return get_state_dir() / f"cb_{safe_id}.json"


def load_state(conv_id: str) -> dict:
    sf = get_state_file(conv_id)
    state = {
        "step_count": 0,
        "consecutive_failures": 0,
        "recent_mutations": [],
        "last_tool_failed": False,
        "current_step_limit": BASE_HEALTHY_STEP_LIMIT,
    }
    if sf.exists():
        try:
            with open(sf, "rb") as f:
                loaded = json.loads(f.read().decode("utf-8", errors="replace"))
                if isinstance(loaded, dict):
                    state.update(loaded)
        except BaseException:
            pass

    # 平滑推导：若旧状态缺失当前动态上限字段，根据健康度自适应赋值
    if not state.get("current_step_limit"):
        is_healthy = (state.get("consecutive_failures", 0) == 0 and not state.get("last_tool_failed", False))
        state["current_step_limit"] = BASE_HEALTHY_STEP_LIMIT if is_healthy else BASE_UNHEALTHY_STEP_LIMIT

    return state


def save_state(conv_id: str, state: dict):
    try:
        sf = get_state_file(conv_id)
        # 原子化落盘：先写临时文件再重命名，杜绝进程读取到半写文件
        tmp_sf = sf.with_suffix(".tmp")
        with open(tmp_sf, "wb") as f:
            f.write(json.dumps(state, ensure_ascii=False, indent=2).encode("utf-8"))
        tmp_sf.replace(sf)
    except BaseException:
        pass


def handle_pre_tool():
    """PreToolUse: 拦截写操作与死循环风险，只读工具毫秒级跳过"""
    data = read_stdin_json()
    if not data:
        emit_json({"decision": "allow"})
        return

    conv_id = data.get("conversationId", "default")
    tool_call = data.get("toolCall", {})
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args", {})

    # 1. 只读探索工具完全豁免，0 延迟放行 (支持 MCP 穿透识别)
    if is_read_only_tool(tool_name, args):
        emit_json({"decision": "allow"})
        return

    state = load_state(conv_id)
    state["step_count"] += 1

    # 2. 连续报错门禁（仅针对非只读的写/执行操作）
    if state["consecutive_failures"] >= MAX_CONSECUTIVE_FAILURES:
        save_state(conv_id, state)
        emit_json({
            "decision": "force_ask",
            "reason": (
                f"[Antigravity 断路器护栏]: 检测到连续 {state['consecutive_failures']} 次写操作或命令报错！"
                f"为防盲目打补丁消耗 Token，已触发主动求证。请确认是否放行此 [{tool_name}] 调用？"
            )
        })
        return

    # 3. 动态弹性步数门禁与良性收尾豁免
    target_file = str(args.get("TargetFile") or args.get("AbsolutePath") or "").lower()
    is_finalization = any(kw in target_file for kw in FINALIZATION_FILE_KEYWORDS)

    # 如果是收尾文件（且无连续报错），免受步数护栏阻拦，平滑完成交付留痕
    if is_finalization and state["consecutive_failures"] == 0:
        save_state(conv_id, state)
        emit_json({"decision": "allow"})
        return

    # 当前生效的动态上限
    current_limit = state.get("current_step_limit", BASE_HEALTHY_STEP_LIMIT)

    # 达到步数上限时触发求证，并自动向后滑动增量租约，消除连环弹窗
    if state["step_count"] >= current_limit:
        # 授权续约：无论用户本次选择“允许一次”，接下来 LEASE_EXTENSION_STEPS 步内都不会再弹窗
        state["current_step_limit"] = state["step_count"] + LEASE_EXTENSION_STEPS
        save_state(conv_id, state)
        emit_json({
            "decision": "force_ask",
            "reason": (
                f"[Antigravity 步数自适应护栏]: 当前轮次已执行 {state['step_count']} 步操作（动态上限 {current_limit}）。"
                f"为防超长无感盲跑，请确认是否继续授权 [{tool_name}]？（批准后将自动追加 {LEASE_EXTENSION_STEPS} 步探索租约）"
            )
        })
        return

    # 4. 同文件震荡检测 (修改同一文件连续 >= 3 次且有失败记录)
    if target_file and tool_name in {"replace_file_content", "write_to_file"}:
        recent = state.get("recent_mutations", [])
        recent.append(target_file)
        if len(recent) > 6:
            recent.pop(0)
        state["recent_mutations"] = recent

        if len(recent) >= MAX_SAME_FILE_TOUCHES and all(f == target_file for f in recent[-MAX_SAME_FILE_TOUCHES:]):
            if state["consecutive_failures"] > 0:
                save_state(conv_id, state)
                fname = Path(target_file).name
                emit_json({
                    "decision": "force_ask",
                    "reason": (
                        f"[代码震荡预警]: 正在第 {len(recent)} 次频繁修改同一文件 [{fname}] 且伴随报错。"
                        f"可能陷入局部死循环，请确认是否继续放行？"
                    )
                })
                return

    save_state(conv_id, state)
    emit_json({"decision": "allow"})


def handle_post_tool():
    """PostToolUse: 统计工具执行结果，更新健康度与动态收敛预算"""
    data = read_stdin_json()
    if not data:
        emit_json({})
        return

    conv_id = data.get("conversationId", "default")
    tool_call = data.get("toolCall", {})
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args", {})
    error = data.get("error")

    # 只读工具的报错不计入断路器失败（如 grep 没搜到属于正常探索）
    if is_read_only_tool(tool_name, args):
        emit_json({})
        return

    state = load_state(conv_id)
    if error:
        state["consecutive_failures"] += 1
        state["last_tool_failed"] = True
        # 出错时收缩上限至警戒水位，但不可小于已执行步数+2以留出必要的自愈空间
        alert_limit = max(state["step_count"] + 2, BASE_UNHEALTHY_STEP_LIMIT)
        if state.get("current_step_limit", BASE_HEALTHY_STEP_LIMIT) > alert_limit:
            state["current_step_limit"] = alert_limit
    else:
        state["consecutive_failures"] = 0
        state["last_tool_failed"] = False
        # 持续成功：若之前被降级，随着成功恢复健康上限
        if state.get("current_step_limit", 0) < BASE_HEALTHY_STEP_LIMIT:
            state["current_step_limit"] = BASE_HEALTHY_STEP_LIMIT

    save_state(conv_id, state)
    emit_json({})


def handle_pre_invocation():
    """PreInvocation: 用户发送新提示/开启新轮次，重置单轮步数与动态租约"""
    data = read_stdin_json()
    if not data:
        emit_json({})
        return

    conv_id = data.get("conversationId", "default")
    state = load_state(conv_id)

    # 关键自愈：每个新指令回合开启时，自动重置单轮步数
    state["step_count"] = 0
    is_healthy = (state.get("consecutive_failures", 0) == 0 and not state.get("last_tool_failed", False))
    state["current_step_limit"] = BASE_HEALTHY_STEP_LIMIT if is_healthy else BASE_UNHEALTHY_STEP_LIMIT
    save_state(conv_id, state)

    emit_json({})


def handle_session_start():
    """SessionStart: 新会话初始化，重置隔离状态"""
    data = read_stdin_json()
    if data:
        try:
            conv_id = data.get("conversationId", "default")
            sf = get_state_file(conv_id)
            if sf.exists():
                sf.unlink(missing_ok=True)
        except BaseException:
            pass
    emit_json({})


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "pre-tool"
    if mode == "pre-tool":
        handle_pre_tool()
    elif mode == "post-tool":
        handle_post_tool()
    elif mode == "pre-invocation":
        handle_pre_invocation()
    elif mode == "session-start":
        handle_session_start()
    else:
        emit_json({"decision": "allow"})


if __name__ == "__main__":
    # 最高级别物理屏障：任何未预料的 BaseException 发生时，绝不抛出非零退出码，直写 allow 确保宿主零阻塞
    try:
        main()
    except BaseException:
        sys.stdout.buffer.write(b'{"decision":"allow"}\n')
        sys.stdout.buffer.flush()
    sys.exit(0)
