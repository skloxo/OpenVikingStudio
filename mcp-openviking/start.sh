#!/bin/bash
# OpenViking MCP Server 启动脚本
# 用法: ./start.sh [port]
#   无参数: stdio 模式（供 OpenClaw 直接调用）
#   有参数: SSE 模式，指定端口

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ─── 环境变量（可按需修改）──────────────────────────────────
# OpenViking HTTP API 地址
export OPENVIKING_API="${OPENVIKING_API:-http://127.0.0.1:1933}"

# OpenViking API Key（多租户模式下必填）
# export OPENVIKING_API_KEY="your-api-key"

# CLI 命令路径（默认使用 PATH 中的 openviking）
export OPENVIKING_CLI="${OPENVIKING_CLI:-openviking}"

# 双模态架构：core（本地核心全量模式）或 satellite（远程卫星安全模式）
export OPENVIKING_MCP_MODE="${OPENVIKING_MCP_MODE:-core}"

# ─── 依赖检查 ─────────────────────────────────────────────
check_deps() {
    if ! command -v python3 &>/dev/null; then
        echo "❌ python3 未找到" >&2
        exit 1
    fi

    # 检查 MCP 依赖
    if ! python3 -c "import mcp.server.fastmcp" 2>/dev/null; then
        echo "⚠️  MCP 库未安装，尝试安装..." >&2
        pip3 install "mcp[cli]" pydantic 2>/dev/null || {
            echo "❌ 无法安装 MCP 依赖" >&2
            exit 1
        }
    fi
}

# ─── 启动 ─────────────────────────────────────────────────
check_deps

if [ -n "$1" ]; then
    echo "🚀 OpenViking MCP Server (SSE) 启动在端口 $1 [模式: $OPENVIKING_MCP_MODE]"
    echo "   API: $OPENVIKING_API"
    exec python3 "$SCRIPT_DIR/mcp_openviking_server.py" "$@"
else
    echo "🚀 OpenViking MCP Server (stdio) 启动中... [模式: $OPENVIKING_MCP_MODE]" >&2
    echo "   API: $OPENVIKING_API" >&2
    exec python3 "$SCRIPT_DIR/mcp_openviking_server.py" "$@"
fi
