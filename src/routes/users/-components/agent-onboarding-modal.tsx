/**
 * agent-onboarding-modal.tsx
 * 智能体专属接入引导与安全防泄露右侧抽屉 (Sheet / Drawer).
 * 遵循 Agent 编码规范与黄金甜点区 (<= 250 行)，严守 NO GREEN EVER 🚫 与 >= 12px 规范。
 */
import * as React from 'react'
import {
  CheckIcon,
  CopyIcon,
  CpuIcon,
  GlobeIcon,
  KeyRoundIcon,
  LaptopIcon,
  ShieldAlertIcon,
  TerminalIcon,
} from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '#/components/ui/sheet'
import { copyTextToClipboard } from '#/lib/clipboard'
import type { CreateAgentResponse } from '#/lib/admin'

export type AgentOnboardingModalProps = {
  data: CreateAgentResponse | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function AgentOnboardingModal({
  data,
  open,
  onOpenChange,
}: AgentOnboardingModalProps) {
  const [activeTab, setActiveTab] = React.useState<'mcp' | 'prompt' | 'url'>('mcp')
  const [copiedKey, setCopiedKey] = React.useState<string | null>(null)

  if (!data) return null

  const { agent, bootstrap } = data
  const isLocal = agent.connection_mode === 'realtimeApi' || bootstrap.topology === 'local'
  const mcpJsonStr = JSON.stringify(bootstrap.mcp_config, null, 2)

  const handleCopy = (text: string, key: string) => {
    copyTextToClipboard(text)
    setCopiedKey(key)
    setTimeout(() => setCopiedKey(null), 2000)
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-xl md:max-w-2xl overflow-y-auto flex flex-col gap-4 font-sans p-6"
      >
        <SheetHeader className="pb-3 border-b border-border/70">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-md bg-muted border border-border text-cyan-500">
              <CpuIcon className="size-5" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <SheetTitle className="text-base font-semibold tracking-tight truncate">
                  接入指南：{agent.agent_id}
                </SheetTitle>
                <Badge
                  variant="outline"
                  className={`text-[12px] h-5 px-1.5 shrink-0 font-medium ${
                    isLocal
                      ? 'border-cyan-500/30 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400'
                      : 'border-muted-foreground/30 bg-muted text-muted-foreground'
                  }`}
                >
                  {isLocal ? (
                    <>
                      <LaptopIcon className="size-3 mr-1" />
                      本地直连
                    </>
                  ) : (
                    <>
                      <GlobeIcon className="size-3 mr-1" />
                      网络远程
                    </>
                  )}
                </Badge>
              </div>
              <SheetDescription className="text-xs text-muted-foreground mt-1">
                已在用户 <span className="font-mono text-foreground font-medium">{agent.user_id}</span> 名下签发专属身份牌。复制以下针对性配置即可秒级接入。
              </SheetDescription>
            </div>
          </div>
        </SheetHeader>

        {/* 拓扑针对性指引 */}
        {isLocal ? (
          <div className="flex items-start gap-2.5 p-3 rounded-md bg-cyan-500/10 border border-cyan-500/30 text-xs">
            <LaptopIcon className="size-4 shrink-0 mt-0.5 text-cyan-600 dark:text-cyan-400" />
            <div>
              <span className="font-semibold text-cyan-700 dark:text-cyan-300">本地宿主直连模式：</span>
              <span className="text-muted-foreground"> 该智能体与 OpenViking 运行于同一物理主机或 WSL 环境，直接监听 </span>
              <code className="px-1 py-0.5 rounded bg-muted border border-border font-mono text-[12px] text-foreground">
                http://127.0.0.1:1933/mcp
              </code>
              <span className="text-muted-foreground">，零外网延迟，无需公网反向代理。</span>
            </div>
          </div>
        ) : (
          <div className="flex items-start gap-2.5 p-3 rounded-md bg-amber-500/10 border border-amber-500/30 text-xs">
            <ShieldAlertIcon className="size-4 shrink-0 mt-0.5 text-amber-600 dark:text-amber-400" />
            <div>
              <span className="font-semibold text-amber-700 dark:text-amber-300">网络远程安全防线：</span>
              <span className="text-muted-foreground"> 远程节点通过反代网关接入，配置中密钥采用 </span>
              <code className="px-1 py-0.5 rounded bg-muted border border-border text-cyan-600 dark:text-cyan-400 font-mono text-[12px]">
                ${'{OPENVIKING_API_KEY}'}
              </code>
              <span className="text-muted-foreground"> 占位符，由客户端本地环境变量注入，绝对禁止在公开 Git 仓库中硬编码明文密钥！</span>
            </div>
          </div>
        )}

        {/* 顶部 Tab 切换 */}
        <div className="flex items-center gap-1.5 border-b border-border pb-2 mt-1">
          <Button
            size="sm"
            variant={activeTab === 'mcp' ? 'secondary' : 'ghost'}
            className="text-xs h-7 px-3"
            onClick={() => setActiveTab('mcp')}
          >
            <TerminalIcon className="size-3.5 mr-1.5" />
            Cursor / VSCode (mcp.json)
          </Button>
          <Button
            size="sm"
            variant={activeTab === 'prompt' ? 'secondary' : 'ghost'}
            className="text-xs h-7 px-3"
            onClick={() => setActiveTab('prompt')}
          >
            <KeyRoundIcon className="size-3.5 mr-1.5" />
            专属认主指令 (System Prompt)
          </Button>
          <Button
            size="sm"
            variant={activeTab === 'url' ? 'secondary' : 'ghost'}
            className="text-xs h-7 px-3"
            onClick={() => setActiveTab('url')}
          >
            MCP 服务端点
          </Button>
        </div>

        {/* Tab 内容区 */}
        <div className="space-y-3 mt-1">
          {activeTab === 'mcp' && (
            <div className="space-y-2">
              <div className="flex justify-between items-center text-xs text-muted-foreground">
                <span>粘贴至 .cursor/mcp.json 或 claude_desktop_config.json：</span>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-6 px-2 text-xs"
                  onClick={() => handleCopy(mcpJsonStr, 'mcp')}
                >
                  {copiedKey === 'mcp' ? (
                    <>
                      <CheckIcon className="size-3.5 mr-1 text-cyan-500" />
                      已复制
                    </>
                  ) : (
                    <>
                      <CopyIcon className="size-3.5 mr-1 text-muted-foreground" />
                      复制 JSON
                    </>
                  )}
                </Button>
              </div>
              <pre className="p-3 rounded-md bg-muted/60 border border-border text-xs font-mono text-foreground overflow-x-auto leading-relaxed">
                {mcpJsonStr}
              </pre>
            </div>
          )}

          {activeTab === 'prompt' && (
            <div className="space-y-2">
              <div className="flex justify-between items-center text-xs text-muted-foreground">
                <span>提供给新 Agent 放入 AGENTS.md 或 System Prompt：</span>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-6 px-2 text-xs"
                  onClick={() => handleCopy(bootstrap.system_prompt, 'prompt')}
                >
                  {copiedKey === 'prompt' ? (
                    <>
                      <CheckIcon className="size-3.5 mr-1 text-cyan-500" />
                      已复制
                    </>
                  ) : (
                    <>
                      <CopyIcon className="size-3.5 mr-1 text-muted-foreground" />
                      复制指令
                    </>
                  )}
                </Button>
              </div>
              <pre className="p-3 rounded-md bg-muted/60 border border-border text-xs font-sans text-foreground overflow-x-auto whitespace-pre-wrap leading-relaxed">
                {bootstrap.system_prompt}
              </pre>
            </div>
          )}

          {activeTab === 'url' && (
            <div className="space-y-2">
              <div className="flex justify-between items-center text-xs text-muted-foreground">
                <span>标准 HTTP/SSE MCP 服务端点：</span>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-6 px-2 text-xs"
                  onClick={() => handleCopy(bootstrap.remote_mcp_url, 'url')}
                >
                  {copiedKey === 'url' ? (
                    <>
                      <CheckIcon className="size-3.5 mr-1 text-cyan-500" />
                      已复制
                    </>
                  ) : (
                    <>
                      <CopyIcon className="size-3.5 mr-1 text-muted-foreground" />
                      复制 URL
                    </>
                  )}
                </Button>
              </div>
              <div className="p-3 rounded-md bg-muted/60 border border-border text-xs font-mono text-foreground break-all leading-relaxed">
                {bootstrap.remote_mcp_url}
              </div>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
