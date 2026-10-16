/**
 * native-bridge-integration-guide.tsx
 * VIKI 原生插件客户端通信桥梁接入指南 (Cockpit UI 规范)。
 * 承接用户中心剥离出的客户端接入三要素与三大标杆渠道（Google 反重力 / DeepSeek Harness / 通用 MCP）。
 *
 * 核心架构哲学：
 * 1. 【真实密钥单一真相源】：严格从 useAppConnection 读取真实 apiKey，绝不伪造硬编码假 Key；
 * 2. 【未就绪引导闭环】：若无真实 Key，提供直达 /users 路由的引导，禁止产生假象；
 * 3. 【三大官方标杆渠道平权并立】：反重力、DSH、通用 MCP 智能体；
 * 4. 严守 Cockpit UI 视觉规范：NO GREEN EVER 🚫，字号硬下限 >= 12px (text-xs)，微圆角高密排版。
 */

import * as React from 'react'
import { Link } from '@tanstack/react-router'
import {
  AlertCircleIcon,
  BotIcon,
  BoxesIcon,
  CheckIcon,
  CopyIcon,
  GlobeIcon,
  KeyIcon,
  LayersIcon,
  ShieldCheckIcon,
  SparklesIcon,
  TerminalIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { useAppConnection } from '#/hooks/use-app-connection'
import { copyTextToClipboard } from '#/lib/clipboard'

export type NativeBridgeIntegrationGuideProps = {
  pluginId?: string
  pluginName?: string
  userApiKey?: string
}

type ChannelType = 'antigravity' | 'dsh' | 'universal-mcp'

export function NativeBridgeIntegrationGuide({
  pluginId = 'openviking-memory',
  pluginName = '核心战地长程记忆',
  userApiKey = '',
}: NativeBridgeIntegrationGuideProps) {
  const { connection } = useAppConnection()
  const [networkMode, setNetworkMode] = React.useState<'public' | 'local'>('public')
  const [activeChannel, setActiveChannel] = React.useState<ChannelType>('antigravity')
  const [copiedItem, setCopiedItem] = React.useState<string | null>(null)

  // 100% 真实密钥判定，绝不伪造硬编码假字符串
  const rawApiKey = userApiKey || connection?.apiKey || ''
  const hasValidApiKey = Boolean(rawApiKey && rawApiKey !== 'vk-user-key-xxxx')
  const effectiveApiKey = hasValidApiKey ? rawApiKey : '<YOUR_USER_KEY>'

  const isLocal = networkMode === 'local'
  const serviceAddress = isLocal ? 'http://127.0.0.1:1933' : 'https://vk.tide.red'
  // 动态根据 pluginId 映射独立专属桥接器包
  const getPluginBridgeDetails = (pid: string) => {
    const id = (pid || 'openviking-memory').toLowerCase()
    if (id.includes('ops')) {
      return {
        pkgName: 'dsh-plugin-openviking-ops',
        version: '1.0.0',
        antigravityDir: 'openviking-ops',
      }
    }
    if (id.includes('fleet')) {
      return {
        pkgName: 'dsh-plugin-openviking-fleet',
        version: '1.0.0',
        antigravityDir: 'openviking-fleet',
      }
    }
    return {
      pkgName: 'dsh-plugin-openviking-memory',
      version: '2.0.12',
      antigravityDir: 'openviking-memory',
    }
  }

  const bridgeDetails = getPluginBridgeDetails(pluginId)
  const bridgeVersion = bridgeDetails.version
  const bridgeTarballUrl = `https://vk.tide.red/studio/${bridgeDetails.pkgName}-${bridgeVersion}.tgz`
  const installCmd = `npm install ${bridgeTarballUrl}`

  const handleCopy = async (text: string, label: string) => {
    try {
      await copyTextToClipboard(text)
      setCopiedItem(label)
      toast.success(`${label} 已复制到剪贴板`)
      setTimeout(() => setCopiedItem(null), 2000)
    } catch {
      toast.error('复制失败，请手动选择复制')
    }
  }

  // 渠道 1：Google 反重力 (Antigravity IDE / CLI)
  const antigravitySetupCmdWin = `cmd /c mklink /J "$env:USERPROFILE\\.gemini\\config\\plugins\\${bridgeDetails.antigravityDir}" "OpenVikingStudio路径\\integrations\\antigravity\\${bridgeDetails.antigravityDir}"\npython setup.py --api ${serviceAddress} --key "${effectiveApiKey}"`

  const antigravitySetupCmdUnix = `mkdir -p ~/.gemini/config/plugins && ln -s /path/to/OpenVikingStudio/integrations/antigravity/${bridgeDetails.antigravityDir} ~/.gemini/config/plugins/${bridgeDetails.antigravityDir}\ncd ~/.gemini/config/plugins/${bridgeDetails.antigravityDir} && python3 setup.py --api ${serviceAddress} --key "${effectiveApiKey}"`

  const antigravityAgentPrompt = `请帮我将当前反重力开发座舱 (Antigravity IDE) 接入 OpenViking 官方核心标准插件：
1. 插件挂载规范目录：~/.gemini/config/plugins/${bridgeDetails.antigravityDir}/
2. 插件源码物理路径：OpenVikingStudio/integrations/antigravity/${bridgeDetails.antigravityDir}
3. 服务端接入地址：${serviceAddress}
4. 专属授权凭据：${effectiveApiKey}${!hasValidApiKey ? ' (⚠️ 请替换为在用户列表复制的真实 User Key)' : ''}
5. 目标接入插件：${pluginName} (${pluginId})
6. 执行要求：
   - 将插件源码通过目录软链挂载至全局 plugins 目录；
   - 运行 python setup.py --api ${serviceAddress} --key "${effectiveApiKey}" 完成凭据落盘；
   - 激活 PreInvocation（记忆预取）、PreToolUse（沙箱守卫）与 Stop（会话归档）三大完整 Hook。`

  // 渠道 2：DeepSeek Harness (DSH)
  const dshCordisPatchYaml = `plugins:
  '${bridgeDetails.pkgName}':
    version: '${bridgeVersion}'
    resolved: '${bridgeTarballUrl}'
    config:
      serverUrl: '${serviceAddress}'
      userApiKey: '${effectiveApiKey}'`

  const dshAgentPrompt = `请帮我安装并接入 ${pluginName} 专属客户端通信桥梁：
1. 目标插件：${bridgeDetails.pkgName}
2. NPM 安装命令：${installCmd}
3. 服务地址：${serviceAddress}
4. 专属凭据：${effectiveApiKey}${!hasValidApiKey ? ' (⚠️ 请替换为在用户列表复制的真实 User Key)' : ''}
5. 请将上述配置写入 cordis.patch.yml 并重启 Harness 服务。`

  // 渠道 3：标准通用智能体 (Universal MCP)
  const universalMcpHttpJson = JSON.stringify(
    {
      mcpServers: {
        openviking: {
          url: `${serviceAddress}/mcp`,
          headers: {
            Authorization: `Bearer ${effectiveApiKey}`,
            'X-API-Key': effectiveApiKey,
          },
        },
      },
    },
    null,
    2,
  )

  const universalAgentPrompt = `请帮我将 OpenViking 体外大脑作为通用 MCP 工具接入当前环境：
1. MCP 服务协议端点：${serviceAddress}/mcp (Streamable HTTP 模式)
2. 认证请求头：Authorization: Bearer ${effectiveApiKey}${!hasValidApiKey ? ' (⚠️ 请替换为在用户列表复制的真实 User Key)' : ''}
3. 请根据当前客户端环境（Cursor / Claude Code / Windsurf / Cline），将上述配置写入对应的 MCP 配置文件（如 .cursor/mcp.json 或 claude_desktop_config.json），并验证连通性。`

  return (
    <div className="space-y-3.5 rounded-md border border-border/70 bg-card/40 p-3.5 font-sans text-xs">
      {/* 头部标题与定位 */}
      <div className="flex items-center justify-between border-b border-border/50 pb-2.5">
        <div className="flex items-center gap-2">
          <LayersIcon className="size-4 text-cyan-500" />
          <span className="font-semibold text-foreground text-xs">
            官方客户端通信桥梁接入指南 (开箱即用三支柱)
          </span>
        </div>
        <Badge variant="outline" className="text-xs font-mono border-cyan-500/40 text-cyan-700 dark:text-cyan-400 bg-cyan-500/10">
          全平台不可变桥梁包 v{bridgeVersion}
        </Badge>
      </div>

      {/* 极简两核心要素置顶 */}
      <div className="space-y-2.5 rounded-md border border-border/60 bg-muted/20 p-2.5">
        {/* 要素 1：服务中枢地址 */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground font-medium">1. 服务中枢地址</span>
            <div className="inline-flex rounded border border-border/60 bg-background/80 p-0.5 text-xs">
              <button
                type="button"
                onClick={() => setNetworkMode('public')}
                className={`px-2 py-0.5 rounded transition-all ${
                  networkMode === 'public'
                    ? 'bg-muted text-cyan-700 dark:text-cyan-400 font-semibold shadow-xs'
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
                    ? 'bg-muted text-cyan-700 dark:text-cyan-400 font-semibold shadow-xs'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                本地内网 (127.0.0.1:1933)
              </button>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground gap-1"
              onClick={() => handleCopy(serviceAddress, '服务地址')}
            >
              {copiedItem === '服务地址' ? (
                <CheckIcon className="size-3 text-cyan-500" />
              ) : (
                <CopyIcon className="size-3" />
              )}
              复制
            </Button>
          </div>
          <div className="rounded border border-border/50 bg-background/80 px-2 py-1.5 font-mono text-xs text-foreground select-all">
            {serviceAddress}
          </div>
        </div>

        {/* 要素 2：用户专属 API Key (真实性治理) */}
        <div className="space-y-1.5 pt-1 border-t border-border/40">
          {hasValidApiKey ? (
            <>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground font-medium">
                  2. 用户专属 API Key (人机平权统一凭据)
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground gap-1"
                  onClick={() => handleCopy(effectiveApiKey, '用户密钥')}
                >
                  {copiedItem === '用户密钥' ? (
                    <CheckIcon className="size-3 text-cyan-500" />
                  ) : (
                    <CopyIcon className="size-3" />
                  )}
                  复制真实密钥
                </Button>
              </div>
              <div className="rounded border border-border/50 bg-background/80 px-2 py-1.5 font-mono text-xs text-foreground break-all select-all">
                {effectiveApiKey}
              </div>
            </>
          ) : (
            <div className="rounded-md border border-amber-500/40 bg-amber-500/10 p-2.5 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 font-semibold text-amber-700 dark:text-amber-400">
                  <KeyIcon className="size-3.5 shrink-0" />
                  <span>未检测到活跃用户密钥 (User API Key)</span>
                </div>
                <Badge
                  variant="outline"
                  className="text-xs font-mono border-amber-500/50 bg-amber-500/20 text-amber-700 dark:text-amber-300"
                >
                  待绑定
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                客户端通信桥梁接入需要绑定您的真实专属 User Key。当前会话未检测到密钥，请前往用户管理中心进行复制或生成。
              </p>
              <div className="pt-0.5">
                <Button
                  variant="outline"
                  size="sm"
                  asChild
                  className="h-6.5 text-xs border-amber-500/40 text-amber-700 dark:text-amber-300 hover:bg-amber-500/15"
                >
                  <Link to="/users">前往用户列表查看与复制专属密钥 ➔</Link>
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 三大官方标杆渠道平权切换卡 */}
      <div className="space-y-2.5 pt-1">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
            <SparklesIcon className="size-3.5 text-cyan-500" />
            <span>选择智能体客户端接入渠道:</span>
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setActiveChannel('antigravity')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium border transition-all ${
                activeChannel === 'antigravity'
                  ? 'border-cyan-500/60 bg-cyan-500/15 text-cyan-700 dark:text-cyan-300 shadow-xs'
                  : 'border-border/60 bg-background/60 text-muted-foreground hover:text-foreground'
              }`}
            >
              <BotIcon className="size-3 text-cyan-500" />
              <span>Google 反重力</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveChannel('dsh')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium border transition-all ${
                activeChannel === 'dsh'
                  ? 'border-cyan-500/60 bg-cyan-500/15 text-cyan-700 dark:text-cyan-300 shadow-xs'
                  : 'border-border/60 bg-background/60 text-muted-foreground hover:text-foreground'
              }`}
            >
              <BoxesIcon className="size-3 text-cyan-500" />
              <span>DeepSeek Harness</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveChannel('universal-mcp')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium border transition-all ${
                activeChannel === 'universal-mcp'
                  ? 'border-cyan-500/60 bg-cyan-500/15 text-cyan-700 dark:text-cyan-300 shadow-xs'
                  : 'border-border/60 bg-background/60 text-muted-foreground hover:text-foreground'
              }`}
            >
              <GlobeIcon className="size-3 text-cyan-500" />
              <span>通用 MCP 智能体</span>
            </button>
          </div>
        </div>

        {/* 渠道 1：Google 反重力 */}
        {activeChannel === 'antigravity' && (
          <div className="space-y-2.5 rounded-md border border-cyan-500/30 bg-card/60 p-3 animate-in fade-in-50">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-cyan-700 dark:text-cyan-400 flex items-center gap-1.5">
                <TerminalIcon className="size-3.5" />
                【极速开箱】反重力 Agent 一键认主提示词
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-1.5 text-xs text-cyan-700 dark:text-cyan-400 hover:text-foreground gap-1"
                onClick={() => handleCopy(antigravityAgentPrompt, '反重力一键认主提示词')}
              >
                <CopyIcon className="size-3" />
                复制提示词
              </Button>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              将此提示词直接发给反重力 IDE 聊天框，智能体将自动完成软链挂载、凭据初始化与 Hook 激活。
            </p>
            <div className="rounded border border-border/60 bg-background/90 p-2 font-mono text-xs text-muted-foreground whitespace-pre-wrap select-all max-h-36 overflow-y-auto">
              {antigravityAgentPrompt}
            </div>

            <div className="pt-1 space-y-1">
              <div className="flex items-center justify-between text-xs text-muted-foreground font-medium">
                <span>手动终端执行命令:</span>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => handleCopy(antigravitySetupCmdWin, 'Windows 安装命令')}
                    className="hover:underline text-cyan-700 dark:text-cyan-400"
                  >
                    复制 Win 命令
                  </button>
                  <span>·</span>
                  <button
                    type="button"
                    onClick={() => handleCopy(antigravitySetupCmdUnix, 'Linux 安装命令')}
                    className="hover:underline text-cyan-700 dark:text-cyan-400"
                  >
                    复制 Linux 命令
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 渠道 2：DeepSeek Harness */}
        {activeChannel === 'dsh' && (
          <div className="space-y-2.5 rounded-md border border-cyan-500/30 bg-card/60 p-3 animate-in fade-in-50">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-cyan-700 dark:text-cyan-400 flex items-center gap-1.5">
                <TerminalIcon className="size-3.5" />
                【极速开箱】DSH Agent 一键认主提示词
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-1.5 text-xs text-cyan-700 dark:text-cyan-400 hover:text-foreground gap-1"
                onClick={() => handleCopy(dshAgentPrompt, 'DSH 一键认主提示词')}
              >
                <CopyIcon className="size-3" />
                复制提示词
              </Button>
            </div>
            <div className="rounded border border-border/60 bg-background/90 p-2 font-mono text-xs text-muted-foreground whitespace-pre-wrap select-all">
              {dshAgentPrompt}
            </div>

            <div className="space-y-1 pt-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground font-medium">NPM 安装直链:</span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-5 px-1.5 text-xs text-cyan-700 dark:text-cyan-400"
                  onClick={() => handleCopy(installCmd, 'NPM 安装命令')}
                >
                  复制
                </Button>
              </div>
              <div className="rounded border border-border/60 bg-background/80 p-2 font-mono text-xs text-foreground select-all">
                {installCmd}
              </div>
            </div>

            <div className="space-y-1 pt-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground font-medium">cordis.patch.yml 插件补丁片段:</span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-5 px-1.5 text-xs text-cyan-700 dark:text-cyan-400"
                  onClick={() => handleCopy(dshCordisPatchYaml, 'DSH 补丁配置')}
                >
                  复制 YAML
                </Button>
              </div>
              <pre className="rounded border border-border/60 bg-background/80 p-2 font-mono text-xs text-muted-foreground overflow-x-auto select-all">
                {dshCordisPatchYaml}
              </pre>
            </div>
          </div>
        )}

        {/* 渠道 3：通用 MCP 智能体 */}
        {activeChannel === 'universal-mcp' && (
          <div className="space-y-2.5 rounded-md border border-cyan-500/30 bg-card/60 p-3 animate-in fade-in-50">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-cyan-700 dark:text-cyan-400 flex items-center gap-1.5">
                <TerminalIcon className="size-3.5" />
                【极速开箱】通用 MCP 认主提示词
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-1.5 text-xs text-cyan-700 dark:text-cyan-400 hover:text-foreground gap-1"
                onClick={() => handleCopy(universalAgentPrompt, '通用 MCP 认主提示词')}
              >
                <CopyIcon className="size-3" />
                复制提示词
              </Button>
            </div>
            <div className="rounded border border-border/60 bg-background/90 p-2 font-mono text-xs text-muted-foreground whitespace-pre-wrap select-all">
              {universalAgentPrompt}
            </div>

            <div className="space-y-1 pt-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground font-medium">Streamable HTTP 模式 (mcp.json):</span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-5 px-1.5 text-xs text-cyan-700 dark:text-cyan-400"
                  onClick={() => handleCopy(universalMcpHttpJson, 'MCP JSON 配置')}
                >
                  复制 JSON
                </Button>
              </div>
              <pre className="rounded border border-border/60 bg-background/80 p-2 font-mono text-xs text-muted-foreground overflow-x-auto select-all">
                {universalMcpHttpJson}
              </pre>
            </div>
          </div>
        )}
      </div>

      <div className="flex items-center gap-1.5 pt-1 text-xs text-muted-foreground/80 font-mono">
        <ShieldCheckIcon className="size-3.5 text-cyan-500 shrink-0" />
        <span>原则：A 就是 A，Key 对了就能用。敏感特权插件在调用时由服务端执行显式校验。</span>
      </div>
    </div>
  )
}
