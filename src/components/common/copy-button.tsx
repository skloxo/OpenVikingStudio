import { useState, useCallback } from 'react'
import { CheckIcon, CopyIcon } from 'lucide-react'
import { Button } from '#/components/ui/button'
import { copyTextToClipboard } from '#/lib/clipboard'
import { cn } from '#/lib/utils'

export interface CopyButtonProps {
  value: string
  label?: string
  showIcon?: boolean
  size?: 'default' | 'sm' | 'xs' | 'icon'
  variant?: 'default' | 'secondary' | 'outline' | 'ghost' | 'link'
  className?: string
  timeout?: number
  onCopied?: () => void
  'aria-label'?: string
}

export function CopyButton({
  value,
  label,
  showIcon = true,
  size = 'xs',
  variant = 'ghost',
  className,
  timeout = 2000,
  onCopied,
  'aria-label': ariaLabel,
}: CopyButtonProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = useCallback(
    async (e: React.MouseEvent) => {
      e.stopPropagation()
      try {
        await copyTextToClipboard(value)
        setCopied(true)
        onCopied?.()
        setTimeout(() => setCopied(false), timeout)
      } catch (err) {
        console.error('Failed to copy to clipboard:', err)
      }
    },
    [value, timeout, onCopied],
  )

  return (
    <Button
      aria-label={ariaLabel || (copied ? 'Copied' : label || 'Copy to clipboard')}
      className={cn(
        'transition-colors select-none',
        copied
          ? 'text-cyan-600 dark:text-cyan-400 font-medium'
          : 'text-muted-foreground hover:text-foreground',
        className,
      )}
      onClick={handleCopy}
      size={size}
      type="button"
      variant={variant}
    >
      {showIcon &&
        (copied ? (
          <CheckIcon className="size-3.5 shrink-0" />
        ) : (
          <CopyIcon className="size-3.5 shrink-0" />
        ))}
      {label && <span>{copied ? '已复制' : label}</span>}
    </Button>
  )
}
