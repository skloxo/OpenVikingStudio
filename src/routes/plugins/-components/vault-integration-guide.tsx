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
      <div className="rounded border border-border/60 bg-muted/20 p-2.5 text-xs text-muted-foreground leading-relaxed space-y-1">
        <div className="flex items-center gap-1.5 text-cyan-600 dark:text-cyan-400 font-semibold">
          <ShieldCheckIcon className="size-3.5" />
          <span>本地化私有凭据定位 · 云端零密码托管声明</span>
        </div>
        <p>
          本插件定位为<strong className="text-foreground">纯本地化私有插件</strong>。OpenViking (VK) 仅作为官方展厅展示曝光与 NPM 安装包托管下载中枢，<strong className="text-foreground">绝非从云端获取或集中托管密码保险库</strong>！
        </p>
        <p className="text-foreground/90 font-medium">
          ⚠️ 智能体安装后，必须由用户在本地客户端配置中指定自身本地机器上的 <code className="text-cyan-600 dark:text-cyan-400 font-mono">.kdbx</code> 数据文件物理绝对路径与主密码环境变量。
        </p>
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
            <span className="text-muted-foreground">本地 KDBX 物理路径示例</span>
            <Button
              variant="ghost"
              size="sm"
              className="h-5 px-1 text-xs"
              onClick={() => handleCopy(defaultPath, 'KDBX路径')}
            >
              复制
            </Button>
          </div>
          <div className="font-mono text-foreground font-medium text-xs truncate" title="Linux/Mac: ~/.openviking/vault.kdbx | Windows: C:/Users/YourName/.openviking/vault.kdbx">
            {defaultPath}
          </div>
          <div className="text-xs text-muted-foreground truncate">
            Windows: C:/Users/YourName/.openviking/vault.kdbx
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
          <div className="text-xs text-muted-foreground truncate">
            在本地 Shell 或操作系统环境变量中配置
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
          <span>本地私有凭据保障契约：</span>
        </div>
        <div>• 智能体客户端直接在本地执行 keepassxc-cli 解密，密码数据 100% 留存本地，永不上云。</div>
        <div>• 智能体客户端支持热重载，修改本地 .kdbx 路径或凭据后免重启即刻生效。</div>
        <div>• 任何增删改凭据操作前，底层强制自动生成 *.bak 灾备物理快照，防止误操作。</div>
      </div>
    </div>
  )
}
