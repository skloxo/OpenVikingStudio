/**
 * agent-onboarding-modal.tsx
 * 智能体专属接入引导与安全防泄露配置弹窗 (Card-114 / v1.7.68).
 * 遵循 Agent 编码规范与黄金甜点区 (<= 250 行)，严守 NO GREEN EVER 🚫 与 >= 12px 规范。
 */
import * as React from 'react'
import {
  CheckIcon,
  CopyIcon,
  CpuIcon,
  KeyRoundIcon,
  ShieldAlertIcon,
  TerminalIcon,
} from 'lucide-react'
import { Button } from '#/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '#/components/ui/dialog'
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
  const mcpJsonStr = JSON.stringify(bootstrap.mcp_config, null, 2)

  const handleCopy = (text: string, key: string) => {
    copyTextToClipboard(text)
    setCopiedKey(key)
    setTimeout(() => setCopiedKey(null), 2000)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl bg-zinc-950 border-zinc-800 text-zinc-100 p-6">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-md bg-zinc-900 border border-zinc-800 text-cyan-400">
              <CpuIcon className="size-5" />
            </div>
            <div>
              <DialogTitle className="text-base font-semibold text-zinc-100">
                智能体接入就绪：{agent.agent_id}
              </DialogTitle>
              <DialogDescription className="text-xs text-zinc-400 mt-1">
                已在用户 <span className="font-mono text-zinc-200">{agent.user_id}</span> 名下签发专属身份牌，复制以下配置即可接入。
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {/* 芒格逆向安全警示 */}
        <div className="flex items-start gap-2.5 p-3 rounded-md bg-amber-950/20 border border-amber-800/40 text-amber-300 text-xs mt-1">
          <ShieldAlertIcon className="size-4 shrink-0 mt-0.5 text-amber-400" />
          <div>
            <span className="font-semibold">芒格安全防线：</span>
            <span> 配置中密钥采用 </span>
            <code className="px-1 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-cyan-300 font-mono text-[12px]">
              ${'{OPENVIKING_API_KEY}'}
            </code>
            <span> 占位符，请由客户端本地环境变量注入，绝对禁止在公开 Git 仓库中硬编码明文密钥！</span>
          </div>
        </div>

        {/* 顶部 Tab 切换 */}
        <div className="flex items-center gap-1.5 border-b border-zinc-800 pb-2 mt-2">
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
            远程 MCP URL
          </Button>
        </div>

        {/* Tab 内容区 */}
        <div className="relative mt-2">
          {activeTab === 'mcp' && (
            <div>
              <div className="flex justify-between items-center mb-1.5 text-xs text-zinc-400">
                <span>粘贴至 .cursor/mcp.json 或 claude_desktop_config.json：</span>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-6 px-2 text-xs border-zinc-700 bg-zinc-900 hover:bg-zinc-800 text-zinc-200"
                  onClick={() => handleCopy(mcpJsonStr, 'mcp')}
                >
                  {copiedKey === 'mcp' ? (
                    <>
                      <CheckIcon className="size-3.5 mr-1 text-cyan-400" />
                      已复制
                    </>
                  ) : (
                    <>
                      <CopyIcon className="size-3.5 mr-1 text-zinc-400" />
                      复制 JSON
                    </>
                  )}
                </Button>
              </div>
              <pre className="p-3 rounded-md bg-zinc-900/90 border border-zinc-800 text-xs font-mono text-zinc-300 overflow-x-auto max-h-48 leading-relaxed">
                {mcpJsonStr}
              </pre>
            </div>
          )}

          {activeTab === 'prompt' && (
            <div>
              <div className="flex justify-between items-center mb-1.5 text-xs text-zinc-400">
                <span>提供给新 Agent 放入 AGENTS.md 或 System Prompt：</span>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-6 px-2 text-xs border-zinc-700 bg-zinc-900 hover:bg-zinc-800 text-zinc-200"
                  onClick={() => handleCopy(bootstrap.system_prompt, 'prompt')}
                >
                  {copiedKey === 'prompt' ? (
                    <>
                      <CheckIcon className="size-3.5 mr-1 text-cyan-400" />
                      已复制
                    </>
                  ) : (
                    <>
                      <CopyIcon className="size-3.5 mr-1 text-zinc-400" />
                      复制指令
                    </>
                  )}
                </Button>
              </div>
              <pre className="p-3 rounded-md bg-zinc-900/90 border border-zinc-800 text-xs font-sans text-zinc-300 overflow-x-auto max-h-48 whitespace-pre-wrap leading-relaxed">
                {bootstrap.system_prompt}
              </pre>
            </div>
          )}

          {activeTab === 'url' && (
            <div>
              <div className="flex justify-between items-center mb-1.5 text-xs text-zinc-400">
                <span>标准远程 HTTP/SSE MCP 服务端点：</span>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-6 px-2 text-xs border-zinc-700 bg-zinc-900 hover:bg-zinc-800 text-zinc-200"
                  onClick={() => handleCopy(bootstrap.remote_mcp_url, 'url')}
                >
                  {copiedKey === 'url' ? (
                    <>
                      <CheckIcon className="size-3.5 mr-1 text-cyan-400" />
                      已复制
                    </>
                  ) : (
                    <>
                      <CopyIcon className="size-3.5 mr-1 text-zinc-400" />
                      复制 URL
                    </>
                  )}
                </Button>
              </div>
              <div className="p-3 rounded-md bg-zinc-900/90 border border-zinc-800 text-xs font-mono text-zinc-300 break-all leading-relaxed">
                {bootstrap.remote_mcp_url}
              </div>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 mt-4 pt-3 border-t border-zinc-800">
          <Button
            size="sm"
            variant="secondary"
            className="text-xs h-8 px-4"
            onClick={() => onOpenChange(false)}
          >
            完成并关闭
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
