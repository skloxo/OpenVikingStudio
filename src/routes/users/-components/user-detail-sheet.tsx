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


import {
  BoxesIcon,
  BotIcon,
  ExternalLinkIcon,
  GlobeIcon,
  KeyIcon,
  LayersIcon,
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
import type { AdminUser } from '#/lib/admin'
import { UserOverviewCard } from './user-overview-card'

export type UserDetailSheetProps = {
  user: AdminUser | null
  open: boolean
  onOpenChange: (open: boolean) => void
  currentUserId?: string
  onRegenerateKey?: (user: AdminUser) => void
  onOpenPluginDrawer?: (user: AdminUser) => void
}

export function UserDetailSheet({
  user,
  open,
  onOpenChange,
  currentUserId,
  onRegenerateKey,
  onOpenPluginDrawer,
}: UserDetailSheetProps) {
  const userId = user?.userId || 'default'
  const isCurrentIdentity = currentUserId === userId

  const handleOpenPluginDrawer = () => {
    if (user && onOpenPluginDrawer) {
      onOpenChange(false)
      onOpenPluginDrawer(user)
    }
  }

  // 官方标杆生态插件概览
  const officialPlugins = [
    {
      id: 'openviking-memory',
      name: 'OpenViking 核心记忆',
      version: 'v2.0.11',
      icon: <BotIcon className="size-4 text-cyan-600 dark:text-cyan-400" />,
      desc: '体外大脑语义向量检索、AST 代码感知与长程经验沉淀 (官方平台底座)',
      meta: '58 工具 · 3 Hook',
    },
    {
      id: 'network-search',
      name: '联网搜索与采集网关',
      version: 'v1.0.0',
      icon: <GlobeIcon className="size-4 text-cyan-600 dark:text-cyan-400" />,
      desc: '26-Key 多源轮询，支持原生标准 API (免装插件) 与定制插件双模态',
      meta: '12 工具 · 双模态',
    },
    {
      id: 'keepass-vault',
      name: 'KeePass 凭据保险箱',
      version: 'v1.0.0',
      icon: <KeyIcon className="size-4 text-cyan-600 dark:text-cyan-400" />,
      desc: '全集群凭据保险箱，本地 KDBX 零泄漏读取，与 VK 零运行时依赖',
      meta: '8 工具 · 零依赖',
    },
  ]

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
            管理当前用户的角色权限、安全密钥与插件能力装配。智能体与人类平权共享用户体系。
          </SheetDescription>
        </SheetHeader>

        {/* 区域 1：用户基础凭据网格 */}
        <UserOverviewCard
          user={user}
          isCurrentIdentity={isCurrentIdentity}
          onRegenerateKey={onRegenerateKey}
        />

        {/* 区域 2：插件装配与能力概览 */}
        <div className="flex flex-1 flex-col gap-3 border-t border-border/60 pt-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="rounded border border-border/60 bg-muted/60 p-1 text-cyan-500">
                <BoxesIcon className="size-3.5" />
              </div>
              <span className="font-semibold text-foreground/90 text-xs">
                插件与能力装配概览 (已就绪 3 项标杆插件)
              </span>
            </div>

            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-6.5 gap-1 border-cyan-500/40 bg-cyan-500/10 px-2.5 font-mono text-xs text-cyan-700 hover:bg-cyan-500/20 active:bg-cyan-500/30 dark:border-cyan-500/50 dark:bg-cyan-950/40 dark:text-cyan-300 dark:hover:bg-cyan-900/50"
              onClick={handleOpenPluginDrawer}
            >
              <ExternalLinkIcon className="size-3" />
              打开插件装配座舱 ➔
            </Button>
          </div>

          <div className="space-y-2">
            {officialPlugins.map((plugin) => (
              <div
                key={plugin.id}
                onClick={handleOpenPluginDrawer}
                className="group flex cursor-pointer flex-col justify-between gap-1.5 rounded-md border border-border/70 bg-muted/20 p-2.5 transition-all hover:border-cyan-500/60 hover:bg-muted/40 hover:shadow-xs"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <div className="p-1 rounded bg-background/80 border border-border/40 shrink-0">
                      {plugin.icon}
                    </div>
                    <span className="font-semibold text-foreground text-xs group-hover:text-cyan-500 transition-colors">
                      {plugin.name}
                    </span>
                    <span className="font-mono text-xs text-muted-foreground">
                      {plugin.version}
                    </span>
                  </div>

                  <Badge
                    variant="outline"
                    className="font-mono text-xs border-cyan-500/30 text-cyan-600 dark:text-cyan-400 bg-cyan-950/10"
                  >
                    {plugin.meta}
                  </Badge>
                </div>

                <p className="text-xs text-muted-foreground leading-relaxed">
                  {plugin.desc}
                </p>
              </div>
            ))}
          </div>

          <div className="mt-auto rounded-md border border-border/60 bg-muted/20 p-2.5 text-xs text-muted-foreground flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <LayersIcon className="size-3.5 text-cyan-500" />
              可通过插件装配座舱配置细粒度 MCP 工具可选、Hook 守卫开关及 NPM 安装包。
            </span>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
