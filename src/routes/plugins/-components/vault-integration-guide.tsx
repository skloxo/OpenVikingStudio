/**
 * vault-integration-guide.tsx
 * KeePass 独立凭据保险箱接入与配置指引组件 (Cockpit UI 规范)。
 *
 * 核心设计哲学 (第一性原理)：
 * 1. 零后端依赖：与 OpenViking 服务端零运行时强依赖，纯本地执行，VK 仅作为官方展厅与托管下载中枢；
 * 2. 查库第一公理：外呼鉴权前查库，高熵密码落盘，严禁向人类索要明文密码；
 * 3. 极速安装与热更新：托管 npm 直链下载，本地 .kdbx 零泄漏安全挂载；
 * 4. 严守 Cockpit UI 视觉规范：NO GREEN EVER 🚫，字号 >= 12px (text-xs)。
 */

import * as React from 'react'
import {
  CheckIcon,
  CopyIcon,
  KeyIcon,
  RefreshCwIcon,
  ShieldCheckIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { copyTextToClipboard } from '#/lib/clipboard'

export function VaultIntegrationGuide() {
  const [copiedKey, setCopiedKey] = React.useState<string | null>(null)

  const installCmd = 'npm install https://vk.tide.red/studio/dsh-plugin-keepass-vault.tgz'
  const defaultPath = '~/.openviking/vault.kdbx'
  const defaultEnv = 'KEEPASS_VAULT_PASSWORD'

  const cordisYamlSnippet = `plugins:
  'dsh-plugin-keepass-vault':
    kdbxPath: '~/.openviking/vault.kdbx'
    passwordEnv: 'KEEPASS_VAULT_PASSWORD'
    autoSnapshot: true`

  const handleCopy = async (text: string, label: string) => {
    try {
      await copyTextToClipboard(text)
      setCopiedKey(label)
      toast.success(`${label} 已复制到剪贴板`)
      setTimeout(() => setCopiedKey(null), 2000)
    } catch {
      toast.error('复制失败，请手动选择复制')
    }
  }

  return (
    <div className="space-y-3 rounded-md border border-border/70 bg-card/40 p-3 font-sans text-xs">
      <div className="flex items-center justify-between border-b border-border/40 pb-2">
        <div className="flex items-center gap-2">
          <KeyIcon className="size-4 text-cyan-500" />
          <span className="font-semibold text-foreground text-xs">
            KeePass 凭据保险箱客户端配置 (零后端依赖)
          </span>
        </div>
        <Badge variant="outline" className="text-xs border-cyan-500/30 text-cyan-600 dark:text-cyan-400">
          本地 KDBX 零泄漏
        </Badge>
      </div>

      {/* 架构解耦物理说明 */}
      <div className="rounded border border-border/60 bg-muted/20 p-2.5 text-xs text-muted-foreground leading-relaxed">
        <strong className="text-foreground">💡 架构解耦契约：</strong>
        本插件与 OpenViking 服务端<strong className="text-foreground">无实质功能依赖与运行时绑定</strong>。OpenViking 仅作为官方展厅展示曝光、统一版本发布与托管下载渠道。智能体客户端直接在本地挂载并读取加密保险箱文件。
      </div>

      {/* 1. 托管安装命令 */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-xs">
          <span className="font-medium text-muted-foreground">客户端 NPM 安装命令 (VK 服务端托管源)</span>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground gap-1"
            onClick={() => handleCopy(installCmd, '安装命令')}
          >
            {copiedKey === '安装命令' ? (
              <CheckIcon className="size-3 text-cyan-400" />
            ) : (
              <CopyIcon className="size-3" />
            )}
            复制
          </Button>
        </div>
        <div className="rounded border border-border/60 bg-background/80 p-2 font-mono text-xs text-foreground select-all">
          {installCmd}
        </div>
      </div>

      {/* 2. 本地保险箱文件与密码环境变量 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
        <div className="space-y-1 rounded border border-border/50 bg-card/30 p-2.5">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">本地 KDBX 文件路径</span>
            <Button
              variant="ghost"
              size="sm"
              className="h-5 px-1 text-xs"
              onClick={() => handleCopy(defaultPath, 'KDBX路径')}
            >
              复制
            </Button>
          </div>
          <div className="font-mono text-foreground font-medium text-xs truncate">
            {defaultPath}
          </div>
        </div>

        <div className="space-y-1 rounded border border-border/50 bg-card/30 p-2.5">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">主密码环境变量名</span>
            <Button
              variant="ghost"
              size="sm"
              className="h-5 px-1 text-xs"
              onClick={() => handleCopy(defaultEnv, '密码环境变量')}
            >
              复制
            </Button>
          </div>
          <div className="font-mono text-foreground font-medium text-xs truncate">
            {defaultEnv}
          </div>
        </div>
      </div>

      {/* 3. DSH / Cordis 配置补丁 */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-xs">
          <span className="font-medium text-muted-foreground">DSH / Cordis 配置片段 (cordis.yml)</span>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-1.5 text-xs text-muted-foreground hover:text-foreground gap-1"
            onClick={() => handleCopy(cordisYamlSnippet, '配置片段')}
          >
            {copiedKey === '配置片段' ? (
              <CheckIcon className="size-3 text-cyan-400" />
            ) : (
              <CopyIcon className="size-3" />
            )}
            复制配置
          </Button>
        </div>
        <pre className="rounded border border-border/60 bg-background/80 p-2 font-mono text-xs text-foreground overflow-x-auto leading-relaxed">
          {cordisYamlSnippet}
        </pre>
      </div>

      {/* 4. 刷新热更新与查库守卫 */}
      <div className="rounded border border-border/40 bg-muted/10 p-2 text-xs text-muted-foreground space-y-1">
        <div className="flex items-center gap-1.5 text-foreground font-medium">
          <RefreshCwIcon className="size-3 text-cyan-500" />
          <span>支持热重载与刷新：</span>
        </div>
        <div>• 智能体客户端支持热更新刷新插件，更新后自动重连本地凭据存储。</div>
        <div>• 任何增删改凭据操作前，底层强制自动生成 *.bak 灾备物理快照。</div>
      </div>
    </div>
  )
}
