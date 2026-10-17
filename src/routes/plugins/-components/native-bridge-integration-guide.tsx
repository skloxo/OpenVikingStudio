/**
 * native-bridge-integration-guide.tsx
 * VIKI 原生与生态插件客户端通信桥梁接入指南 (Cockpit UI 规范)。
 * 承接用户中心剥离出的客户端接入要素与三大标杆渠道（Google 反重力 / DeepSeek Harness / 通用 MCP）。
 *
 * 核心架构哲学：
 * 1. 【真实密钥单一真相源】：严格从 useAppConnection 读取真实 apiKey，绝不伪造硬编码假 Key；
 * 2. 【去伪存真独立解耦】：全系插件（Memory, Ops, Fleet, KeePass, Dify, CPA）独立专属包与配置，零假冒；
 * 3. 【三大官方标杆渠道平权并立】：反重力、DSH、通用 MCP 智能体；
 * 4. 严守 Cockpit UI 视觉规范：NO GREEN EVER 🚫，字号硬下限 >= 12px (text-xs)，微圆角高密排版。
 */

import * as React from 'react'
import { Link } from '@tanstack/react-router'
import {
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
import { resolvePluginBridgeConfig } from '../-lib/native-bridge-resolver'

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

  const bridge = resolvePluginBridgeConfig(
    pluginId,
    pluginName,
    serviceAddress,
    effectiveApiKey,
    hasValidApiKey,
  )

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

  return (
    <div className="space-y-3.5 rounded-md border border-border/70 bg-card/40 p-3.5 font-sans text-xs">
      {/* 头部标题与定位 */}
      <div className="flex items-center justify-between border-b border-border/50 pb-2.5">
        <div className="flex items-center gap-2">
          <LayersIcon className="size-4 text-cyan-500" />
          <span className="font-semibold text-foreground text-xs">
            官方客户端通信桥梁接入指南 ({bridge.pkgName})
          </span>
        </div>
        <Badge variant="outline" className="text-xs font-mono border-cyan-500/40 text-cyan-700 dark:text-cyan-400 bg-cyan-500/10">
          全平台独立桥梁包 v{bridge.version}
        </Badge>
      </div>

      {/* 接入要素区 */}
      {bridge.isLocalVault ? (
        <div className="rounded border border-border/60 bg-muted/20 p-2.5 text-xs text-muted-foreground leading-relaxed space-y-1">
          <div className="flex items-center gap-1.5 text-cyan-600 dark:text-cyan-400 font-semibold">
            <ShieldCheckIcon className="size-3.5" />
            <span>本地化私有凭据定位 · 零云端依赖声明</span>
          </div>
          <p>
            本插件定位为<strong className="text-foreground">纯本地化私有插件</strong>。OpenViking 仅作为官方展厅与 NPM 安装包托管下载中枢，<strong className="text-foreground">服务端不获取、不保存任何密码保险库</strong>。
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1 font-mono text-xs">
            <div className="rounded border border-border/50 bg-background/80 p-2 space-y-0.5">
              <div className="text-muted-foreground text-xs">本地 KDBX 默认路径:</div>
              <div className="text-foreground font-semibold">~/.openviking/vault.kdbx</div>
            </div>
            <div className="rounded border border-border/50 bg-background/80 p-2 space-y-0.5">
              <div className="text-muted-foreground text-xs">主密码环境变量名:</div>
              <div className="text-foreground font-semibold">KEEPASS_VAULT_PASSWORD</div>
            </div>
          </div>
        </div>
      ) : bridge.isExternalService ? (
        <div className="rounded border border-border/60 bg-muted/20 p-2.5 text-xs text-muted-foreground leading-relaxed space-y-1.5">
          <div className="flex items-center gap-1.5 text-cyan-600 dark:text-cyan-400 font-semibold">
            <ShieldCheckIcon className="size-3.5" />
            <span>独立外部服务桥接定位</span>
          </div>
          <p>
            本插件直接面向目标系统服务接口与专属 API 密钥对接，VK 仅作为官方展示、插件包托管与接入引导平台。
          </p>
        </div>
      ) : (
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
      )}

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
                onClick={() => handleCopy(bridge.antigravityAgentPrompt, '反重力一键认主提示词')}
              >
                <CopyIcon className="size-3" />
                复制提示词
              </Button>
            </div>
            <div className="rounded border border-border/60 bg-background/90 p-2 font-mono text-xs text-muted-foreground whitespace-pre-wrap select-all max-h-36 overflow-y-auto">
              {bridge.antigravityAgentPrompt}
            </div>

            <div className="pt-1 space-y-1">
              <div className="flex items-center justify-between text-xs text-muted-foreground font-medium">
                <span>手动终端执行命令:</span>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => handleCopy(bridge.antigravitySetupCmdWin, 'Windows 安装命令')}
                    className="hover:underline text-cyan-700 dark:text-cyan-400"
                  >
                    复制 Win 命令
                  </button>
                  <span>·</span>
                  <button
                    type="button"
                    onClick={() => handleCopy(bridge.antigravitySetupCmdUnix, 'Linux 安装命令')}
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
                onClick={() => handleCopy(bridge.dshAgentPrompt, 'DSH 一键认主提示词')}
              >
                <CopyIcon className="size-3" />
                复制提示词
              </Button>
            </div>
            <div className="rounded border border-border/60 bg-background/90 p-2 font-mono text-xs text-muted-foreground whitespace-pre-wrap select-all">
              {bridge.dshAgentPrompt}
            </div>

            <div className="space-y-1 pt-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground font-medium">NPM 安装直链:</span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-5 px-1.5 text-xs text-cyan-700 dark:text-cyan-400"
                  onClick={() => handleCopy(bridge.installCmd, 'NPM 安装命令')}
                >
                  复制
                </Button>
              </div>
              <div className="rounded border border-border/60 bg-background/80 p-2 font-mono text-xs text-foreground select-all">
                {bridge.installCmd}
              </div>
            </div>

            <div className="space-y-1 pt-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground font-medium">cordis.patch.yml 插件补丁片段:</span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-5 px-1.5 text-xs text-cyan-700 dark:text-cyan-400"
                  onClick={() => handleCopy(bridge.dshCordisPatchYaml, 'DSH 补丁配置')}
                >
                  复制 YAML
                </Button>
              </div>
              <pre className="rounded border border-border/60 bg-background/80 p-2 font-mono text-xs text-muted-foreground overflow-x-auto select-all">
                {bridge.dshCordisPatchYaml}
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
                onClick={() => handleCopy(bridge.universalAgentPrompt, '通用 MCP 认主提示词')}
              >
                <CopyIcon className="size-3" />
                复制提示词
              </Button>
            </div>
            <div className="rounded border border-border/60 bg-background/90 p-2 font-mono text-xs text-muted-foreground whitespace-pre-wrap select-all">
              {bridge.universalAgentPrompt}
            </div>

            <div className="space-y-1 pt-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground font-medium">mcp.json 客户端配置:</span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-5 px-1.5 text-xs text-cyan-700 dark:text-cyan-400"
                  onClick={() => handleCopy(bridge.universalMcpJson, 'MCP JSON 配置')}
                >
                  复制 JSON
                </Button>
              </div>
              <pre className="rounded border border-border/60 bg-background/80 p-2 font-mono text-xs text-muted-foreground overflow-x-auto select-all">
                {bridge.universalMcpJson}
              </pre>
            </div>
          </div>
        )}
      </div>

      <div className="flex items-center gap-1.5 pt-1 text-xs text-muted-foreground/80 font-mono">
        <ShieldCheckIcon className="size-3.5 text-cyan-500 shrink-0" />
        <span>原则：独立解耦，真实凭据。特权插件在调用时由服务端执行显式权限拦截。</span>
      </div>
    </div>
  )
}
