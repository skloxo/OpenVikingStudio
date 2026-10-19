---
name: satellite-fleet-ops
description: OpenViking 卫星集群拓扑协同与同频运维专用技能。涵盖多节点体检巡检、健康对齐、版本漂移侦测与一键同频分发 SOP。
---

# 🛰️ 卫星集群运维管理技能 (Satellite Fleet Ops)

## 一、核心物理契约与第一性原理

1. **集群拓扑一等公民**：
   - OpenViking 采用分布式主从/对等拓扑（如主节点 Master 与边缘卫星节点 3070 远程客户端、2080Ti 本地节点）；
   - 严禁边缘节点配置产生漂移，必须与主节点全局规范时刻保持同频。

2. **巡检先于同步 (Inspect Before Sync)**：
   - 遇集群报错、403 或心跳超时，必须首先执行 `openviking_fleet_check` 采集各节点拓扑状态与版本指纹；
   - 确认漂移点后再调用 `openviking_fleet_sync` 分发最新服务端脚本与全局规范。

---

## 二、标准工具调用

1. **`openviking_fleet_check`**：
   - 巡检范围：`target_node='all'`、`'3070'`、`'2080ti'`
   - 返回指标：各节点的进程存活、端口连通、HTTP 延迟及 API 状态。

2. **`openviking_fleet_sync`**：
   - 目标节点：`target_node='all'`、`'3070'`、`'2080ti'`
   - 执行动作：分发最新 `satellite_mcp_server.py` 与 `AGENTS.md`，自动自愈 403 越权与配置漂移。
