/**
 * agent-bridge-onboarding.tsx
 * 客户端轻量通信通道桥 (Client RPC Bridge) 安装接入指引与三要素自动化配置组件。
 *
 * 遵循 Cockpit UI 视觉规范：
 * 1. 严格禁止使用绿色 🚫 (NO GREEN EVER)；
 * 2. 正常状态统一采用冰青 (cyan-500/cyan-400)；
 * 3. 字号物理硬下限 >= 12px (text-xs)；
 * 4. 三要素独立芯片直出，支持同机内网与跨网公网双端点自适应切换；
 * 5. 覆盖 DSH Cordis 插件、通用 MCP 客户端、认主 System Prompt 三大场景。
 */

import * as React from 'react'
import {
  AppWindowIcon,
  CopyIcon,
  GlobeIcon,
  HomeIcon,
  ServerIcon,
  SparklesIcon,
  TerminalIcon,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Label } from '#/components/ui/label'
import { fetchLatestClientBridge } from '../-lib/capability-bundles'
import type { ClientBridgePackageInfo } from '../-lib/capability-bundles'

export type AgentBridgeOnboardingProps = {
  agentId: string
  userId: string
  onCopy: (text: string, title: string, e?: React.MouseEvent) => void
}

type OnboardingTab = 'dsh-yaml' | 'mcp-json' | 'system-prompt'

export function AgentBridgeOnboarding({
  agentId,
  userId,
  onCopy,
}: AgentBridgeOnboardingProps) {
  // 端点网络环境切换 (同机内网 vs 跨网公网)
  const [networkMode, setNetworkMode] = React.useState<'local' | 'public'>('public')
  // 接入场景 Tab
  const [activeTab, setActiveTab] = React.useState<OnboardingTab>('dsh-yaml')

  // 动态客户端桥梁元数据
  const [liveBridgeMeta, setLiveBridgeMeta] = React.useState<ClientBridgePackageInfo | null>(null)

  const currentEndpointUrl = networkMode === 'local'
    ? 'http://127.0.0.1:1933/mcp'
    : 'https://vk.tide.red/mcp'

  // 挂载及切换网络时异步预取最新包信息
  React.useEffect(() => {
    let active = true
    fetchLatestClientBridge(networkMode).then((info) => {
      if (active) {
        setLiveBridgeMeta(info)
      }
    })
    return () => {
      active = false
    }
  }, [networkMode])

  const currentPackageName = liveBridgeMeta?.packageName || 'dsh-plugin-openviking'
  const currentVersion = liveBridgeMeta?.version || '1.5.4'
  const currentInstallCmd = liveBridgeMeta?.installCommand || 'npm install https://vk.tide.red/studio/dsh-plugin-openviking-1.5.4.tgz'

  // 点击复制时，现场实时向服务端查询最新包信息与链接 (单一真实源 SSOT)
  const handleCopyTarball = async (e?: React.MouseEvent) => {
    const latest = await fetchLatestClientBridge(networkMode)
    setLiveBridgeMeta(latest)
    onCopy(latest.packageUrl, `Tarball 下载地址 (v${latest.version})`, e)
  }

  const handleCopyInstallCommand = async (e?: React.MouseEvent) => {
    const latest = await fetchLatestClientBridge(networkMode)
    setLiveBridgeMeta(latest)
    onCopy(latest.installCommand, `安装命令 (v${latest.version})`, e)
  }

  // 1. DSH Cordis 插件 YAML
  const dshYamlSnippet = React.useMemo(() => {
    return `# DeepSeek Harness (DSH) 插件补丁 (cordis.patch.yml)
# 安装桥梁: ${currentInstallCmd}
# 架构: 官方一体化通信通道桥 (动态 MCP 工具投影 + 先验记忆感知 Hook)
plugins:
  - id: openviking
    name: "${currentPackageName}"
    config:
      endpointUrl: "${currentEndpointUrl}"
      userKey: "\${OPENVIKING_USER_KEY}"
      userKeyEnv: "OPENVIKING_USER_KEY"
      agentId: "${agentId}"
      userId: "${userId || 'default'}"
      enableMcp: true
      enableHook: true
      peer: "deepseek-harness@satellite"
`
  }, [currentInstallCmd, currentPackageName, currentEndpointUrl, agentId, userId])

  // 2. 通用 MCP JSON (Cursor / Claude Desktop)
  const mcpJsonSnippet = React.useMemo(() => {
    return JSON.stringify(
      {
        mcpServers: {
          openviking: {
            url: currentEndpointUrl,
            headers: {
              Authorization: 'Bearer ${OPENVIKING_USER_KEY}',
              'X-Agent-ID': agentId,
            },
          },
        },
      },
      null,
      2
    )
  }, [currentEndpointUrl, agentId])

  // 3. 通用认主 System Prompt
  const systemPromptSnippet = React.useMemo(() => {
    return `你已接入 OpenViking 体系，身份凭据与行为准则如下：
1. 【身份证与端点】不可变 Agent ID: ${agentId}，属主 User: ${userId}，端点: ${currentEndpointUrl}；
2. 【体外大脑第一公理】开局遇到架构难题或复杂事实，必须优先调用 find / search 工具检索体外记忆；
3. 【踩坑沉淀闭环】解决棘手 Bug 后，必须调用 openviking_record_evolution_lesson 将经验持久化沉淀；
4. 【工程物理规范】遵循单文件 100~300 行黄金甜点区（严禁超 500 行）；严格遵行 NO GREEN EVER 🚫 视觉语义。`
  }, [agentId, userId, currentEndpointUrl])

  return (
    <div className="rounded-md border border-border/70 bg-muted/20 p-3 font-mono text-xs space-y-3">
      {/* 头部标题与 Tarball 快捷复制 */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/50 pb-2">
        <div className="flex items-center gap-2">
          <TerminalIcon className="size-3.5 text-cyan-500" />
          <span className="font-semibold text-foreground text-xs">
            客户端通信通道桥 (Client RPC Bridge) 接入指引
          </span>
          <Badge variant="outline" className="text-xs font-mono border-border/60">
            {currentPackageName}@{currentVersion}
          </Badge>
        </div>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={handleCopyTarball}
          className="h-6 gap-1 text-xs"
        >
          <CopyIcon className="size-3" />
          复制 Tarball 地址
        </Button>
      </div>

      {/* 架构公理说明 */}
      <p className="text-muted-foreground leading-relaxed">
        外部智能体（本地 IDE 或远程节点）只需安装此轻量通道桥，配置三要素凭据，即可通过 RPC 动态调用服务端已赋权的核心记忆、联网搜索与凭据中枢三大真实插件。
      </p>

      {/* 物理三要素直出芯片卡片 */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        {/* 要素 1: 端点 URL */}
        <div className="flex flex-col justify-between rounded border border-border/60 bg-background/80 p-2">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="font-semibold text-foreground">① 通信端点 URL</span>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setNetworkMode('local')}
                className={`px-1 py-0.5 rounded text-xs transition-colors ${
                  networkMode === 'local'
                    ? 'bg-cyan-500/20 text-cyan-600 dark:text-cyan-400 font-semibold'
                    : 'hover:text-foreground'
                }`}
                title="同机内网直连 (127.0.0.1)"
              >
                <HomeIcon className="size-2.5 inline mr-0.5" />内网
              </button>
              <button
                type="button"
                onClick={() => setNetworkMode('public')}
                className={`px-1 py-0.5 rounded text-xs transition-colors ${
                  networkMode === 'public'
                    ? 'bg-cyan-500/20 text-cyan-600 dark:text-cyan-400 font-semibold'
                    : 'hover:text-foreground'
                }`}
                title="跨网公网直连 (vk.tide.red)"
              >
                <GlobeIcon className="size-2.5 inline mr-0.5" />公网
              </button>
            </div>
          </div>
          <div className="mt-1 flex items-center justify-between font-mono">
            <span className="truncate text-cyan-600 dark:text-cyan-400" title={currentEndpointUrl}>
              {currentEndpointUrl}
            </span>
            <button
              type="button"
              onClick={(e) => onCopy(currentEndpointUrl, '端点 URL', e)}
              className="p-0.5 text-muted-foreground hover:text-foreground shrink-0"
              title="复制端点 URL"
            >
              <CopyIcon className="size-3" />
            </button>
          </div>
        </div>

        {/* 要素 2: 属主凭据 Key */}
        <div className="flex flex-col justify-between rounded border border-border/60 bg-background/80 p-2">
          <div className="text-foreground font-semibold">
            ② 所属用户 API Key
          </div>
          <div className="mt-1 flex items-center justify-between font-mono text-muted-foreground">
            <span className="truncate">{'${OPENVIKING_USER_KEY}'}</span>
            <Badge variant="outline" className="border-cyan-500/30 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 text-xs px-1 py-0">
              服务端动态校验
            </Badge>
          </div>
        </div>

        {/* 要素 3: 不可变身份证 ID */}
        <div className="flex flex-col justify-between rounded border border-border/60 bg-background/80 p-2">
          <div className="text-foreground font-semibold">
            ③ 永久 Agent ID (身份证)
          </div>
          <div className="mt-1 flex items-center justify-between font-mono">
            <span className="truncate text-foreground font-medium">{agentId}</span>
            <button
              type="button"
              onClick={(e) => onCopy(agentId, 'Agent ID', e)}
              className="p-0.5 text-muted-foreground hover:text-foreground shrink-0"
              title="复制 Agent ID"
            >
              <CopyIcon className="size-3" />
            </button>
          </div>
        </div>
      </div>

      {/* 客户端安装命令 */}
      <div className="space-y-1">
        <Label className="text-xs text-muted-foreground">客户端 NPM 通信桥安装命令:</Label>
        <div className="flex items-center justify-between rounded bg-background p-2 font-mono text-foreground border border-border/40">
          <code className="text-cyan-600 dark:text-cyan-400 font-semibold">{currentInstallCmd}</code>
          <button
            type="button"
            onClick={handleCopyInstallCommand}
            className="text-muted-foreground hover:text-foreground"
            title="复制安装命令"
          >
            <CopyIcon className="size-3" />
          </button>
        </div>
      </div>

      {/* 场景 Tab 切换直出 */}
      <div className="space-y-1.5 pt-1">
        <div className="flex flex-wrap items-center justify-between gap-1.5">
          <div className="flex items-center gap-1 border-b border-border/50 pb-1">
            <button
              type="button"
              onClick={() => setActiveTab('dsh-yaml')}
              className={`px-2 py-0.5 rounded text-xs transition-colors flex items-center gap-1 ${
                activeTab === 'dsh-yaml'
                  ? 'border border-cyan-500/40 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 font-semibold'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <ServerIcon className="size-3" />
              <span>DSH Cordis 插件补丁</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('mcp-json')}
              className={`px-2 py-0.5 rounded text-xs transition-colors flex items-center gap-1 ${
                activeTab === 'mcp-json'
                  ? 'border border-cyan-500/40 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 font-semibold'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <AppWindowIcon className="size-3" />
              <span>通用 MCP JSON (Cursor/Claude)</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('system-prompt')}
              className={`px-2 py-0.5 rounded text-xs transition-colors flex items-center gap-1 ${
                activeTab === 'system-prompt'
                  ? 'border border-cyan-500/40 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 font-semibold'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <SparklesIcon className="size-3" />
              <span>认主系统提示词 (一键托底)</span>
            </button>
          </div>

          <button
            type="button"
            onClick={(e) => {
              const snippet =
                activeTab === 'dsh-yaml'
                  ? dshYamlSnippet
                  : activeTab === 'mcp-json'
                  ? mcpJsonSnippet
                  : systemPromptSnippet
              onCopy(snippet, '配置文本', e)
            }}
            className="text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-1 text-xs"
          >
            <CopyIcon className="size-3" />
            <span>复制当前配置</span>
          </button>
        </div>

        {/* 预览代码框 */}
        <pre className="max-h-36 overflow-y-auto rounded bg-background p-2.5 text-xs text-foreground/90 border border-border/40 font-mono leading-relaxed">
          {activeTab === 'dsh-yaml' && dshYamlSnippet}
          {activeTab === 'mcp-json' && mcpJsonSnippet}
          {activeTab === 'system-prompt' && systemPromptSnippet}
        </pre>
      </div>
    </div>
  )
}
