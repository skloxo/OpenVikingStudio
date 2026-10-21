/**
 * plugin-prompts-section.tsx
 * 建议交互提示词构件 (1:1 对齐反重力原生 Suggested Prompts 体验)。
 * 
 * 遵循法典与 UI 规范:
 * 1. NO GREEN EVER 🚫;
 * 2. 字号硬下限 >= 12px (text-xs);
 * 3. 单击即复制，毫秒级 toast 反馈与图标状态切换;
 * 4. 黄金甜点区 50~100 行。
 */

import * as React from 'react'
import { CheckIcon, CopyIcon, SparklesIcon } from 'lucide-react'
import { toast } from 'sonner'
import { copyTextToClipboard } from '#/lib/clipboard'

export type PluginPromptsSectionProps = {
  prompts: string[]
}

export function PluginPromptsSection({ prompts }: PluginPromptsSectionProps) {
  const [copiedIndex, setCopiedIndex] = React.useState<number | null>(null)

  if (!prompts || prompts.length === 0) return null

  const handleCopy = async (prompt: string, idx: number) => {
    try {
      await copyTextToClipboard(prompt)
      setCopiedIndex(idx)
      toast.success('提示词已复制到剪贴板')
      setTimeout(() => setCopiedIndex(null), 2000)
    } catch {
      toast.error('复制失败，请手动选择')
    }
  }

  return (
    <div className="space-y-2 rounded-md border border-cyan-500/30 bg-cyan-500/5 p-3 text-xs">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 font-semibold text-foreground">
          <SparklesIcon className="size-3.5 text-cyan-600 dark:text-cyan-400" />
          <span>建议交互提示词 (点击复制)</span>
        </div>
        <span className="font-mono text-muted-foreground text-xs">
          {prompts.length} 条场景提示词
        </span>
      </div>

      <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2 pt-1">
        {prompts.map((prompt, idx) => {
          const isCopied = copiedIndex === idx
          return (
            <button
              key={idx}
              type="button"
              onClick={() => handleCopy(prompt, idx)}
              className="group flex items-center justify-between gap-2 rounded-md border border-border/50 bg-card/60 p-2 text-left font-sans text-xs text-foreground/90 transition-all hover:border-cyan-500/50 hover:bg-card/90 hover:text-cyan-700 dark:hover:text-cyan-300"
            >
              <span className="line-clamp-2 leading-relaxed">
                💬 {prompt}
              </span>
              <span className="shrink-0 text-muted-foreground transition-colors group-hover:text-cyan-600 dark:group-hover:text-cyan-400">
                {isCopied ? (
                  <CheckIcon className="size-3.5 text-cyan-500" />
                ) : (
                  <CopyIcon className="size-3.5 opacity-60 group-hover:opacity-100" />
                )}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
