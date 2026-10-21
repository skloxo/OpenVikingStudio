// @vitest-environment jsdom

import * as React from 'react'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { SetupIdentityDirectory } from './setup-identity-directory'

vi.mock('#/lib/admin', () => ({
  fetchAdminAccounts: vi.fn().mockResolvedValue([
    { accountId: 'default', userCount: 2 },
    { accountId: 'tenant-a', userCount: 1 },
  ]),
  fetchAdminUserDirectory: vi.fn().mockResolvedValue([
    { accountId: 'default', userId: 'admin', role: 'admin' },
    { accountId: 'default', userId: 'analyst', role: 'user' },
  ]),
}))

vi.mock('#/hooks/use-server-mode', () => ({
  fetchServerHealth: vi.fn().mockResolvedValue({
    mode: 'multi_user',
    admin_user: { account_id: 'default', user_id: 'admin' },
  }),
}))

describe('SetupIdentityDirectory', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('renders nothing when adminApiKey is empty', () => {
    const { container } = render(
      <SetupIdentityDirectory
        connection={{
          baseUrl: 'http://127.0.0.1:1933',
          apiKey: '',
          adminApiKey: '',
          accountId: 'default',
          userId: 'admin',
        }}
        onChange={vi.fn()}
      />,
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders directory picker when adminApiKey is present', async () => {
    render(
      <SetupIdentityDirectory
        connection={{
          baseUrl: 'http://127.0.0.1:1933',
          apiKey: '',
          adminApiKey: 'ov-admin-test-key',
          accountId: 'default',
          userId: 'admin',
        }}
        onChange={vi.fn()}
      />,
    )

    expect(
      screen.getByText(/受信任身份目录|Trusted Identity Directory/i),
    ).toBeTruthy()
    expect(screen.getByText(/RBAC Ready/i)).toBeTruthy()

    await waitFor(() => {
      expect(screen.getByText(/^Target Account$|^目标账户$/i)).toBeTruthy()
    })
  })

  it('strictly adheres to NO GREEN EVER rule and minimum 12px font size', () => {
    const { container } = render(
      <SetupIdentityDirectory
        connection={{
          baseUrl: 'http://127.0.0.1:1933',
          apiKey: '',
          adminApiKey: 'ov-admin-test-key',
          accountId: 'default',
          userId: 'admin',
        }}
        onChange={vi.fn()}
      />,
    )

    const html = container.innerHTML
    expect(html).not.toMatch(/text-emerald/i)
    expect(html).not.toMatch(/bg-emerald/i)
    expect(html).not.toMatch(/border-emerald/i)
    expect(html).not.toMatch(/text-green/i)
    expect(html).not.toMatch(/bg-green/i)
    expect(html).not.toMatch(/border-green/i)

    // 禁用 < 12px 微字
    expect(html).not.toMatch(/text-\[([0-9]|10|11)px\]/)
  })
})
