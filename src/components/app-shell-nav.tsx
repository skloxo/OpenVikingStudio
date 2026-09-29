import * as React from 'react'
import { Link } from '@tanstack/react-router'
import {
  BlocksIcon,
  BrainCircuitIcon,
  ChevronRightIcon,
  ClipboardListIcon,
  DnaIcon,
  HomeIcon,
  PlugZapIcon,
  ScrollTextIcon,
  Share2Icon,
  SparklesIcon,
} from 'lucide-react'
import type { useTranslation } from 'react-i18next'

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '#/components/ui/collapsible'
import {
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
} from '#/components/ui/sidebar'

export type NavItem = {
  icon: React.ComponentType
  id: string
  section: 'workspace' | 'operations' | 'settings'
  titleKey: string
  to: string
  children?: readonly NavSubItem[]
}

export type NavSubItem = {
  icon: React.ComponentType
  id: string
  titleKey: string
  to: string
}

export type NavGroupItemProps = {
  item: NavItem & { children: readonly NavSubItem[] }
  pathname: string
  title: string
  t: ReturnType<typeof useTranslation>['t']
}

export const NAV_ITEMS: readonly NavItem[] = [
  {
    icon: HomeIcon,
    id: 'home',
    section: 'workspace',
    titleKey: 'navigation.home.title',
    to: '/home',
  },
  {
    icon: PlugZapIcon,
    id: 'playground',
    section: 'workspace',
    titleKey: 'navigation.playground.title',
    to: '/playground',
  },
  {
    icon: BrainCircuitIcon,
    id: 'retrieval',
    section: 'workspace',
    titleKey: 'navigation.retrieval.title',
    to: '/retrieval',
  },
  {
    icon: DnaIcon,
    id: 'evolution',
    section: 'workspace',
    titleKey: 'navigation.evolution.title',
    to: '/evolution',
  },
  {
    icon: SparklesIcon,
    id: 'skills',
    section: 'workspace',
    titleKey: 'navigation.skills.title',
    to: '/skills',
  },
  {
    icon: Share2Icon,
    id: 'graph',
    section: 'workspace',
    titleKey: 'navigation.graph.title',
    to: '/graph',
  },
  {
    icon: BlocksIcon,
    id: 'sessions',
    section: 'workspace',
    titleKey: 'navigation.sessions.title',
    to: '/sessions',
  },
  {
    icon: ScrollTextIcon,
    id: 'requestLogs',
    section: 'operations',
    titleKey: 'navigation.requestLogs.title',
    to: '/request-logs',
  },
  {
    icon: ClipboardListIcon,
    id: 'tasks',
    section: 'operations',
    titleKey: 'navigation.tasks.title',
    to: '/tasks',
  },
]

export const NAV_SECTIONS = [
  { id: 'workspace', titleKey: 'sidebar.groups.workspace' },
  { id: 'operations', titleKey: 'sidebar.groups.operations' },
] as const

export function resolveLanguage(
  rawLanguage: string | undefined,
): 'zh-CN' | 'en' {
  if (!rawLanguage) {
    return 'zh-CN'
  }
  return rawLanguage.toLowerCase().startsWith('zh') ? 'zh-CN' : 'en'
}

export function NavGroupItem({ item, pathname, title, t }: NavGroupItemProps) {
  const isGroupActive =
    pathname === item.to ||
    pathname.startsWith(`${item.to}/`) ||
    item.children.some(
      (child) =>
        pathname === child.to || pathname.startsWith(`${child.to}/`),
    )
  const Icon = item.icon

  return (
    <Collapsible
      key={item.id}
      defaultOpen={isGroupActive}
      className="group/collapsible"
    >
      <SidebarMenuItem>
        <CollapsibleTrigger
          render={
            <SidebarMenuButton
              isActive={isGroupActive}
              tooltip={title}
              className="h-9"
            >
              <Icon />
              <span>{title}</span>
              <ChevronRightIcon className="ml-auto transition-transform duration-200 group-data-open/collapsible:rotate-90" />
            </SidebarMenuButton>
          }
        />
        <CollapsibleContent>
          <SidebarMenuSub>
            {item.children.map((child) => {
              const ChildIcon = child.icon
              const childActive =
                pathname === child.to ||
                (child.to !== item.to && pathname.startsWith(`${child.to}/`))
              const childTitle = t(child.titleKey, { ns: 'appShell' })

              return (
                <SidebarMenuSubItem key={child.id}>
                  <SidebarMenuSubButton
                    render={<Link to={child.to} />}
                    isActive={childActive}
                  >
                    <ChildIcon />
                    <span>{childTitle}</span>
                  </SidebarMenuSubButton>
                </SidebarMenuSubItem>
              )
            })}
          </SidebarMenuSub>
        </CollapsibleContent>
      </SidebarMenuItem>
    </Collapsible>
  )
}
