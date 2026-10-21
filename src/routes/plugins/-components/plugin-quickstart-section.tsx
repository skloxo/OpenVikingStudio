/**
 * plugin-quickstart-section.tsx
 * 插件极速开箱与客户端接入指引分段组件 (Card-215 解耦重构)。
 * 遵循 Cockpit UI 规范：NO GREEN EVER 🚫，字号 >= 12px，黄金甜点区 100~200 行。
 */

import * as React from 'react'
import {
  CheckIcon,
  CopyIcon,
  LaptopIcon,
  TerminalIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { copyTextToClipboard } from '#/lib/clipboard'
import type { QuadPluginItem } from '../-lib/plugin-types'

export type PluginQuickstartSectionProps = {
  plugin: QuadPluginItem
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

  const psCmd = `powershell -ExecutionPolicy Bypass -Command "iwr -Uri 'https://vk.tide.red/studio/${pid}.tgz' -OutFile '$env:TEMP\\${pid}.tgz'; New-Item -ItemType Directory -Force -Path \\"$env:USERPROFILE\\.gemini\\config\\plugins\\${pid}\\" | Out-Null; tar -xzf '$env:TEMP\\${pid}.tgz' -C \\"$env:USERPROFILE\\.gemini\\config\\plugins\\${pid}\\"; python \\"$env:USERPROFILE\\.gemini\\config\\plugins\\${pid}\\setup.py\\" --install"`
  const bashCmd = `curl -fsSL https://vk.tide.red/studio/${pid}.tgz -o /tmp/${pid}.tgz && mkdir -p ~/.gemini/config/plugins/${pid} && tar -xzf /tmp/${pid}.tgz -C ~/.gemini/config/plugins/${pid} && python3 ~/.gemini/config/plugins/${pid}/setup.py --install`
  const localCmd = `cd integrations/antigravity/${pid}\npython setup.py --install`
  const dshCmd = `npm install https://vk.tide.red/studio/dsh-plugin-${pid}.tgz`

  // 判定是否提供 DSH 桥接包支持
  const hasDshBridge = ['openviking-memory', 'openviking-ops', 'fleet-mesh', 'keepass-vault', 'dify', 'cpa-squad'].includes(pid)

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

      {/* 方式一：Windows PowerShell */}
      <div className="space-y-1.5 rounded-md border border-border/50 bg-card/40 p-3">
        <div className="flex items-center justify-between gap-2">
          <span className="font-semibold text-foreground text-xs flex items-center gap-1.5">
            <LaptopIcon className="size-3.5 text-muted-foreground" />
            方式一：Windows PowerShell (Antigravity 一键全自动)
          </span>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-xs font-mono gap-1 text-muted-foreground hover:text-foreground"
            onClick={() => handleCopy(psCmd, 'PowerShell 开箱')}
          >
            {copiedKey === 'PowerShell 开箱' ? (
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
        <pre className="rounded bg-muted/40 p-2 font-mono text-xs text-foreground/90 overflow-x-auto whitespace-pre-wrap break-all border border-border/40">
          {psCmd}
        </pre>
      </div>

      {/* 方式二：Linux / WSL2 */}
      <div className="space-y-1.5 rounded-md border border-border/50 bg-card/40 p-3">
        <div className="flex items-center justify-between gap-2">
          <span className="font-semibold text-foreground text-xs flex items-center gap-1.5">
            <TerminalIcon className="size-3.5 text-muted-foreground" />
            方式二：Linux / WSL2 (Antigravity 一键全自动)
          </span>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-xs font-mono gap-1 text-muted-foreground hover:text-foreground"
            onClick={() => handleCopy(bashCmd, 'Bash 开箱')}
          >
            {copiedKey === 'Bash 开箱' ? (
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
        <pre className="rounded bg-muted/40 p-2 font-mono text-xs text-foreground/90 overflow-x-auto whitespace-pre-wrap break-all border border-border/40">
          {bashCmd}
        </pre>
      </div>

      {/* 方式三：本地开发手动挂载 */}
      <div className="space-y-1.5 rounded-md border border-border/50 bg-card/40 p-3">
        <div className="flex items-center justify-between gap-2">
          <span className="font-semibold text-foreground text-xs">
            本地源码仓库自举挂载
          </span>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-xs font-mono gap-1 text-muted-foreground hover:text-foreground"
            onClick={() => handleCopy(localCmd, '本地挂载')}
          >
            {copiedKey === '本地挂载' ? (
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
        <pre className="rounded bg-muted/40 p-2 font-mono text-xs text-foreground/90 overflow-x-auto whitespace-pre-wrap border border-border/40">
          {localCmd}
        </pre>
      </div>

      {/* 方式四：DeepSeek Harness (Cordis 生态) */}
      {hasDshBridge && (
        <div className="rounded-md border border-border/40 bg-muted/10 p-3 space-y-1.5">
          <div className="flex items-center justify-between gap-2">
            <span className="text-muted-foreground text-xs">
              DeepSeek Harness (DSH / Cordis 客户端生态专用)
            </span>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs font-mono gap-1 text-muted-foreground hover:text-foreground"
              onClick={() => handleCopy(dshCmd, 'DSH NPM 安装')}
            >
              {copiedKey === 'DSH NPM 安装' ? (
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
          <pre className="rounded bg-muted/30 p-2 font-mono text-xs text-muted-foreground overflow-x-auto whitespace-pre-wrap break-all border border-border/30">
            {dshCmd}
          </pre>
        </div>
      )}
    </div>
  )
}
