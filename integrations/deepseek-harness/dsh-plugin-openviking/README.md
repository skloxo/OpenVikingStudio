# dsh-plugin-openviking

> **OpenViking 客户端通用轻量 RPC 通信桥梁与 Hook 套件 (DeepSeek Harness Bundle)**  
> 专为 DeepSeek Harness (DSH) 客户端设计。**服务端本体 + 客户端极简 RPC 桥**：
> - **服务端 (云端/本机 1933)**：运行全量代码、向量库与 FastMCP **50 项物理工具**；
> - **客户端 (Agent 本地)**：仅安装本 **RPC 通信桥梁** 与配套 **Agent 对接认知技能**，零本地重型依赖。

---

## 🌟 核心特性与第一性原理

1. **官方 Schemastery 原生 GUI 表单 (Zero-YAML)**：
   - 遵循 DSH 官方 Schemastery 规范导出 `Config` Schema；
   - DSH 客户端「设置 -> OpenViking 体外大脑」自动生成**全可视化图形配置表单**；
   - 密码框支持 `role('secret')`，Token 安全脱敏遮罩，小白用户零代码、零编辑 YAML 即可使用。

2. **双轨分离认证鉴权与动态能力投影**：
   - **身份验真 (User Key)**：在 HTTP Header 中安全传递 `Authorization: Bearer <key>`，拦截 401 非法调用；
   - **权限范围与能力投影 (Agent ID)**：通过 `/mcp?agent_id=<id>` 动态向模型下发所属角色授权的白名单工具（支持全量 50 项工具）；
   - **零重启热重载 (Volatile Hot-Reload)**：监听 `loader/volatile-update`，切换 Agent ID 或保存 Key 毫秒级重置连接，零重启生效。

3. **被动无感先验拦截 Hook (底牌透明)**：
   - 动态监听会话事件，在模型组装 Prompt 阶段自动并发预取体外记忆，注入 `ctx.systemPrompt`；
   - 提示词头部明示注入内容，Agent 吸收已知事实，无需重复调用检索盲搜。

4. **极轻量零重依赖**：
   - 纯单文件 Schema (`schema.js`) 自包含内嵌，全插件打包仅 ~15KB，无本地 Python/数据库负担。

---

## 🚀 安装与配置

### 方式 A：公网不可变 Tarball 一键安装（推荐）
在 DSH 客户端「插件中心 -> 安装插件」输入全局 SSOT 链接：
```text
https://vk.tide.red/studio/dsh-plugin-openviking-1.5.1.tgz
```

### 方式 B：npm 包名安装
在 DSH 客户端「插件中心 -> 安装插件」输入包名：
```text
dsh-plugin-openviking
```

### 方式 C：本地目录安装
将本目录放置于机器任意目录，或软链接至：
- Windows: `C:\Users\<用户名>\.dsh\plugins\openviking`
- Linux/macOS: `~/.dsh/plugins/openviking`

---

## ⚙️ 图形化配置说明 (DSH 设置界面)

安装完成后，打开 DSH **设置 -> 插件配置 -> OpenViking 体外大脑**，直接填写以下表单：

| 配置字段 | 默认值 | 说明 |
| :--- | :--- | :--- |
| **endpointUrl** | `https://vk.tide.red/mcp` | OpenViking 通信端点 (支持同机内网 `http://127.0.0.1:1933/mcp` 与跨网公网) |
| **userKey** | *(必填)* | 所属用户 User API Key (带密码遮罩，在 HTTP Header 中安全传递) |
| **agentId** | *(必填)* | 专属智能体工兵 ID (在 OpenViking 智能体中心复制，如 `ag_cd3c029d7ea4`) |
| **enableMcp** | `true` | 是否挂载体外 MCP 工具箱 (开启后通过 RPC 动态投影服务端全部授权工具) |
| **enableHook** | `true` | 是否启用前置记忆感知 Hook (无感注入 System Prompt) |
| **userId** | `default` | 租户 / 账户标识 |
| **peer** | `deepseek-harness@satellite` | 节点调用来源标识 (用于审计追踪) |

点击「保存」，DSH 自动热重载，模型即可通过 RPC 实时拥有被动记忆召回与受控的体外大脑工具！
