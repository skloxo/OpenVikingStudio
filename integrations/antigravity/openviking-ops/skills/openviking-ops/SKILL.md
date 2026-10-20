---
name: openviking-ops
description: OpenViking 核心服务运维、拓扑体检、存储初始化与特权管控专用技能。涵盖 16 项系统运维特权工具的高阶 SOP 与安全护栏。
---

# OpenViking 核心运维特权操作法典 (OpenViking Ops SSOT)

本技能定义 OpenViking (VK) 核心服务运维、文件目录拓扑重构、记忆纯度治理与特权工具链的最佳实践与执行 SOP。

---

## 一、三位一体运维特权架构

1. **MCP 特权工具层 (`openviking-ops`)**：
   - 直连服务端 `OPENVIKING_API`，通过 FastMCP 暴露 16 项高特权算子；
   - 依赖管理员凭据 (`OPENVIKING_API_KEY`)，遵循零信任单轨鉴权。
2. **Hook 反射弧防御层 (`ov_ops_audit.py`)**：
   - 监听 `PreToolUse` 事件，针对停机或服务控制动作强制记录审计日志并保护进程。
3. **技能认知层 (`openviking-ops`)**：
   - 赋予智能体系统运维专家潜意识：先查后动、原子提交兜底、动静态隔离与平滑重载。

---

## 二、十六项运维特权算子图谱 (OPS_16_TOOL_NAMES SSOT)

| 运维域 | 算子名称 | 核心职责与安全契约 |
| :--- | :--- | :--- |
| **资源与索引** | `openviking_add_resource` | 向体外大脑挂载新文件、目录或 URL 资源，支持同步/异步解析 |
|  | `openviking_list_resources` | 检索浏览指定 URI 目录下的已挂载资源清单 |
|  | `openviking_delete_resource` | **高危**：安全注销并移除指定的体外大脑资源 |
|  | `openviking_reindex` | 触发全盘或局部向量索引与知识库重构 |
|  | `openviking_commit` | 工作区变更版本快照物理提交（带 reason 留痕） |
| **文件系统拓扑** | `openviking_mv` | 底层文件或目录安全原子重定位与拓扑移动 |
|  | `openviking_rename` | 知识库文件或目录安全重命名 |
|  | `openviking_webdav_info` | 查询 WebDAV 协议挂载端点、支持方法与挂载命令 |
| **质量与自愈** | `openviking_memory_purity_report` | 评估记忆纯度、概念漂移程度与信噪比 (SNR) |
|  | `openviking_retry_dead_letter` | 触发死信队列消息自愈重试与故障排查 |
| **监听订阅** | `openviking_list_watches` | 查看自动刷新系统监听订阅任务清单 |
|  | `openviking_cancel_watch` | 取消指定的自动刷新系统监听任务 |
|  | `openviking_manage_watch` | 动态更新或调整系统监听器轮询周期与激活状态 |
| **核心服务管控** | `openviking_server_doctor` | 全系统底层硬件、向量库、数据库与存储引擎深度体检诊断 |
|  | `openviking_server_control` | 核心中枢生命周期控制：`status`, `reload` (平滑重载), `restart`, `drain` |
|  | `openviking_server_init` | **高危**：底座存储引擎与数据表引导初始化 (`force` 需慎用) |

---

## 三、四大核心运维 SOP

### 1. 服务健康体检 SOP
- **执行顺序**：`openviking_server_doctor` ➔ `openviking_memory_purity_report`；
- **异常收敛**：若检测到 LanceDB 索引碎片超标或向量库异常，先调用 `openviking_commit` 提交当前状态，再调度 `openviking_reindex` 重建。

### 2. 变更版本提交 SOP
- 任何资源增删或目录移动 (`openviking_mv`) 完成后，**必须强制调用** `openviking_commit(reason="...")` 固化物理快照；
- 确保 Git 与体外大脑双轨版本留痕一致。

### 3. 死信队列自愈排查 SOP
- 定期或感知到处理卡顿后，执行 `openviking_retry_dead_letter(max_count=10)`；
- 观察自愈重试日志，定位无法入库的异常数据格式。

### 4. 服务平滑重载与生命周期准则
- 严禁盲目粗暴杀死进程；修改配置后优先采用 `openviking_server_control(action="reload")` 平滑热更；
- 确需重启时，先调用 `openviking_server_control(action="status")` 确认无正在运行的重索引或批处理任务。
