param(
    [string]$Peer = "",
    [string]$Key = "",
    [string]$Api = "https://vk.tide.red"
)

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

# 3. 输出配置与握手验证
Write-Host "------------------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "🎉 OpenViking Satellite MCP 客户端就绪！" -ForegroundColor Green
Write-Host "   目标脚本: $TargetPy" -ForegroundColor White

if ($Peer) {
    Write-Host "   绑定身份: $Peer" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📡 正在向 OpenViking 中枢发起入网握手探测..." -ForegroundColor DarkGray
    try {
        $headers = @{ "X-OpenViking-Actor-Peer" = $Peer; "X-Caller" = $Peer }
        if ($Key) { $headers["Authorization"] = "Bearer $Key" }
        $resp = Invoke-RestMethod -Uri "$Api/health" -Headers $headers -TimeoutSec 5 -ErrorAction Stop
        Write-Host "✅ 握手成功！智能体唯一身份证已接入中枢: $Peer" -ForegroundColor Green
    } catch {
        Write-Host "⚠️ 握手提示 (请确认中枢网络或密钥): $_" -ForegroundColor Yellow
    }
}

$safeKey = if ($Key) { $Key } else { "your_api_key_here" }
$safePeer = if ($Peer) { $Peer } else { "your_client@your_node" }

Write-Host ""
Write-Host "💡 客户端配置代码块 (可直接贴入 Cursor / Claude Code / Antigravity / Windsurf):" -ForegroundColor Yellow
$jsonSample = @"
{
  "mcpServers": {
    "openviking": {
      "command": "python",
      "args": ["$($TargetPy.Replace('\', '/'))"],
      "env": {
        "OPENVIKING_API": "$Api",
        "OPENVIKING_API_KEY": "$safeKey",
        "OPENVIKING_ACTOR_PEER": "$safePeer"
      },
      "timeout": 30000
    }
  }
}
"@
Write-Host $jsonSample -ForegroundColor White

if ($safePeer -like "xiaomimo*") {
    Write-Host ""
    Write-Host "💡 Xiaomi MiMo Desktop 配置代码块 (贴入 ~/.config/mimocode/mimocode.jsonc):" -ForegroundColor Yellow
    $mimoSample = @"
{
  "mcp": {
    "openviking": {
      "type": "local",
      "command": ["python", "$($TargetPy.Replace('\', '/'))"],
      "environment": {
        "OPENVIKING_API": "$Api",
        "OPENVIKING_API_KEY": "$safeKey",
        "OPENVIKING_ACTOR_PEER": "$safePeer"
      },
      "timeout": 30000,
      "enabled": true
    }
  },
  "plugin": [
    "C:/Users/Skl/.openviking/mimo-openviking-plugin.mjs"
  ]
}
"@
    Write-Host $mimoSample -ForegroundColor Cyan
}
Write-Host "------------------------------------------------------------------" -ForegroundColor DarkGray
