import type { PluginCapability } from '../capability-bundles'

export const vaultPlugin: PluginCapability = {
  pluginId: 'keepass-vault',
  name: 'KeePass 凭据保险箱插件',
  version: '1.0.1',
  description: '本地私有凭据管理插件 (云端零密码存储，客户端本地直接挂载 KDBX 数据文件)',
  totalTools: 9,
  skill: {
    name: 'keepass-vault',
    summary: '全集群凭据唯一真实源规范，要求 Agent 遇到外部鉴权强制先查库、严禁索要或明文输出密码。',
    chapters: [
      { title: '第 1 章：查库第一性公理', summary: '遇到服务器登录或 API 鉴权，强制调用 keepass_get，严禁询问用户。' },
      { title: '第 2 章：高熵密码生成与写盘', summary: '批量注册或改密时自动生成 ≥20 位高熵密码，并实时安全回写归档。' },
      { title: '第 3 章：写前自动快照容灾', summary: '任何写操作前底层自动生成 .bak 快照，保障物理库绝对零丢失。' },
    ],
  },
  gui: {
    name: '本地私有凭据托管展厅',
    cloudConfigSummary: '云端控制台仅提供官方展厅展示、不可变插件包托管下载与配置引导，绝不集中存储或远程传输用户私有密码库。',
    clientDialogSummary: '智能体客户端直接在本地通过 keepassxc-cli 解密用户本机的 .kdbx 数据库文件，密码数据 100% 留存本地。',
  },
  hooks: [
    {
      id: 'vault_guard_hook',
      name: '写前防抖物理快照',
      triggerEvent: 'before_vault_write',
      description: '任何凭据增删改前自动生成 *.bak 快照防抖备份',
      defaultEnabled: true,
    },
  ],
  bundles: [
    {
      id: 'vault-read',
      name: '凭据安全只读包',
      roleType: 'consumer',
      description: '条目模糊搜索、明文安全解密、凭据拓扑树与保险箱探针',
      icon: 'key',
      toolIds: ['keepass_get', 'keepass_search', 'keepass_list_tree', 'keepass_status', 'keepass_export_attachment'],
      tools: [
        { id: 'keepass_get', name: 'keepass_get', description: '安全读取指定凭据条目' },
        { id: 'keepass_search', name: 'keepass_search', description: '模糊搜索凭据条目与账号' },
        { id: 'keepass_list_tree', name: 'keepass_list_tree', description: '获取凭据分组拓扑树' },
        { id: 'keepass_status', name: 'keepass_status', description: '凭据库解锁与健康状态' },
        { id: 'keepass_export_attachment', name: 'keepass_export_attachment', description: '安全导出私钥或证书附件' },
      ],
    },
    {
      id: 'vault-manage',
      name: '凭据治理运维包',
      roleType: 'ops',
      description: '高熵新建凭据、属性修改、条目废弃与弱密健康审计 (敏感)',
      icon: 'shield-check',
      requiredRole: 'admin',
      toolIds: ['keepass_add', 'keepass_edit', 'keepass_rm', 'keepass_analyze'],
      tools: [
        { id: 'keepass_add', name: 'keepass_add', description: '高熵新建凭据条目' },
        { id: 'keepass_edit', name: 'keepass_edit', description: '更新已有凭据属性' },
        { id: 'keepass_rm', name: 'keepass_rm', description: '安全废弃或删除凭据', isDangerous: true },
        { id: 'keepass_analyze', name: 'keepass_analyze', description: '弱密与重复密码健康审计' },
      ],
    },
  ],
}
