# 📘 DeepSeek Harness (DSH) 客户端对接与运维手册

> **文档定位**：DeepSeek Harness (DSH) 桌面端 / Web 端连接 OpenViking (VK) 记忆中枢与集群运维指南。  
> **适用节点**：Windows 宿主机 (2080Ti)、远程算力节点 (3070)、WSL 混合环境。

---

## 🧭 一、 架构与目录索引 (Architecture & Paths)

DeepSeek Harness 基于 **Cordis 插件化微内核框架** 构建，采用分层 Overlay 补丁机制装配功能。

### 1. 物理目录结构

| 目录类型 | 真实物理路径 | 作用说明 |
|:---|:---|:---|
| **只读程序目录** | `C:\Users\<User>\AppData\Local\Programs\DeepSeek Harness` | 客户端 Electron 与 Chromium 二进制，**严禁在此修改配置（不会生效）** |
| **真实活动配置主目录 (`$DSH_HOME`)** | `C:\Users\<User>\.dsh` | 唯一的全局用户数据与运行时配置根目录 |
| **桌面端活动补丁 (`desktop`)** | `C:\Users\<User>\.dsh\profiles\desktop\cordis.patch.yml` | **桌面客户端唯一生效的用户补丁文件** |
| **Web 端活动补丁 (`web`)** | `C:\Users\<User>\.dsh\profiles\web\cordis.patch.yml` | Web/CLI 模式生效的用户补丁文件 |
| **会话持久化存储** | `C:\Users\<User>\.dsh\sessions\` | 各工作区与对话历史 JSON |
| **凭据存储 (`credentials`)** | `C:\Users\<User>\.dsh\.credentials.yaml` | 客户端凭据授权缓存 |

---

## ⚡ 二、 MCP 对接第一性原理与规范

### 1. 核心插件职责解耦

- **连接器插件**：`@deepseek-ai/dsh-mcp-client`  
  这是连接外部 MCP 服务的**唯一插件**。负责管理 stdio 子进程生命周期、HTTP 连接、工具暴露 (`mcp__<serverName>__<rawName>`) 与系统提示词 (instructions) 注入。
- **资源消费插件**：`@deepseek-ai/dsh-mcp-resources`  
  这是 DSH 底层 profile 自带的**内置服务**，负责向模型暴露 `list_mcp_resources`、`read_mcp_resource`、`list_mcp_resource_templates` 工具。**严禁在 patch 中手动向其配置 `mcpServers`**！

### 2. 标准 Cordis Patch 语法

必须使用 `- insert:` 指令将新插件条目插入到 Loader 阵列中：

```yaml
- insert:
    - id: mcp-openviking
      name: "@deepseek-ai/dsh-mcp-client"
      config:
        serverName: openviking
        transport: stdio
        command: wsl.exe
        args:
          - -e
          - python3
          - /home/skloxo/aho/openclaw/project/OpenVikingStudio/mcp-openviking/satellite_mcp_server.py
        env:
          OPENVIKING_API: "http://127.0.0.1:1933"
          OPENVIKING_ACTOR_PEER: "deepseek-harness@2080ti"
          OPENVIKING_CLIENT: "deepseek-harness"
        reconnect:
          enabled: true
          initialDelayMs: 500
          maxDelayMs: 15000
          maxAttempts: 10
```

> **安全契约**：API Key **严禁明文硬编码**于 YAML 中。`satellite_mcp_server.py` 会自动从本地 `~/.openviking/ov.conf` 或环境动态读取鉴权。

---

## 🔍 三、 历史踩坑根因分析 (Postmortem)

1. **改错文件**：修改了安装目录下的 `AppData\Local\Programs\...`，而 DSH 启动加载的是 `~/.dsh/profiles/desktop/cordis.patch.yml`；
2. **用错插件名**：误将 `@deepseek-ai/dsh-mcp-resources` 当作客户端，其实该插件是内部资源共享工具提供者；
3. **嵌套格式错误**：误写了 Claude Desktop 风格的 `mcpServers: { openviking: { command: [...] } }`，Cordis 需要扁平的 `command` (字符串) 与 `args` (数组)；
4. **缺少 insert 指令**：直接在顶层罗列新条目无法被 Loader 正确挂载为新增插件。

---

## 🛰️ 四、 3070 节点快速接入指南

在 3070 节点上安装部署 DSH 并接入 VK：

1. **安装程序**：安装 DSH Windows 安装包；
2. **定位 `$DSH_HOME`**：打开 `C:\Users\<User>\.dsh\profiles\desktop\`；
3. **下发 Patch**：在 `cordis.patch.yml` 末尾追加上面的 `- insert:` 块（注意调整 `OPENVIKING_ACTOR_PEER` 为 `deepseek-harness@3070`）；
4. **启动验收**：重启 DSH，在输入框输入 `ping openviking`，确认模型成功调用 `mcp__openviking__openviking_ping` 并返回 healthy。
