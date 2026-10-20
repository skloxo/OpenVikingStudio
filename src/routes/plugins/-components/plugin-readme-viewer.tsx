/**
 * plugin-readme-viewer.tsx
 * 插件原生 Markdown 文档渲染器 (Cockpit UI 规范)。
 * 
 * 核心设计哲学 (与 Google Antigravity 插件详情页 100% 互通):
 * 1. 【一源两端】：直接渲染插件根目录下的 README.md，两端展现完全一致；
 * 2. 【脱水极简】：提供优雅的代码块渲染与右上角一键复制按钮；
 * 3. 【视觉门禁】：NO GREEN EVER 🚫，字号硬下限 >= 12px (text-xs)，6px 微圆角；
 * 4. 【单文件黄金甜点区】：<= 200 行。
 */

import * as React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkBreaks from 'remark-breaks'
import { CheckIcon, CopyIcon } from 'lucide-react'
import { Button } from '#/components/ui/button'

export type PluginReadmeViewerProps = {
  content?: string
  fallbackDescription?: string
}

function CodeBlock({ children, className }: { children: React.ReactNode; className?: string }) {
  const [copied, setCopied] = React.useState(false)
  const text = String(children).replace(/\n$/, '')
  const language = className ? className.replace('language-', '') : ''

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // 容错降级
    }
  }

  return (
    <div className="relative group my-3 rounded-md border border-border/60 bg-muted/30 overflow-hidden font-mono text-xs">
      <div className="flex items-center justify-between border-b border-border/40 bg-muted/50 px-3 py-1.5 text-xs text-muted-foreground">
        <span>{language || 'text'}</span>
        <Button
          variant="ghost"
          size="icon"
          className="size-6 text-muted-foreground hover:text-cyan-500 hover:bg-cyan-500/10"
          onClick={handleCopy}
          title="复制命令"
        >
          {copied ? <CheckIcon className="size-3 text-cyan-500" /> : <CopyIcon className="size-3" />}
        </Button>
      </div>
      <pre className="p-3 overflow-x-auto text-xs leading-relaxed text-foreground select-text font-mono">
        <code>{text}</code>
      </pre>
    </div>
  )
}

export function PluginReadmeViewer({ content, fallbackDescription }: PluginReadmeViewerProps) {
  if (!content) {
    return (
      <div className="rounded-md border border-border/60 bg-card/40 p-4 text-xs text-muted-foreground space-y-2">
        <p className="font-semibold text-foreground">暂无专属 README 文档</p>
        <p className="leading-relaxed">{fallbackDescription || '该插件尚未托管详细说明文档。'}</p>
      </div>
    )
  }

  return (
    <div className="plugin-markdown-root font-sans text-xs text-foreground leading-relaxed space-y-3">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks]}
        components={{
          h1: ({ children }) => (
            <h1 className="text-base font-bold text-foreground border-b border-border/40 pb-2 mb-3 tracking-tight">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-sm font-semibold text-foreground mt-4 mb-2 flex items-center gap-1.5 tracking-tight">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-xs font-semibold text-foreground mt-3 mb-1.5">{children}</h3>
          ),
          p: ({ children }) => <p className="text-xs leading-relaxed my-2 text-foreground/90">{children}</p>,
          ul: ({ children }) => <ul className="list-disc list-inside space-y-1 my-2 pl-1">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal list-inside space-y-1 my-2 pl-1">{children}</ol>,
          li: ({ children }) => <li className="text-xs text-foreground/90 leading-relaxed">{children}</li>,
          hr: () => <hr className="my-3 border-border/50" />,
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-cyan-500/50 bg-cyan-500/5 px-3 py-1.5 my-2 text-xs text-muted-foreground italic rounded-r">
              {children}
            </blockquote>
          ),
          code: ({ inline, className, children, ...props }: any) => {
            if (inline) {
              return (
                <code
                  className="rounded bg-muted/60 px-1 py-0.5 font-mono text-xs text-cyan-600 dark:text-cyan-400 border border-border/40"
                  {...props}
                >
                  {children}
                </code>
              )
            }
            return <CodeBlock className={className}>{children}</CodeBlock>
          },
          table: ({ children }) => (
            <div className="overflow-x-auto my-3 rounded border border-border/50">
              <table className="w-full border-collapse text-xs text-left">{children}</table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border-b border-border/50 bg-muted/40 px-3 py-2 font-semibold text-foreground">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border-b border-border/30 px-3 py-2 text-foreground/80">{children}</td>
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noreferrer"
              className="text-cyan-600 hover:text-cyan-500 dark:text-cyan-400 underline underline-offset-2"
            >
              {children}
            </a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
