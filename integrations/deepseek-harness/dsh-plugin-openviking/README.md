# dsh-plugin-openviking

> **OpenViking 体外大脑一体化官方插件套件 (DeepSeek Harness Bundle)**  
> 专为 DeepSeek Harness (DSH) 客户端设计，双轨合一：**主动 MCP 47项工具箱** + **被动无感先验拦截 Hook**。

---

## 🌟 核心特性

1. **官方 Schemastery 原生 GUI 表单 (Zero-YAML)**：
   - 遵循 DSH 官方 Schemastery 规范导出 `Config` Schema；
   - DSH 客户端「设置 -> OpenViking 体外大脑」自动生成**全可视化图形配置表单**；
   - 密码框支持 `role('secret')`，Token 安全脱敏遮罩，小白用户零代码、零编辑 YAML 即可使用。

2. **双轨合一极简架构**：
   - **主动 MCP 工具箱**：动态加载 `@deepseek-ai/dsh-mcp-client`，通过 Streamable HTTP 协议连接 OpenViking，自动在请求头附加 `Authorization: Bearer <apiKey>`，向模型注入全部 47 项体外大脑工具；
   - **被动先验拦截 Hook**：动态监听会话事件，在模型组装 Prompt 阶段自动并发预取体外记忆，注入 `ctx.systemPrompt`。

3. **零外部重依赖**：
   - 采用标准 Node.js ESM 规范，轻量高效，无冗余三方包。

---

## 🚀 安装与配置

### 方式 A：npm 包一键安装（推荐）
在 DSH 客户端「插件中心 -> 安装插件」输入包名：
```text
dsh-plugin-openviking
```
（或者指定本地目录 / 内部 npm 私有源）

### 方式 B：本地目录安装
将本目录放置于机器任意目录，或软链接至：
- Windows: `C:\Users\<用户名>\.dsh\plugins\openviking`
- Linux/macOS: `~/.dsh/plugins/openviking`

在 DSH 插件中心点击「添加插件」，输入本地目录路径即可。

---

## ⚙️ 图形化配置说明 (DSH 设置界面)

安装完成后，打开 DSH **设置 -> OpenViking 体外大脑**，直接填写以下表单：

| 配置字段 | 默认值 | 说明 |
| :--- | :--- | :--- |
| **apiUrl** | `https://vk.tide.red` | OpenViking 服务端地址 |
| **agentId** | *(必填)* | 智能体工兵 ID (在 OpenViking Studio 复制，如 `ag_cd3c029d7ea4`) |
| **apiKey** | *(选填)* | 用户的 User Key / API Token (带密码遮罩，在 HTTP Header 中安全传递) |
| **enableMcp** | `true` | 是否挂载 47 项体外大脑 MCP 工具箱 |
| **enableHook** | `true` | 是否启用前置记忆感知 Hook (无感注入 System Prompt) |
| **userId** | `default` | 租户 / 账户标识 |
| **peer** | `deepseek-harness@satellite` | 节点调用来源标识 (用于审计追踪) |

点击「保存」，DSH 自动热重载，模型即可同时拥有被动记忆召回与主动 47 项体外大脑工具！
