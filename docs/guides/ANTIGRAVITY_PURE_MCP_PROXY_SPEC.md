# Antigravity 原生插件纯透明 MCP 代理架构规约 (SSOT)

本规范确立 Antigravity / Antigravity IDE 原生插件体系的终极架构模式 —— **纯透明 MCP 代理桥 (Pure Stdio-to-Streamable-HTTP MCP Proxy)**，彻底废黜客户端本地手写适配器模式，实现全集群、跨宿主能力统一归中与零感知热更。

---

## 一、架构背景与第一性原理

### 1. 传统本地手写适配器模式的物理缺陷 (Anti-Pattern)
在早期版本中，反重力插件在本地 `server.py` 中通过 `@mcp.tool()` 手工声明每一个工具，并在本地拼接 REST 请求。这种模式存在四大致命弊端：
1. **割裂与漂移**：服务端迭代了 35 个工具，客户端仅维护了 26 个，导致能力被严重人为阉割；
2. **双重维护负债**：服务端接口参数演进时，必须同时修改客户端手写代码并重新发布打包；
3. **脆弱的协议转换**：在本地手写 JSON 拼装与异常处理，极易遭遇 404/405/422 状态码未捕获；
4. **客户端臃肿**：单文件突破 400~500 行安全红线，违背奥卡姆剃刀原理。

### 2. 终极真理：本地薄桥，能力归中 (The Pure Proxy Truth)
**“客户端只做透明管道，所有业务能力与工具契约 100% 物理内聚在服务端”**：
- 客户端启动极其轻量级的 Python 代理（约 150~180 行）；
- 代理只做协议穿透：将反重力宿主的 **标准 Stdio JSON-RPC 2.0** 流量，无损透传至后端的 **Streamable-HTTP (`/mcp`)**；
- 工具列表、参数定义、类型约束与执行逻辑全部由服务端 FastMCP 单一真实源 (SSOT) 驱动。

```
┌────────────────────────────────────────────────────────┐
│               Antigravity IDE 宿主环境                  │
├────────────────────────────────────────────────────────┤
│  客户端 MCP 进程: server.py (纯透明代理桥, ~180 行)    │
│  - 监听 Stdio (stdin / stdout)                         │
│  - 捕获 JSON-RPC 2.0 请求并注入鉴权上下文              │
└──────────────────────────┬─────────────────────────────┘
                           │ Streamable-HTTP (POST /mcp)
                           ▼
┌────────────────────────────────────────────────────────┐
│             OpenViking 核心服务端 (FastMCP)            │
├────────────────────────────────────────────────────────┤
│  - 单一真实源 (SSOT): 原生注册 35 项战地工具与资源     │
│  - 统一用户与空间隔离 (X-OpenViking-User 物理沙盒)     │
│  - 服务端热更，全集群智能体（DSH / 反重力）即刻同频    │
└────────────────────────────────────────────────────────┘
```

---

## 二、四大核心设计铁律 (Inviolable Rules)

### 1. 零业务代码渗透铁律 (Zero Hardcoded Tools)
- 客户端 `server.py` **绝对禁止出现任何 `@mcp.tool()` 业务声明**；
- 严禁在客户端定义具体的工具名称、参数类型或写死 API 端点；
- `tools/list` 与 `tools/call` 必须 100% 由服务端 `/mcp` 动态返回并执行。

### 2. 鉴权与上下文三元组强制注入 (Triple Context Injection)
纯代理在向服务端转发 HTTP 请求时，必须严格注入以下请求头，确保用户沙盒物理隔离与安全：
```http
Authorization: Bearer <API_KEY>
X-OpenViking-User: <USER_ID>      # 如: antigravity@2080ti
X-OpenViking-Account: default
Accept: application/json, text/event-stream
Content-Type: application/json
```

### 3. 双向协议保真与无损透传 (Lossless JSON-RPC Tunneling)
- **请求透传**：客户端发送的 `initialize`, `tools/list`, `tools/call`, `resources/list` 等请求，原始保留其 `jsonrpc`, `id`, `method`, `params`；
- **响应透传**：服务端返回的 `result` 或 `error` 原样回写到 `stdout`，严禁擅自修改结构或包装虚假 fallback；
- **流式兼容**：服务端返回 SSE 流式块时，聚合首个合法 JSON 报文或透传终端帧。

### 4. 故障优雅降级与零崩溃退出 (Graceful Error Degradation)
- 当远端服务离线、端口未通或发生 HTTP 500 时，代理进程**严禁调用 `sys.exit()` 崩溃**；
- 必须封装为标准 MCP JSON-RPC Error：
  ```json
  {
    "jsonrpc": "2.0",
    "id": "<request_id>",
    "error": {
      "code": -32603,
      "message": "OpenViking 服务端无法连接: http://127.0.0.1:1933/mcp - 请检查服务状态"
    }
  }
  ```
  这保障了宿主 IDE 永远不会因为网络断开而出现进程悬挂或插件崩溃。

---

## 三、标准模板脚手架 (Reference Implementation)

全系插件重构为纯代理时，标准 `server.py` 控制在 150~180 行左右，采用如下最小拓扑架构：

```python
import sys, json, os, urllib.request, urllib.error

# 1. 动态加载环境与配置
SERVER_URL = os.environ.get("OPENVIKING_API_URL", "http://127.0.0.1:1933").rstrip("/")
API_KEY = os.environ.get("OPENVIKING_API_KEY", "")
USER_ID = os.environ.get("OPENVIKING_USER_ID", "antigravity@2080ti")

def forward_to_mcp(payload: dict) -> dict:
    target_url = f"{SERVER_URL}/mcp"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "X-OpenViking-User": USER_ID,
        "X-OpenViking-Account": "default"
    }
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
        
    req = urllib.request.Request(target_url, data=json.dumps(payload).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        # 解析返回并无损透传
        return json.loads(resp.read().decode())

def main():
    # 2. 标椎 Stdio 循环
    while True:
        line = sys.stdin.readline()
        if not line: break
        req = json.loads(line)
        # 3. 直通转发
        res = forward_to_mcp(req)
        sys.stdout.write(json.dumps(res) + "\n")
        sys.stdout.flush()
```

---

## 四、全系插件演进路线图 (Rollout Roadmap)

全集群所有 Antigravity 插件统一收敛至本架构规范：

| 插件名称 | 当前状态 | 目标架构 | 核心收益 |
| :--- | :--- | :--- | :--- |
| **`openviking-memory`** | **已重构为纯透明代理 (v2.0.27)** | Stdio ➔ `/mcp` 纯代理 | 激活全部 35 个战地工具，两端完全同频 |
| **`openviking-ops`** | 规划中 (Card-221) | Stdio ➔ `/mcp` 纯代理 | 运维与系统监控工具统一归中 |
| **`keepass-vault`** | 规划中 | Stdio ➔ `/mcp` 纯代理 | 凭据管理逻辑与后端安全堡垒统一 |
| **`dify` / `cpa`** | 孵化中 | 原生即采用纯代理模式 | 零历史包袱，100% 遵循本规约 |

---
*本规约为 Workspace 与全集群 Antigravity 原生插件开发最高工程法典，凡改动必须严格对齐。*
