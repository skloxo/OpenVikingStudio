import { createFileRoute, Link } from '@tanstack/react-router'
import {
  ArrowRightIcon,
  BotIcon,
  BoxesIcon,
  FileCode2Icon,
  ServerCogIcon,
  SlidersHorizontalIcon,
  UsersIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from '#/components/ui/card'

export const Route = createFileRoute('/admin/')({
  component: AdminOverviewPage,
})

function AdminOverviewPage() {
  const { t } = useTranslation('adminConsole')

  const cards = [
    {
      to: '/admin/configuration/server' as const,
      icon: ServerCogIcon,
      title: t('overview.serverCardTitle'),
      desc: t('overview.serverCardDesc'),
    },
    {
      to: '/admin/configuration' as const,
      icon: SlidersHorizontalIcon,
      title: t('overview.accountCardTitle'),
      desc: t('overview.accountCardDesc'),
    },
    {
      to: '/admin/users/memory-templates' as const,
      icon: FileCode2Icon,
      title: t('overview.templatesCardTitle'),
      desc: t('overview.templatesCardDesc'),
    },
    {
      to: '/admin/users/groups' as const,
      icon: UsersIcon,
      title: t('overview.groupsCardTitle'),
      desc: t('overview.groupsCardDesc'),
    },
    {
      to: '/admin/vikingbot' as const,
      icon: BotIcon,
      title: t('overview.botCardTitle'),
      desc: t('overview.botCardDesc'),
    },
    {
      to: '/plugins' as const,
      icon: BoxesIcon,
      title: t('overview.workspaceCardTitle'),
      desc: t('overview.workspaceCardDesc'),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h2 className="text-lg font-semibold">{t('overview.title')}</h2>
        <p className="text-sm text-muted-foreground">
          {t('overview.description')}
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {cards.map((card) => {
          const Icon = card.icon
          return (
            <Link key={card.to} to={card.to} className="group block">
              <Card className="h-full transition-colors group-hover:border-cyan-500/40">
                <CardHeader className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex size-9 items-center justify-center rounded-lg bg-cyan-500/10 text-cyan-500">
                      <Icon className="size-4" />
                    </div>
                    <ArrowRightIcon className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-cyan-500" />
                  </div>
                  <CardTitle className="text-base">{card.title}</CardTitle>
                  <CardDescription className="text-xs leading-relaxed">
                    {card.desc}
                  </CardDescription>
                </CardHeader>
              </Card>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
