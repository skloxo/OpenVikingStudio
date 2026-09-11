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

# 参数解析
PEER=""
KEY=""
API_URL="${OPENVIKING_API:-https://vk.tide.red}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --peer|-p) PEER="$2"; shift 2 ;;
    --key|-k)  KEY="$2"; shift 2 ;;
    --api|-a)  API_URL="$2"; shift 2 ;;
    *) shift ;;
  esac
done

# 3. 设置执行权限
chmod +x "$TARGET_PY"

# 4. 生成调用包装脚本 (若传入身份与密钥则固化注入)
WRAPPER_BIN="$SCRIPT_DIR/openviking-satellite"
cat << EOF > "$WRAPPER_BIN"
#!/bin/bash
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
export PYTHONUNBUFFERED=1
export OPENVIKING_API="${API_URL}"
EOF

if [ -n "$KEY" ]; then
  echo "export OPENVIKING_API_KEY=\"$KEY\"" >> "$WRAPPER_BIN"
fi
if [ -n "$PEER" ]; then
  echo "export OPENVIKING_ACTOR_PEER=\"$PEER\"" >> "$WRAPPER_BIN"
fi
echo 'exec python3 "$SCRIPT_DIR/satellite_mcp_server.py" "$@"' >> "$WRAPPER_BIN"
chmod +x "$WRAPPER_BIN"

echo "------------------------------------------------------------------"
echo "🎉 OpenViking Satellite MCP 客户端就绪！"
echo "   运行脚本: $TARGET_PY"
echo "   启动包装: $WRAPPER_BIN"

if [ -n "$PEER" ]; then
  echo "   绑定身份: $PEER"
  echo ""
  echo "📡 正在向 OpenViking 中枢发起入网握手探测..."
  python3 -c "
import urllib.request, json
req = urllib.request.Request('${API_URL}/health', headers={'X-OpenViking-Actor-Peer': '${PEER}', 'X-Caller': '${PEER}'})
if '${KEY}':
    req.add_header('Authorization', 'Bearer ${KEY}')
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        print('✅ 握手成功！智能体唯一身份证已接入中枢: ${PEER}')
except Exception as e:
    print('⚠️ 握手提示 (请确认中枢网络或密钥):', e)
" 2>/dev/null || true
fi

echo ""
echo "💡 客户端 MCP 配置代码块 (可直接粘贴至 Cursor / Claude Code / Windsurf):"
cat << EOF
{
  "mcpServers": {
    "openviking": {
      "command": "python3",
      "args": ["$TARGET_PY"],
      "env": {
        "OPENVIKING_API": "${API_URL}",
        "OPENVIKING_API_KEY": "${KEY:-your_api_key_here}",
        "OPENVIKING_ACTOR_PEER": "${PEER:-your_client@your_node}"
      },
      "timeout": 30000
    }
  }
}
EOF
echo "------------------------------------------------------------------"
