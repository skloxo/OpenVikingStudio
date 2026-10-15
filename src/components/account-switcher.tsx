import {
  Building2Icon,
  CheckIcon,
  ChevronDownIcon,
  LoaderCircleIcon,
  PlusIcon,
  SearchIcon,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '#/components/ui/popover'
import { cn } from '#/lib/utils'
import {
  selectAccountUser,
  useAccountSwitcher,
} from './use-account-switcher'
import {
  CreateAccountDialog,
  ManualSwitchDialog,
} from './account-switcher-dialogs'

export { selectAccountUser }

export function AccountSwitcher() {
  const { t } = useTranslation('accountSwitcher')
  const {
    connection,
    canManageAccounts,
    accountLabel,
    open,
    setOpen,
    createOpen,
    setCreateOpen,
    search,
    setSearch,
    switchingAccountId,
    setSwitchingAccountId,
    manualSwitch,
    setManualSwitch,
    createDraft,
    setCreateDraft,
    accountsQuery,
    filteredAccounts,
    selectAccount,
    createAccount,
    switchIdentity,
    switchManagementAccount,
  } = useAccountSwitcher()

  if (!canManageAccounts) {
    return (
      <div
        className="flex h-10 min-w-0 flex-1 items-center gap-2 rounded-lg px-2 text-left group-data-[collapsible=icon]:size-9 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0"
        title={accountLabel}
      >
        <span className="flex size-7 shrink-0 items-center justify-center rounded-md border border-sidebar-border bg-sidebar-accent/50">
          <Building2Icon className="size-4" />
        </span>
        <span className="min-w-0 flex-1 truncate text-sm font-semibold group-data-[collapsible=icon]:hidden">
          {accountLabel}
        </span>
      </div>
    )
  }

  return (
    <>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger className="flex h-10 min-w-0 flex-1 items-center gap-2 rounded-lg px-2 text-left outline-none transition-colors hover:bg-sidebar-accent focus-visible:ring-2 focus-visible:ring-sidebar-ring group-data-[collapsible=icon]:size-9 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0">
          <span className="flex size-7 shrink-0 items-center justify-center rounded-md border border-sidebar-border bg-sidebar-accent/50">
            <Building2Icon className="size-4" />
          </span>
          <span className="min-w-0 flex-1 truncate text-sm font-semibold group-data-[collapsible=icon]:hidden">
            {accountLabel}
          </span>
          <ChevronDownIcon className="size-4 shrink-0 text-muted-foreground group-data-[collapsible=icon]:hidden" />
        </PopoverTrigger>
        <PopoverContent
          side="bottom"
          align="start"
          sideOffset={6}
          className="w-64 gap-0 p-0"
        >
          <div className="border-b p-2">
            <div className="relative">
              <SearchIcon className="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder={t('searchPlaceholder')}
                className="h-8 pl-8 text-sm"
              />
            </div>
          </div>
          <div className="max-h-60 overflow-y-auto p-1.5">
            {accountsQuery.isLoading ? (
              <div className="flex items-center justify-center gap-2 px-2.5 py-6 text-sm text-muted-foreground">
                <LoaderCircleIcon className="size-3.5 animate-spin" />
                {t('loading')}
              </div>
            ) : accountsQuery.isError ? (
              <div className="grid gap-1 px-2.5 py-5 text-center">
                <p className="text-sm font-medium text-destructive">
                  {t('errors.loadAccounts')}
                </p>
                <p className="line-clamp-2 text-xs text-muted-foreground">
                  {accountsQuery.error instanceof Error
                    ? accountsQuery.error.message
                    : String(accountsQuery.error)}
                </p>
              </div>
            ) : filteredAccounts.length === 0 ? (
              <p className="px-2.5 py-6 text-center text-sm text-muted-foreground">
                {t('empty')}
              </p>
            ) : (
              filteredAccounts.map((account) => {
                const active = account.accountId === connection.accountId
                const switching = switchingAccountId === account.accountId
                return (
                  <button
                    key={account.accountId}
                    type="button"
                    disabled={Boolean(switchingAccountId)}
                    onClick={() => void selectAccount(account.accountId)}
                    className={cn(
                      'flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left transition-colors hover:bg-accent disabled:cursor-wait disabled:opacity-60',
                      active && 'bg-accent/70',
                    )}
                  >
                    <span className="flex size-7 shrink-0 items-center justify-center rounded-md border bg-background">
                      <Building2Icon className="size-3.5" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium">
                        {account.accountId}
                      </span>
                      <span className="block text-xs text-muted-foreground">
                        {t('memberCount', { count: account.userCount })}
                      </span>
                    </span>
                    {switching ? (
                      <LoaderCircleIcon className="size-3.5 animate-spin" />
                    ) : active ? (
                      <CheckIcon className="size-3.5 text-primary" />
                    ) : null}
                  </button>
                )
              })
            )}
          </div>
          <div className="border-t p-1.5">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="w-full justify-start px-2.5"
              onClick={() => {
                setOpen(false)
                setCreateOpen(true)
              }}
            >
              <PlusIcon />
              {t('create')}
            </Button>
          </div>
        </PopoverContent>
      </Popover>

      <ManualSwitchDialog
        manualSwitch={manualSwitch}
        onManualSwitchChange={setManualSwitch}
        switchingAccountId={switchingAccountId}
        onSwitchingAccountIdChange={setSwitchingAccountId}
        switchIdentity={switchIdentity}
        switchManagementAccount={switchManagementAccount}
      />

      <CreateAccountDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        createDraft={createDraft}
        onCreateDraftChange={setCreateDraft}
        createAccountMutation={createAccount}
      />
    </>
  )
}
