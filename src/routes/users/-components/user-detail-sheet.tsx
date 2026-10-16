/**
 * user-detail-sheet.tsx
 * 用户详情与专属凭据管理右侧抽屉面板 (User Detail Control Panel).
 *
 * 核心设计哲学 (第一性原理)：
 * 1. 人机平权 (User ≡ Agent)：用户即系统接入实体，彻底切除“在册智能体”历史残留；
 * 2. 用户抽屉聚焦：用户凭据、安全密钥、角色归属与插件装配概览；
 * 3. 极速联动：提供「打开插件装配座舱 ➔」直通按键，秒级调出三大标杆插件配置；
 * 4. 严守 NO GREEN EVER 🚫、>= 12px 字体下限与 100~300 行黄金甜点区。
 */


import { Link } from '@tanstack/react-router'
import {
  BoxesIcon,
  ExternalLinkIcon,
  ShieldCheckIcon,
} from 'lucide-react'

import { Badge } from '#/components/ui/badge'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '#/components/ui/sheet'
import type { AdminUser } from '#/lib/admin'
import { UserOverviewCard } from './user-overview-card'

export type UserDetailSheetProps = {
  user: AdminUser | null
  open: boolean
  onOpenChange: (open: boolean) => void
  currentUserId?: string
  onRegenerateKey?: (user: AdminUser) => void
}

export function UserDetailSheet({
  user,
  open,
  onOpenChange,
  currentUserId,
  onRegenerateKey,
}: UserDetailSheetProps) {
  const userId = user?.userId || 'default'
  const isCurrentIdentity = currentUserId === userId

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="flex w-full flex-col gap-4 overflow-y-auto border-l border-border bg-card p-6 font-sans text-xs data-[side=right]:sm:max-w-155 data-[side=right]:lg:max-w-180"
      >
        <SheetHeader className="space-y-1 border-b border-border/70 pb-3">
          <div className="flex items-center gap-2">
            <SheetTitle className="text-sm font-semibold tracking-tight text-foreground">
              用户详情与安全座舱
            </SheetTitle>
            <Badge variant="outline" className="font-mono text-xs">
              {userId}
            </Badge>
            {isCurrentIdentity && (
              <Badge className="border-cyan-500/30 bg-cyan-500/10 text-xs text-cyan-600 dark:text-cyan-400">
                当前使用身份
              </Badge>
            )}
          </div>
          <SheetDescription className="text-xs text-muted-foreground">
            管理当前用户的空间角色与专属 User API Key 凭据。人机平权统一接入。
          </SheetDescription>
        </SheetHeader>

        {/* 区域 1：用户基础凭据网格 */}
        <UserOverviewCard
          user={user}
          isCurrentIdentity={isCurrentIdentity}
          onRegenerateKey={onRegenerateKey}
        />

        {/* 区域 2：能力接入指南指引卡片 */}
        <div className="flex flex-1 flex-col justify-between gap-3 border-t border-border/60 pt-3">
          <div className="rounded-md border border-border/60 bg-muted/20 p-3 space-y-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="rounded border border-border/60 bg-muted/60 p-1 text-cyan-500">
                  <BoxesIcon className="size-3.5" />
                </div>
                <span className="font-semibold text-foreground/90 text-xs">
                  全集群插件与能力连接
                </span>
              </div>
            </div>

            <p className="text-xs text-muted-foreground leading-relaxed">
              本用户的专属 <code className="font-mono text-foreground font-medium">User API Key</code> 可直接用于授权外部智能体（DSH、Antigravity、Cursor 等）接入 Wiki 原生能力插件。
              全集群所有能力插件（核心记忆、系统运维、联网搜索、KeePass、Dify、CPA 算力等）已统一收拢至「插件中心」，可前往获取对应插件的接口地址、NPM 安装包直链及 MCP 客户端配置模板。
            </p>

            <div className="pt-1">
              <Link
                to="/plugins"
                onClick={() => onOpenChange(false)}
                className="inline-flex h-7 items-center gap-1.5 rounded-md border border-cyan-500/40 bg-cyan-500/10 px-2.5 font-mono text-xs text-cyan-700 hover:bg-cyan-500/20 active:bg-cyan-500/30 dark:border-cyan-500/50 dark:bg-cyan-950/40 dark:text-cyan-300 dark:hover:bg-cyan-900/50 transition-colors"
              >
                <ExternalLinkIcon className="size-3" />
                前往插件中心查看与安装能力 ➔
              </Link>
            </div>
          </div>

          <div className="mt-auto rounded-md border border-border/50 bg-muted/10 p-2.5 text-xs text-muted-foreground/80 flex items-center gap-1.5 font-mono">
            <ShieldCheckIcon className="size-3.5 text-cyan-500 shrink-0" />
            <span>原则：A 就是 A，Key 对了就能用。敏感特权插件在调用时由服务端执行显式校验。</span>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
