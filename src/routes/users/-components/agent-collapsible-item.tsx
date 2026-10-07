/**
 * agent-collapsible-item.tsx
 * 单个智能体原位折叠展开面板 (Collapsible Item)。
 * 彻底切除字体重叠、排版挤压与跳页。全面整合 47 个 FastMCP 工具与 HOOK 生命周期契约。
 * 彻底切除硬编码的本地/公网模式选择，全面拥抱“角色工具包”与端点智能自适应！
 */
import {
  ChevronDownIcon,
  ChevronRightIcon,
  CopyIcon,
  CpuIcon,
  RadioIcon,
  RotateCcwIcon,
  SaveIcon,
  ShieldCheckIcon,
  SparklesIcon,
  Trash2Icon,
  ZapIcon,
} from 'lucide-react'
import * as React from 'react'
import { toast } from 'sonner'

import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { Label } from '#/components/ui/label'
import type { UpdateAgentInput, UserAgentItem } from '#/lib/admin'
import { ALL_TOOL_IDS, MASTER_MAINTAINER_TOOL_IDS } from '../-constants/agent-tools'

import { HookLifecycleMatrix } from './hook-lifecycle-matrix'
import { ToolACLMatrix } from './tool-acl-matrix'

export type AgentCollapsibleItemProps = {
  agent: UserAgentItem
  userId: string
  userRole?: string
  isExpanded: boolean
  onToggleExpand: () => void
  onUpdate: (agentId: string, input: UpdateAgentInput) => void
  onDelete: (agent: UserAgentItem) => void
  onActivate: (agentId: string) => void
  isUpdating: boolean
}

export function AgentCollapsibleItem({
  agent,
  userId,
  userRole = 'user',
  isExpanded,
  onToggleExpand,
  onUpdate,
  onDelete,
  onActivate,
  isUpdating,
}: AgentCollapsibleItemProps) {
  const [name, setName] = React.useState(agent.agent_name || '')
  const [roleDesc, setRoleDesc] = React.useState(agent.role_desc || '')
  const [selectedTools, setSelectedTools] = React.useState<string[]>(
    agent.allowed_tools,
  )

  // Hook 核心生命周期控制状态
  const [hookAutoRecall, setHookAutoRecall] = React.useState(true)
  const [hookAutoCapture, setHookAutoCapture] = React.useState(true)
  const [hookPreToolGuard, setHookPreToolGuard] = React.useState(true)

  React.useEffect(() => {
    setName(agent.agent_name || '')
    setRoleDesc(agent.role_desc || '')
    setSelectedTools(agent.allowed_tools)
  }, [agent])

  const handleCopy = async (text: string, label: string, e?: React.MouseEvent) => {
    e?.stopPropagation()
    try {
      await navigator.clipboard.writeText(text)
      toast.success(`已复制 ${label}`)
    } catch {
      toast.error('复制失败')
    }
  }

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault()
    onUpdate(agent.agent_id, {
      agent_name: name.trim() || undefined,
      role_desc: roleDesc.trim() || undefined,
      allowed_tools: selectedTools,
    })
  }

  const isActive = agent.status === 'active'
  const validToolCount = agent.allowed_tools.includes('*')
    ? ALL_TOOL_IDS.length
    : agent.allowed_tools.filter((id) => ALL_TOOL_IDS.includes(id)).length

  // 检测是否拥有中枢运维全量工具
  const isMasterBundle =
    agent.allowed_tools.includes('*') ||
    validToolCount >= MASTER_MAINTAINER_TOOL_IDS.length

  // 网络端点策略：初值根据访问宿主工程化自适应，支持显式胶囊秒级切换
  const defaultMode = React.useMemo<'local' | 'public'>(() => {
    if (typeof window !== 'undefined') {
      const h = window.location.hostname
      return (h === 'localhost' || h === '127.0.0.1') ? 'local' : 'public'
    }
    return 'public'
  }, [])
  const [endpointMode, setEndpointMode] = React.useState<'local' | 'public'>(defaultMode)
  const activeBaseUrl = endpointMode === 'local' ? 'http://127.0.0.1:1933' : 'https://vk.tide.red'

  const mcpUrl = `${activeBaseUrl}/mcp?agent_id=${encodeURIComponent(agent.agent_id)}&user_id=${encodeURIComponent(userId)}`

  const unifiedPluginConfigSnippet = React.useMemo(() => {
    return JSON.stringify({
      name: 'dsh-plugin-openviking',
      serverName: 'openviking',
      transport: 'streamable-http',
      url: mcpUrl,
      headers: {
        'X-OpenViking-Agent-ID': agent.agent_id,
        'X-OpenViking-User': userId,
        ...(endpointMode === 'public' ? { 'Authorization': 'Bearer ${OPENVIKING_API_KEY}' } : {}),
      },
      hooks: { autoRecall: hookAutoRecall, autoCapture: hookAutoCapture, preToolGuard: hookPreToolGuard },
    }, null, 2)
  }, [mcpUrl, agent.agent_id, userId, endpointMode, hookAutoRecall, hookAutoCapture, hookPreToolGuard])

  const universalPromptSnippet = React.useMemo(() => {
    const roleTitle = isMasterBundle
      ? '🧠 中枢总控角色 (47项全特权工具 + 底座治理)'
      : '🛰️ 卫星工兵角色 (31项一线业务工具 + 知识/AST/单测)'

    const hookItems = [
      hookAutoRecall ? '✅ 已开启「先验记忆自动预取」：优先调用 `find` 向体外大脑检索规范与历史经验；' : '⚪ 未开启先验记忆预取；',
      hookAutoCapture ? '✅ 已开启「轮次经验自动沉淀」：排障或得出重要结论后，主动调用 `record_lesson` 入库；' : '⚪ 未开启轮次经验沉淀；',
      hookPreToolGuard ? '✅ 已开启「工具前置安全守卫」：严禁越权或泄露敏感 Key，受控沙箱运行。' : '⚪ 未开启工具前置守卫。',
    ].join('\n  - ')

    const authDesc = endpointMode === 'local'
      ? '- **认证模式**: 同机内网直连（免 API Key，系统以 `agent_id` 身份证唯一识别）'
      : '- **认证模式**: 跨网公网（双重安全防护：`agent_id` 身份证 + 所属用户 API Key）\n- **Header**: `Authorization: Bearer ${OPENVIKING_API_KEY}` (请替换为所属用户实际的 API Key)'

    return `# OpenViking 智能体认主与接入协议 (Universal Agent Prompt)

你是已在 OpenViking 认证在籍的智能体。请读取并严格遵守以下身份凭据与行为契约：

## 一、 智能体凭证 (Identity Credentials)
- **智能体 ID**: \`${agent.agent_id}\`
- **智能体名称**: \`${agent.agent_name || agent.agent_id}\`
- **所属用户**: \`${userId}\`
- **角色定位**: ${roleTitle}
- **FastMCP 端点**: \`${mcpUrl}\`
${authDesc}

## 二、 Hook 核心反射弧规则
  - ${hookItems}

## 三、 绝对工程红线与规范
1. **代码审美与字号**：遵循高密冷淡设计规范，字号物理硬下限 >= 12px (text-xs)，NO GREEN EVER 🚫；
2. **单文件规模**：严守 100~300 行黄金甜点区，绝对物理硬上限 <= 500 行，违者主动拆解领域接缝；
3. **闭环留痕**：完成复杂迭代后，确保测试通过，版本一致并记录体外大脑。
`
  }, [agent.agent_id, agent.agent_name, userId, isMasterBundle, mcpUrl, endpointMode, hookAutoRecall, hookAutoCapture, hookPreToolGuard])

  return (
    <div
      className={`rounded-md border transition-all text-xs font-sans ${
        isExpanded
          ? 'border-cyan-500/50 bg-card shadow-xs'
          : 'border-border/60 bg-muted/10 hover:bg-muted/30'
      }`}
    >
      {/* 收起态结构：两行清晰布局，彻底消除挤压与重叠 */}
      <div
        className="p-3 cursor-pointer select-none space-y-2"
        onClick={onToggleExpand}
      >
        {/* 第一行：展开图标 + 名称 + 状态 + 快捷操作 */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <button
              type="button"
              className="p-0.5 text-muted-foreground hover:text-foreground shrink-0"
              title={isExpanded ? '收起详情' : '展开就地配置'}
            >
              {isExpanded ? (
                <ChevronDownIcon className="size-4 text-cyan-500" />
              ) : (
                <ChevronRightIcon className="size-4" />
              )}
            </button>

            <span className="font-semibold text-foreground text-sm truncate max-w-48 sm:max-w-64">
              {agent.agent_name || agent.agent_id}
            </span>

            <Badge
              variant="outline"
              className={`text-xs px-1.5 py-0 font-normal shrink-0 ${
                isActive
                  ? 'border-cyan-500/30 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400'
                  : 'border-muted-foreground/30 bg-muted text-muted-foreground'
              }`}
            >
              {isActive ? '在籍' : '已下线'}
            </Badge>
          </div>

          <div
            className="flex items-center gap-1 shrink-0"
            onClick={(e) => e.stopPropagation()}
          >
            {isActive ? (
              <Button
                type="button"
                size="icon-xs"
                variant="ghost"
                className="size-6 text-muted-foreground hover:text-rose-500 hover:bg-rose-500/10"
                onClick={() => onDelete(agent)}
                title="下线软删除"
              >
                <Trash2Icon className="size-3" />
              </Button>
            ) : (
              <Button
                type="button"
                size="icon-xs"
                variant="ghost"
                className="size-6 text-cyan-600 hover:bg-cyan-500/10"
                onClick={() => onActivate(agent.agent_id)}
                title="重新激活"
              >
                <RotateCcwIcon className="size-3" />
              </Button>
            )}
          </div>
        </div>

        {/* 第二行：身份证 ID 芯片 + 角色工具包 Badge + 工具数 Badge + 消息统计 */}
        <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-border/20 text-xs font-mono">
          <div className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-background/80 border border-border/50 text-foreground">
            <span className="text-muted-foreground">ID:</span>
            <span>{agent.agent_id}</span>
            <button type="button" className="hover:text-foreground p-0.5" onClick={(e) => handleCopy(agent.agent_id, '永久身份证 ID', e)} title="复制永久身份证 ID">
              <CopyIcon className="size-3 text-muted-foreground hover:text-foreground" />
            </button>
          </div>
          <Badge variant="outline" className="text-xs h-5 px-1.5 gap-1 border-border/60">
            {isMasterBundle ? <CpuIcon className="size-2.5 text-cyan-500" /> : <RadioIcon className="size-2.5 text-cyan-500" />}
            {isMasterBundle ? '🧠 中枢总控' : '🛰️ 卫星工兵'}
          </Badge>
          <Badge variant="outline" className="text-xs h-5 px-1.5 gap-1 border-border/60">
            <ShieldCheckIcon className="size-2.5 text-cyan-500" />
            {validToolCount}/{ALL_TOOL_IDS.length} 工具
          </Badge>
          <Badge variant="outline" className="text-xs h-5 px-1.5 gap-1 border-border/60">
            <ZapIcon className="size-2.5 text-cyan-500" />
            Hook {[hookAutoRecall, hookAutoCapture, hookPreToolGuard].filter(Boolean).length}/3
          </Badge>
          <span className="text-muted-foreground ml-auto tabular-nums">{agent.total_messages} 消息</span>
        </div>
      </div>

      {/* 展开态：就地原位编辑与接入配置面板 (Zero Jump, Pure In-place) */}
      {isExpanded && (
        <form onSubmit={handleSave} className="border-t border-border/50 p-4 space-y-4 bg-background/50">
          {/* 基本属性原位修改 */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs font-medium text-foreground">
                智能体名称 (自定义可改) <span className="text-rose-500">*</span>
              </Label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="例如 前端结对助手"
                className="h-7 text-xs bg-background"
              />
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-medium text-foreground">角色定位 / 职能描述</Label>
              <Input
                value={roleDesc}
                onChange={(e) => setRoleDesc(e.target.value)}
                placeholder="例如 自动化编译巡检、代码审查"
                className="h-7 text-xs bg-background"
              />
            </div>

            {/* 独立 ID 卡片，单行紧凑自解释 */}
            <div className="sm:col-span-2 rounded-md border border-border/50 bg-muted/20 p-2 flex items-center justify-between gap-2">
              <div className="text-xs text-muted-foreground flex items-center gap-1.5 truncate">
                <span>永久身份证 (ID):</span>
                <code className="font-mono text-xs font-semibold text-foreground px-1.5 py-0.5 rounded bg-background border border-border/60 select-all">{agent.agent_id}</code>
              </div>
              <Button type="button" size="sm" variant="ghost" className="h-6 text-xs px-2 text-cyan-600 hover:bg-cyan-500/10 shrink-0" onClick={(e) => handleCopy(agent.agent_id, '永久身份证 ID', e)}>
                <CopyIcon className="size-3 mr-1" /> 复制 ID
              </Button>
            </div>
          </div>

          {/* 工具授权矩阵 - 角色工具包驱动 */}
          <ToolACLMatrix
            selectedTools={selectedTools}
            onChange={setSelectedTools}
            disabled={isUpdating}
            userRole={userRole}
          />

          {/* Hook 核心生命周期与被动注入控制卡片 */}
          <HookLifecycleMatrix
            autoRecall={hookAutoRecall}
            onToggleAutoRecall={() => setHookAutoRecall(!hookAutoRecall)}
            autoCapture={hookAutoCapture}
            onToggleAutoCapture={() => setHookAutoCapture(!hookAutoCapture)}
            preToolGuard={hookPreToolGuard}
            onTogglePreToolGuard={() => setHookPreToolGuard(!hookPreToolGuard)}
            disabled={isUpdating}
          />

          {/* 接入与托底指令中心 (两大纯粹场景：DSH GUI 一键接入 vs 通用智能体认主提示词) */}
          <div className="space-y-2 pt-2 border-t border-border/40">
            <div className="flex flex-wrap items-center justify-between gap-1.5">
              <span className="font-semibold text-foreground flex items-center gap-1.5">
                <ZapIcon className="size-3.5 text-cyan-500" />
                智能体接入方案 (二选一极简落地)
              </span>
              <div className="flex items-center gap-1 bg-muted/40 p-0.5 rounded border border-border/40 font-mono text-xs">
                <button
                  type="button"
                  onClick={() => setEndpointMode('local')}
                  className={`px-1.5 py-0.5 rounded transition-colors ${
                    endpointMode === 'local'
                      ? 'bg-background text-cyan-600 dark:text-cyan-400 font-medium shadow-2xs'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                  title="同机 0 延迟直连，信任免 Key"
                >
                  🏠 同机内网
                </button>
                <button
                  type="button"
                  onClick={() => setEndpointMode('public')}
                  className={`px-1.5 py-0.5 rounded transition-colors ${
                    endpointMode === 'public'
                      ? 'bg-background text-cyan-600 dark:text-cyan-400 font-medium shadow-2xs'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                  title="跨网公网穿透，双重鉴权防护"
                >
                  🌐 跨网公网
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {/* 场景 1：DeepSeek Harness (DSH GUI 插件/MCP 图形化安装) */}
              <div className="rounded-lg border border-border/60 bg-muted/15 p-3 space-y-2.5 flex flex-col justify-between">
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-foreground flex items-center gap-1.5 text-xs">
                      <RadioIcon className="size-3.5 text-cyan-500" />
                      方案一：DSH GUI 图形化安装
                    </span>
                    <Badge variant="outline" className="text-xs font-mono h-4 px-1 border-border/60">
                      DSH 客户端
                    </Badge>
                  </div>
                  <div className="text-xs text-muted-foreground leading-relaxed">
                    在 DSH 客户端左下角点击「设置」➔「插件 / MCP」➔「添加服务器」，无需修改任何代码文件。
                  </div>

                  {/* 填写要素快速对照 */}
                  <div className="space-y-1 font-mono text-xs bg-background/80 p-2 rounded border border-border/40">
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">服务名称 (Name):</span>
                      <span className="text-foreground font-semibold">openviking</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">传输类型 (Type):</span>
                      <span className="text-foreground">streamable-http</span>
                    </div>
                    <div className="flex items-center justify-between gap-1">
                      <span className="text-muted-foreground shrink-0">端点 (URL):</span>
                      <span className="text-cyan-600 dark:text-cyan-400 truncate max-w-44 select-all" title={mcpUrl}>
                        {mcpUrl}
                      </span>
                    </div>
                    <div className="flex items-center justify-between gap-1 pt-0.5 border-t border-border/20">
                      <span className="text-muted-foreground shrink-0">鉴权模式:</span>
                      <span className="truncate text-foreground">
                        {endpointMode === 'local' ? (
                          <span className="text-cyan-600 dark:text-cyan-400 font-medium">免 Key (以 Agent ID 身份证认证)</span>
                        ) : (
                          <span className="text-amber-500 dark:text-amber-400">需带 Bearer {'<用户Key>'}</span>
                        )}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-1 border-t border-border/30">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="h-7 text-xs flex-1 text-cyan-600 border-cyan-500/40 hover:bg-cyan-500/10 font-medium"
                    onClick={(e) => handleCopy(mcpUrl, 'DSH MCP 端点 URL', e)}
                    title="复制用于 DSH GUI 输入框的端点 URL"
                  >
                    <CopyIcon className="size-3 mr-1" />
                    复制端点 URL
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="h-7 text-xs flex-1 text-foreground border-border hover:bg-muted"
                    onClick={(e) => handleCopy(unifiedPluginConfigSnippet, 'DSH 一体化插件 JSON', e)}
                    title="复制包含 Hook 的完整 DSH 插件配置"
                  >
                    <CopyIcon className="size-3 mr-1" />
                    复制插件 JSON
                  </Button>
                </div>
              </div>

              {/* 场景 2：通用智能体认主提示词 (直接复制发给 Agent 托底) */}
              <div className="rounded-lg border border-cyan-500/30 bg-cyan-500/5 p-3 space-y-2.5 flex flex-col justify-between">
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-foreground flex items-center gap-1.5 text-xs">
                      <SparklesIcon className="size-3.5 text-cyan-500" />
                      方案二：通用认主提示词 (一键托底)
                    </span>
                    <Badge variant="outline" className="text-xs font-mono h-4 px-1 border-cyan-500/40 text-cyan-600 dark:text-cyan-400">
                      Cursor / VSCode / Claude / 外部 Agent
                    </Badge>
                  </div>
                  <div className="text-xs text-muted-foreground leading-relaxed">
                    复制结构化提示词直接发给目标 Agent 的聊天框。智能体自动读懂身份 ID、MCP 接口与 Hook 规范，自行完成对接托底。
                  </div>

                  {/* 提示词要素卡片 */}
                  <div className="font-mono text-xs bg-background/80 p-2 rounded border border-border/40 text-muted-foreground space-y-0.5">
                    <div className="text-foreground font-medium flex items-center gap-1">
                      <ShieldCheckIcon className="size-3 text-cyan-500" />
                      已封装着籍 ID、FastMCP 端点与 Hook 契约
                    </div>
                    <div className="truncate">Agent: {agent.agent_id} ({agent.agent_name || '未命名'})</div>
                    <div className="truncate text-muted-foreground/80">包含先验检索、经验回传与单文件黄金甜点区规范</div>
                  </div>
                </div>

                <div className="pt-1 border-t border-border/30">
                  <Button
                    type="button"
                    size="sm"
                    className="h-7 text-xs w-full bg-cyan-600 hover:bg-cyan-500 text-white font-medium shadow-xs"
                    onClick={(e) => handleCopy(universalPromptSnippet, '通用智能体认主提示词', e)}
                    title="复制结构化 Prompt 直接发给目标 Agent 聊天框"
                  >
                    <CopyIcon className="size-3 mr-1" />
                    一键复制通用认主提示词 (直接发给 Agent)
                  </Button>
                </div>
              </div>
            </div>
          </div>

          {/* 底部就地操作栏 */}
          <div className="flex items-center justify-end gap-2 pt-2 border-t border-border/40">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 text-xs"
              onClick={onToggleExpand}
            >
              收起面板
            </Button>
            <Button
              type="submit"
              size="sm"
              className="h-7 text-xs"
              disabled={isUpdating}
            >
              <SaveIcon className="size-3 mr-1" />
              {isUpdating ? '保存中...' : '保存配置'}
            </Button>
          </div>
        </form>
      )}
    </div>
  )
}
