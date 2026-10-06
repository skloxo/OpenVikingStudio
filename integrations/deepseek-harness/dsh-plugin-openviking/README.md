# dsh-plugin-openviking

> **OpenViking 体外大脑一体化官方套件 (DeepSeek Harness Bundle)**  
> 专为 DeepSeek Harness (DSH) 客户端设计，双轨合一：**主动 MCP 工具箱** + **被动无感先验拦截 Hook**。

---

## 🌟 核心特性

1. **组合包原生契约 (Native Bundle)**：
   - 严格遵循 DSH Cordis 组合包规范，声明 `dsh.bundle.patch: "./cordis.patch.yml"`；
   - 在 DSH 客户端插件中心呈现为单一卡片，内含两个独立运行中的子组件：
     - `mcp-openviking`：接入 OpenViking FastMCP 卫星服务，提供主动知识召回与持久化工具；
     - `openviking-hook`：拦截用户消息，自动向记忆中枢执行先验上下文预取并注入 System Prompt。

2. **零配置文件污染**：
   - 无需手动修改 profile 的 `cordis.patch.yml`；
   - 100% 经由 DSH GUI 插件生命周期统一管理与一键启闭。

3. **安全与依赖注入**：
   - 严格遵循 Cordis 框架规则，导出 `inject = ['systemPrompt']`；
   - 原生 Node.js ESM 实现，零外部依赖包。

---

## 🚀 安装指南

### 1. 本地目录部署
将本目录复制或软链接至 Windows 宿主机插件目录：
```text
C:\Users\<User>\.dsh\plugins\openviking
```

### 2. DSH GUI 界面一键安装
1. 打开 DeepSeek Harness 桌面客户端，进入 **设置 -> 插件**；
2. 点击右上角 **「添加插件」**；
3. 输入本地路径：`C:\Users\<User>\.dsh\plugins\openviking`；
4. 点击安装并开启开关。
