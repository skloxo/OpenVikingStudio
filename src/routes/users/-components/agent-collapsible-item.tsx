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

  // 网络端点物理双轨：同时提供同机内网与跨网公网两个端点，消除切换与输入认知成本
  const localMcpUrl = `http://127.0.0.1:1933/mcp?agent_id=${encodeURIComponent(agent.agent_id)}&user_id=${encodeURIComponent(userId)}`
  const publicMcpUrl = `https://vk.tide.red/mcp?agent_id=${encodeURIComponent(agent.agent_id)}&user_id=${encodeURIComponent(userId)}`
  const dshPluginTarballUrl = 'https://vk.tide.red/studio/dsh-plugin-openviking-1.3.0.tgz'

  const dshYamlSnippet = React.useMemo(() => `- id: mcp-openviking
  name: "@deepseek-ai/dsh-mcp-client"
  config:
    serverName: openviking
    transport: streamable-http
    url: "${publicMcpUrl}"
    headers:
      Authorization: "Bearer <OPENVIKING_API_KEY>"
    reconnect:
      enabled: true

- id: openviking-hook
  name: dsh-plugin-openviking
  config:
    api: "${publicMcpUrl.split('/mcp')[0]}"
    peer: "${agent.agent_id}"
    autoRecall: ${hookAutoRecall}
    autoCapture: ${hookAutoCapture}
    preToolGuard: ${hookPreToolGuard}`, [publicMcpUrl, agent.agent_id, hookAutoRecall, hookAutoCapture, hookPreToolGuard])

  const universalPromptSnippet = React.useMemo(() => {
    const roleTitle = isMasterBundle ? '🧠 中枢总控角色 (47项全特权工具)' : '🛰️ 卫星工兵角色 (31项一线业务工具)'
    const hookItems = [
      hookAutoRecall ? '✅ 已开启「先验记忆自动预取」：优先调用 `find` 向体外大脑检索' : '⚪ 未开启先验记忆预取',
      hookAutoCapture ? '✅ 已开启「轮次经验自动沉淀」：排障后主动调用 `record_lesson`' : '⚪ 未开启轮次经验沉淀',
      hookPreToolGuard ? '✅ 已开启「工具前置安全守卫」：严禁越权或泄露敏感 Key' : '⚪ 未开启工具前置守卫',
    ].join('\n  - ')

    return `# OpenViking 智能体认主与接入协议 (Universal Agent Prompt)
你是已在 OpenViking 认证在籍的智能体。请读取并严格遵守以下契约：
- 智能体 ID: \`${agent.agent_id}\` | 所属用户: \`${userId}\` | 角色: ${roleTitle}
- 内网端点: \`${localMcpUrl}\` | 公网端点: \`${publicMcpUrl}\`
- 鉴权契约: User Key + Agent ID 绑定校验 (Header: \`Authorization: Bearer \${OPENVIKING_API_KEY}\`)
## Hook 规则:
  - ${hookItems}
## 绝对工程红线:
1. 视觉字号 >= 12px (text-xs)，NO GREEN EVER 🚫；
2. 单文件严守 100~300 行黄金甜点区，硬上限 <= 500 行；`
  }, [agent.agent_id, userId, isMasterBundle, localMcpUrl, publicMcpUrl, hookAutoRecall, hookAutoCapture, hookPreToolGuard])

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
                智能体接入方案 (提供同机内网与跨网公网双端点)
              </span>
              <span className="text-muted-foreground text-xs font-mono">
                统一鉴权: User Key + Agent ID 绑定校验
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {/* 场景 1：DeepSeek Harness (DSH 插件/MCP 接入) */}
              <div className="rounded-lg border border-border/60 bg-muted/15 p-3 space-y-2.5 flex flex-col justify-between">
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-foreground flex items-center gap-1.5 text-xs">
                      <ZapIcon className="size-3.5 text-cyan-500" />
                      方案一：DSH 客户端一体化套件 (GUI 表单)
                    </span>
                    <Badge variant="outline" className="text-xs font-mono h-4 px-1 border-border/60">
                      DSH 客户端
                    </Badge>
                  </div>

                  {/* 步骤 1：插件一键安装包 (tarball) */}
                  <div className="rounded border border-cyan-500/30 bg-cyan-500/5 p-2 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-foreground text-xs flex items-center gap-1">
                        📦 步骤 1：复制插件安装包链接 (.tgz)
                      </span>
                      <button
                        type="button"
                        onClick={(e) => handleCopy(dshPluginTarballUrl, 'DSH 插件安装链接', e)}
                        className="text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-1 text-xs font-medium cursor-pointer"
                        title="复制可直接贴入 DSH「添加插件」的安装包链接"
                      >
                        <CopyIcon className="size-3" />
                        一键复制
                      </button>
                    </div>
                    <div className="text-xs text-muted-foreground truncate font-mono bg-background/60 px-1.5 py-0.5 rounded border border-border/30">
                      {dshPluginTarballUrl}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      打开 DSH 客户端 → 插件 → 添加插件 → 粘贴此链接，点击「安装」即可。
                    </div>
                  </div>

                  {/* 步骤 2：在 DSH 设置中填入本工兵身份 */}
                  <div className="space-y-1 font-mono text-xs bg-background/80 p-2 rounded border border-border/40">
                    <div className="text-xs text-muted-foreground font-sans">
                      ⚙️ 步骤 2：在 DSH「设置 → OpenViking」填入以下专属身份：
                    </div>
                    <div className="flex items-center justify-between pt-1 border-t border-border/30">
                      <span className="text-muted-foreground">智能体工兵 ID (agentId):</span>
                      <div className="flex items-center gap-1">
                        <span className="text-foreground font-semibold">{agent.agent_id}</span>
                        <button type="button" onClick={(e) => handleCopy(agent.agent_id, '工兵 ID', e)} className="p-0.5 hover:text-foreground cursor-pointer" title="复制工兵 ID">
                          <CopyIcon className="size-3 text-cyan-600" />
                        </button>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">服务端点 (apiUrl):</span>
                      <span className="text-foreground">https://vk.tide.red</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">用户认证 (apiKey):</span>
                      <span className="text-foreground">个人中心 User Key</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 pt-1 border-t border-border/30">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="h-7 text-xs flex-1 text-cyan-600 border-cyan-500/40 hover:bg-cyan-500/10 font-medium px-1"
                    onClick={(e) => handleCopy(dshPluginTarballUrl, 'DSH 插件安装链接', e)}
                    title="复制可以直接贴入 DSH「添加插件」的安装包链接"
                  >
                    <CopyIcon className="size-3 mr-1" />
                    插件链接
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="h-7 text-xs flex-1 text-cyan-600 border-cyan-500/40 hover:bg-cyan-500/10 font-medium px-1"
                    onClick={(e) => handleCopy(publicMcpUrl, '跨网公网端点 URL', e)}
                    title="复制跨网公网 URL (vk.tide.red)"
                  >
                    <CopyIcon className="size-3 mr-1" />
                    公网 URL
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="h-7 text-xs flex-1 text-foreground border-border hover:bg-muted px-1"
                    onClick={(e) => handleCopy(dshYamlSnippet, 'DSH 一体化 Patch (YAML)', e)}
                    title="复制可直接贴入 cordis.patch.yml 的 YAML 配置"
                  >
                    <CopyIcon className="size-3 mr-1" />
                    复制 YAML
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
