# 📘 OpenViking (VK) Agent 对接与本地高性能架构最佳实践指南

> **文档目的**：供其他 AI Agent（或开发团队）快速复刻与对接 OpenViking (VK) 体外大脑。本文档详细说明了运行环境、网络鉴权、交互协议、优化手段及底层设计哲学。

---

## 一、 🖥️ 宿主电脑与运行环境 (Host Environment)

- **操作系统**：Windows 11 (64-bit)
- **工作区根目录**：`c:\Users\Skl\OneDrive - skloxo\Work`
- **Python 运行时**：Python 3.11 嵌入式环境 (`C:\Program Files\Tencent\Marvis\MarvisAgent\1.0.1100.240\runtime\python311`)
- **依赖软件包**：
  - `openviking` (v0.4.12)
  - `openviking-sdk` (v0.1.6)
  - Python 标准库：`urllib.request`, `json`, `os`, `time`, `argparse`（实现零外部依赖轻量级直连）

---

## 二、 🌐 网络与鉴权环境 (Network & Auth Protocol)

- **服务基准地址**：`https://vk.tide.red` (公网 HTTPS REST API)
- **API 规范**：OpenViking OpenAPI 3.1.0 (v0.4.10 Fork 版本)
- **鉴权模式**：`trusted` 信任鉴权模式

### 🔑 标准请求头规范 (Mandatory Headers)
针对 Fork 版本的 OpenViking，所有 HTTP 请求**必须注入以下 4 大专属 Header**：
```http
Accept: application/json
Content-Type: application/json
X-API-Key: vk-sk-<YOUR_API_KEY_HERE>
X-OpenViking-Account: default
X-OpenViking-User: default
X-User-Data: <YOUR_USER_DATA_TOKEN_HERE>
```

---

## 三、 🔌 与 OpenViking 对接的交互流程 (Ingestion & Search Workflow)

### 1. 两阶段文件上传与向量化 (Two-Phase Ingestion)
OpenViking 不允许直接向 `POST /api/v1/resources` 传递本地宿主机绝对路径。必须严格执行两阶段协议：
1. **阶段 1：二进制分块上传**：
   - 接口：`POST /api/v1/resources/temp_upload` (使用 `multipart/form-data`)
   - 返回：`temp_file_id` (如 `upload_f453df646d984d12b34da18f326aed37.md`)
2. **阶段 2：关联至虚拟 URI 并触发向量化**：
   - 接口：`POST /api/v1/resources`
   - Payload：
     ```json
     {
       "temp_file_id": "upload_f453df64...",
       "to": "viking://resources/work_1_yujia/README.md",
       "reason": "Master Whitepaper Sync",
       "instruction": "解析并建立向量",
       "wait": false
     }
     ```

### 2. 虚拟文件系统 (Viking URI Schemes)
统一划分为 5 大虚拟命名空间：
- `viking://resources/work_1_yujia/` ➔ 项目静态文档与 191 原型
- `viking://resources/user_preferences/` ➔ 个人工作偏好与输出铁律
- `viking://resources/bug_memories/` ➔ 避坑经验与历史缺陷
- `viking://user/sessions/` ➔ 阶段性会话 Walkthrough
- `viking://agent/skills/` ➔ 分布式 Agent 技能仓库

---

## 四、 ⚡ 本地性能优化与工程实施 (Local Optimizations)

我们在本地标准客户端 [.agents/skills/openviking/scripts/openviking_client.py](file:///c:/Users/Skl/OneDrive%20-%20skloxo/Work/.agents/skills/openviking/scripts/openviking_client.py) 中实施了 3 大针对性优化：

### 1. 本地 LRU 磁盘/内存二级缓存 (`.openviking_cache.json`)
- **耗时对比**：
  - 未使用缓存：向公网发请求 + 后端 Vector 算力生成，耗时 **5339.07 ms (5.3 秒)**；
  - 使用缓存：在 24 小时 TTL 内命中本地缓存，耗时 **< 1 ms (0.8 ms)**！

### 2. 异步非阻塞上传模式 (`wait=False`)
- **耗时对比**：
  - 同步模式 (`wait=True`)：HTTP 请求挂起等待服务器切片与 Embedding，耗时 **15~30 秒**（极易 Timeout）；
  - 异步模式 (`wait=False`)：生成 `task_id` 后在 **50 ms 内瞬间返回**，向量化交由 OpenViking 后台工作线程。

### 3. 服务端重启自愈与并发冲突重试
- **问题**：服务器重启会清空临时目录 `/temp/upload/`；多次连续上载同名 URI 会触发 `409 CONFLICT (path_busy)`。
- **机制**：客户端自动捕获 HTTP 409/500，重新申请 `temp_file_id` 并重试。

---

## 五、 🧠 本地优化的设计逻辑与根本原因 (Architectural Rationale)

1. **为什么要做本地 LRU 缓存？**
   - **原因**：在大模型思考阶段（Thinking Phase），如果每次自动唤醒都经历 5 秒的公网向量计算，用户会感到明显的卡顿与迟滞。通过缓存将频繁调用的业务上下文降至 `< 1ms`，才能实现**真正的无感流畅体验**。

2. **为什么写在 `.agents/AGENTS.md` 规则引擎中？**
   - **原因**：真正成熟的 Agent 绝不能靠人类每次提醒“请查 VK”。把无感自动唤醒规则写入 Agent 的全局规范中，使 Agent 在感知到项目词汇时**隐式自动触发搜索**，从而达到“无需多言”的默契。

3. **为什么要采用两阶段异步上传？**
   - **原因**：保证 Agent 能够快速响应用户，避免长轮询等待。

---

## 六、 🛠️ 供其他 Agent 快速复用的命令行 (CLI Cheat Sheet)

在终端可以直接运行以下指令：

```bash
# 1. 服务健康度检查
python 02_IT系统开发与功能需求/openviking_client.py health

# 2. 混合向量检索 (自动缓存加速, <1ms)
python 02_IT系统开发与功能需求/openviking_client.py search "单笔调迁单"

# 3. 绕过缓存直接发公网查询
python 02_IT系统开发与功能需求/openviking_client.py search "单笔调迁单" --no-cache

# 4. 上传并异步向量化本地文件
python 02_IT系统开发与功能需求/openviking_client.py upload "c:/path/to/file.md" --to "viking://resources/work/file.md"

# 5. 一键批量增量同步工作区
python 02_IT系统开发与功能需求/openviking_client.py sync
```
