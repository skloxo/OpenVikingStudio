# 🌐 卫星集群同频运维说明书 (SKILL.md)

## 一、身份契约与能力定位
本机智能体已挂载跨节点卫星集群同频协调器，掌控集群内各物理机节点。
全系统共授权挂载 2 项跨机工具与 1 项 Hook 物理守卫。

## 二、集群物理节点拓扑
- **2080Ti (Local / Windows)**: 本地主宿主与开发机，承载本地 IDE 与核心代码仓；
- **RTX 3070 (Remote Windows)**: 远端 Windows 计算节点，承载 DSH 智能体执行环境；
- **Mac Studio (M3 Ultra)**: 远端 Unix 节点，承载高并发算力与本地模型加速。

## 三、跨机运维武器清单 (2 Tools SSOT)
- `openviking_fleet_check(target: Optional[str] = None)`: 跨物理机节点执行端到端健康体检与网络探活（支持 target='2080ti'/'3070'/'mac-studio' 或留空全量探测）；
- `openviking_fleet_sync(target: Optional[str] = None)`: 跨节点一键同频分发 AGENTS.md 规范、satellite_mcp_server.py、配置文件与凭据。

## 四、经典协同 SOP
1. **集群巡检**：调用 `openviking_fleet_check()` 自动探测所有可用卫星节点并生成健康矩阵；
2. **一键同频**：本地代码或规范更新后，调用 `openviking_fleet_sync()` 实现全集群一秒同频。
