# Claude Desktop 原生适配与 MCP 挂载指南

> **归属中枢**：[openviking-plugin-ops](../SKILL.md)  
> **适用宿主**：Claude Desktop (Windows / macOS)，官方通过 `claude_desktop_config.json` 进行服务挂载。

---

## 1. 配置文件路径物理定位

- **macOS**：`~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**：`%APPDATA%\Claude\claude_desktop_config.json` (`C:\Users\<User>\AppData\Roaming\Claude\claude_desktop_config.json`)

---

## 2. 挂载范式

### 2.1 远程 Streamable-HTTP / SSE 模式 (推荐)
直接通过 FastMCP 端点桥接，支持租户鉴权与工兵隔离：
```json
{
  "mcpServers": {
    "openviking": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://vk.tide.red/mcp?plugin_id=openviking-memory&user_id=default"
      ],
      "env": {
        "OPENVIKING_API_KEY": "Bearer <YOUR_API_KEY>"
      }
    }
  }
}
```

### 2.2 本地 Stdio 模式 (用于单机隔离或本地调试)
```json
{
  "mcpServers": {
    "openviking": {
      "command": "python",
      "args": [
        "C:/Users/Skl/.openviking/satellite_mcp_server.py"
      ],
      "env": {
        "OPENVIKING_API": "https://vk.tide.red",
        "OPENVIKING_API_KEY": "<YOUR_API_KEY>",
        "OPENVIKING_USER": "default",
        "OPENVIKING_ACTOR_PEER": "claude-desktop@workstation"
      }
    }
  }
}
```

---

## 3. 避坑要点
1. **进程环境变量隔离**：Claude Desktop 启动时可能不继承用户 Shell 的环境变量，必须在 `env` 字典中显式声明 API Key；
2. **连接超时容错**：冷启动若存在模型加载延迟，建议启动时配置客户端超时为 30s。
