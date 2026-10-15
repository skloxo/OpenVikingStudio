/**
 * capability-bundles.ts
 * 智能体中心角色工具包 (Capability Bundles) 与官方标杆 Quad 插件规约单一真实源 (SSOT)。
 *
 * 核心架构哲学：
 * 1. 客户端通信桥梁 (dsh-plugin-openviking) 独立打包托管，供外部智能体安装通道；
 * 2. 服务端真实内置 Quad 插件体系：
 *    - openviking-memory (34战地工具, 3 Hook, 记忆检索与代码感知完全体)；
 *    - openviking-ops (17系统运维工具, 2 Hook, 哨兵巡检与底座自愈)；
 *    - network-search (13工具, 3 Hook, 26-Key 轮询与全网采集)；
 *    - keepass-vault (9工具, 1 Hook, 密码凭据单一真实源)；
 *    - dify (12工具, 2 Hook, 智能体与工作流中枢)；
 *    - cpa-squad (2工具, 2 Hook, CPA跨模型算力协同)；
 *    - fleet-mesh (2工具, 1 Hook, 卫星集群同频运维)；
 * 3. “四位一体 (Quad)”架构：每个插件均具备【① 技能导轨 + ② Hook 拦截 + ③ MCP 角色包 + ④ GUI 视窗】；
 * 4. 模块化解耦：单文件行数严格控制在 100~300 行黄金甜点区，子插件在 ./plugins/ 独立治理。
 */

import { memoryPlugin } from './plugins/memory-plugin'
import { opsPlugin } from './plugins/ops-plugin'
import { searchPlugin } from './plugins/search-plugin'
import { vaultPlugin } from './plugins/vault-plugin'
import { difyPlugin } from './plugins/dify-plugin'
import { cpaPlugin } from './plugins/cpa-plugin'
import { fleetPlugin } from './plugins/fleet-plugin'

export type ToolItem = {
  id: string
  name: string
  description: string
  isDangerous?: boolean
}

export type ToolBundle = {
  id: string
  name: string
  roleType: 'consumer' | 'ops'
  description: string
  icon: string
  requiredRole?: 'admin' | 'root'
  toolIds: string[]
  tools: ToolItem[]
}

export type HookItem = {
  id: string
  name: string
  description: string
  triggerEvent: string
  defaultEnabled?: boolean
}

export type PluginSkill = {
  name: string
  chapters: { title: string; summary: string }[]
  summary: string
}

export type PluginGui = {
  name: string
  cloudConfigSummary: string
  clientDialogSummary: string
}

export type PluginCapability = {
  pluginId: string
  name: string
  version: string
  description: string
  totalTools: number
  // 四位一体固定四大支柱
  bundles: ToolBundle[] // 1. MCP 工具包
  hooks: HookItem[] // 2. 钩子 (Hook)
  skill?: PluginSkill // 3. 技能 (Skill)
  gui?: PluginGui // 4. 插件的 GUI
}

export type ClientBridgePackageInfo = {
  packageName: string
  version: string
  packageUrl: string
  installCommand: string
}

/**
 * 实时从服务端动态获取最新客户端通道桥包信息 (单一真实源 SSOT)。
 * 坚决杜绝依赖静态编译常量或页面加载初期的过时缓存。
 */
export async function fetchLatestClientBridge(
  networkMode: 'local' | 'public' = 'public'
): Promise<ClientBridgePackageInfo> {
  const baseUrl = networkMode === 'local' ? 'http://127.0.0.1:1933' : 'https://vk.tide.red'
  try {
    const timestamp = Date.now()
    const res = await fetch(`/api/v1/plugins/bridge/client-package?_t=${timestamp}`, {
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        Pragma: 'no-cache',
      },
    })
    if (res.ok) {
      const data = await res.json()
      const ver = data?.result?.version || '1.5.2'
      const pkgName = data?.result?.package_name || 'dsh-plugin-openviking'
      const pkgFile = data?.result?.package_file || `${pkgName}-${ver}.tgz`
      const pkgUrl = data?.result?.package_url || `${baseUrl}/studio/${pkgFile}`
      const installCmd = data?.result?.install_command || `npm install ${pkgUrl}`
      return {
        packageName: pkgName,
        version: ver,
        packageUrl: pkgUrl,
        installCommand: installCmd,
      }
    }
  } catch (err) {
    console.error('Failed to fetch latest client bridge package info:', err)
  }
  const fallbackUrl = `${baseUrl}/studio/dsh-plugin-openviking-1.5.4.tgz`
  return {
    packageName: 'dsh-plugin-openviking',
    version: '1.5.4',
    packageUrl: fallbackUrl,
    installCommand: `npm install ${fallbackUrl}`,
  }
}

export const CLIENT_BRIDGE_META = {
  packageName: 'dsh-plugin-openviking',
  version: '1.5.4',
  downloadUrl: 'https://vk.tide.red/studio/dsh-plugin-openviking-1.5.4.tgz',
  description: '轻量客户端通信通道桥梁。安装到智能体本地环境后，通过 UserKey + AgentID 握手与服务端中心化官方插件动态交互。',
  installCommand: 'npm install https://vk.tide.red/studio/dsh-plugin-openviking-1.5.4.tgz',
}

/**
 * 官方标杆 Quad 插件全量能力清单 SSOT
 */
export const PLUGIN_CAPABILITIES: PluginCapability[] = [
  memoryPlugin,
  opsPlugin,
  searchPlugin,
  vaultPlugin,
  difyPlugin,
  cpaPlugin,
  fleetPlugin,
]
