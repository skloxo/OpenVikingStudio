# Cursor / Cline / VS Code 原生适配与插件开发指南

> **归属中枢**：[openviking-plugin-ops](../SKILL.md)  
> **适用宿主**：Cursor, Cline (VS Code 扩展), Roo Code, Windsurf

---

## 1. 宿主特性与配置入口

- **Cursor**：`~/.cursor/mcp.json` 或项目级 `.cursor/mcp.json`；
- **Cline**：`%APPDATA%/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`；
- **规则下发**：通过 `.cursorrules` / `.clinerules` 注入 OpenViking 协同契约。

---

## 2. 挂载标准配置

```json
{
  "mcpServers": {
    "openviking": {
      "command": "python",
      "args": [
        "-u",
        "-m", "openviking_mcp_client"
      ],
      "env": {
        "OPENVIKING_API": "https://vk.tide.red",
        "OPENVIKING_API_KEY": "${env:OPENVIKING_API_KEY}",
        "OPENVIKING_USER": "default",
        "OPENVIKING_ACTOR_PEER": "cursor@developer"
      }
    }
  }
}
```

---

## 3. 动态契约与记忆协同
在 `.cursorrules` 中注入：
```markdown
# OpenViking Exocortex Contract
- 凡收到复杂工程、架构设计或疑难排查任务，优先调用 `openviking_find` 召回历史设计偏好；
- 根治复杂 Bug 或重大架构重构后，必须调用 `openviking_record_evolution_lesson` 写入体外大脑。
```
