import type { PluginCapability } from '../capability-bundles'

export const fleetPlugin: PluginCapability = {
  pluginId: 'fleet-mesh',
  name: '卫星集群同频运维插件',
  version: '1.0.0',
  description: '跨物理机节点（MacBook M3 / 宿主 PC / 云端 VPS）健康巡检与配置技能一键同频',
  totalTools: 2,
  skill: {
    name: 'satellite-fleet-ops',
    summary: '跨物理节点运行态巡检与配置技能一键同步同频规约。',
    chapters: [
      { title: '第 1 章：集群节点健康巡检', summary: '调用 openviking_fleet_check 检测集群各物理机心跳与负载。' },
      { title: '第 2 章：配置与技能同频同步', summary: '调用 openviking_fleet_sync 一键下发最新技能与环境配置。' },
    ],
  },
  gui: {
    name: '卫星集群拓扑与同频视窗',
    cloudConfigSummary: '直观呈现 MacBook M3、本地宿主与云端 VPS 的拓扑连通链路与同频版本。',
    clientDialogSummary: '智能体客户端透明执行节点自检并参与集群协同同频。',
  },
  hooks: [
    {
      id: 'fleet_heartbeat_sync_hook',
      name: '集群心跳与版本飘移预警',
      triggerEvent: 'before_fleet_sync',
      description: '定时检测多物理机版本哈希，感知技能落后时主动阻断',
      defaultEnabled: true,
    },
  ],
  bundles: [
    {
      id: 'fleet-mesh-core',
      name: '卫星集群同频包',
      roleType: 'ops',
      description: '跨节点健康度巡检与配置技能一键同频',
      icon: 'network',
      toolIds: ['openviking_fleet_check', 'openviking_fleet_sync'],
      tools: [
        { id: 'openviking_fleet_check', name: 'fleet_check', description: '卫星集群节点运行态健康体检' },
        { id: 'openviking_fleet_sync', name: 'fleet_sync', description: '跨节点配置与技能一键同频同步' },
      ],
    },
  ],
}
