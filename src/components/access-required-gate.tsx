import * as React from 'react'
import { Link } from '@tanstack/react-router'
import { ShieldAlertIcon, PlugZapIcon } from 'lucide-react'
import { Button } from '#/components/ui/button'

type AccessRequiredGateProps = {
  description?: string
  title?: string
}

export function AccessRequiredGate({
  description = '当前 OpenViking 公网服务已开启独立 API Key 安全防护隔离。请前往【连接设置】填入合法的 Root 或 User API Key 以解锁面板与数据通信。',
  title = '🔒 需要配置 API Key 授权验证',
}: AccessRequiredGateProps) {
  return (
    <div className="flex min-h-[420px] w-full flex-col items-center justify-center gap-4 rounded-xl border border-destructive/20 bg-muted/20 px-6 py-12 text-center shadow-xs">
      <div className="flex size-14 items-center justify-center rounded-2xl border border-destructive/30 bg-destructive/10 text-destructive shadow-inner">
        <ShieldAlertIcon className="size-7" />
      </div>
      <div className="max-w-md">
        <h3 className="text-lg font-semibold tracking-tight text-foreground">{title}</h3>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{description}</p>
      </div>
      <div className="mt-2 flex items-center gap-3">
        <Link to="/settings">
          <Button variant="default" size="sm" className="gap-2">
            <PlugZapIcon className="size-4" />
            <span>前往连接设置 (Go to Settings)</span>
          </Button>
        </Link>
      </div>
    </div>
  )
}
