/**
 * use-app-connection.tsx
 * OpenViking 控制台服务端连接、多租户身份切换与运行时鉴权 Provider 及 Hook。
 * 遵循 Agent 编码规范与黄金甜点区（<= 500 行，目标 300 行）。
 */
import * as React from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate, useRouterState } from '@tanstack/react-router'

import { ovClient } from '#/lib/ov-client'

import {
  AUTH_PROMPT_SUPPRESSION_MS,
  applyConnection,
  createConnectionHealthHeaders,
  createConnectionRoleProbeKey,
  createIdentityScopeKey,
  createManagementAccountConnection,
  detectConnectionIdentity,
  normalizeConnectionDraft,
  persistConnection,
  readInitialConnection,
  resolveConnectionRoleProbeState,
  resolveInitialApiKey,
  resolveSwitchedIdentity,
  shouldRedirectToLoginOnApiError,
  synchronizeConnectionRuntime,
  synchronizeResolvedDataIdentity,
} from './app-connection-utils'
import type {
  AppConnectionContextValue,
  ConnectionDraft,
  ConnectionIdentitySummary,
  ConnectionRole,
  GeneratedCredential,
} from './app-connection-types'
import { detectServerMode } from './use-server-mode'
import type { ServerMode } from './use-server-mode'

// Re-export types and utilities for backward compatibility
export type {
  AppConnectionContextValue,
  ConnectionDraft,
  ConnectionIdentitySummary,
  ConnectionRole,
  GeneratedCredential,
}
export {
  createConnectionRoleProbeKey,
  createIdentityScopeKey,
  createManagementAccountConnection,
  resolveConnectionRoleProbeState,
  resolveInitialApiKey,
  resolveSwitchedIdentity,
  shouldRedirectToLoginOnApiError,
  synchronizeConnectionRuntime,
  synchronizeResolvedDataIdentity,
}

const AppConnectionContext =
  React.createContext<AppConnectionContextValue | null>(null)

export function summarizeConnectionIdentity(
  connection: ConnectionDraft,
  serverMode: ServerMode,
): ConnectionIdentitySummary {
  if (serverMode === 'dev') {
    return { labelKey: 'identitySummary.dev' }
  }

  const segments = [connection.accountId, connection.userId].filter(Boolean)
  if (!segments.length) {
    return { labelKey: 'identitySummary.unset' }
  }

  return {
    labelKey: 'identitySummary.named',
    values: {
      identity: segments.join(' / '),
    },
  }
}

export function useAppConnection(): AppConnectionContextValue {
  const context = React.useContext(AppConnectionContext)
  if (!context) {
    throw new Error(
      'useAppConnection must be used within AppConnectionProvider.',
    )
  }
  return context
}

export function AppConnectionProvider({
  children,
}: {
  children: React.ReactNode
}) {
  const queryClient = useQueryClient()
  const authPromptSuppressedUntilRef = React.useRef(0)
  const navigate = useNavigate()
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  })
  const initialConnectionRef = React.useRef<ConnectionDraft | null>(null)
  const synchronizedRoleProbeRef = React.useRef<{
    key: string
    role: ConnectionRole
  } | null>(null)

  if (initialConnectionRef.current === null) {
    initialConnectionRef.current = readInitialConnection()
    applyConnection(initialConnectionRef.current, 'checking')
  }

  const [connection, setConnection] = React.useState<ConnectionDraft>(
    initialConnectionRef.current,
  )
  const [connectionRole, setConnectionRole] =
    React.useState<ConnectionRole>('unknown')
  const [isConnectionRoleLoading, setConnectionRoleLoading] = React.useState(
    () =>
      Boolean(
        initialConnectionRef.current?.baseUrl &&
        (initialConnectionRef.current.adminApiKey ||
          initialConnectionRef.current.apiKey),
      ),
  )
  const [serverMode, setServerMode] = React.useState<ServerMode>('checking')
  const [generatedCredential, setGeneratedCredential] =
    React.useState<GeneratedCredential | null>(null)

  const openConnectionSettings = React.useCallback(() => {
    if (pathname !== '/settings') {
      void navigate({ to: '/settings' })
    }
  }, [navigate, pathname])

  React.useEffect(() => {
    applyConnection(connection, serverMode)
    persistConnection(connection)
  }, [connection, serverMode])

  React.useEffect(() => {
    let cancelled = false

    setServerMode('checking')
    void detectServerMode(
      connection.baseUrl,
      createConnectionHealthHeaders(connection),
    ).then((mode) => {
      if (!cancelled) {
        setServerMode(mode)
      }
    })

    return () => {
      cancelled = true
    }
  }, [
    connection.accountId,
    connection.adminApiKey,
    connection.apiKey,
    connection.baseUrl,
    connection.userId,
  ])

  React.useEffect(() => {
    let cancelled = false
    const isCancelled = () => cancelled
    const apiKey = connection.adminApiKey || connection.apiKey
    const roleProbe = resolveConnectionRoleProbeState({
      apiKey,
      baseUrl: connection.baseUrl,
      serverMode,
    })
    const probeKey = createConnectionRoleProbeKey(connection, serverMode)
    const synchronizedProbe = synchronizedRoleProbeRef.current

    if (synchronizedProbe?.key === probeKey) {
      synchronizedRoleProbeRef.current = null
      setConnectionRole(synchronizedProbe.role)
      setConnectionRoleLoading(false)
      return () => {
        cancelled = true
      }
    }

    setConnectionRole(roleProbe.role)
    setConnectionRoleLoading(roleProbe.isLoading)
    if (!roleProbe.shouldProbe) {
      return () => {
        cancelled = true
      }
    }

    void detectConnectionIdentity(connection)
      .then(async (controlIdentity) => {
        if (isCancelled()) return

        const dataIdentity =
          connection.apiKey &&
          (controlIdentity.role === 'root' ||
            (controlIdentity.role === 'admin' &&
              controlIdentity.accountId === connection.accountId))
            ? await detectConnectionIdentity(connection, 'data')
            : !connection.adminApiKey
              ? controlIdentity
              : null
        if (isCancelled()) return

        const { accountId, role } = controlIdentity
        const dataConnection = dataIdentity
          ? synchronizeResolvedDataIdentity(connection, dataIdentity)
          : null
        if (dataConnection) {
          const next = synchronizeConnectionRuntime(dataConnection, serverMode)
          synchronizedRoleProbeRef.current = {
            key: createConnectionRoleProbeKey(next, serverMode),
            role,
          }
          queryClient.clear()
          setConnection(next)
          return
        }

        if (
          role === 'admin' &&
          accountId &&
          connection.accountId !== accountId
        ) {
          const next = synchronizeConnectionRuntime(
            { ...connection, accountId },
            serverMode,
          )
          synchronizedRoleProbeRef.current = {
            key: createConnectionRoleProbeKey(next, serverMode),
            role,
          }
          queryClient.clear()
          setConnection(next)
          return
        }
        setConnectionRole(role)
        setConnectionRoleLoading(false)
      })
      .catch(() => {
        if (!cancelled) {
          setConnectionRole('unknown')
          setConnectionRoleLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [
    connection.accountId,
    connection.adminApiKey,
    connection.apiKey,
    connection.baseUrl,
    connection.userId,
    queryClient,
    serverMode,
  ])

  React.useEffect(() => {
    const interceptorId = ovClient.instance.interceptors.response.use(
      (response) => response,
      (error) => {
        return Promise.reject(error)
      },
    )

    return () => {
      ovClient.instance.interceptors.response.eject(interceptorId)
    }
  }, [])

  const value = React.useMemo<AppConnectionContextValue>(() => {
    const commitConnection = (next: ConnectionDraft) => {
      authPromptSuppressedUntilRef.current =
        Date.now() + AUTH_PROMPT_SUPPRESSION_MS
      const normalized = synchronizeConnectionRuntime(next, serverMode)
      queryClient.clear()
      setConnection(normalized)
    }

    return {
      clearGeneratedCredential: () => setGeneratedCredential(null),
      connection,
      connectionRole,
      generatedCredential,
      identityScopeKey: createIdentityScopeKey(connection, serverMode),
      isConnectionRoleLoading,
      openConnectionSettings,
      saveConnection: commitConnection,
      setGeneratedCredential,
      serverMode,
      switchIdentity: async ({
        accountId,
        allowLegacyIdentityFallback,
        apiKey,
        userId,
      }) => {
        if (serverMode === 'dev' || serverMode === 'checking') {
          throw new Error(
            'The current server mode does not support identity switching.',
          )
        }

        const requested = normalizeConnectionDraft({
          ...connection,
          accountId,
          apiKey: serverMode === 'trusted' ? '' : apiKey,
          userId,
        })
        const identity = await detectConnectionIdentity(requested, 'data')
        const resolvedIdentity = resolveSwitchedIdentity(
          requested,
          identity,
          allowLegacyIdentityFallback,
        )
        if (!resolvedIdentity) {
          throw new Error(
            'The selected credential does not match the target account and user.',
          )
        }

        if (pathname === '/playground') {
          await navigate({
            replace: true,
            search: { upload: false },
            to: '/playground',
          })
        }
        commitConnection({
          ...requested,
          ...resolvedIdentity,
        })
      },
      switchManagementAccount: async (accountId) => {
        if (connectionRole !== 'root') {
          throw new Error(
            'Only a validated Root credential can switch management accounts.',
          )
        }
        commitConnection(
          createManagementAccountConnection(connection, accountId),
        )
      },
    }
  }, [
    connection,
    connectionRole,
    generatedCredential,
    isConnectionRoleLoading,
    navigate,
    openConnectionSettings,
    pathname,
    queryClient,
    serverMode,
  ])

  return (
    <AppConnectionContext.Provider value={value}>
      {children}
    </AppConnectionContext.Provider>
  )
}
