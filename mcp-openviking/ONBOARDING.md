# 🛰️ OpenViking 卫星智能体「提示词 + Key」一键入网指南 (Onboarding SSOT)

本文档定义了如何为任何未来新增的卫星智能体（Cursor、Claude Code、Windsurf、Cline、OpenClaw 子代理或远程节点 Agent）实现**零手动配置门槛、自备唯一身份证 (`client@node`)** 并一键接入 OpenViking 体外大脑。

---

## 📌 一、 智能体身份证规范 (Actor-Peer Specification)

全集群统一采用符合 OpenViking 核心契约的双元身份证格式：
```
{客户端/角色}@{所在节点/机器}
```
* **客户端类型 (`client`)**：`cursor`, `claude`, `windsurf`, `cline`, `antigravity`, `openclaw`, `researcher` 等。
* **物理节点 (`node`)**：`mac`, `3070`, `2080ti`, `cloud`, `wsl` 等。
* **示例**：`cursor@mac`, `windsurf@3070`, `cline@2080ti`, `researcher@mac`。

> **后端自动化契约**：MCP 客户端发起任何请求时均自动携带 `X-OpenViking-Actor-Peer` 与 `X-Caller` 请求头。OpenViking 中枢（任务中心、探针、拓扑大盘）会自动识别并动态注册该身份证，**无需预先在数据库中手动建表录入**。

---

## 🚀 二、 方式一：对话式自主 Agent「提示词 + Key」一键自举（最推荐）

适用于具备终端执行能力（Bash/PowerShell/Terminal）的 Agent（如 Claude Code, Cline, Antigravity, OpenClaw 等）。

### 📋 复制以下【入职自举提示词】直接发给新 Agent：

```markdown
你是 OpenViking 集群的卫星智能体。你的唯一身份证已标定为：[你的ID，例如 cursor@mac]

请在终端中执行以下一键入职命令，接入中枢并挂载体外大脑 MCP：

【Linux / macOS 环境】：
bash mcp-openviking/install_satellite.sh --peer [你的ID，如 cursor@mac] --key [你的API_KEY] --api https://vk.tide.red

【Windows PowerShell 环境】：
.\mcp-openviking\install_satellite.ps1 -Peer [你的ID，如 cursor@win] -Key [你的API_KEY] -Api https://vk.tide.red

执行完成后，请调用 openviking_ping 工具确认中枢连通性，并严格遵守全集群开发四项铁律：
1. 查库第一 (Search First)：在动手编码前，优先调用 openviking_find 检索 master_memory/ 继承已有经验；
2. 绝对禁止使用绿色 🚫 (NO GREEN EVER)：UI 状态统一采用冰青 (正向)、哑灰 (中性)、玫瑰红 (异常)；
3. 单文件 100~300 行黄金区：绝对禁止新增或重构单个文件超过 500 行；
4. 踩坑体外沉淀：解决疑难 Bug 后，必须调用 openviking_record_evolution_lesson 存入体外大脑。
```

> **效果**：Agent 执行命令后，安装脚本会自动验证 Python 依赖、生成封装脚本、向中枢发送 `/health` 握手探针，并输出完整 MCP 配置。Agent 随后执行 `openviking_ping` 即可宣告入列！

---

## ⚙️ 三、 方式二：纯配置型 IDE「8 行 JSON」即插即用

适用于通过 GUI 界面直接配置 MCP 的 IDE（如 Cursor, Windsurf, Claude Desktop）。

### 📋 复制以下配置，粘贴至 IDE 的 `mcpServers` 配置区：

```json
{
  "mcpServers": {
    "openviking": {
      "command": "python3",
      "args": ["/绝对路径/mcp-openviking/satellite_mcp_server.py"],
      "env": {
        "OPENVIKING_API": "https://vk.tide.red",
        "OPENVIKING_API_KEY": "你的API_KEY",
        "OPENVIKING_ACTOR_PEER": "cursor@mac"
      },
      "timeout": 30000
    }
  }
}
```
*(Windows 环境下 `command` 设为 `python`，路径使用斜杠 `/` 或双反斜杠 `\\`)*

---

## 🛰️ 四、 方式三：中枢 Agent 一键远程推流 (Fleet Ops)

对于已配置 SSH 免密或 FRP 穿透的节点（如 3070、2080Ti、Mac Studio）：
* **用户无需登录远程机器**，直接对本地主 Agent 说：
  > “帮我把 3070 上的新 Agent `windsurf@3070` 同步配置好”
* 主 Agent 直接调用内置 MCP 工具：
  ```python
  openviking_fleet_sync(target_node="3070")
  ```
  自动通过 SCP 同步最新的脚本与全局规范，并在远程自动完成配置。

---

## 👁️ 五、 接入验证与效果走查

新 Agent 完成接入后：
1. **调用验证**：Agent 执行 `openviking_ping` 返回：
   ```json
   { "status": "pong", "actor_peer": "cursor@mac", "endpoint": "https://vk.tide.red" }
   ```
2. **任务中心留痕**：在 OpenViking Studio 任务中心 (`/studio/tasks`) 中，该 Agent 触发的任何任务（记忆存储、检索、工序流转）在发起人一栏均会以 `[客户端] @ 节点` 的高密 Badge 形式精准展示，彻底告别模糊不清。
