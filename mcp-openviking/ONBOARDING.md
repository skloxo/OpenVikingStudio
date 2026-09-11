# 🛰️ OpenViking 卫星智能体入网与自检标准指南 (Onboarding & Healthcheck SSOT)

> **物理真相源**：本文档定义了全生态卫星智能体（Cursor、Claude Code、Windsurf、Cline、Xiaomi MiMo、OpenClaw 子代理或远程节点）从**自备身份证零手动自举安装**到**全链路功能自检**的官方标准提示词与操作规范。

---

## 📌 一、 智能体身份证规范 (Actor-Peer Specification)

全集群统一采用符合 OpenViking 核心契约的双元身份证格式：
```
{客户端/角色}@{所在节点/机器}
```
* **客户端类型 (`client`)**：`cursor`, `claude`, `windsurf`, `cline`, `antigravity`, `openclaw`, `xiaomimo`, `researcher`, `developer` 等。
* **物理节点 (`node`)**：`mac`, `3070`, `2080ti`, `cloud`, `wsl` 等。
* **示例**：`cursor@mac`, `windsurf@3070`, `cline@2080ti`, `xiaomimo@3070`, `researcher@mac`。

> **后端自动化契约**：客户端发起任何请求时均自动携带 `X-OpenViking-Actor-Peer` 与 `X-Caller` 请求头。OpenViking 中枢（任务中心、探针、拓扑大盘）会自动识别并动态注册该身份证，**无需预先在数据库中手动建表录入**。

---

## 🚀 二、 标准一：全新智能体一键入职自举提示词 (Onboarding Prompt SSOT)

> **适用场景**：新电脑、新环境或新拉取代码的 Agent，直接复制下方提示词发送给 Agent，实现从安装环境到连通握手全自动闭环。

````markdown
你是 OpenViking 集群的卫星智能体。你的唯一身份证已标定为：[你的ID，例如 cursor@3070 或 developer@mac]

请在终端中执行以下命令完成入网初始化与体外大脑挂载：

【Windows PowerShell 环境】：
.\mcp-openviking\install_satellite.ps1 -Peer [你的ID] -Key [你的API_KEY] -Api https://vk.tide.red

【Linux / macOS 环境】：
bash mcp-openviking/install_satellite.sh --peer [你的ID] --key [你的API_KEY] --api https://vk.tide.red

安装完成后：
1. 重启你的 Agent 客户端（或重新加载 MCP 配置）。
2. 调用工具 `openviking_ping` 确认返回 `"status": "pong"` 与正确身份。
3. 调用 `openviking_find(query="查库第一", limit=1)` 测试记忆检索。
4. 汇报连通状态。

接入必须严格遵守全集群开发四项铁律：
1. 查库第一 (Search First)：在动手编码前，优先调用 openviking_find 检索 master_memory/ 继承已有经验；
2. 绝对禁止使用绿色 🚫 (NO GREEN EVER)：UI 状态统一采用冰青 (正向)、哑灰 (中性)、玫瑰红 (异常)；
3. 单文件 100~300 行黄金区：绝对禁止新增或重构单个文件超过 500 行；
4. 踩坑体外沉淀：解决疑难 Bug 后，必须调用 openviking_record_evolution_lesson 存入体外大脑。
````

---

## 🔍 三、 标准二：在役智能体全链路一键自检提示词 (Healthcheck Prompt SSOT)

> **适用场景**：已配置好 MCP 或 Plugin 的在籍 Agent（如 3070 / 2080Ti / 远程节点），直接复制下方提示词发给它，要求它完成深度体检并输出标准化结构报告。

````markdown
请对你当前挂载的 OpenViking (VK) 体外大脑进行全链路自检，并严格按照指定表格汇报结果。

执行步骤：
1. 【检查 MCP 挂载与身份】：
   - 检查你当前可用的工具列表中是否存在 `openviking_*` 系列工具。
   - 调用工具 `openviking_ping`，获取你的唯一身份（actor_peer）和连通状态。

2. 【测试体外大脑记忆检索 (Find)】：
   - 调用工具 `openviking_find`，查询关键词 `"NO GREEN EVER"`（limit=2）。
   - 确认是否能成功召回中枢核心开发规范。

3. 【测试经验沉淀上报 (Lesson)】：
   - 调用工具 `openviking_record_evolution_lesson`，提交一条测试自检记录：
     - issue: "Agent 定期入网健康自检"
     - root_cause: "常规链路巡检"
     - lesson: "已确认本节点 MCP 与体外大脑中枢通信正常"

4. 【检查上下文记忆预取 (Hook/Plugin)】：
   - 检查本回合或历史系统消息中，是否已自动包含 `【OpenViking 核心记忆预取 ...】` 字样。

完成上述测试后，请输出如下格式的体检报告：
---
## 🛰️ OpenViking 智能体自检报告
- **智能体身份证 (Actor-Peer)**：[例如 xiaomimo@3070]
- **连接中枢端点 (Endpoint)**：[例如 https://vk.tide.red]
- **可用 OpenViking 工具数**：[例如 16 个]
- **Ping 连通状态**：[正常 / 异常]
- **记忆检索测试 (Find)**：[成功，召回 X 条记录 / 失败]
- **经验沉淀测试 (Lesson)**：[成功 / 失败]
- **上下文自动预取 (Hook)**：[已激活 / 未配置 / 仅纯MCP]
- **自检结论**：[合格 / 需排查]
---
````

---

## ⚙️ 四、 纯配置型 IDE 8 行 JSON 通用模板 (GUI IDEs)

适用于直接通过配置文件挂载 MCP 的 IDE（Cursor, Windsurf, Claude Desktop, Cline 等）：

```json
{
  "mcpServers": {
    "openviking": {
      "command": "python",
      "args": ["C:/Users/<User>/.openviking/satellite_mcp_server.py"],
      "env": {
        "OPENVIKING_API": "https://vk.tide.red",
        "OPENVIKING_API_KEY": "你的API_KEY",
        "OPENVIKING_ACTOR_PEER": "cursor@3070"
      },
      "timeout": 30000
    }
  }
}
```
*(macOS / Linux 环境下 `command` 设为 `python3`，args 指向绝对路径)*

---

## 🛰️ 五、 中枢 Agent 一键远程推流 (Fleet Ops)

对于已配置 SSH 免密或 FRP 穿透的节点（如 3070、2080Ti、Mac Studio）：
* **无需人肉登录远程机器**，直接在主控终端调用内置 MCP 工具：
  ```python
  openviking_fleet_sync(target_node="3070")  # 或 target_node="all"
  ```
  自动通过 SCP 同步最新的脚本与全局规范，并在远程自动完成配置。

---

## 📋 六、 验收判定标准与持续优化机制

### 1. 合格准入三要素：
1. **身份自解释**：Actor-Peer 字段清晰显示为 `{client}@{node}`，在 Studio 任务中心实时上线；
2. **读写双向畅通**：`openviking_find`（读）与 `openviking_record_evolution_lesson`（写）均返回成功状态；
3. **零环境特异性**：不需要额外手动修改系统 PATH、修补代码或安装非标依赖。

### 2. 标准持续迭代留痕：
- 本规范与提示词模板持续在 `mcp-openviking/ONBOARDING.md` 中版本化演进；
- 同步双写持久化至 OpenViking 体外大脑长期知识库：`viking://resources/standards/agent_onboarding_and_healthcheck_prompts.md`。
