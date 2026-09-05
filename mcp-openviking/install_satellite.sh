#!/bin/bash
# ==============================================================================
# OpenViking Satellite MCP Client — 一键安装与极速分发脚本 (Linux / macOS)
# ==============================================================================
# 功能: 在独立远程节点 (Mac Studio, 远程 GPU 服务器, 开发者电脑) 一键配置 Satellite MCP
# 仅依赖: python3 (>=3.10) + pip
# ==============================================================================

set -e

echo "🚀 [OpenViking Satellite] 开始配置轻量级体外大脑 MCP 客户端..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_PY="$SCRIPT_DIR/satellite_mcp_server.py"

if [ ! -f "$TARGET_PY" ]; then
    echo "❌ 找不到 $TARGET_PY" >&2
    exit 1
fi

# 1. 检查 Python 运行环境
if ! command -v python3 &>/dev/null; then
    echo "❌ 错误: 未找到 python3，请先安装 Python 3.10+" >&2
    exit 1
fi

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ 检测到 Python: $PY_VER"

# 2. 安装/验证 mcp 库
if ! python3 -c "import mcp.server.fastmcp" &>/dev/null; then
    echo "📦 正在安装核心依赖 'mcp[cli]' 与 'pydantic'..."
    python3 -m pip install "mcp[cli]" pydantic
else
    echo "✅ MCP 核心依赖已满足"
fi

# 3. 设置执行权限
chmod +x "$TARGET_PY"

# 4. 生成调用包装脚本
WRAPPER_BIN="$SCRIPT_DIR/openviking-satellite"
cat << 'EOF' > "$WRAPPER_BIN"
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONUNBUFFERED=1
exec python3 "$SCRIPT_DIR/satellite_mcp_server.py" "$@"
EOF
chmod +x "$WRAPPER_BIN"

echo "------------------------------------------------------------------"
echo "🎉 OpenViking Satellite MCP 客户端就绪！"
echo "   运行脚本: $TARGET_PY"
echo "   启动包装: $WRAPPER_BIN"
echo ""
echo "💡 各客户端配置示例 (Claude Code / Cursor / WorkBuddy):"
cat << EOF
{
  "mcpServers": {
    "openviking": {
      "command": "python3",
      "args": ["$TARGET_PY"],
      "env": {
        "OPENVIKING_API": "${OPENVIKING_API:-http://127.0.0.1:1933}",
        "OPENVIKING_API_KEY": "${OPENVIKING_API_KEY:-your_api_key_here}"
      }
    }
  }
}
EOF
echo "------------------------------------------------------------------"
