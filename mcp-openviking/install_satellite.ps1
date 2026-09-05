# ==============================================================================
# OpenViking Satellite MCP Client — Windows PowerShell 安装与分发脚本
# ==============================================================================

$ErrorActionPreference = "Stop"

Write-Host "🚀 [OpenViking Satellite] 开始配置轻量级体外大脑 MCP 客户端 (Windows)..." -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$TargetPy = Join-Path $ScriptDir "satellite_mcp_server.py"

if (-not (Test-Path $TargetPy)) {
    Write-Error "❌ 找不到 $TargetPy"
}

# 1. 检测 Python 环境
try {
    $pyVer = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    Write-Host "✅ 检测到 Python: $pyVer" -ForegroundColor Green
} catch {
    Write-Error "❌ 错误: 未在 PATH 中找到 python，请先安装 Python 3.10+"
}

# 2. 检查并安装 mcp 依赖
try {
    python -c "import mcp.server.fastmcp" 2>$null
    Write-Host "✅ MCP 核心依赖已满足" -ForegroundColor Green
} catch {
    Write-Host "📦 正在安装核心依赖 'mcp[cli]' 与 'pydantic'..." -ForegroundColor Yellow
    python -m pip install "mcp[cli]" pydantic
}

# 3. 输出配置示例
Write-Host "------------------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "🎉 OpenViking Satellite MCP 客户端就绪！" -ForegroundColor Green
Write-Host "   目标脚本: $TargetPy" -ForegroundColor White
Write-Host ""
Write-Host "💡 Windows 客户端配置样例 (Cursor / Claude Code / Antigravity):" -ForegroundColor Yellow
$jsonSample = @"
{
  "mcpServers": {
    "openviking": {
      "command": "python",
      "args": ["$($TargetPy.Replace('\', '/'))"],
      "env": {
        "OPENVIKING_API": "http://127.0.0.1:1933",
        "OPENVIKING_API_KEY": "your_api_key_here"
      }
    }
  }
}
"@
Write-Host $jsonSample -ForegroundColor White
Write-Host "------------------------------------------------------------------" -ForegroundColor DarkGray
