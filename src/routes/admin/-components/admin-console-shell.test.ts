import { describe, expect, it } from 'vitest'

import { NAV_ITEMS } from '#/components/app-shell-nav'
import { isAdminWorkspacePath } from './admin-console-shell'

describe('Admin console consolidation and sidebar pruning', () => {
  it('excludes /graph from primary workspace navigation', () => {
    expect(NAV_ITEMS.some((item) => item.id === 'graph' || item.to === '/graph')).toBe(
      false,
    )
    expect(NAV_ITEMS.some((item) => item.id === 'arranger' && item.to === '/arranger')).toBe(
      true,
    )
  })

  it('treats /admin, /users, /accounts, and /settings as admin console routes', () => {
    expect(isAdminWorkspacePath('/admin')).toBe(true)
    expect(isAdminWorkspacePath('/admin/configuration/server')).toBe(true)
    expect(isAdminWorkspacePath('/users')).toBe(true)
    expect(isAdminWorkspacePath('/accounts')).toBe(true)
    expect(isAdminWorkspacePath('/settings')).toBe(true)
    expect(isAdminWorkspacePath('/sessions')).toBe(false)
    expect(isAdminWorkspacePath('/compile')).toBe(false)
  })
})
