/**
 * client-install-tab.tsx
 * 客户端一键开箱即用接入与三大渠道多模态配置选项卡 (Client Install & Multi-Channel Tab).
 *
 * 核心架构哲学：
 * 1. 【三大官方标杆渠道平权并立】：
 *    - 渠道 1：Google 反重力 (Antigravity IDE / CLI 官方标准插件)
 *    - 渠道 2：DeepSeek Harness (DSH npm 不可变包直链)
 *    - 渠道 3：标准通用智能体 (Cursor / Claude Code / Windsurf / Universal MCP)
 * 2. 【极速开箱即用 (Out-of-the-Box)】：每个渠道均提供一键复制认主提示词 (Agent Prompt)，发给 Agent 秒级自愈跑通，零人肉手调；
 * 3. 【极简两核心要素平权】：服务地址 + 用户密钥 (单点真实源)；
 * 4. 严守 Cockpit UI 视觉规范：NO GREEN EVER 🚫，字号物理硬下限 >= 12px (text-xs)。
 */

import * as React from 'react'
import {
  BotIcon,
  BoxesIcon,
  CheckIcon,
  CopyIcon,
  FileCode2Icon,
  GlobeIcon,
  KeyIcon,
  KeyRoundIcon,
  LayersIcon,
  ServerIcon,
  ShieldCheckIcon,
  SparklesIcon,
  TerminalIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { copyTextToClipboard } from '#/lib/clipboard'
import type { AdminUser } from '#/lib/admin'
import { fetchLatestClientBridge } from '../../agents/-lib/capability-bundles'

export type ClientInstallTabProps = {
  user: AdminUser
  currentAccountId: string
}

type ChannelType = 'antigravity' | 'dsh' | 'universal-mcp'

export function ClientInstallTab({ user, currentAccountId }: ClientInstallTabProps) {
  const [networkMode, setNetworkMode] = React.useState<'public' | 'local'>('public')
  const [activeChannel, setActiveChannel] = React.useState<ChannelType>('antigravity')
  const [copiedItem, setCopiedItem] = React.useState<string | null>(null)
  const [bridgePkg, setBridgePkg] = React.useState<{
    packageName: string
    version: string
    packageUrl: string
    installCommand: string
  }>({
    packageName: 'dsh-plugin-openviking',
    version: '1.5.6',
    packageUrl: 'https://vk.tide.red/studio/dsh-plugin-openviking-1.5.6.tgz',
    installCommand: 'npm install https://vk.tide.red/studio/dsh-plugin-openviking-1.5.6.tgz',
  })

  // 动态同步最新服务端客户端插件包信息
  React.useEffect(() => {
    let active = true
    fetchLatestClientBridge(networkMode).then((info) => {
      if (active) setBridgePkg(info)
    })
    return () => {
      active = false
    }
  }, [networkMode])

  const isLocal = networkMode === 'local'
  const serviceAddress = isLocal ? 'http://127.0.0.1:1933' : 'https://vk.tide.red'
  const userApiKey = user.apiKey || ''
  const accountId = user.accountId || currentAccountId || 'default'
  const userId = user.userId || 'default'

  const handleCopy = async (text: string, label: string) => {
    try {
      await copyTextToClipboard(text)
      setCopiedItem(label)
      toast.success(`${label}已复制到剪贴板`)
      setTimeout(() => setCopiedItem(null), 2000)
    } catch {
      toast.error('复制失败，请手动选择复制')
    }
  }

  // ─────────────────────────────────────────────────────────────
  // 渠道 1：Google 反重力 (Antigravity IDE / CLI)
  // ─────────────────────────────────────────────────────────────
  const antigravitySetupCmdWin = `cmd /c mklink /J "$env:USERPROFILE\\.gemini\\config\\plugins\\openviking-memory" "OpenVikingStudio路径\\integrations\\antigravity\\openviking-memory"\npython setup.py --api ${serviceAddress} --key "${userApiKey}"`

  const antigravitySetupCmdUnix = `mkdir -p ~/.gemini/config/plugins && ln -s /path/to/OpenVikingStudio/integrations/antigravity/openviking-memory ~/.gemini/config/plugins/openviking-memory\ncd ~/.gemini/config/plugins/openviking-memory && python3 setup.py --api ${serviceAddress} --key "${userApiKey}"`

  const antigravityAgentPrompt = `请帮我将当前反重力开发座舱 (Antigravity IDE) 接入 OpenViking 官方核心记忆标准插件：
1. 插件挂载规范目录：~/.gemini/config/plugins/openviking-memory/
2. 插件源码物理路径：OpenVikingStudio/integrations/antigravity/openviking-memory
3. 服务端接入地址：${serviceAddress}
4. 专属授权凭据：${userApiKey}
5. 专用账户身份：User=${userId}, Account=${accountId}
6. 执行要求：
   - 将插件源码通过目录软链挂载至全局 plugins 目录；
   - 运行 python setup.py --api ${serviceAddress} --key "${userApiKey}" 完成凭据落盘；
   - 清理工作区项目内可能残留的历史 hooks.json，交由全局插件声明式 hooks.json 统一管理；
   - 激活 PreInvocation（记忆预取）、PreToolUse（沙箱守卫）与 Stop（会话归档）三大完整能力。`

  // ─────────────────────────────────────────────────────────────
  // 渠道 2：DeepSeek Harness (DSH)
  // ─────────────────────────────────────────────────────────────
  const dshCordisPatchYaml = `plugins:
  '${bridgePkg.packageName}':
    version: '${bridgePkg.version}'
    resolved: '${bridgePkg.packageUrl}'
    config:
      serverUrl: '${serviceAddress}'
      userApiKey: '${userApiKey}'
      accountId: '${accountId}'
      userId: '${userId}'`

  const dshAgentPrompt = `请帮我安装并接入 OpenViking 官方客户端插件：
1. NPM 安装命令：${bridgePkg.installCommand}
2. 服务地址：${serviceAddress}
3. 专属凭据：${userApiKey}
4. 租户与用户：Account=${accountId}, User=${userId}
5. 请将上述配置写入 cordis.patch.yml 并重启 Harness 服务。`

  // ─────────────────────────────────────────────────────────────
  // 渠道 3：标准通用智能体 (Universal MCP - Cursor / Claude / Windsurf / Cline)
  // ─────────────────────────────────────────────────────────────
  const universalMcpHttpJson = JSON.stringify(
    {
      mcpServers: {
        openviking: {
          url: `${serviceAddress}/mcp`,
          headers: {
            Authorization: `Bearer ${userApiKey}`,
            'X-API-Key': userApiKey,
            'X-OpenViking-User': userId,
            'X-OpenViking-Account': accountId,
          },
        },
      },
    },
    null,
    2,
  )

  const universalMcpStdioJson = JSON.stringify(
    {
      mcpServers: {
        openviking: {
          command: 'python',
          args: ['/path/to/OpenVikingStudio/mcp-openviking/mcp_openviking_server.py'],
          env: {
            OPENVIKING_API: serviceAddress,
            OPENVIKING_API_KEY: userApiKey,
            OPENVIKING_USER: userId,
            OPENVIKING_MCP_MODE: 'core',
          },
        },
      },
    },
    null,
    2,
  )

  const universalAgentPrompt = `请帮我将 OpenViking 体外大脑作为通用 MCP 工具接入当前环境：
1. MCP 服务协议端点：${serviceAddress}/mcp (Streamable HTTP 模式)
2. 认证请求头：Authorization: Bearer ${userApiKey}
3. 专属用户标识：${userId} (Account: ${accountId})
4. 请根据当前客户端环境（Cursor / Claude Code / Windsurf / Cline），将上述配置写入对应的 MCP 配置文件（如 .cursor/mcp.json 或 claude_desktop_config.json），并验证连通性。`

  return (
    <div className="space-y-4 font-sans text-xs">
      {/* 极简两核心要素置顶 (人机平权统一接入凭据) */}
      <div className="space-y-2.5 rounded-md border border-border/70 bg-card/40 p-3">
        <h4 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
          <LayersIcon className="size-3.5 text-cyan-500" />
          接入核心两要素 (人机平权统一凭据单一真实源)
        </h4>

        {/* 1. 服务地址 */}
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">服务中枢地址</span>
              <div className="inline-flex rounded-md border border-border/60 bg-muted/20 p-0.5 text-[12px]">
                <button
                  type="button"
                  onClick={() => setNetworkMode('public')}
                  className={`px-2 py-0.5 rounded transition-all ${
                    networkMode === 'public'
                      ? 'bg-background text-cyan-400 shadow-sm font-medium'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  公网 (vk.tide.red)
                </button>
                <button
                  type="button"
                  onClick={() => setNetworkMode('local')}
                  className={`px-2 py-0.5 rounded transition-all ${
                    networkMode === 'local'
                      ? 'bg-background text-cyan-400 shadow-sm font-medium'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  本地内网 (127.0.0.1:1933)
                </button>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground gap-1"
              onClick={() => handleCopy(serviceAddress, '服务地址')}
            >
              {copiedItem === '服务地址' ? (
                <CheckIcon className="size-3 text-cyan-400" />
              ) : (
                <CopyIcon className="size-3" />
              )}
              复制
            </Button>
          </div>
          <div className="rounded border border-border/60 bg-background/80 p-2 font-mono text-xs text-foreground select-all">
            {serviceAddress}
          </div>
        </div>

        {/* 2. 用户密钥 */}
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">用户专属 API Key (绑定身份: {userId})</span>
            {userApiKey && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground gap-1"
                onClick={() => handleCopy(userApiKey, '用户密钥')}
              >
                {copiedItem === '用户密钥' ? (
                  <CheckIcon className="size-3 text-cyan-400" />
                ) : (
                  <CopyIcon className="size-3" />
                )}
                复制
              </Button>
            )}
          </div>
          {userApiKey ? (
            <div className="rounded border border-border/60 bg-background/80 p-2 font-mono text-xs text-foreground break-all select-all">
              {userApiKey}
            </div>
          ) : (
            <div className="rounded border border-border/40 bg-muted/20 p-2 text-xs text-muted-foreground flex items-center justify-between">
              <span>该用户当前未直接暴露明文密钥</span>
              <span className="text-[12px] text-cyan-400">可在用户列表点击“重置”重新签发</span>
            </div>
          )}
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          三大官方标杆渠道平权切换卡 (Channel Selector Tabs)
         ───────────────────────────────────────────────────────────── */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
            <SparklesIcon className="size-3.5 text-cyan-500" />
            <span>选择智能体客户端接入渠道 (开箱即用三支柱):</span>
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setActiveChannel('antigravity')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium border transition-all ${
                activeChannel === 'antigravity'
                  ? 'border-cyan-500/70 bg-cyan-500/15 text-cyan-400 shadow-sm'
                  : 'border-border/60 bg-card/40 text-muted-foreground hover:text-foreground hover:bg-card/70'
              }`}
            >
              <BotIcon className="size-3.5 text-cyan-400" />
              <span>Google 反重力</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveChannel('dsh')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium border transition-all ${
                activeChannel === 'dsh'
                  ? 'border-cyan-500/70 bg-cyan-500/15 text-cyan-400 shadow-sm'
                  : 'border-border/60 bg-card/40 text-muted-foreground hover:text-foreground hover:bg-card/70'
              }`}
            >
              <BoxesIcon className="size-3.5 text-cyan-400" />
              <span>DeepSeek Harness</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveChannel('universal-mcp')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium border transition-all ${
                activeChannel === 'universal-mcp'
                  ? 'border-cyan-500/70 bg-cyan-500/15 text-cyan-400 shadow-sm'
                  : 'border-border/60 bg-card/40 text-muted-foreground hover:text-foreground hover:bg-card/70'
              }`}
            >
              <GlobeIcon className="size-3.5 text-cyan-400" />
              <span>通用 MCP 智能体</span>
            </button>
          </div>
        </div>

        {/* ─────────────────────────────────────────────────────────────
            渠道 1 视窗：Google 反重力 (Antigravity IDE / CLI)
           ───────────────────────────────────────────────────────────── */}
        {activeChannel === 'antigravity' && (
          <div className="space-y-3 rounded-md border border-cyan-500/40 bg-card/40 p-3.5 animate-in fade-in-50">
            <div className="flex items-center justify-between border-b border-border/50 pb-2.5">
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="border-cyan-500/50 text-cyan-400 font-mono text-[12px]">
                  官方标准插件 v2.0.11
                </Badge>
                <span className="font-semibold text-foreground text-xs">
                  Google Gemini Agent 规范原生一等公民插件
                </span>
              </div>
              <span className="text-[12px] text-muted-foreground">
                支持 VS Code 架构 Antigravity IDE 与 Headless CLI
              </span>
            </div>

            {/* 核心价值：一键开箱即用 Prompt */}
            <div className="space-y-2 rounded-md border border-cyan-500/30 bg-cyan-500/5 p-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-cyan-400 flex items-center gap-1.5">
                  <TerminalIcon className="size-3.5" />
                  【极速开箱】反重力 Agent 一键认主提示词 (直接复制发给 Agent)
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-1.5 text-xs text-cyan-400 hover:text-foreground gap-1"
                  onClick={() => handleCopy(antigravityAgentPrompt, '反重力一键认主提示词')}
                >
                  {copiedItem === '反重力一键认主提示词' ? (
                    <CheckIcon className="size-3 text-cyan-400" />
                  ) : (
                    <CopyIcon className="size-3" />
                  )}
                  复制提示词
                </Button>
              </div>
              <p className="text-[12px] text-muted-foreground leading-relaxed">
                无需人工手调！将此提示词直接发送给反重力 IDE 中的智能体，它将自动完成软链挂载、凭据初始化与 Hook 激活。
              </p>
              <div className="rounded border border-border/60 bg-background/90 p-2.5 font-mono text-[12px] text-muted-foreground whitespace-pre-wrap select-all">
                {antigravityAgentPrompt}
              </div>
            </div>

            {/* 本地物理安装脚本快速执行 */}
            <div className="space-y-2 rounded-md border border-border/60 bg-background/50 p-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <ServerIcon className="size-3.5 text-cyan-500" />
                  或者手动终端 10 秒快速执行命令:
                </span>
                <div className="flex items-center gap-1.5">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground gap-1"
                    onClick={() => handleCopy(antigravitySetupCmdWin, 'Windows 安装命令')}
                  >
                    复制 Windows 命令
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground gap-1"
                    onClick={() => handleCopy(antigravitySetupCmdUnix, 'Linux/macOS 命令')}
                  >
                    复制 Linux/macOS
                  </Button>
                </div>
              </div>
              <div className="space-y-1.5">
                <div className="text-[12px] text-muted-foreground font-medium">Windows PowerShell:</div>
                <pre className="rounded border border-border/60 bg-background/80 p-2 font-mono text-[12px] text-muted-foreground overflow-x-auto select-all">
                  {antigravitySetupCmdWin}
                </pre>
                <div className="text-[12px] text-muted-foreground font-medium">Linux / macOS:</div>
                <pre className="rounded border border-border/60 bg-background/80 p-2 font-mono text-[12px] text-muted-foreground overflow-x-auto select-all">
                  {antigravitySetupCmdUnix}
                </pre>
              </div>
            </div>

            <div className="text-[12px] text-muted-foreground flex items-center gap-2">
              <ShieldCheckIcon className="size-3.5 text-cyan-500" />
              <span>特性支持：内置声明式 `plugin.json`，自动挂载记忆预取、特权沙箱守卫与会话结晶三大 Hook。</span>
            </div>
          </div>
        )}

        {/* ─────────────────────────────────────────────────────────────
            渠道 2 视窗：DeepSeek Harness (DSH)
           ───────────────────────────────────────────────────────────── */}
        {activeChannel === 'dsh' && (
          <div className="space-y-3 rounded-md border border-cyan-500/40 bg-card/40 p-3.5 animate-in fade-in-50">
            <div className="flex items-center justify-between border-b border-border/50 pb-2.5">
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="border-cyan-500/50 text-cyan-400 font-mono text-[12px]">
                  NPM 直链包 v{bridgePkg.version}
                </Badge>
                <span className="font-semibold text-foreground text-xs">
                  DeepSeek Harness / Cordis 生态官方标准插件
                </span>
              </div>
              <span className="text-[12px] text-muted-foreground">不可变 Tarball 直链分发</span>
            </div>

            {/* DSH Agent 一键认主提示词 */}
            <div className="space-y-2 rounded-md border border-cyan-500/30 bg-cyan-500/5 p-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-cyan-400 flex items-center gap-1.5">
                  <TerminalIcon className="size-3.5" />
                  【极速开箱】DSH Agent 一键认主提示词
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-1.5 text-xs text-cyan-400 hover:text-foreground gap-1"
                  onClick={() => handleCopy(dshAgentPrompt, 'DSH 一键认主提示词')}
                >
                  {copiedItem === 'DSH 一键认主提示词' ? (
                    <CheckIcon className="size-3 text-cyan-400" />
                  ) : (
                    <CopyIcon className="size-3" />
                  )}
                  复制提示词
                </Button>
              </div>
              <div className="rounded border border-border/60 bg-background/90 p-2.5 font-mono text-[12px] text-muted-foreground whitespace-pre-wrap select-all">
                {dshAgentPrompt}
              </div>
            </div>

            {/* NPM 安装直链 */}
            <div className="space-y-1.5 rounded-md border border-border/60 bg-background/50 p-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <BoxesIcon className="size-3.5 text-cyan-500" />
                  NPM 一键安装命令 (零第三方 npm 源抖动):
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground gap-1"
                  onClick={() => handleCopy(bridgePkg.installCommand, 'NPM 安装命令')}
                >
                  复制命令
                </Button>
              </div>
              <div className="rounded border border-border/60 bg-background/90 p-2 font-mono text-xs text-foreground break-all select-all">
                {bridgePkg.installCommand}
              </div>
            </div>

            {/* Cordis YAML 补丁 */}
            <div className="space-y-1.5 rounded-md border border-border/60 bg-background/50 p-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <FileCode2Icon className="size-3.5 text-cyan-500" />
                  配置文件补丁 (cordis.patch.yml):
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground gap-1"
                  onClick={() => handleCopy(dshCordisPatchYaml, 'Cordis 配置补丁')}
                >
                  复制 YAML
                </Button>
              </div>
              <pre className="rounded border border-border/60 bg-background/80 p-2 font-mono text-[12px] text-muted-foreground overflow-x-auto select-all">
                {dshCordisPatchYaml}
              </pre>
            </div>
          </div>
        )}

        {/* ─────────────────────────────────────────────────────────────
            渠道 3 视窗：标准通用智能体 (Universal MCP - Cursor / Claude / Windsurf)
           ───────────────────────────────────────────────────────────── */}
        {activeChannel === 'universal-mcp' && (
          <div className="space-y-3 rounded-md border border-cyan-500/40 bg-card/40 p-3.5 animate-in fade-in-50">
            <div className="flex items-center justify-between border-b border-border/50 pb-2.5">
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="border-cyan-500/50 text-cyan-400 font-mono text-[12px]">
                  Universal Model Context Protocol
                </Badge>
                <span className="font-semibold text-foreground text-xs">
                  跨平台标准 MCP (Cursor / Claude Desktop / Claude Code / Windsurf / Cline)
                </span>
              </div>
              <span className="text-[12px] text-muted-foreground">HTTP Streamable & Stdio 双模</span>
            </div>

            {/* 通用 Agent 一键认主提示词 */}
            <div className="space-y-2 rounded-md border border-cyan-500/30 bg-cyan-500/5 p-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-cyan-400 flex items-center gap-1.5">
                  <TerminalIcon className="size-3.5" />
                  【极速开箱】通用智能体一键接入提示词 (直接复制发给任何 AI 编程助手)
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-1.5 text-xs text-cyan-400 hover:text-foreground gap-1"
                  onClick={() => handleCopy(universalAgentPrompt, '通用 Agent 认主提示词')}
                >
                  {copiedItem === '通用 Agent 认主提示词' ? (
                    <CheckIcon className="size-3 text-cyan-400" />
                  ) : (
                    <CopyIcon className="size-3" />
                  )}
                  复制提示词
                </Button>
              </div>
              <div className="rounded border border-border/60 bg-background/90 p-2.5 font-mono text-[12px] text-muted-foreground whitespace-pre-wrap select-all">
                {universalAgentPrompt}
              </div>
            </div>

            {/* 格式 A：远程 Streamable-HTTP 配置 */}
            <div className="space-y-1.5 rounded-md border border-border/60 bg-background/50 p-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <GlobeIcon className="size-3.5 text-cyan-500" />
                  标准 HTTP 远程端点配置 (无需本地 Python 环境):
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground gap-1"
                  onClick={() => handleCopy(universalMcpHttpJson, 'HTTP MCP 配置')}
                >
                  复制 JSON
                </Button>
              </div>
              <pre className="rounded border border-border/60 bg-background/80 p-2 font-mono text-[12px] text-muted-foreground overflow-x-auto select-all">
                {universalMcpHttpJson}
              </pre>
            </div>

            {/* 格式 B：本地 Stdio FastMCP 配置 */}
            <div className="space-y-1.5 rounded-md border border-border/60 bg-background/50 p-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <KeyRoundIcon className="size-3.5 text-cyan-500" />
                  本地 Stdio 进程配置 (高性能 IPC 管道):
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground gap-1"
                  onClick={() => handleCopy(universalMcpStdioJson, 'Stdio MCP 配置')}
                >
                  复制 JSON
                </Button>
              </div>
              <pre className="rounded border border-border/60 bg-background/80 p-2 font-mono text-[12px] text-muted-foreground overflow-x-auto select-all">
                {universalMcpStdioJson}
              </pre>
            </div>

            {/* 各主流客户端配置路径提示卡 */}
            <div className="rounded border border-border/60 bg-card/60 p-2.5 text-[12px] text-muted-foreground space-y-1">
              <div className="font-semibold text-foreground">各客户端配置文件路径速查:</div>
              <div>• <b>Cursor</b>: Settings ➔ Features ➔ MCP ➔ Add New MCP Server</div>
              <div>• <b>Claude Desktop (Windows)</b>: %APPDATA%\Claude\claude_desktop_config.json</div>
              <div>• <b>Claude Desktop (macOS)</b>: ~/Library/Application Support/Claude/claude_desktop_config.json</div>
              <div>• <b>Claude Code CLI</b>: claude mcp add openviking -- {serviceAddress}/mcp</div>
              <div>• <b>Windsurf / Cline / Roo Code</b>: .vscode/mcp.json 或 .cline/mcp.json</div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
