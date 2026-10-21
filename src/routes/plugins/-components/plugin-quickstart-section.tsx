/**
 * plugin-quickstart-section.tsx
 * 插件极速开箱与客户端接入指引分段组件 (Card-215 解耦重构)。
 * 遵循 Cockpit UI 规范：NO GREEN EVER 🚫，字号 >= 12px，黄金甜点区 100~200 行。
 */

import * as React from 'react'
import {
  BoxesIcon,
  CheckIcon,
  CopyIcon,
  LaptopIcon,
  TerminalIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { copyTextToClipboard } from '#/lib/clipboard'
import type {
  DshPackageMapping,
  DshPluginBridgeInfo,
  QuadPluginItem,
  QuickstartCommandItem,
} from '../-lib/plugin-types'

export type PluginQuickstartSectionProps = {
  plugin: QuadPluginItem
}

/**
 * DSH (DeepSeek Harness) 专用 NPM 桥接包映射 (与 integrations/deepseek-harness package.json 对齐)
 * 遵循 SSOT 原则：版本默认动态继承自当前插件真实版本，杜绝硬编码滞后漂移。
 */
const DSH_BRIDGE_REGISTRY: Record<string, { pkg: string; ver?: string }> = {
  'openviking-memory': { pkg: 'dsh-plugin-openviking-memory' },
  'openviking-ops': { pkg: 'dsh-plugin-openviking-ops' },
  'fleet-mesh': { pkg: 'dsh-plugin-openviking-fleet', ver: '1.0.3' },
  'keepass-vault': { pkg: 'dsh-plugin-keepass-vault', ver: '1.0.2' },
  'cpa-squad': { pkg: 'dsh-plugin-cpa', ver: '1.0.1' },
  'dify': { pkg: 'dsh-plugin-dify', ver: '1.0.1' },
  'agent-circuit-breaker': { pkg: 'agent-circuit-breaker', ver: '1.3.3' },
}

export function PluginQuickstartSection({ plugin }: PluginQuickstartSectionProps) {
  const [copiedKey, setCopiedKey] = React.useState<string | null>(null)
  const pid = plugin.plugin_id

  const handleCopy = async (text: string, label: string) => {
    try {
      await copyTextToClipboard(text)
      setCopiedKey(label)
      toast.success(`${label} 命令已复制`)
      setTimeout(() => setCopiedKey(null), 2000)
    } catch {
      toast.error('复制失败，请手动选择复制')
    }
  }

  const version = plugin.version || '1.0.0'
  const agTarball = `${pid}-${version}.tgz`

  // DSH 专用桥接包版本对齐 (SSOT: 动态直连当前插件真实版本)
  const registeredDsh = DSH_BRIDGE_REGISTRY[pid]
  const dshInfo: DshPluginBridgeInfo = registeredDsh
    ? { pkg: registeredDsh.pkg, ver: version || registeredDsh.ver || '1.0.0' }
    : { pkg: `dsh-plugin-${pid}`, ver: version }
  const effectiveDshVer = dshInfo.ver
  const dshTarball = `${dshInfo.pkg}-${effectiveDshVer}.tgz`

  // 强类型命令配置列表 (数据驱动统一渲染)
  const commands: QuickstartCommandItem[] = [
    {
      id: 'powershell',
      title: '方式一：Windows PowerShell (Antigravity 一键全自动)',
      command: `powershell -ExecutionPolicy Bypass -Command "iwr -Uri 'https://vk.tide.red/studio/${agTarball}' -OutFile '$env:TEMP\\${pid}.tgz'; New-Item -ItemType Directory -Force -Path \\"$env:USERPROFILE\\.gemini\\config\\plugins\\${pid}\\" | Out-Null; tar -xzf '$env:TEMP\\${pid}.tgz' -C \\"$env:USERPROFILE\\.gemini\\config\\plugins\\${pid}\\"; python \\"$env:USERPROFILE\\.gemini\\config\\plugins\\${pid}\\setup.py\\" --install"`,
      copyLabel: 'PowerShell 开箱',
      iconType: 'laptop',
    },
    {
      id: 'bash',
      title: '方式二：Linux / WSL2 (Antigravity 一键全自动)',
      command: `curl -fsSL https://vk.tide.red/studio/${agTarball} -o /tmp/${pid}.tgz && mkdir -p ~/.gemini/config/plugins/${pid} && tar -xzf /tmp/${pid}.tgz -C ~/.gemini/config/plugins/${pid} && python3 ~/.gemini/config/plugins/${pid}/setup.py --install`,
      copyLabel: 'Bash 开箱',
      iconType: 'terminal',
    },
    {
      id: 'local',
      title: '本地源码仓库自举挂载',
      command: `cd integrations/antigravity/${pid}\npython setup.py --install`,
      copyLabel: '本地挂载',
      iconType: 'terminal',
    },
  ]

  if (['openviking-memory', 'openviking-ops', 'fleet-mesh', 'keepass-vault', 'dify', 'cpa-squad'].includes(pid)) {
    commands.push({
      id: 'dsh',
      title: 'DeepSeek Harness (DSH / Cordis 客户端生态专用)',
      command: `npm install https://vk.tide.red/studio/${dshTarball}`,
      copyLabel: 'DSH NPM 安装',
      iconType: 'cube',
      badge: `v${effectiveDshVer}`,
    })
  }

  return (
    <div className="space-y-3 font-sans text-xs">
      <div className="flex items-center justify-between border-b border-border/40 pb-2">
        <h4 className="flex items-center gap-1.5 font-semibold text-foreground">
          <TerminalIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
          全自动开箱与客户端接入命令
        </h4>
        <Badge variant="outline" className="text-xs font-mono border-border/60">
          开箱即用
        </Badge>
      </div>

      {commands.map((item) => (
        <div
          key={item.id}
          className={`space-y-1.5 rounded-md border p-3 ${
            item.id === 'dsh'
              ? 'border-border/40 bg-muted/10'
              : 'border-border/50 bg-card/40'
          }`}
        >
          <div className="flex items-center justify-between gap-2">
            <span
              className={`font-semibold text-xs flex items-center gap-1.5 ${
                item.id === 'dsh' ? 'text-muted-foreground' : 'text-foreground'
              }`}
            >
              {item.iconType === 'laptop' ? (
                <LaptopIcon className="size-3.5 text-muted-foreground" />
              ) : item.iconType === 'cube' ? (
                <BoxesIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
              ) : (
                <TerminalIcon className="size-3.5 text-muted-foreground" />
              )}
              <span>{item.title}</span>
              {item.badge && (
                <Badge variant="outline" className="text-xs font-mono px-1.5 py-0 border-cyan-500/30 text-cyan-600 dark:text-cyan-400">
                  {item.badge}
                </Badge>
              )}
            </span>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs font-mono gap-1 text-muted-foreground hover:text-foreground"
              onClick={() => handleCopy(item.command, item.copyLabel)}
            >
              {copiedKey === item.copyLabel ? (
                <>
                  <CheckIcon className="size-3 text-cyan-500" />
                  <span>已复制</span>
                </>
              ) : (
                <>
                  <CopyIcon className="size-3" />
                  <span>复制</span>
                </>
              )}
            </Button>
          </div>
          <pre
            className={`rounded p-2 font-mono text-xs overflow-x-auto whitespace-pre-wrap break-all border ${
              item.id === 'dsh'
                ? 'bg-muted/30 text-muted-foreground border-border/30'
                : 'bg-muted/40 text-foreground/90 border border-border/40'
            }`}
          >
            {item.command}
          </pre>
        </div>
      ))}
    </div>
  )
}
