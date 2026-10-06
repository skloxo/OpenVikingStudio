/**
 * agent-collapsible-item.tsx
 * 单个智能体原位折叠展开面板 (Collapsible Item)。
 * 彻底切除字体重叠、排版挤压与跳页。全面整合 47 个 FastMCP 工具与 HOOK 生命周期契约。
 */
import {
  CheckSquareIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  CopyIcon,
  GlobeIcon,
  LaptopIcon,
  RotateCcwIcon,
  SaveIcon,
  ShieldCheckIcon,
  SquareIcon,
  TerminalIcon,
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
import { ALL_TOOL_IDS } from '../-constants/agent-tools'

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
  const initialMode =
    agent.connection_mode === 'realtimeApi' ||
    agent.connection_mode === 'local' ||
    agent.agent_id.includes('2080ti')
      ? 'realtimeApi'
      : 'apiClient'
  const [connectionMode, setConnectionMode] = React.useState<'realtimeApi' | 'apiClient'>(initialMode)
  const [publicGatewayUrl, setPublicGatewayUrl] = React.useState<string>(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('ov_public_gateway_url') || 'https://vk.tide.red'
    }
    return 'https://vk.tide.red'
  })

  // Hook 核心生命周期控制状态 (可显式勾选配置)
  const [hookAutoRecall, setHookAutoRecall] = React.useState(true)
  const [hookAutoCapture, setHookAutoCapture] = React.useState(true)
  const [hookPreToolGuard, setHookPreToolGuard] = React.useState(true)

  React.useEffect(() => {
    setName(agent.agent_name || '')
    setRoleDesc(agent.role_desc || '')
    setSelectedTools(agent.allowed_tools)
    const mode =
      agent.connection_mode === 'realtimeApi' ||
      agent.connection_mode === 'local' ||
      agent.agent_id.includes('2080ti')
        ? 'realtimeApi'
        : 'apiClient'
    setConnectionMode(mode)
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
    if (typeof window !== 'undefined' && publicGatewayUrl.trim()) {
      localStorage.setItem('ov_public_gateway_url', publicGatewayUrl.trim())
    }
    onUpdate(agent.agent_id, {
      agent_name: name.trim() || undefined,
      role_desc: roleDesc.trim() || undefined,
      connection_mode: connectionMode,
      allowed_tools: selectedTools,
    })
  }

  const isLocal = connectionMode === 'realtimeApi'
  const isActive = agent.status === 'active'
  const validToolCount = agent.allowed_tools.includes('*')
    ? ALL_TOOL_IDS.length
    : agent.allowed_tools.filter((id) => ALL_TOOL_IDS.includes(id)).length

  const localOrigin =
    typeof window !== 'undefined' && window.location.origin.includes('localhost')
      ? window.location.origin
      : 'http://127.0.0.1:1933'
  const cleanPublicGateway = (publicGatewayUrl.trim() || 'https://vk.tide.red').replace(/\/+$/, '')
  const activeBaseUrl = isLocal ? localOrigin : cleanPublicGateway

  const mcpUrl = `${activeBaseUrl}/mcp?agent_id=${encodeURIComponent(agent.agent_id)}&user_id=${encodeURIComponent(userId)}`

  const clientConfigSnippet = JSON.stringify(
    {
      mcpServers: {
        openviking: {
          url: mcpUrl,
          type: 'streamable-http',
          headers: {
            'X-OpenViking-Agent': agent.agent_id,
            'X-OpenViking-User': userId,
            ...(!isLocal ? { Authorization: 'Bearer ${OPENVIKING_API_KEY}' } : {}),
          },
        },
      },
    },
    null,
    2,
  )

  const hookConfigSnippet = JSON.stringify(
    {
      openviking: {
        serverUrl: activeBaseUrl,
        agentId: agent.agent_id,
        userId: userId,
        mode: isLocal ? 'local_direct' : 'remote_gateway',
        hooks: {
          autoRecall: { event: 'UserPromptSubmit', enabled: hookAutoRecall },
          autoCapture: { event: 'afterTurn', enabled: hookAutoCapture },
          preToolGuard: { event: 'PreToolUse', enabled: hookPreToolGuard },
        },
      },
    },
    null,
    2,
  )

  const unifiedPluginConfigSnippet = JSON.stringify(
    {
      name: 'dsh-plugin-openviking',
      serverName: 'openviking',
      transport: 'streamable-http',
      url: mcpUrl,
      headers: {
        'X-OpenViking-Agent-ID': agent.agent_id,
        'X-OpenViking-User': userId,
        'Authorization': 'Bearer ${OPENVIKING_API_KEY}',
      },
      hooks: {
        autoRecall: hookAutoRecall,
        autoCapture: hookAutoCapture,
        preToolGuard: hookPreToolGuard,
      },
    },
    null,
    2,
  )

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

        {/* 第二行：身份证 ID 芯片 + 拓扑 Badge + 工具数 Badge + 消息统计 */}
        <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-border/20 text-xs font-mono">
          <div className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-background/80 border border-border/50 text-foreground">
            <span className="text-muted-foreground">ID:</span>
            <span>{agent.agent_id}</span>
            <button
              type="button"
              className="hover:text-foreground p-0.5"
              onClick={(e) => handleCopy(agent.agent_id, '永久身份证 ID', e)}
              title="复制永久身份证 ID"
            >
              <CopyIcon className="size-3 text-muted-foreground hover:text-foreground" />
            </button>
          </div>

          <Badge variant="outline" className="text-xs h-5 px-1.5 gap-1 border-border/60">
            {isLocal ? (
              <LaptopIcon className="size-2.5 text-cyan-500" />
            ) : (
              <GlobeIcon className="size-2.5 text-cyan-500" />
            )}
            {isLocal ? '本地直连 (2080Ti)' : '网络远程 (3070)'}
          </Badge>

          <Badge variant="outline" className="text-xs h-5 px-1.5 gap-1 border-border/60">
            <ShieldCheckIcon className="size-2.5 text-cyan-500" />
            {validToolCount} / {ALL_TOOL_IDS.length} 项工具
          </Badge>

          <span className="text-muted-foreground ml-auto tabular-nums">
            {agent.total_messages} 条消息
          </span>
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

            {/* 网络拓扑方式选择 (本地环境 2080Ti vs 公网模式 3070) */}
            <div className="sm:col-span-2 space-y-1.5 p-2.5 rounded-md border border-border/50 bg-muted/20">
              <div className="flex items-center justify-between">
                <Label className="text-xs font-medium text-foreground flex items-center gap-1.5">
                  <GlobeIcon className="size-3 text-cyan-500" />
                  网络拓扑接入模式 (支持随时切换)
                </Label>
                <span className="text-xs font-mono text-muted-foreground">
                  {isLocal ? '本机直连 · 127.0.0.1:1933' : '公网中继 · FRP 穿透'}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setConnectionMode('realtimeApi')}
                  className={`p-2 rounded border text-left transition-colors cursor-pointer ${
                    connectionMode === 'realtimeApi'
                      ? 'border-cyan-500 bg-cyan-500/10 text-foreground font-medium shadow-xs'
                      : 'border-border/60 bg-background text-muted-foreground hover:bg-muted/30'
                  }`}
                >
                  <div className="flex items-center gap-1 text-xs">
                    <LaptopIcon className="size-3 text-cyan-500" />
                    <span>本地宿主直连</span>
                    <span className="text-xs text-cyan-600 dark:text-cyan-400 font-mono ml-auto">2080Ti / 本机</span>
                  </div>
                  <div className="text-xs text-muted-foreground mt-0.5">
                    智能体与中枢同机/局域网，直连 127.0.0.1:1933
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setConnectionMode('apiClient')}
                  className={`p-2 rounded border text-left transition-colors cursor-pointer ${
                    connectionMode === 'apiClient'
                      ? 'border-cyan-500 bg-cyan-500/10 text-foreground font-medium shadow-xs'
                      : 'border-border/60 bg-background text-muted-foreground hover:bg-muted/30'
                  }`}
                >
                  <div className="flex items-center gap-1 text-xs">
                    <GlobeIcon className="size-3 text-cyan-500" />
                    <span>公网远程模式</span>
                    <span className="text-xs text-cyan-600 dark:text-cyan-400 font-mono ml-auto">3070 / 工位</span>
                  </div>
                  <div className="text-xs text-muted-foreground mt-0.5">
                    跨公网卫星节点，通过 FRP 穿透或公网网关连接
                  </div>
                </button>
              </div>

              {/* 公网模式下展开公网 Base URL 配置 */}
              {!isLocal && (
                <div className="pt-2 border-t border-border/30 space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">公网端点 Base URL (3070 等远程工位节点使用):</span>
                    <button
                      type="button"
                      className="text-xs text-cyan-600 hover:underline cursor-pointer"
                      onClick={() => setPublicGatewayUrl('https://vk.tide.red')}
                    >
                      重置默认 (vk.tide.red)
                    </button>
                  </div>
                  <Input
                    value={publicGatewayUrl}
                    onChange={(e) => setPublicGatewayUrl(e.target.value)}
                    placeholder="例如 https://vk.tide.red 或 FRP 穿透端点"
                    className="h-7 text-xs font-mono bg-background"
                  />
                </div>
              )}
            </div>

            {/* 独立 ID 卡片，两行自解释，绝无重叠 */}
            <div className="sm:col-span-2 rounded-md border border-border/50 bg-muted/20 p-2.5 space-y-1.5">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>系统唯一永久身份证 (ID)</span>
                <span className="font-mono text-xs">永久锁定 · MCP / HOOK 鉴权凭据</span>
              </div>
              <div className="flex items-center justify-between gap-2">
                <code className="font-mono text-xs font-semibold text-foreground px-2 py-0.5 rounded bg-background border border-border/60 select-all">
                  {agent.agent_id}
                </code>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  className="h-6 text-xs px-2 text-cyan-600 hover:bg-cyan-500/10"
                  onClick={(e) => handleCopy(agent.agent_id, '永久身份证 ID', e)}
                >
                  <CopyIcon className="size-3 mr-1" /> 复制 ID
                </Button>
              </div>
            </div>
          </div>

          {/* 工具授权矩阵 (Tool ACL) */}
          <ToolACLMatrix
            selectedTools={selectedTools}
            onChange={setSelectedTools}
            disabled={isUpdating}
            userRole={userRole}
          />

          {/* 被动 Hook 核心生命周期控制卡片 (可显式勾选配置) */}
          <div className="space-y-2 pt-2 border-t border-border/40">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-foreground flex items-center gap-1.5">
                <ShieldCheckIcon className="size-3.5 text-cyan-500" />
                Hook 核心生命周期与被动注入控制
              </span>
              <span className="text-xs text-muted-foreground font-mono">
                已启用 {[hookAutoRecall, hookAutoCapture, hookPreToolGuard].filter(Boolean).length} / 3 项被动钩子
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {/* 1. 先验记忆自动预取 */}
              <div
                onClick={() => setHookAutoRecall(!hookAutoRecall)}
                className={`p-2.5 rounded-md border text-left transition-all cursor-pointer select-none space-y-1 ${
                  hookAutoRecall
                    ? 'border-cyan-500/60 bg-cyan-500/10 text-foreground'
                    : 'border-border/60 bg-muted/10 text-muted-foreground hover:bg-muted/20'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 font-medium text-xs">
                    {hookAutoRecall ? (
                      <CheckSquareIcon className="size-3.5 text-cyan-500" />
                    ) : (
                      <SquareIcon className="size-3.5 text-muted-foreground" />
                    )}
                    <span>🧠 先验记忆自动预取</span>
                  </div>
                  <Badge variant="outline" className="text-xs font-mono h-4 px-1">
                    Prompt 前置
                  </Badge>
                </div>
                <div className="text-xs text-muted-foreground">
                  模型组装提示词前，自动从体外大脑检索相关经验注入 System Prompt
                </div>
              </div>

              {/* 2. 轮次经验自动沉淀 */}
              <div
                onClick={() => setHookAutoCapture(!hookAutoCapture)}
                className={`p-2.5 rounded-md border text-left transition-all cursor-pointer select-none space-y-1 ${
                  hookAutoCapture
                    ? 'border-cyan-500/60 bg-cyan-500/10 text-foreground'
                    : 'border-border/60 bg-muted/10 text-muted-foreground hover:bg-muted/20'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 font-medium text-xs">
                    {hookAutoCapture ? (
                      <CheckSquareIcon className="size-3.5 text-cyan-500" />
                    ) : (
                      <SquareIcon className="size-3.5 text-muted-foreground" />
                    )}
                    <span>📥 轮次经验自动沉淀</span>
                  </div>
                  <Badge variant="outline" className="text-xs font-mono h-4 px-1">
                    对话后置
                  </Badge>
                </div>
                <div className="text-xs text-muted-foreground">
                  单轮会话结束后，自动捕获助手输出的新结论与踩坑事实并入库
                </div>
              </div>

              {/* 3. 工具前置安全守卫 */}
              <div
                onClick={() => setHookPreToolGuard(!hookPreToolGuard)}
                className={`p-2.5 rounded-md border text-left transition-all cursor-pointer select-none space-y-1 ${
                  hookPreToolGuard
                    ? 'border-cyan-500/60 bg-cyan-500/10 text-foreground'
                    : 'border-border/60 bg-muted/10 text-muted-foreground hover:bg-muted/20'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 font-medium text-xs">
                    {hookPreToolGuard ? (
                      <CheckSquareIcon className="size-3.5 text-cyan-500" />
                    ) : (
                      <SquareIcon className="size-3.5 text-muted-foreground" />
                    )}
                    <span>🛡️ 工具前置安全守卫</span>
                  </div>
                  <Badge variant="outline" className="text-xs font-mono h-4 px-1">
                    工具拦截
                  </Badge>
                </div>
                <div className="text-xs text-muted-foreground">
                  工具执行前拦截敏感 Key 泄露、检测目标路径越权，确保安全沙箱
                </div>
              </div>
            </div>
          </div>

          {/* 统一整合：FastMCP 工具端点 + HOOK 生命周期插件 */}
          <div className="space-y-2 pt-2 border-t border-border/40">
            <span className="font-semibold text-foreground flex items-center gap-1.5">
              <ZapIcon className="size-3.5 text-cyan-500" />
              中枢接入与 MCP + HOOK 一体化整合
            </span>

            <div className="rounded border border-border/40 bg-background p-2.5 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <TerminalIcon className="size-3 text-cyan-500" />
                  <span>FastMCP 专属端点 (Streamable HTTP):</span>
                </div>
                <div className="flex items-center gap-1">
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    className="h-6 px-1.5 text-xs text-cyan-600 hover:bg-cyan-500/10 font-semibold"
                    onClick={(e) => handleCopy(unifiedPluginConfigSnippet, 'DSH 一体化插件整合配置', e)}
                    title="复制 MCP + Hook 合二为一的完整 DSH 插件配置"
                  >
                    <CopyIcon className="size-3 mr-1" />
                    复制一体化插件配置
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    className="h-6 px-1.5 text-xs text-cyan-600 hover:bg-cyan-500/10"
                    onClick={(e) => handleCopy(mcpUrl, 'FastMCP 链接', e)}
                  >
                    <CopyIcon className="size-3 mr-1" />
                    复制 URL
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground"
                    onClick={(e) => handleCopy(clientConfigSnippet, '客户端 MCP JSON', e)}
                  >
                    <CopyIcon className="size-3 mr-1" />
                    独立 MCP 配置
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground"
                    onClick={(e) => handleCopy(hookConfigSnippet, 'HOOK 生命周期配置', e)}
                  >
                    <CopyIcon className="size-3 mr-1" />
                    独立 Hook 配置
                  </Button>
                </div>
              </div>
              <code className="font-mono text-xs block p-1.5 rounded bg-muted/30 select-all truncate">
                {mcpUrl}
              </code>
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
