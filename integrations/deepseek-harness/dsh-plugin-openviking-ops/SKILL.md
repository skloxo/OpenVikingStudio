# 🛡️ OpenViking 系统运维治理特权说明书 (SKILL.md)

## 一、身份契约与能力定位
本机智能体已挂载 OpenViking 专属运维治理特权中枢，具备超级管理员 (Admin/Root) 权限。
全系统共授权挂载 17 项运维特权工具与 2 项 Hook 物理守卫。

## 二、严禁行为 (Negative Guardrails) 🚫
1. **绝对禁止自写 Python 脚本测试工具**：所有 17 项特权工具已由 FastMCP 原生挂载，直接发起 Tool Call，严禁在工作区编写脚本盲跑探测；
2. **破坏性操作必须二次确认**：删除用户 (`delete_user`)、清空队列或重建索引等高危操作必须保持审慎。

## 三、特权运维武器清单 (17 Tools SSOT)
- `openviking_server_doctor()`: 服务端健康全要素体检（AGFS、VectorDB、APIKeyManager、Embedding 全链路探测）；
- `openviking_system_status()`: 检索系统底层资源分布、向量数、集合状态与运行指标；
- `openviking_list_watches()`: 获取当前活跃的目录与文件变更监听哨兵任务；
- `openviking_cancel_watch(watch_id: str)`: 停止并注销后台监听任务；
- `openviking_manage_watch(...)`: 动态创建或调整资源监听策略；
- `openviking_reindex(uri: str = "viking://resources/")`: 强制重建指定路径的向量与语义索引；
- `openviking_consistency()`: 物理存储与向量索引一致性审计与自愈；
- `openviking_observer()`: 查看观察者性能采样与事件流水线；
- `openviking_metrics()`: 导出 Prometheus/OpenTelemetry 监控指标；
- `openviking_privacy()`: 租户数据隐私边界与脱敏隔离状态探测；
- `openviking_harness_stats()`: 查看 DSH 客户端与宿主进程资源占用、Token 吞吐指标；
- `openviking_usage_stats()`: 租户调用次数、配额消耗与成本分摊统计；
- `openviking_server_init()`: 首次部署初始化系统目录与系统基线；
- `openviking_server_control(action: "restart"|"reload"|"status")`: 服务端守护进程控制；
- `openviking_backup(...)`: 全量/增量冷备导出；
- `openviking_restore(...)`: 灾难恢复与快照导入；
- `openviking_ping()`: 极速存活与网络延迟探测。

## 四、经典运维 SOP
1. **健康体检**：进入会话首先调用 `openviking_server_doctor()` 与 `openviking_system_status()` 获取全局大盘；
2. **死信诊断**：检查 DLQ 队列，排查失败任务；若索引落后，调用 `openviking_reindex()` 重建。
