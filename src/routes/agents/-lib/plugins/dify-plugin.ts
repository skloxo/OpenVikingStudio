import type { PluginCapability } from '../capability-bundles'

export const difyPlugin: PluginCapability = {
  pluginId: 'dify',
  name: 'Dify 智能体与工作流中枢',
  version: '1.0.0',
  description: '全生命周期可视化 AI 智能体编排与工作流中枢 (应用管理、DSL 导入导出、知识库检索引擎与模型提供商)',
  totalTools: 12,
  skill: {
    name: 'dify-ops',
    summary: '指导 Agent 调度 Dify 工作流执行、DSL 配置导入导出与知识库语义检索测试。',
    chapters: [
      { title: '第 1 章：应用检索与工作流调度', summary: '通过 dify_list_apps 与 dify_run_workflow 自动化触发编排任务。' },
      { title: '第 2 章：DSL 版本化规范归档', summary: '通过 export_dsl 与 import_dsl 实现工作流代码化版本受控。' },
      { title: '第 3 章：知识库检索与切片评测', summary: '通过 dify_search_dataset 执行 Hit-Testing 语义切片测试。' },
    ],
  },
  gui: {
    name: 'Dify 工作流与知识库配置中心',
    cloudConfigSummary: '集中配置 Dify 实例控制面 API 端点、Workspace 租户空间、管理员密钥与应用路由映射。',
    clientDialogSummary: '智能体客户端无缝感知已装配的工作流与知识库，直接通过 MCP 执行自动化任务。',
  },
  hooks: [
    {
      id: 'dify_execution_audit',
      name: '工作流入参合规审计',
      triggerEvent: 'before_workflow_run',
      description: '工作流触发前校验 inputs 契约与入参必填项',
      defaultEnabled: true,
    },
    {
      id: 'dify_dsl_backup_hook',
      name: 'DSL 覆写前自动备份',
      triggerEvent: 'before_dsl_import',
      description: '覆盖导入应用 DSL 前自动拉取当前版本归档备份',
      defaultEnabled: true,
    },
  ],
  bundles: [
    {
      id: 'dify-app-ops',
      name: '应用编排与工作流包',
      roleType: 'consumer',
      description: '应用检索、规范详情、DSL 导入导出、工作流触发与应用删除',
      icon: 'workflow',
      toolIds: ['dify_status', 'dify_list_apps', 'dify_get_app', 'dify_export_dsl', 'dify_import_dsl', 'dify_delete_app', 'dify_run_workflow'],
      tools: [
        { id: 'dify_status', name: 'dify_status', description: '检查 Dify 服务端连通状态与资产总览' },
        { id: 'dify_list_apps', name: 'dify_list_apps', description: '分页列出工作区内应用与工作流清单' },
        { id: 'dify_get_app', name: 'dify_get_app', description: '获取指定应用/工作流详细配置规格' },
        { id: 'dify_export_dsl', name: 'dify_export_dsl', description: '导出应用或工作流完整 YAML DSL 规范配置' },
        { id: 'dify_import_dsl', name: 'dify_import_dsl', description: '导入 YAML DSL 创建或覆盖更新应用' },
        { id: 'dify_delete_app', name: 'dify_delete_app', description: '按 UUID 物理删除指定应用 (高危)', isDangerous: true },
        { id: 'dify_run_workflow', name: 'dify_run_workflow', description: '传入参数触发执行指定工作流并捕获执行轨迹' },
      ],
    },
    {
      id: 'dify-kb-ops',
      name: '知识库与模型管理包',
      roleType: 'consumer',
      description: '知识库列表、高品质数据集创建、语义检索 Hit-Testing 与模型厂商',
      icon: 'database',
      toolIds: ['dify_list_datasets', 'dify_create_dataset', 'dify_delete_dataset', 'dify_search_dataset', 'dify_list_model_providers'],
      tools: [
        { id: 'dify_list_datasets', name: 'dify_list_datasets', description: '分页列出工作区内知识库数据集清单' },
        { id: 'dify_create_dataset', name: 'dify_create_dataset', description: '新建高品质知识库数据集' },
        { id: 'dify_delete_dataset', name: 'dify_delete_dataset', description: '按 UUID 物理删除指定知识库 (高危)', isDangerous: true },
        { id: 'dify_search_dataset', name: 'dify_search_dataset', description: '对指定知识库执行 Hit-Testing 语义测试检索' },
        { id: 'dify_list_model_providers', name: 'dify_list_model_providers', description: '列出工作区已配置模型提供商与凭据状态' },
      ],
    },
  ],
}
